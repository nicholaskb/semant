#!/usr/bin/env python3
"""
Knowledge Graph Visualizer - Web Interface
Visualizes the hot dog flier job and other KG data in an interactive web interface
"""
import asyncio
import json
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from kg.models.graph_manager import KnowledgeGraphManager
import rdflib
import networkx as nx
from datetime import datetime

app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Graph Visualizer - Hot Dog Mission</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        #header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1 {
            margin: 0;
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stats {
            display: flex;
            gap: 30px;
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        #controls {
            position: absolute;
            top: 100px;
            right: 20px;
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 1000;
            width: 250px;
        }
        
        #controls h3 {
            margin-top: 0;
            color: #333;
        }
        
        .filter-group {
            margin: 10px 0;
        }
        
        .filter-group label {
            display: block;
            margin: 5px 0;
            cursor: pointer;
            color: #555;
        }
        
        .filter-group input[type="checkbox"] {
            margin-right: 8px;
        }
        
        #graph {
            width: 100%;
            height: calc(100vh - 100px);
            background: white;
            position: relative;
        }
        
        .node {
            cursor: pointer;
            stroke: #fff;
            stroke-width: 2px;
        }
        
        .node-agent { fill: #ff6b6b; }
        .node-task { fill: #4ecdc4; }
        .node-decision { fill: #45b7d1; }
        .node-image { fill: #96ceb4; }
        .node-flier { fill: #feca57; }
        .node-mission { fill: #ff9ff3; }
        .node-default { fill: #95afc0; }
        
        .node:hover {
            stroke: #333;
            stroke-width: 3px;
        }
        
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 2px;
        }
        
        .link-arrow {
            fill: #999;
        }
        
        .node-label {
            font-size: 12px;
            pointer-events: none;
            text-anchor: middle;
            fill: #333;
        }
        
        .link-label {
            font-size: 10px;
            fill: #666;
            text-anchor: middle;
        }
        
        #tooltip {
            position: absolute;
            text-align: left;
            padding: 10px;
            font-size: 12px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        #legend {
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin: 5px 0;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
            border: 2px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px 0;
            width: 100%;
        }
        
        button:hover {
            background: #5a67d8;
        }
        
        #search {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div id="header">
        <h1>🌭 Knowledge Graph Visualizer - Hot Dog Mission</h1>
        <div class="stats">
            <div class="stat-item">
                <span>📊 Nodes:</span>
                <span id="node-count">0</span>
            </div>
            <div class="stat-item">
                <span>🔗 Edges:</span>
                <span id="edge-count">0</span>
            </div>
            <div class="stat-item">
                <span>🎯 Decisions:</span>
                <span id="decision-count">0</span>
            </div>
            <div class="stat-item">
                <span>🎨 Images:</span>
                <span id="image-count">0</span>
            </div>
        </div>
    </div>
    
    <div id="controls">
        <h3>🔍 Filter & Search</h3>
        <input type="text" id="search" placeholder="Search nodes...">
        
        <div class="filter-group">
            <label><input type="checkbox" class="filter" data-type="agent" checked> Agents</label>
            <label><input type="checkbox" class="filter" data-type="task" checked> Tasks</label>
            <label><input type="checkbox" class="filter" data-type="decision" checked> Decisions</label>
            <label><input type="checkbox" class="filter" data-type="image" checked> Images</label>
            <label><input type="checkbox" class="filter" data-type="flier" checked> Fliers</label>
        </div>
        
        <button onclick="resetZoom()">Reset Zoom</button>
        <button onclick="centerGraph()">Center Graph</button>
        <button onclick="toggleLabels()">Toggle Labels</button>
        <button onclick="refreshData()">Refresh Data</button>
    </div>
    
    <div id="graph"></div>
    
    <div id="tooltip"></div>
    
    <div id="legend">
        <h4 style="margin-top: 0;">Legend</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #ff6b6b;"></div>
            <span>Agent</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #4ecdc4;"></div>
            <span>Task</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #45b7d1;"></div>
            <span>Decision</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #96ceb4;"></div>
            <span>Image</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #feca57;"></div>
            <span>Flier</span>
        </div>
    </div>
    
    <script>
        let graphData = null;
        let simulation = null;
        let svg = null;
        let g = null;
        let showLabels = true;
        
        // Initialize the graph
        function initGraph() {
            const width = window.innerWidth;
            const height = window.innerHeight - 100;
            
            // Create SVG
            svg = d3.select("#graph")
                .append("svg")
                .attr("width", width)
                .attr("height", height);
            
            // Add zoom behavior
            const zoom = d3.zoom()
                .scaleExtent([0.1, 10])
                .on("zoom", (event) => {
                    g.attr("transform", event.transform);
                });
            
            svg.call(zoom);
            
            // Create container group
            g = svg.append("g");
            
            // Define arrow markers
            svg.append("defs").selectAll("marker")
                .data(["arrow"])
                .enter().append("marker")
                .attr("id", d => d)
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 20)
                .attr("refY", 0)
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M0,-5L10,0L0,5")
                .attr("class", "link-arrow");
            
            // Load initial data
            loadGraphData();
        }
        
        function loadGraphData() {
            fetch('/api/graph')
                .then(response => response.json())
                .then(data => {
                    graphData = data;
                    updateStats();
                    renderGraph();
                });
        }
        
        function updateStats() {
            document.getElementById('node-count').textContent = graphData.nodes.length;
            document.getElementById('edge-count').textContent = graphData.links.length;
            document.getElementById('decision-count').textContent = 
                graphData.nodes.filter(n => n.type === 'decision').length;
            document.getElementById('image-count').textContent = 
                graphData.nodes.filter(n => n.type === 'image').length;
        }
        
        function renderGraph() {
            const width = window.innerWidth;
            const height = window.innerHeight - 100;
            
            // Clear existing elements
            g.selectAll("*").remove();
            
            // Filter nodes based on checkboxes
            const activeTypes = Array.from(document.querySelectorAll('.filter:checked'))
                .map(cb => cb.dataset.type);
            
            const searchTerm = document.getElementById('search').value.toLowerCase();
            
            const filteredNodes = graphData.nodes.filter(node => {
                const typeMatch = activeTypes.includes(node.type) || node.type === 'default';
                const searchMatch = !searchTerm || 
                    node.label.toLowerCase().includes(searchTerm) ||
                    node.id.toLowerCase().includes(searchTerm);
                return typeMatch && searchMatch;
            });
            
            const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
            const filteredLinks = graphData.links.filter(link => 
                filteredNodeIds.has(link.source.id || link.source) && 
                filteredNodeIds.has(link.target.id || link.target)
            );
            
            // Create force simulation
            simulation = d3.forceSimulation(filteredNodes)
                .force("link", d3.forceLink(filteredLinks).id(d => d.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(30));
            
            // Create links
            const link = g.append("g")
                .selectAll("line")
                .data(filteredLinks)
                .enter().append("line")
                .attr("class", "link")
                .attr("marker-end", "url(#arrow)");
            
            // Create link labels
            const linkLabel = g.append("g")
                .selectAll("text")
                .data(filteredLinks)
                .enter().append("text")
                .attr("class", "link-label")
                .text(d => d.label)
                .style("opacity", showLabels ? 1 : 0);
            
            // Create nodes
            const node = g.append("g")
                .selectAll("circle")
                .data(filteredNodes)
                .enter().append("circle")
                .attr("class", d => `node node-${d.type}`)
                .attr("r", d => d.type === 'agent' || d.type === 'mission' ? 15 : 10)
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended))
                .on("mouseover", showTooltip)
                .on("mouseout", hideTooltip)
                .on("click", handleNodeClick);
            
            // Create node labels
            const nodeLabel = g.append("g")
                .selectAll("text")
                .data(filteredNodes)
                .enter().append("text")
                .attr("class", "node-label")
                .text(d => d.label.length > 20 ? d.label.substring(0, 20) + "..." : d.label)
                .style("opacity", showLabels ? 1 : 0);
            
            // Update positions on tick
            simulation.on("tick", () => {
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                linkLabel
                    .attr("x", d => (d.source.x + d.target.x) / 2)
                    .attr("y", d => (d.source.y + d.target.y) / 2);
                
                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                
                nodeLabel
                    .attr("x", d => d.x)
                    .attr("y", d => d.y - 15);
            });
        }
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        function showTooltip(event, d) {
            const tooltip = document.getElementById('tooltip');
            tooltip.style.opacity = 1;
            tooltip.style.left = (event.pageX + 10) + 'px';
            tooltip.style.top = (event.pageY + 10) + 'px';
            tooltip.innerHTML = `
                <strong>${d.label}</strong><br>
                Type: ${d.type}<br>
                ID: ${d.id.substring(d.id.lastIndexOf('/') + 1)}
                ${d.metadata ? '<br>' + d.metadata : ''}
            `;
        }
        
        function hideTooltip() {
            document.getElementById('tooltip').style.opacity = 0;
        }
        
        function handleNodeClick(event, d) {
            console.log('Clicked node:', d);
            // Could open details panel or navigate to resource
        }
        
        function resetZoom() {
            svg.transition().duration(750).call(
                d3.zoom().transform,
                d3.zoomIdentity
            );
        }
        
        function centerGraph() {
            const width = window.innerWidth;
            const height = window.innerHeight - 100;
            svg.transition().duration(750).call(
                d3.zoom().transform,
                d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8)
            );
        }
        
        function toggleLabels() {
            showLabels = !showLabels;
            d3.selectAll('.node-label').style('opacity', showLabels ? 1 : 0);
            d3.selectAll('.link-label').style('opacity', showLabels ? 1 : 0);
        }
        
        function refreshData() {
            loadGraphData();
        }
        
        // Event listeners
        document.querySelectorAll('.filter').forEach(checkbox => {
            checkbox.addEventListener('change', renderGraph);
        });
        
        document.getElementById('search').addEventListener('input', renderGraph);
        
        // Initialize on load
        window.addEventListener('load', initGraph);
        window.addEventListener('resize', () => {
            const width = window.innerWidth;
            const height = window.innerHeight - 100;
            svg.attr('width', width).attr('height', height);
            simulation.force('center', d3.forceCenter(width / 2, height / 2));
            simulation.alpha(0.3).restart();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/graph')
async def get_graph():
    """Extract graph data from the Knowledge Graph"""
    
    # Load the persistent RDF file directly
    g = rdflib.Graph()
    g.parse('knowledge_graph_persistent.n3', format='n3')
    
    nodes = []
    links = []
    node_ids = set()
    
    # Process triples to create nodes and edges
    for s, p, o in g:
        s_str = str(s)
        p_str = str(p)
        o_str = str(o)
        
        # Determine node types
        def get_node_type(uri):
            uri_lower = uri.lower()
            if 'agent' in uri_lower or 'commander' in uri_lower:
                return 'agent'
            elif 'task' in uri_lower:
                return 'task'
            elif 'decision' in uri_lower:
                return 'decision'
            elif 'image' in uri_lower or 'midjourney' in uri_lower:
                return 'image'
            elif 'flier' in uri_lower:
                return 'flier'
            elif 'mission' in uri_lower:
                return 'mission'
            else:
                return 'default'
        
        # Add subject node
        if s_str not in node_ids and s_str.startswith('http'):
            node_ids.add(s_str)
            label = s_str.split('/')[-1].split('#')[-1]
            nodes.append({
                'id': s_str,
                'label': label[:50],
                'type': get_node_type(s_str)
            })
        
        # Add object node if it's a URI
        if isinstance(o, rdflib.URIRef) and o_str not in node_ids:
            node_ids.add(o_str)
            label = o_str.split('/')[-1].split('#')[-1]
            nodes.append({
                'id': o_str,
                'label': label[:50],
                'type': get_node_type(o_str)
            })
        
        # Add edge if object is a URI
        if isinstance(o, rdflib.URIRef):
            predicate_label = p_str.split('#')[-1].split('/')[-1]
            links.append({
                'source': s_str,
                'target': o_str,
                'label': predicate_label[:30]
            })
    
    # Filter for hot dog related nodes
    hot_dog_nodes = []
    hot_dog_ids = set()
    
    for node in nodes:
        if 'hot-dog' in node['id'].lower() or 'hot dog' in node['label'].lower():
            hot_dog_nodes.append(node)
            hot_dog_ids.add(node['id'])
    
    # Add connected nodes (1 degree of separation)
    for link in links:
        if link['source'] in hot_dog_ids:
            for node in nodes:
                if node['id'] == link['target'] and node['id'] not in hot_dog_ids:
                    hot_dog_nodes.append(node)
                    hot_dog_ids.add(node['id'])
        elif link['target'] in hot_dog_ids:
            for node in nodes:
                if node['id'] == link['source'] and node['id'] not in hot_dog_ids:
                    hot_dog_nodes.append(node)
                    hot_dog_ids.add(node['id'])
    
    # Filter links to only include those between our nodes
    hot_dog_links = [
        link for link in links 
        if link['source'] in hot_dog_ids and link['target'] in hot_dog_ids
    ]
    
    # If no hot dog specific data, return all data
    if not hot_dog_nodes:
        return jsonify({
            'nodes': nodes[:100],  # Limit to prevent browser overload
            'links': links[:200]
        })
    
    return jsonify({
        'nodes': hot_dog_nodes,
        'links': hot_dog_links
    })

if __name__ == '__main__':
    print("🌭 Starting Knowledge Graph Visualizer...")
    print("📍 Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=5000)
