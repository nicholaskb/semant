# KG-Based Children's Book Creation Workflow

## Overview

This document explains the fully KG-persisted architecture for creating children's books with McKinsey agent reviews. The system uses:

1. **Scientific Workflow** (ResearchAgent + StoryWriterAgent) to plan and write stories
2. **Image Generation** (BookGeneratorTool) to create illustrations
3. **Judge Agents** (JudgeAgent) to review and select best images
4. **Knowledge Graph** for all persistence (no JSON files)
5. **Inter-Agent Communication** via KG messages
6. **Email Integration** for agent continuity and user interaction

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KGProjectManager                          │
│  - Project-level storage in Knowledge Graph                  │
│  - Workflow step tracking                                    │
│  - Agent note/message management                              │
│  - Context retrieval for resumption                          │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Scientific  │    │   Image     │    │  McKinsey   │
│  Workflow    │    │   Judge     │    │  Reviewer   │
│              │    │             │    │             │
│ ResearchAgent│    │ JudgeAgent  │    │ 4 Agents    │
│ StoryWriter  │    │             │    │             │
└──────────────┘    └──────────────┘    └──────────────┘
```

## How It Works

### 1. Scientific Workflow - Story Planning & Writing

**Phase:** Research → Writing

**Agents:**
- `ResearchAgent`: Researches children's book best practices
- `StoryWriterAgent`: Writes age-appropriate story text

**Process:**
1. ResearchAgent queries KG and external sources for writing guidelines
2. Findings stored in KG with project context
3. StoryWriterAgent uses findings to write story pages
4. All story pages stored in KG at project level
5. Diary entries logged for each agent action

**KG Storage:**
```turtle
<project:book_20250116_120000> core:hasWorkflowStep <project:book_20250116_120000/step/research> .
<project:book_20250116_120000/step/research> core:stepStatus "completed" .
<project:book_20250116_120000/step/research> core:stepResult "{...findings...}" .

agent:book_research_agent core:hasDiaryEntry _:diary1 .
_:diary1 core:message "Researched children's book best practices..." .
```

### 2. Image Generation

**Phase:** Illustration Creation

**Tools:**
- `BookGeneratorTool`: Generates images via Midjourney API

**Process:**
1. Creates prompts from story text
2. Generates images for each page
3. Uploads to GCS bucket
4. Stores image URLs in KG
5. Links images to project and pages

**KG Storage:**
```turtle
<project:book_20250116_120000> core:hasWorkflowStep <project:book_20250116_120000/step/image_generation> .
<project:book_20250116_120000/step/image_generation> core:stepResult "{...image_urls...}" .
```

### 3. Judge Workflow - Image Selection

**Phase:** Review & Selection

**Agents:**
- `JudgeAgent`: Reviews images against criteria

**Process:**
1. JudgeAgent evaluates each image based on:
   - Visual quality and clarity
   - Relevance to story text
   - Appeal to target audience (ages 5-10)
   - Artistic style consistency
   - Emotional resonance
2. Scores images (0-10)
3. Approves/rejects based on score threshold (≥7.0)
4. Stores judgments in KG
5. Selected images used for final book

**KG Storage:**
```turtle
<project:book_20250116_120000/step/judgment_page_1> core:stepResult "{...judgment...}" .
agent:image_judge_agent core:hasDiaryEntry _:judge_diary1 .
```

### 4. McKinsey Review

**Phase:** Strategic Assessment

**Agents:**
- `EngagementManagerAgent`: Overall coordination
- `StrategyLeadAgent`: Story quality review
- `ImplementationLeadAgent`: Design review
- `ValueRealizationLeadAgent`: Market value assessment

**Process:**
1. Each agent reviews specific aspects
2. Reviews stored in KG with project context
3. Agents can query KG for previous context
4. All diary entries persisted to KG

### 5. Persistence & Resumption

**Project-Level Storage:**
- All workflow steps stored in KG with project URI
- Agent messages/notes linked to project
- Diary entries linked to agents and project
- Context can be queried for resumption

**Resuming Workflow:**
```bash
python scripts/tools/create_book_with_mckinsey_review.py --project-id book_20250116_120000 --resume
```

**Context Retrieval:**
```python
context = await project_manager.get_project_context()
# Returns:
# - Project status
# - Completed workflow steps
# - Agent messages/notes
# - Previous reviews
```

### 6. Inter-Agent Communication

**Via KG Messages:**
```python
# Broadcast message to agents
message_id = await project_manager.broadcast_to_agents(
    message_type="image_review_request",
    content={"image_url": "...", "page": 1},
    target_capabilities=["DECISION_MAKING"]
)

# Leave note for specific agent
await project_manager.leave_note_for_agent(
    target_agent="image_judge_agent",
    note="Please prioritize artistic style consistency",
    note_type="instruction"
)
```

**KG Storage:**
```turtle
<message:uuid> core:messageType "image_review_request" .
<message:uuid> core:relatedToProject <project:book_20250116_120000> .
<message:uuid> core:targetCapability "DECISION_MAKING" .
```

### 7. Email Integration

**Agent Continuity:**
- Checks for email replies mentioning "mckinsey" or "science"
- Processes replies and generates responses using agents
- Stores interactions in KG as agent notes
- Enables agents to "pick up where they left off"

**Email Processing:**
```python
# Check for replies
emails = email_integration.receive_email(query="UNSEEN")

# Process McKinsey-related emails
if "mckinsey" in email_body:
    await project_manager.leave_note_for_agent(
        target_agent="engagement_manager",
        note=f"Email from {sender}: {email_body}",
        note_type="email_reply"
    )
    
    # Generate response using agents
    response = await reviewer._generate_mckinsey_response(email_body)
    email_integration.send_email(recipient=sender, body=response)
```

## User Interaction

### Resuming Workflow

If user wants to modify image selection:

1. **Query KG for project context:**
   ```python
   context = await project_manager.get_project_context()
   # Get all judgments
   judgments = [step for step in context["workflow_steps"] if "judgment" in step["step"]]
   ```

2. **Modify selections:**
   ```python
   # User can override judge decisions
   await project_manager.save_workflow_step(
       "user_image_override",
       "completed",
       {"page_3": "user_selected", "reason": "prefer brighter colors"}
   )
   ```

3. **Regenerate HTML:**
   ```python
   # Script will use user selections instead of judge selections
   final_images = user_selections if user_selections else selected_images
   ```

### Email Replies

Users can email replies mentioning "mckinsey" or "science":

- **McKinsey replies:** Processed by EngagementManagerAgent
- **Science replies:** Processed by ResearchAgent
- **All interactions:** Stored in KG as agent notes
- **Agents can:** Query KG to see previous email context

## KG Schema

### Project Structure
```turtle
@prefix core: <http://example.org/core#> .
@prefix project: <http://example.org/project/> .
@prefix agent: <http://example.org/agent/> .

# Project node
project:book_20250116_120000
    a core:Project ;
    core:projectTitle "Where Worlds Begin" ;
    core:status "active" ;
    core:hasWorkflowStep project:book_20250116_120000/step/research ;
    core:hasWorkflowStep project:book_20250116_120000/step/story_writing ;
    core:hasWorkflowStep project:book_20250116_120000/step/image_generation ;
    core:hasWorkflowStep project:book_20250116_120000/step/image_selection .

# Workflow step
project:book_20250116_120000/step/research
    a core:WorkflowStep ;
    core:stepName "research" ;
    core:stepStatus "completed" ;
    core:stepResult "{...JSON...}" .

# Agent diary entry
agent:book_research_agent
    core:hasDiaryEntry _:diary1 .

_:diary1
    core:message "Researched children's book best practices..." ;
    core:timestamp "2025-01-16T12:00:00" ;
    core:details "{...JSON...}" .

# Agent note
project:book_20250116_120000/note/uuid1
    a core:AgentNote ;
    core:relatedToProject project:book_20250116_120000 ;
    core:targetAgent "image_judge_agent" ;
    core:noteContent "Please prioritize artistic style consistency" ;
    core:noteType "instruction" .
```

## Usage

### Create New Book
```bash
python scripts/tools/create_book_with_mckinsey_review.py
```

### Resume Existing Project
```bash
python scripts/tools/create_book_with_mckinsey_review.py --project-id book_20250116_120000 --resume
```

### Query Project Context
```python
from scripts.tools.create_book_with_mckinsey_review import KGProjectManager
from kg.models.graph_manager import KnowledgeGraphManager

kg = KnowledgeGraphManager(persistent_storage=True)
await kg.initialize()

project_manager = KGProjectManager(kg, "book_20250116_120000")
context = await project_manager.get_project_context()

print(f"Status: {context['status']}")
print(f"Steps: {len(context['workflow_steps'])}")
print(f"Messages: {len(context['agent_messages'])}")
```

## Key Features

✅ **Full KG Persistence** - No JSON files, everything in Knowledge Graph  
✅ **Scientific Workflow** - ResearchAgent + StoryWriterAgent for story creation  
✅ **Judge Agents** - Automated image review and selection  
✅ **Project-Level Storage** - All work linked to project URI  
✅ **Context Retrieval** - Agents can query KG for project progress  
✅ **Inter-Agent Communication** - Agents leave notes and broadcast messages via KG  
✅ **Email Integration** - Agents respond to email replies  
✅ **Workflow Resumption** - Can resume from any point using project ID  
✅ **Diary Persistence** - All agent diary entries stored in KG  

## Benefits

1. **No Data Loss** - Everything persisted in KG, can resume anytime
2. **Agent Continuity** - Agents can query KG to see what happened before
3. **User Control** - Users can modify selections and resume workflow
4. **Inter-Agent Collaboration** - Agents can leave notes for each other
5. **Email Integration** - Agents can respond to user emails
6. **Full Audit Trail** - All actions logged in KG with timestamps

