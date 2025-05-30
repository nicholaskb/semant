from typing import List, Optional, Dict, Callable, Any
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
import time
from pydantic import Field, BaseModel
import uuid
import json
import openai
import logging
from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger

# Load environment variables
load_dotenv()

# Initialize OpenAI Client
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not found in environment variables.")

GPT_MODEL = "gpt-4"
EMBEDDING_MODEL = "text-embedding-3-large"

# Initialize OpenAI client
client = OpenAI()

class AgentMessage(BaseModel):
    """Base message model for agent communication."""
    sender: str
    recipient: str
    content: Dict[str, Any]
    timestamp: float
    message_type: str
    metadata: Optional[Dict[str, Any]] = None

class DiaryAgent:
    """A diary agent that can write and query diary entries using vector storage."""
    
    def __init__(
        self,
        name: str,
        instructions: str,
        diary_dir: str = "diary_entries",
        vector_name: Optional[str] = None,
        model: str = GPT_MODEL,
        auto_save_responses: bool = True
    ):
        self.name = name
        self.instructions = instructions
        self.diary: List[str] = []
        self.diary_dir = diary_dir
        self.diary_collection_name = f"{name.lower().replace(' ', '_')}_diary"
        self.vector_name = vector_name or f"{name.lower().replace(' ', '_')}_vector"
        self.model = model
        self.auto_save_responses = auto_save_responses
        
        # Create diary directory if it doesn't exist
        os.makedirs(diary_dir, exist_ok=True)
        
        # Initialize Qdrant client
        self.qdrant = QdrantClient(host="localhost", port=6333)
        
        # Create collection if it doesn't exist
        try:
            self.qdrant.get_collection(self.diary_collection_name)
        except Exception:
            self.qdrant.create_collection(
                collection_name=self.diary_collection_name,
                vectors_config={
                    self.vector_name: rest.VectorParams(
                        distance=rest.Distance.COSINE,
                        size=1536,  # OpenAI embedding size
                    )
                }
            )

    def embed_text(self, text: str) -> List[float]:
        """Create an embedding for the given text using OpenAI's embedding model."""
        response = client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding

    def write_to_diary(self, entry: str) -> None:
        """
        Write an entry to the diary:
        1. Upserting it into Qdrant
        2. Appending to the diary list
        3. Writing to local directory
        """
        try:
            logger.info(f"Writing entry to diary: {entry[:100]}...")
            
            # Create embedding
            embedding = self.embed_text(entry)
            
            # Upsert to Qdrant
            self.qdrant.upsert(
                collection_name=self.diary_collection_name,
                points=[
                    rest.PointStruct(
                        id=uuid.uuid4().hex,
                        vector={self.vector_name: embedding},
                        payload={"entry": entry},
                    )
                ],
            )
            
            # Add to local list
            self.diary.append(entry)
            
            # Write to file
            diary_file_path = os.path.join(
                self.diary_dir,
                f"{self.name.lower().replace(' ', '_')}_diary.txt"
            )
            with open(diary_file_path, "a") as f:
                f.write(entry + "\n")
                
            logger.info("Successfully wrote entry to diary")
            
        except Exception as e:
            logger.error(f"Error writing to diary: {str(e)}")
            raise

    def query_diary(self, query: str, top_k: int = 5) -> List[str]:
        """Query the diary for entries related to the provided query string."""
        try:
            # Create query embedding
            query_embedding = self.embed_text(query)
            
            # Search Qdrant
            results = self.qdrant.search(
                collection_name=self.diary_collection_name,
                query_vector=(self.vector_name, query_embedding),
                limit=top_k,
            )
            
            # Extract entries from results
            entries = [result.payload["entry"] for result in results]
            logger.info(f"Found {len(entries)} relevant diary entries")
            return entries
            
        except Exception as e:
            logger.error(f"Error querying diary: {str(e)}")
            return []

    def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and potentially save it to the diary."""
        try:
            # If auto-save is enabled and the message is substantial
            if self.auto_save_responses and len(str(message.content)) > 10:
                self.write_to_diary(str(message.content))
            
            # Process the message (implement your logic here)
            response_content = {
                "status": "processed",
                "message": "Message processed successfully"
            }
            
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content=response_content,
                timestamp=time.time(),
                message_type="response"
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return AgentMessage(
                sender=self.name,
                recipient=message.sender,
                content={"error": str(e)},
                timestamp=time.time(),
                message_type="error"
            )

    def list_tools(self) -> List[str]:
        """List the available tools/functions."""
        return ["write_to_diary", "query_diary"]

    def get_diary_summary(self) -> Dict[str, Any]:
        """Get a summary of the diary contents."""
        return {
            "total_entries": len(self.diary),
            "latest_entry": self.diary[-1] if self.diary else None,
            "diary_path": os.path.join(self.diary_dir, f"{self.name.lower().replace(' ', '_')}_diary.txt")
        } 