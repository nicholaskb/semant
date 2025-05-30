from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main_agent import MainAgent
from typing import List
from fastapi.staticfiles import StaticFiles
import logging
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Semant Main Agent API")
app.mount("/static", StaticFiles(directory="static"), name="static")
main_agent = MainAgent()
logger = logging.getLogger(__name__)

class InvestigateRequest(BaseModel):
    topic: str

@app.post("/investigate")
async def investigate(request: InvestigateRequest):
    try:
        return await main_agent.handle_investigate(request.topic)
    except Exception as e:
        logger.error(f"/investigate endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class TraverseRequest(BaseModel):
    start_node: str
    max_depth: int = 2

@app.post("/traverse")
async def traverse(request: TraverseRequest):
    try:
        return await main_agent.handle_traverse(request.start_node, request.max_depth)
    except Exception as e:
        logger.error(f"/traverse endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class FeedbackRequest(BaseModel):
    feedback: str

@app.post("/feedback")
def feedback(request: FeedbackRequest):
    try:
        return main_agent.handle_feedback(request.feedback)
    except Exception as e:
        logger.error(f"/feedback endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    history: List[str] = []

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        return await main_agent.handle_chat(request.message, request.history)
    except Exception as e:
        logger.error(f"/chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/artifacts")
def list_artifacts():
    try:
        return [
            {
                "artifact_id": a.artifact_id,
                "content": a.content,
                "author": a.author,
                "timestamp": a.timestamp
            }
            for a in main_agent.artifacts
        ]
    except Exception as e:
        logger.error(f"/artifacts endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 