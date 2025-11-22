"""
Spatial Color Arrangement Agent for Children's Book Swarm
Date: 2025-01-08
TaskMaster Task #104

Arranges output images in 2D spatial coordinates based on color harmony.
Uses color analysis to create visually pleasing neighbor relationships.

REUSES (NO DUPLICATES):
- agents/core/base_agent.py - BaseAgent class
- agents/domain/color_palette_agent.py - ColorPaletteAgent for color analysis
- kg/models/graph_manager.py - KnowledgeGraphManager
"""

import uuid
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from loguru import logger

# ✅ REUSE: Existing BaseAgent
from agents.core.base_agent import BaseAgent, AgentMessage

# ✅ REUSE: Existing KG Manager
from kg.models.graph_manager import KnowledgeGraphManager

# ✅ REUSE: Existing ColorPaletteAgent
from agents.domain.color_palette_agent import ColorPaletteAgent

# ✅ REUSE: RDFLib for KG operations
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD


# Namespaces
SCHEMA = Namespace("http://schema.org/")
KG = Namespace("http://example.org/kg#")
BOOK = Namespace("http://example.org/childrens-book#")


class SpatialColorAgent(BaseAgent):
    """
    Agent that arranges images in 2D space by color harmony.
    
    Algorithm:
    1. Analyze each image's dominant colors using ColorPaletteAgent
    2. Compute color harmony scores between all pairs
    3. Arrange in 2D space:
       - Group by hue (primary color family)
       - Sort by saturation and brightness
       - Assign x,y coordinates
    4. Store spatial positions in KG
    
    Output: Each image gets book:spatialPosition, book:dominantColor,
            and book:colorHarmonyNeighbors
    
    Reuses:
    - BaseAgent for framework
    - ColorPaletteAgent for color analysis (NO duplicate color code)
    - KnowledgeGraphManager for KG operations
    """
    
    def __init__(
        self,
        agent_id: str = "spatial_color_agent",
        capabilities: Optional[set] = None,
        kg_manager: Optional[KnowledgeGraphManager] = None,
        color_agent: Optional[ColorPaletteAgent] = None,
    ):
        """
        Initialize the Spatial Color Arrangement Agent.
        
        Args:
            agent_id: Unique agent identifier
            capabilities: Set of capabilities
            kg_manager: Knowledge graph manager instance
            color_agent: Color palette agent instance
        """
        # ✅ REUSE: BaseAgent constructor
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities or {"color_analysis", "spatial_arrangement"}
        )
        
        # ✅ REUSE: KnowledgeGraphManager
        self.kg_manager = kg_manager or KnowledgeGraphManager()
        
        # ✅ REUSE: ColorPaletteAgent
        self.color_agent = color_agent or ColorPaletteAgent(
            agent_id="color_palette_analyzer",
            capabilities={"image_analysis"}
        )
        
        logger.info(f"SpatialColorAgent initialized")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process message to arrange images spatially.
        
        Expected message.content:
        {
            "action": "arrange_by_color"
        }
        """
        action = message.content.get("action")
        
        if action == "arrange_by_color":
            return await self._handle_arrange_by_color(message)
        else:
            return self._create_error_response(
                message.sender_id,
                f"Unknown action: {action}"
            )
    
    async def _handle_arrange_by_color(self, message: AgentMessage) -> AgentMessage:
        """Handle spatial color arrangement."""
        try:
            logger.info(f"{self.agent_id}: Starting color-based spatial arrangement")
            
            # Get all output images from KG
            output_images = await self._get_output_images()
            logger.info(f"{self.agent_id}: Found {len(output_images)} output images")
            
            if not output_images:
                return self._create_error_response(
                    message.sender_id,
                    "No output images found. Run ImageIngestionAgent first."
                )
            
            # Analyze colors for each image
            color_data = await self._analyze_all_colors(output_images)
            
            # Arrange in 2D space by color
            spatial_arrangement = self._compute_spatial_positions(color_data)
            
            # Store spatial positions in KG
            stored_count = await self._store_spatial_positions(spatial_arrangement)
            
            logger.info(
                f"{self.agent_id}: Arranged {stored_count} images in color space"
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "status": "success",
                    "images_arranged": stored_count,
                    "spatial_data": spatial_arrangement,
                },
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"{self.agent_id}: Error in arrange_by_color: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _get_output_images(self) -> List[Dict[str, Any]]:
        """Query KG for all output images."""
        query = """
        PREFIX schema: <http://schema.org/>
        PREFIX kg: <http://example.org/kg#>
        
        SELECT ?uri ?name ?url
        WHERE {
            ?uri a schema:ImageObject ;
                 kg:imageType "output" ;
                 schema:name ?name ;
                 schema:contentUrl ?url .
        }
        ORDER BY ?name
        """
        
        results = await self.kg_manager.query_graph(query)
        
        return [{
            "uri": str(r["uri"]),
            "name": str(r["name"]),
            "url": str(r["url"]),
        } for r in results]
    
    async def _analyze_all_colors(
        self,
        images: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze dominant colors for all images.
        
        Uses ColorPaletteAgent to avoid duplicating color analysis logic.
        
        Args:
            images: List of image metadata dicts
        
        Returns:
            List of dicts with image + color data
        """
        color_data = []
        
        for img in images:
            # ✅ REUSE: ColorPaletteAgent for color analysis
            color_message = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="color_palette_analyzer",
                content={"image_urls": [img["url"]]},
                message_type="request"
            )
            
            try:
                color_response = await self.color_agent.process_message(color_message)
                color_analysis = color_response.content.get("color_palette_analysis", "")
                
                # Extract dominant color from analysis
                dominant_color = self._extract_dominant_color(color_analysis)
                
                # Convert to HSV for spatial arrangement
                hsv = self._hex_to_hsv(dominant_color)
                
                color_data.append({
                    "uri": img["uri"],
                    "name": img["name"],
                    "url": img["url"],
                    "dominant_color": dominant_color,
                    "hue": hsv[0],
                    "saturation": hsv[1],
                    "brightness": hsv[2],
                    "analysis": color_analysis,
                })
                
            except Exception as e:
                logger.error(f"Failed to analyze colors for {img['name']}: {e}")
                # Use fallback color
                color_data.append({
                    "uri": img["uri"],
                    "name": img["name"],
                    "url": img["url"],
                    "dominant_color": "#888888",  # Neutral gray fallback
                    "hue": 0,
                    "saturation": 0,
                    "brightness": 0.5,
                    "analysis": "",
                })
        
        return color_data
    
    def _extract_dominant_color(self, color_analysis: str) -> str:
        """
        Extract hex color code from color analysis text.
        
        Args:
            color_analysis: Text from ColorPaletteAgent
        
        Returns:
            Hex color code like "#FF5733"
        """
        # Look for hex color codes in the analysis
        hex_pattern = r'#[0-9A-Fa-f]{6}'
        matches = re.findall(hex_pattern, color_analysis)
        
        if matches:
            return matches[0]  # Return first color found
        
        # Look for common color names and map to hex
        color_map = {
            "red": "#FF0000",
            "orange": "#FFA500",
            "yellow": "#FFFF00",
            "green": "#00FF00",
            "blue": "#0000FF",
            "purple": "#800080",
            "pink": "#FFC0CB",
            "brown": "#8B4513",
            "gray": "#808080",
            "grey": "#808080",
            "black": "#000000",
            "white": "#FFFFFF",
        }
        
        analysis_lower = color_analysis.lower()
        for color_name, hex_code in color_map.items():
            if color_name in analysis_lower:
                return hex_code
        
        # Default to gray if no color found
        return "#888888"
    
    def _hex_to_hsv(self, hex_color: str) -> Tuple[float, float, float]:
        """
        Convert hex color to HSV (Hue, Saturation, Value/Brightness).
        
        Args:
            hex_color: Hex color code like "#FF5733"
        
        Returns:
            Tuple of (hue [0-360], saturation [0-1], brightness [0-1])
        """
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        
        # Convert RGB to HSV
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        diff = max_c - min_c
        
        # Brightness (Value)
        v = max_c
        
        # Saturation
        s = 0 if max_c == 0 else (diff / max_c)
        
        # Hue
        if diff == 0:
            h = 0
        elif max_c == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_c == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360
        
        return (h, s, v)
    
    def _compute_spatial_positions(
        self,
        color_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Compute 2D spatial positions for images based on color harmony.
        
        Algorithm:
        - X axis: Hue (0-360 degrees)
        - Y axis: Combination of saturation and brightness
        - This creates natural color clustering
        
        Args:
            color_data: List of images with color info
        
        Returns:
            List with spatial positions added
        """
        arranged_data = []
        
        for img in color_data:
            # Map hue to X coordinate (normalize to 0-100)
            x = (img["hue"] / 360.0) * 100
            
            # Map saturation*brightness to Y coordinate
            y = (img["saturation"] * img["brightness"]) * 100
            
            # Find color harmony neighbors (within 30 degrees hue)
            neighbors = []
            for other in color_data:
                if other["uri"] == img["uri"]:
                    continue
                
                # Calculate hue difference (handle wrap-around)
                hue_diff = min(
                    abs(img["hue"] - other["hue"]),
                    360 - abs(img["hue"] - other["hue"])
                )
                
                # Similar hue = harmonious
                if hue_diff < 30:  # Within 30 degrees
                    neighbors.append(other["uri"])
            
            arranged_data.append({
                **img,
                "spatial_position": f"{x:.2f},{y:.2f}",
                "color_harmony_neighbors": neighbors[:5],  # Top 5 closest
            })
        
        return arranged_data
    
    async def _store_spatial_positions(
        self,
        spatial_data: List[Dict[str, Any]]
    ) -> int:
        """
        Store spatial positions and color data in KG.
        
        Args:
            spatial_data: List of images with spatial positions
        
        Returns:
            Number of images stored
        """
        stored_count = 0
        
        for img in spatial_data:
            image_ref = URIRef(img["uri"])
            
            triples = [
                # Spatial position
                (image_ref, BOOK.spatialPosition, Literal(img["spatial_position"])),
                
                # Dominant color
                (image_ref, BOOK.dominantColor, Literal(img["dominant_color"])),
            ]
            
            # Add color harmony neighbors
            for neighbor_uri in img["color_harmony_neighbors"]:
                triples.append((
                    image_ref,
                    BOOK.colorHarmonyNeighbor,
                    URIRef(neighbor_uri)
                ))
            
            # Add all triples
            for triple in triples:
                await self.kg_manager.add_triple(*triple)
            
            stored_count += 1
        
        logger.info(f"{self.agent_id}: Stored spatial positions for {stored_count} images")
        return stored_count


# ============================================================================
# Standalone function
# ============================================================================

async def arrange_images_by_color() -> Dict[str, Any]:
    """
    Convenience function to arrange images spatially.
    
    Returns:
        Arrangement results
    """
    agent = SpatialColorAgent()
    
    message = AgentMessage(
        sender_id="cli",
        recipient_id="spatial_color_agent",
        content={"action": "arrange_by_color"},
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )
    
    response = await agent._process_message_impl(message)
    return response.content

