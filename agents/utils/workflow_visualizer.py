"""
Workflow Visualization Generator
Generates HTML visualizations from workflow data stored in Knowledge Graph.

Reuses patterns from hotdog_flow_viz.html but generates dynamically from KG data.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger
from kg.models.graph_manager import KnowledgeGraphManager


class WorkflowVisualizer:
    """Generate HTML visualizations from workflow KG data."""
    
    def __init__(self, kg_manager: Optional[KnowledgeGraphManager] = None):
        self.kg_manager = kg_manager or KnowledgeGraphManager()
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure KG manager is initialized."""
        if not self._initialized:
            await self.kg_manager.initialize()
            self._initialized = True
    
    async def generate_html_visualization(
        self,
        workflow_id: str,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate HTML visualization for a workflow.
        
        Args:
            workflow_id: The workflow ID
            output_path: Optional path to save HTML file
            
        Returns:
            Path to generated HTML file
        """
        await self._ensure_initialized()
        
        # Extract workflow data from KG
        workflow_data = await self._extract_workflow_data(workflow_id)
        
        # Generate HTML
        html_content = self._generate_html(workflow_data)
        
        # Save to file
        if output_path is None:
            output_path = Path(f"workflow_viz_{workflow_id}.html")
        
        output_path.write_text(html_content)
        logger.info(f"Generated workflow visualization: {output_path}")
        
        return str(output_path)
    
    async def _extract_workflow_data(self, workflow_id: str) -> Dict[str, Any]:
        """Extract workflow data from Knowledge Graph."""
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        execution_uri = f"http://example.org/execution/{workflow_id}"
        
        # Query for execution steps
        query = f"""
        PREFIX : <http://example.org/core#>
        PREFIX ex: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?step ?action ?status ?result ?error ?startedAt ?completedAt
        WHERE {{
            <{execution_uri}> ex:hasStep ?step .
            ?step ex:action ?action .
            OPTIONAL {{ ?step ex:status ?status . }}
            OPTIONAL {{ ?step ex:result ?result . }}
            OPTIONAL {{ ?step ex:error ?error . }}
            OPTIONAL {{ ?step ex:startedAt ?startedAt . }}
            OPTIONAL {{ ?step ex:completedAt ?completedAt . }}
        }}
        ORDER BY ?step
        """
        
        try:
            results = await self.kg_manager.query_graph(query)
        except Exception as e:
            logger.warning(f"Could not query execution steps: {e}, using plan steps instead")
            # Fallback: query plan steps
            query = f"""
            PREFIX : <http://example.org/core#>
            PREFIX ex: <http://example.org/ontology#>
            
            SELECT ?plan ?step ?action
            WHERE {{
                <{workflow_uri}> ex:hasPlan ?plan .
                ?plan :hasStep ?step .
                ?step :action ?action .
            }}
            ORDER BY ?step
            """
            results = await self.kg_manager.query_graph(query)
        
        # Parse results into timeline items
        timeline_items = []
        decisions = []
        tasks = []
        images = []
        retries = 0
        
        if not results:
            # No execution data yet, create placeholder
            timeline_items.append({
                "type": "task",
                "title": "Workflow Created",
                "description": "Workflow initialized and ready for execution",
                "time": "",
                "status": "pending"
            })
        else:
            for i, result in enumerate(results):
                action = str(result.get("action", f"Step {i+1}"))
                status = str(result.get("status", "unknown"))
                result_data = str(result.get("result", "")) if result.get("result") else ""
                
                # Classify item type
                if "choose" in action.lower() or "select" in action.lower() or "decision" in action.lower():
                    item_type = "decision"
                    decisions.append({
                        "title": action,
                        "description": f"✅ Selected: {result_data}" if result_data else "Decision made"
                    })
                elif "generate" in action.lower() or "create" in action.lower():
                    item_type = "task"
                    tasks.append({
                        "title": action,
                        "status": status
                    })
                    # Check for retries
                    if status == "retry" or "retry" in action.lower() or "retry" in result_data.lower():
                        retries += 1
                elif "image" in action.lower() or (status == "completed" and "image" in result_data.lower()):
                    item_type = "image"
                    images.append({
                        "title": action,
                        "quality": self._extract_quality(result_data)
                    })
                else:
                    item_type = "task"
                
                timeline_items.append({
                    "type": item_type,
                    "title": action,
                    "description": result_data[:100] if result_data else status,  # Truncate long descriptions
                    "time": str(result.get("startedAt", "")),
                    "status": status
                })
        
        return {
            "workflow_id": workflow_id,
            "timeline_items": timeline_items,
            "stats": {
                "decisions": len(decisions),
                "images": len(images),
                "retries": retries,
                "tasks": len(tasks) if tasks else len(timeline_items)
            },
            "decisions": decisions,
            "tasks": tasks,
            "images": images
        }
    
    def _extract_quality(self, result_data: str) -> Optional[float]:
        """Extract quality score from result data if present."""
        import re
        if isinstance(result_data, str):
            match = re.search(r'quality[:\s]+([\d.]+)', result_data.lower())
            if match:
                return float(match.group(1))
        return None
    
    def _generate_html(self, workflow_data: Dict[str, Any]) -> str:
        """Generate HTML visualization from workflow data."""
        stats = workflow_data["stats"]
        timeline_items = workflow_data["timeline_items"]
        
        # Generate timeline HTML
        timeline_html = self._generate_timeline_html(timeline_items)
        
        # Generate network graph data
        network_data = self._generate_network_data(timeline_items)
        
        # Generate flowchart (Mermaid)
        flowchart = self._generate_mermaid_flowchart(timeline_items)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Workflow Flow Visualization - {workflow_data['workflow_id']}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }}
        
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        
        .tab {{
            padding: 10px 20px;
            cursor: pointer;
            background: #f5f5f5;
            border: none;
            border-radius: 5px 5px 0 0;
            font-size: 14px;
            font-weight: 600;
        }}
        
        .tab.active {{
            background: #667eea;
            color: white;
        }}
        
        .viz-container {{
            display: none;
            min-height: 600px;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            background: #fafafa;
        }}
        
        .viz-container.active {{
            display: block;
        }}
        
        #network {{
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            background: white;
        }}
        
        .timeline-item {{
            display: flex;
            align-items: center;
            margin: 20px 0;
            position: relative;
        }}
        
        .timeline-time {{
            min-width: 100px;
            font-size: 12px;
            color: #666;
        }}
        
        .timeline-marker {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #667eea;
            margin: 0 20px;
            position: relative;
            z-index: 2;
        }}
        
        .timeline-marker.decision {{
            background: #45b7d1;
        }}
        
        .timeline-marker.task {{
            background: #4ecdc4;
        }}
        
        .timeline-marker.image {{
            background: #96ceb4;
        }}
        
        .timeline-marker.complete {{
            background: #feca57;
        }}
        
        .timeline-content {{
            flex: 1;
            padding: 15px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .timeline-title {{
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .timeline-description {{
            font-size: 14px;
            color: #666;
        }}
        
        .timeline-line {{
            position: absolute;
            left: 130px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #ddd;
            z-index: 1;
        }}
        
        .stats {{
            display: flex;
            gap: 30px;
            margin-bottom: 20px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 5px;
        }}
        
        .stat {{
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        
        #mermaid-diagram {{
            background: white;
            padding: 20px;
            border-radius: 5px;
        }}
        
        .legend {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 5px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .legend-color {{
            width: 15px;
            height: 15px;
            border-radius: 50%;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Workflow Flow Visualization</h1>
        <p style="text-align: center; color: #666;">{workflow_data['workflow_id']}</p>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{stats['decisions']}</div>
                <div class="stat-label">Decisions</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['images']}</div>
                <div class="stat-label">Images</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['retries']}</div>
                <div class="stat-label">Retries</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['tasks']}</div>
                <div class="stat-label">Tasks</div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showViz('timeline')">📅 Timeline Flow</button>
            <button class="tab" onclick="showViz('network')">🕸️ Network Graph</button>
            <button class="tab" onclick="showViz('flowchart')">📊 Flowchart</button>
        </div>
        
        <!-- Timeline View -->
        <div id="timeline" class="viz-container active">
            <h3>Mission Timeline</h3>
            <div style="position: relative;">
                <div class="timeline-line"></div>
                {timeline_html}
            </div>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #667eea;"></div>
                    <span>Start/End</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #45b7d1;"></div>
                    <span>Decision</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4ecdc4;"></div>
                    <span>Task</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #96ceb4;"></div>
                    <span>Image</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #feca57;"></div>
                    <span>Complete</span>
                </div>
            </div>
        </div>
        
        <!-- Network Graph View -->
        <div id="network-container" class="viz-container">
            <h3>Mission Network Graph</h3>
            <div id="network"></div>
        </div>
        
        <!-- Flowchart View -->
        <div id="flowchart" class="viz-container">
            <h3>Mission Flowchart</h3>
            <div id="mermaid-diagram">
                <div class="mermaid">
{flowchart}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Initialize Mermaid
        mermaid.initialize({{ startOnLoad: true }});
        
        // Tab switching
        function showViz(vizId) {{
            document.querySelectorAll('.viz-container').forEach(v => {{
                v.classList.remove('active');
            }});
            
            document.querySelectorAll('.tab').forEach(t => {{
                t.classList.remove('active');
            }});
            
            if (vizId === 'network') {{
                document.getElementById('network-container').classList.add('active');
                initNetwork();
            }} else {{
                document.getElementById(vizId).classList.add('active');
            }}
            
            event.target.classList.add('active');
        }}
        
        // Initialize network graph
        function initNetwork() {{
            var nodes = new vis.DataSet({network_data['nodes']});
            var edges = new vis.DataSet({network_data['edges']});
            
            var container = document.getElementById('network');
            var data = {{ nodes: nodes, edges: edges }};
            
            var options = {{
                groups: {{
                    agent: {{color: {{background: '#ff6b6b'}}, shape: 'box'}},
                    start: {{color: {{background: '#667eea'}}}},
                    decision: {{color: {{background: '#45b7d1'}}, shape: 'diamond'}},
                    task: {{color: {{background: '#4ecdc4'}}, shape: 'box'}},
                    image: {{color: {{background: '#96ceb4'}}, shape: 'circle'}},
                    complete: {{color: {{background: '#feca57'}}, shape: 'star'}}
                }},
                layout: {{
                    hierarchical: {{
                        direction: 'UD',
                        sortMethod: 'directed',
                        levelSeparation: 100
                    }}
                }},
                physics: {{
                    hierarchicalRepulsion: {{
                        nodeDistance: 150
                    }}
                }},
                edges: {{
                    smooth: {{
                        type: 'cubicBezier',
                        roundness: 0.4
                    }}
                }}
            }};
            
            var network = new vis.Network(container, data, options);
        }}
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_timeline_html(self, timeline_items: List[Dict[str, Any]]) -> str:
        """Generate timeline HTML from items."""
        html_parts = []
        
        # Add start
        html_parts.append("""
                <div class="timeline-item">
                    <div class="timeline-time">START</div>
                    <div class="timeline-marker"></div>
                    <div class="timeline-content">
                        <div class="timeline-title">🚀 Mission Initiated</div>
                        <div class="timeline-description">Workflow started</div>
                    </div>
                </div>
        """)
        
        # Add items
        for i, item in enumerate(timeline_items):
            item_type = item.get("type", "task")
            title = item.get("title", f"Step {i+1}")
            description = item.get("description", "")
            status = item.get("status", "")
            
            type_label = item_type.upper()
            marker_class = f"timeline-marker {item_type}"
            
            html_parts.append(f"""
                <div class="timeline-item">
                    <div class="timeline-time">{type_label}</div>
                    <div class="{marker_class}"></div>
                    <div class="timeline-content">
                        <div class="timeline-title">{title}</div>
                        <div class="timeline-description">{description}</div>
                    </div>
                </div>
            """)
        
        # Add complete
        html_parts.append("""
                <div class="timeline-item">
                    <div class="timeline-time">COMPLETE</div>
                    <div class="timeline-marker complete"></div>
                    <div class="timeline-content">
                        <div class="timeline-title">🎉 Workflow Complete</div>
                        <div class="timeline-description">All steps finished successfully</div>
                    </div>
                </div>
        """)
        
        return "\n".join(html_parts)
    
    def _generate_network_data(self, timeline_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate network graph data."""
        import json
        
        nodes = [
            {"id": 1, "label": "Workflow Start", "group": "start"}
        ]
        edges = []
        
        node_id = 2
        for i, item in enumerate(timeline_items):
            item_type = item.get("type", "task")
            title = item.get("title", f"Step {i+1}")[:30]  # Truncate
            # Escape quotes for JSON
            title = title.replace('"', "'")
            
            nodes.append({
                "id": node_id,
                "label": title,
                "group": item_type
            })
            
            if i == 0:
                edges.append({"from": 1, "to": node_id, "arrows": "to"})
            else:
                edges.append({"from": node_id - 1, "to": node_id, "arrows": "to"})
            
            node_id += 1
        
        # Add end node
        nodes.append({"id": node_id, "label": "Complete", "group": "complete"})
        if timeline_items:
            edges.append({"from": node_id - 1, "to": node_id, "arrows": "to"})
        else:
            edges.append({"from": 1, "to": node_id, "arrows": "to"})
        
        return {
            "nodes": json.dumps(nodes),
            "edges": json.dumps(edges)
        }
    
    def _generate_mermaid_flowchart(self, timeline_items: List[Dict[str, Any]]) -> str:
        """Generate Mermaid flowchart."""
        lines = ["graph TD"]
        lines.append("    Start([🚀 Mission Start])")
        
        node_map = {"Start": 0}
        node_counter = 1
        
        for item in timeline_items:
            item_type = item.get("type", "task")
            title = item.get("title", f"Step {node_counter}")
            # Clean title for Mermaid
            clean_title = title.replace('"', "'").replace('\n', ' ')[:30]
            node_name = f"N{node_counter}"
            
            if item_type == "decision":
                lines.append(f"    {node_name}{{{clean_title}}}")
            else:
                lines.append(f"    {node_name}[{clean_title}]")
            
            # Connect to previous
            prev_node = f"N{node_counter - 1}" if node_counter > 1 else "Start"
            lines.append(f"    {prev_node} --> {node_name}")
            
            node_map[title] = node_counter
            node_counter += 1
        
        lines.append(f"    N{node_counter - 1} --> End([🎉 Complete])")
        lines.append("    style Start fill:#667eea,color:#fff")
        lines.append("    style End fill:#feca57,color:#333")
        
        return "\n".join(lines)

