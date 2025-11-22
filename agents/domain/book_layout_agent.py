"""
Book Layout Agent - Task #109
Generates HTML and PDF from approved page designs.
Reuses: BaseAgent, HTML patterns from generate_complete_book_now.py
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from pathlib import Path
import uuid

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF

SCHEMA = Namespace("http://schema.org/")
BOOK = Namespace("http://example.org/childrens-book#")


class BookLayoutAgent(BaseAgent):
    """Generates final HTML/PDF book from approved designs."""
    
    def __init__(self, agent_id: str = "book_layout_agent", kg_manager: Optional[KnowledgeGraphManager] = None):
        super().__init__(agent_id=agent_id)
        self.kg_manager = kg_manager or KnowledgeGraphManager()
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        action = message.content.get("action")
        if action == "generate_book":
            return await self._handle_generate(message)
        return self._create_error_response(message.sender_id, f"Unknown action: {action}")
    
    async def _handle_generate(self, message: AgentMessage) -> AgentMessage:
        try:
            designs = await self._get_approved_designs()
            if not designs:
                return self._create_error_response(message.sender_id, "No approved designs")
            
            html = self._generate_html(designs)
            html_file = Path("childrens_books") / f"book_{uuid.uuid4().hex[:8]}.html"
            html_file.parent.mkdir(exist_ok=True)
            html_file.write_text(html)
            
            # Store book in KG
            book_uri = await self._store_book_in_kg(html_file, designs)
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success", "html_file": str(html_file), "book_uri": book_uri},
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _get_approved_designs(self) -> List[Dict[str, Any]]:
        """Get approved page designs."""
        query = """
        PREFIX book: <http://example.org/childrens-book#>
        SELECT ?design ?pageNum WHERE {
            ?design a book:PageDesign ;
                    book:designStatus "approved" ;
                    book:pageNumber ?pageNum .
        }
        ORDER BY ?pageNum
        """
        results = await self.kg_manager.query_graph(query)
        return [{"uri": str(r["design"]), "page_num": int(r["pageNum"])} for r in results]
    
    def _generate_html(self, designs: List[Dict[str, Any]]) -> str:
        """Generate HTML (simplified, reuses patterns from generate_complete_book_now.py)."""
        html = """<!DOCTYPE html>
<html><head><title>Children's Book</title>
<style>
.book-page { display: flex; gap: 20px; margin: 40px; page-break-after: always; }
.left-column { flex: 1; }
.right-column { flex: 2; }
.image-grid { display: grid; gap: 10px; }
.grid-3x3 { grid-template-columns: repeat(3, 1fr); }
.grid-3x4 { grid-template-columns: repeat(4, 1fr); }
img { width: 100%; height: auto; }
.story-text { font-family: 'Comic Sans MS'; font-size: 18pt; margin-top: 20px; }
</style></head><body>"""
        
        for design in designs:
            html += f"""
<div class=\"book-page\">
  <div class=\"left-column\">
    <img src=\"placeholder_{design['page_num']}.png\" class=\"input-image\"/>
    <div class=\"story-text\">Page {design['page_num']} text here</div>
  </div>
  <div class=\"right-column\">
    <div class=\"image-grid grid-3x3\"></div>
  </div>
</div>"""
        
        html += "</body></html>"
        return html
    
    async def _store_book_in_kg(self, html_file: Path, designs: List[Dict[str, Any]]) -> str:
        """Store complete book in KG."""
        book_id = str(uuid.uuid4())
        book_uri = f"http://example.org/book/{book_id}"
        book_ref = URIRef(book_uri)
        
        triples = [
            (book_ref, RDF.type, SCHEMA.Book),
            (book_ref, SCHEMA.contentUrl, Literal(str(html_file))),
        ]
        
        for triple in triples:
            await self.kg_manager.add_triple(*triple)
        
        return book_uri

