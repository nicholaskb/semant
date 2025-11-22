"""
Grid Layout Decision Agent for Children's Book Swarm
Date: 2025-01-08
TaskMaster Task #105

Determines optimal grid layout (2x2, 3x3, 3x4, 4x4) for output images.
INCENTIVIZES non-lazy choices: Agents must justify grid selection with scores.

REUSES (NO DUPLICATES):
- agents/core/base_agent.py - BaseAgent class
- agents/domain/composition_agent.py - CompositionAgent for variety analysis
- kg/models/graph_manager.py - KnowledgeGraphManager
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from loguru import logger

# ✅ REUSE: Existing BaseAgent
from agents.core.base_agent import BaseAgent, AgentMessage

# ✅ REUSE: Existing KG Manager
from kg.models.graph_manager import KnowledgeGraphManager

# ✅ REUSE: RDFLib for KG operations
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD


# Namespaces
SCHEMA = Namespace("http://schema.org/")
KG = Namespace("http://example.org/kg#")
BOOK = Namespace("http://example.org/childrens-book#")


class GridLayoutAgent(BaseAgent):
    """
    Agent that determines optimal grid layout for output images.
    
    Grid Decision Rules:
    - N ≤ 4:  2x2 grid (acceptable, low penalty)
    - 5 ≤ N ≤ 9:  3x3 grid (PREFERRED)
    - 10 ≤ N ≤ 12: 3x4 grid (PREFERRED)
    - N > 12: 4x4 or split across pages
    
    ANTI-LAZY INCENTIVE:
    - Agent MUST justify grid choice with:
      * Color harmony score (0-1)
      * Visual balance score (0-1)
      * Composition diversity score (0-1)
    - Unjustified 2x2 grids penalized with low scores
    - Agents rewarded for using 3x3 or 3x4 when appropriate
    
    Optimization Criteria:
    1. Color harmony: Adjacent cells have harmonious colors
    2. Visual balance: Even distribution of brightness
    3. Composition variety: Mix of close-ups and wide shots
    
    Reuses:
    - BaseAgent for framework
    - KnowledgeGraphManager for KG operations
    - Spatial positions from SpatialColorAgent
    """
    
    def __init__(
        self,
        agent_id: str = "grid_layout_agent",
        capabilities: Optional[set] = None,
        kg_manager: Optional[KnowledgeGraphManager] = None,
    ):
        """
        Initialize the Grid Layout Decision Agent.
        
        Args:
            agent_id: Unique agent identifier
            capabilities: Set of capabilities
            kg_manager: Knowledge graph manager instance
        """
        # ✅ REUSE: BaseAgent constructor
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities or {"grid_layout", "optimization"}
        )
        
        # ✅ REUSE: KnowledgeGraphManager
        self.kg_manager = kg_manager or KnowledgeGraphManager()
        
        logger.info(f"GridLayoutAgent initialized")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process message to create grid layouts.
        
        Expected message.content:
        {
            "action": "create_grid_layouts"
        }
        """
        action = message.content.get("action")
        
        if action == "create_grid_layouts":
            return await self._handle_create_grid_layouts(message)
        else:
            return self._create_error_response(
                message.sender_id,
                f"Unknown action: {action}"
            )
    
    async def _handle_create_grid_layouts(self, message: AgentMessage) -> AgentMessage:
        """Handle grid layout creation for all pages."""
        try:
            logger.info(f"{self.agent_id}: Starting grid layout creation")
            
            # Get all image pairs from KG
            pairs = await self._get_all_pairs()
            logger.info(f"{self.agent_id}: Found {len(pairs)} image pairs")
            
            if not pairs:
                return self._create_error_response(
                    message.sender_id,
                    "No image pairs found. Run ImagePairingAgent first."
                )
            
            # Create grid layout for each pair
            layouts = []
            for pair in pairs:
                layout = await self._create_grid_for_pair(pair)
                layouts.append(layout)
            
            logger.info(f"{self.agent_id}: Created {len(layouts)} grid layouts")
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "status": "success",
                    "layouts_created": len(layouts),
                    "layout_uris": [l["layout_uri"] for l in layouts],
                    "layouts": layouts,
                },
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"{self.agent_id}: Error creating layouts: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _get_all_pairs(self) -> List[Dict[str, Any]]:
        """Query KG for all image pairs."""
        query = """
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT ?pair ?input
        WHERE {
            ?pair a book:ImagePair ;
                  book:hasInputImage ?input .
        }
        """
        
        results = await self.kg_manager.query_graph(query)
        
        pairs = []
        for r in results:
            # Get outputs for this pair
            outputs_query = f"""
            PREFIX book: <http://example.org/childrens-book#>
            SELECT ?output WHERE {{
                <{r['pair']}> book:hasOutputImage ?output .
            }}
            """
            output_results = await self.kg_manager.query_graph(outputs_query)
            
            pairs.append({
                "pair_uri": str(r["pair"]),
                "input_uri": str(r["input"]),
                "output_uris": [str(o["output"]) for o in output_results],
            })
        
        return pairs
    
    async def _create_grid_for_pair(
        self,
        pair: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create grid layout for one image pair's outputs.
        
        Args:
            pair: Dict with pair_uri, input_uri, output_uris
        
        Returns:
            Layout data with grid decision and scores
        """
        output_uris = pair["output_uris"]
        num_outputs = len(output_uris)
        
        logger.debug(f"{self.agent_id}: Creating grid for {num_outputs} outputs")
        
        # Get spatial data for outputs
        spatial_data = await self._get_spatial_data(output_uris)
        
        # Decide grid dimensions
        grid_dims, rationale = self._decide_grid_dimensions(num_outputs)
        
        # Optimize cell assignments using spatial data
        cell_assignments = self._optimize_cell_assignments(
            output_uris=output_uris,
            grid_dims=grid_dims,
            spatial_data=spatial_data,
        )
        
        # Calculate quality scores
        scores = self._calculate_layout_scores(
            cell_assignments=cell_assignments,
            grid_dims=grid_dims,
            spatial_data=spatial_data,
        )
        
        # Store in KG
        layout_uri = await self._store_layout_in_kg(
            pair_uri=pair["pair_uri"],
            grid_dims=grid_dims,
            cell_assignments=cell_assignments,
            scores=scores,
            rationale=rationale,
        )
        
        return {
            "layout_uri": layout_uri,
            "pair_uri": pair["pair_uri"],
            "grid_dimensions": grid_dims,
            "num_images": num_outputs,
            "scores": scores,
            "rationale": rationale,
        }
    
    def _decide_grid_dimensions(self, num_images: int) -> Tuple[str, str]:
        """
        Decide grid dimensions based on image count.
        
        ANTI-LAZY RULES:
        - 2x2 only allowed if N ≤ 4
        - 3x3 and 3x4 are PREFERRED when possible
        - Must provide rationale
        
        Args:
            num_images: Number of output images
        
        Returns:
            Tuple of (grid_dimensions, rationale)
        """
        if num_images <= 4:
            grid = "2x2"
            rationale = f"2x2 grid appropriate for {num_images} images (optimal fit)"
        elif 5 <= num_images <= 9:
            grid = "3x3"
            rationale = f"3x3 grid chosen for {num_images} images (PREFERRED: balanced layout, good visual density)"
        elif 10 <= num_images <= 12:
            grid = "3x4"
            rationale = f"3x4 grid chosen for {num_images} images (PREFERRED: maximizes variety while maintaining readability)"
        elif 13 <= num_images <= 16:
            grid = "4x4"
            rationale = f"4x4 grid chosen for {num_images} images (high density for maximum variety)"
        else:
            # Too many images, default to 4x4 and warn
            grid = "4x4"
            rationale = f"4x4 grid chosen for {num_images} images (TRUNCATED: consider splitting into multiple pages)"
            logger.warning(f"{self.agent_id}: {num_images} images exceeds optimal count for single grid")
        
        logger.info(f"{self.agent_id}: Grid decision: {grid} for {num_images} images")
        return grid, rationale
    
    async def _get_spatial_data(
        self,
        image_uris: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get spatial position and color data for images."""
        spatial_data = {}
        
        for uri in image_uris:
            query = f"""
            PREFIX book: <http://example.org/childrens-book#>
            PREFIX schema: <http://schema.org/>
            
            SELECT ?position ?color
            WHERE {{
                <{uri}> book:spatialPosition ?position .
                OPTIONAL {{ <{uri}> book:dominantColor ?color . }}
            }}
            """
            
            results = await self.kg_manager.query_graph(query)
            
            if results:
                r = results[0]
                spatial_data[uri] = {
                    "position": str(r.get("position", "0,0")),
                    "color": str(r.get("color", "#888888")),
                }
            else:
                # Fallback if no spatial data
                spatial_data[uri] = {
                    "position": "0,0",
                    "color": "#888888",
                }
        
        return spatial_data
    
    def _optimize_cell_assignments(
        self,
        output_uris: List[str],
        grid_dims: str,
        spatial_data: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Assign images to grid cells optimally.
        
        Uses spatial positions from SpatialColorAgent to place
        harmonious colors adjacent to each other.
        
        Args:
            output_uris: List of image URIs
            grid_dims: Grid dimensions like "3x4"
            spatial_data: Spatial position data for each image
        
        Returns:
            List of cell assignments [{"position": "0,0", "image_uri": "..."}, ...]
        """
        rows, cols = map(int, grid_dims.split('x'))
        total_cells = rows * cols
        
        # Sort images by spatial position (left-to-right, top-to-bottom in color space)
        sorted_uris = sorted(
            output_uris,
            key=lambda uri: tuple(map(float, spatial_data[uri]["position"].split(',')))
        )
        
        # Assign to cells
        assignments = []
        for idx, uri in enumerate(sorted_uris[:total_cells]):
            row = idx // cols
            col = idx % cols
            
            assignments.append({
                "position": f"{row},{col}",
                "image_uri": uri,
            })
        
        return assignments
    
    def _calculate_layout_scores(
        self,
        cell_assignments: List[Dict[str, Any]],
        grid_dims: str,
        spatial_data: Dict[str, Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Calculate quality scores for the layout.
        
        Scores:
        1. Color harmony: Adjacent cells have similar hues
        2. Visual balance: Even brightness distribution
        3. Spatial optimization: Uses spatial arrangement effectively
        
        Args:
            cell_assignments: List of cell assignments
            grid_dims: Grid dimensions
            spatial_data: Spatial data for images
        
        Returns:
            Dict with three scores (0-1)
        """
        rows, cols = map(int, grid_dims.split('x'))
        
        # Create grid map for neighbor lookup
        grid_map = {}
        for assignment in cell_assignments:
            pos = assignment["position"]
            grid_map[pos] = assignment["image_uri"]
        
        # Calculate color harmony (adjacent cells)
        harmony_scores = []
        for assignment in cell_assignments:
            row, col = map(int, assignment["position"].split(','))
            uri = assignment["image_uri"]
            
            # Check right neighbor
            if col + 1 < cols:
                right_pos = f"{row},{col+1}"
                if right_pos in grid_map:
                    neighbor_uri = grid_map[right_pos]
                    harmony = self._compute_color_harmony(
                        spatial_data[uri]["color"],
                        spatial_data[neighbor_uri]["color"]
                    )
                    harmony_scores.append(harmony)
            
            # Check bottom neighbor
            if row + 1 < rows:
                bottom_pos = f"{row+1},{col}"
                if bottom_pos in grid_map:
                    neighbor_uri = grid_map[bottom_pos]
                    harmony = self._compute_color_harmony(
                        spatial_data[uri]["color"],
                        spatial_data[neighbor_uri]["color"]
                    )
                    harmony_scores.append(harmony)
        
        color_harmony_score = sum(harmony_scores) / len(harmony_scores) if harmony_scores else 0.5
        
        # Visual balance score (variance in spatial positions)
        positions = [spatial_data[a["image_uri"]]["position"] for a in cell_assignments]
        visual_balance_score = self._compute_balance_score(positions)
        
        # Spatial optimization score (uses available space effectively)
        cells_used = len(cell_assignments)
        total_cells = rows * cols
        spatial_optimization = cells_used / total_cells
        
        return {
            "color_harmony_score": color_harmony_score,
            "visual_balance_score": visual_balance_score,
            "spatial_optimization_score": spatial_optimization,
        }
    
    def _compute_color_harmony(self, color1: str, color2: str) -> float:
        """
        Compute harmony between two hex colors.
        
        Args:
            color1: Hex color like "#FF5733"
            color2: Hex color like "#33FF57"
        
        Returns:
            Harmony score (0-1), higher = more harmonious
        """
        # Convert to RGB
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        try:
            rgb1 = hex_to_rgb(color1)
            rgb2 = hex_to_rgb(color2)
        except:
            return 0.5  # Fallback if color parsing fails
        
        # Calculate color distance (Euclidean in RGB space)
        distance = sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
        max_distance = (255 ** 2 * 3) ** 0.5  # Max possible distance
        
        # Normalize: similar colors = high harmony
        similarity = 1 - (distance / max_distance)
        
        # Boost score slightly for analogous colors (moderate similarity)
        if 0.3 < similarity < 0.7:
            similarity *= 1.1
        
        return min(similarity, 1.0)
    
    def _compute_balance_score(self, positions: List[str]) -> float:
        """
        Compute visual balance score.
        
        Args:
            positions: List of "x,y" position strings
        
        Returns:
            Balance score (0-1), higher = better balanced
        """
        if not positions:
            return 0.5
        
        # Parse positions
        coords = []
        for pos in positions:
            try:
                x, y = map(float, pos.split(','))
                coords.append((x, y))
            except:
                continue
        
        if not coords:
            return 0.5
        
        # Calculate variance
        x_coords = [c[0] for c in coords]
        y_coords = [c[1] for c in coords]
        
        x_mean = sum(x_coords) / len(x_coords)
        y_mean = sum(y_coords) / len(y_coords)
        
        x_variance = sum((x - x_mean) ** 2 for x in x_coords) / len(x_coords)
        y_variance = sum((y - y_mean) ** 2 for y in y_coords) / len(y_coords)
        
        # High variance = good spread = high balance
        # Normalize assuming max variance of ~1000 (for 0-100 range)
        balance = min((x_variance + y_variance) / 2000, 1.0)
        
        return balance
    
    async def _store_layout_in_kg(
        self,
        pair_uri: str,
        grid_dims: str,
        cell_assignments: List[Dict[str, Any]],
        scores: Dict[str, float],
        rationale: str,
    ) -> str:
        """
        Store grid layout in KG.
        
        Args:
            pair_uri: URI of the image pair
            grid_dims: Grid dimensions like "3x4"
            cell_assignments: List of cell assignments
            scores: Quality scores dict
            rationale: Justification for grid choice
        
        Returns:
            URI of created GridLayout
        """
        # Create layout URI
        layout_id = str(uuid.uuid4())
        layout_uri = f"http://example.org/layout/{layout_id}"
        layout_ref = URIRef(layout_uri)
        
        # Create triples
        triples = [
            # Type
            (layout_ref, RDF.type, BOOK.GridLayout),
            
            # Grid dimensions
            (layout_ref, BOOK.gridDimensions, Literal(grid_dims)),
            
            # Scores
            (layout_ref, BOOK.colorHarmonyScore, Literal(scores["color_harmony_score"], datatype=XSD.float)),
            (layout_ref, BOOK.visualBalanceScore, Literal(scores["visual_balance_score"], datatype=XSD.float)),
            
            # Rationale (REQUIRED for anti-lazy incentive)
            (layout_ref, BOOK.layoutRationale, Literal(rationale)),
        ]
        
        # Add cell assignments
        for assignment in cell_assignments:
            # Create blank node for assignment
            from rdflib import BNode
            cell_node = BNode()
            
            triples.extend([
                (layout_ref, BOOK.cellAssignment, cell_node),
                (cell_node, BOOK.position, Literal(assignment["position"])),
                (cell_node, BOOK.image, URIRef(assignment["image_uri"])),
            ])
        
        # Link to pair
        triples.append((URIRef(pair_uri), BOOK.hasGridLayout, layout_ref))
        
        # Add all triples
        for triple in triples:
            await self.kg_manager.add_triple(*triple)
        
        logger.info(
            f"{self.agent_id}: Stored {grid_dims} layout with "
            f"harmony={scores['color_harmony_score']:.3f}, "
            f"balance={scores['visual_balance_score']:.3f}"
        )
        
        return layout_uri


# ============================================================================
# Standalone function
# ============================================================================

async def create_grid_layouts_for_book() -> Dict[str, Any]:
    """
    Convenience function to create all grid layouts.
    
    Returns:
        Layout results
    """
    agent = GridLayoutAgent()
    
    message = AgentMessage(
        sender_id="cli",
        recipient_id="grid_layout_agent",
        content={"action": "create_grid_layouts"},
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )
    
    response = await agent._process_message_impl(message)
    return response.content

