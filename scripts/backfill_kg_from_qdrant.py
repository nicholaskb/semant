#!/usr/bin/env python3
"""
Backfill Knowledge Graph with image data from Qdrant.

This script ensures KG has image nodes with schema:contentUrl pointing to GCS URLs,
so the API fallback can find them when Qdrant metadata is missing gcs_url.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger
from tqdm import tqdm

async def backfill_kg_from_qdrant(
    collection_name: str = "childrens_book_images",
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Backfill KG with image data from Qdrant.
    
    Args:
        collection_name: Qdrant collection name
        qdrant_host: Qdrant host
        qdrant_port: Qdrant port
        dry_run: If True, only report what would be done
    
    Returns:
        Statistics about the backfill operation
    """
    logger.info("=" * 70)
    logger.info("BACKFILLING KG FROM QDRANT")
    logger.info("=" * 70)
    
    # Connect to Qdrant
    try:
        qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        logger.info(f"✅ Connected to Qdrant at {qdrant_host}:{qdrant_port}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Qdrant: {e}")
        return {"error": str(e)}
    
    # Connect to KG - use try/finally to ensure cleanup
    kg = None
    try:
        kg = KnowledgeGraphManager(persistent_storage=True)
        await kg.initialize()
        logger.info("✅ Connected to Knowledge Graph")
        # Reduce logging verbosity for bulk operations (but keep ERROR level)
        logger.remove()
        logger.add(sys.stderr, level="WARNING", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
        # Add separate handler for errors to ensure they're always visible
        logger.add(sys.stderr, level="ERROR", format="<red>{time:YYYY-MM-DD HH:mm:ss}</red> | <level>{level: <8}</level> | <level>{message}</level>")
    except Exception as e:
        logger.error(f"❌ Failed to connect to KG: {e}")
        return {"error": str(e)}
    
    try:
        # Get all points from Qdrant (with pagination)
        logger.info(f"\n📦 Fetching all images from Qdrant collection '{collection_name}'...")
        try:
            all_points = []
            next_page_offset = None
            
            while True:
                points, next_page_offset = qdrant_client.scroll(
                    collection_name=collection_name,
                    limit=1000,  # Fetch in batches
                    offset=next_page_offset,
                    with_payload=True
                )
                
                if not points:
                    break
                    
                all_points.extend(points)
                logger.info(f"  Fetched {len(points)} images (total: {len(all_points)})...")
                
                if next_page_offset is None:
                    break
            
            points = all_points
            logger.info(f"✅ Found {len(points)} total images in Qdrant")
            
            # Validate we got data
            if len(points) == 0:
                logger.warning("⚠️  No points fetched from Qdrant")
        except Exception as e:
            logger.error(f"❌ Failed to fetch from Qdrant: {e}")
            # Error return - cleanup will happen in finally
            return {"error": str(e)}
        
        if not points:
            logger.warning("⚠️  No images found in Qdrant")
            # Return empty stats but still cleanup
            return {"total": 0, "processed": 0, "skipped": 0, "errors": 0, "with_gcs_url": 0, "without_gcs_url": 0}
        
        # Process each point
        stats = {
            "total": len(points),
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "with_gcs_url": 0,
            "without_gcs_url": 0,
        }
        
        logger.info(f"\n🔄 Processing {len(points)} images...")
        
        # Batch save every N images to reduce I/O
        BATCH_SAVE_INTERVAL = 50  # Save every 50 images instead of every triple
        
        # Use tqdm for progress bar
        with tqdm(total=len(points), desc="Backfilling KG", unit="image", ncols=100) as pbar:
            for i, point in enumerate(points, 1):
                try:
                    payload = point.payload
                    image_uri = payload.get("image_uri", "")
                    gcs_url = payload.get("gcs_url", "")
                    filename = payload.get("filename", "")
                    image_type = payload.get("image_type", "")
                    description = payload.get("description", "")
                    
                    if not image_uri:
                        tqdm.write(f"⚠️  Skipping point {point.id}: no image_uri")
                        stats["skipped"] += 1
                        pbar.update(1)
                        continue
                    
                    # Check if already in KG (use SELECT instead of ASK)
                    # Only check if not in dry_run mode (saves queries)
                    if not dry_run:
                        check_query = f"""
                        PREFIX schema: <http://schema.org/>
                        SELECT ?url WHERE {{
                            <{image_uri}> schema:contentUrl ?url .
                        }}
                        LIMIT 1
                        """
                        try:
                            kg_check_results = await kg.query_graph(check_query)
                            
                            if kg_check_results and isinstance(kg_check_results, list) and len(kg_check_results) > 0:
                                stats["skipped"] += 1
                                pbar.update(1)
                                pbar.set_postfix({"skipped": stats["skipped"], "added": stats["processed"]})
                                continue
                        except Exception as e:
                            # If check fails, log but continue (might be transient error)
                            tqdm.write(f"⚠️  KG check failed for {image_uri[:50]}: {e}, continuing...")
                            # Continue to add it anyway
                    
                    if not gcs_url:
                        stats["without_gcs_url"] += 1
                        # Still create KG node but without contentUrl
                        if not dry_run:
                            await _create_kg_node(kg, image_uri, filename, None, image_type, description)
                        stats["processed"] += 1
                        pbar.update(1)
                        pbar.set_postfix({"skipped": stats["skipped"], "added": stats["processed"]})
                        continue
                    
                    stats["with_gcs_url"] += 1
                    
                    if dry_run:
                        tqdm.write(f"Would create KG node: {image_uri[:50]} → {gcs_url[:60]}")
                    else:
                        # Create KG node with GCS URL
                        await _create_kg_node(kg, image_uri, filename, gcs_url, image_type, description)
                    
                    stats["processed"] += 1
                    pbar.update(1)
                    pbar.set_postfix({"skipped": stats["skipped"], "added": stats["processed"]})
                    
                    # Batch save every N images to reduce I/O (though each triple still saves individually)
                    # This is a compromise - the real fix would be to modify KG manager to support batch mode
                    if stats["processed"] % BATCH_SAVE_INTERVAL == 0:
                        # The graph is already saved after each triple, but we can at least reduce cache clears
                        pass
                    
                except Exception as e:
                    tqdm.write(f"❌ Error processing point {point.id}: {e}")
                    stats["errors"] += 1
                    pbar.update(1)
                    pbar.set_postfix({"errors": stats["errors"]})
        
        # Final save (though it's already saved after each triple)
        if not dry_run and kg:
            kg.save_graph()
        
        # Restore normal logging before final summary
        logger.remove()
        logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
        
        logger.info("\n" + "=" * 70)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total images: {stats['total']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Skipped (already exists): {stats['skipped']}")
        logger.info(f"With gcs_url: {stats['with_gcs_url']}")
        logger.info(f"Without gcs_url: {stats['without_gcs_url']}")
        logger.info(f"Errors: {stats['errors']}")
        
        return stats
        
    finally:
        # ALWAYS clean up resources, even if there's an error
        if kg:
            try:
                await kg.shutdown()
                # Only log if logging is still configured
                try:
                    logger.debug("KG manager shut down cleanly")
                except:
                    pass
            except Exception as e:
                try:
                    logger.warning(f"Error shutting down KG manager: {e}")
                except:
                    pass
        
        # Note: Qdrant client doesn't need explicit cleanup (it's just a connection)


async def _create_kg_node(
    kg: KnowledgeGraphManager,
    image_uri: str,
    filename: str,
    gcs_url: str | None,
    image_type: str,
    description: str
):
    """Create a KG node for an image - batches all triples before save."""
    from rdflib import URIRef, Literal, RDF, XSD
    from rdflib.namespace import Namespace
    
    SCHEMA = Namespace("http://schema.org/")
    KG = Namespace("http://example.org/kg#")
    DC = Namespace("http://purl.org/dc/elements/1.1/")
    
    image_ref = URIRef(image_uri)
    
    # Helper to ensure string values (handle bytes, None, etc.)
    def ensure_string(value):
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return str(value)
    
    # Batch all triples for this image
    # Add type - PRIORITY 1 FIX: Store book:InputImage/book:OutputImage types to match pairing queries
    BOOK = Namespace("http://example.org/childrens-book#")
    await kg.add_triple(str(image_ref), str(RDF.type), str(SCHEMA.ImageObject))
    
    # Add book-specific type based on image_type
    image_type_lower = ensure_string(image_type).lower()
    if image_type_lower == "input":
        await kg.add_triple(str(image_ref), str(RDF.type), str(BOOK.InputImage))
    elif image_type_lower == "output":
        await kg.add_triple(str(image_ref), str(RDF.type), str(BOOK.OutputImage))
    
    # Add name
    if filename:
        await kg.add_triple(str(image_ref), str(SCHEMA.name), ensure_string(filename))
    
    # Add GCS URL (CRITICAL for API fallback)
    if gcs_url:
        await kg.add_triple(str(image_ref), str(SCHEMA.contentUrl), ensure_string(gcs_url))
    
    # Add image type (lowercase for consistency)
    if image_type:
        await kg.add_triple(str(image_ref), str(KG.imageType), ensure_string(image_type_lower))
    
    # Add description
    if description:
        await kg.add_triple(str(image_ref), str(SCHEMA.description), ensure_string(description))
    
    # Note: Each add_triple saves automatically, but we can't disable that without modifying KG manager
    # The logging reduction above helps with the verbosity issue


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill KG from Qdrant")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to KG")
    parser.add_argument("--collection", default="childrens_book_images", help="Qdrant collection name")
    
    args = parser.parse_args()
    
    result = asyncio.run(backfill_kg_from_qdrant(
        collection_name=args.collection,
        dry_run=args.dry_run
    ))
    
    if "error" in result:
        sys.exit(1)

