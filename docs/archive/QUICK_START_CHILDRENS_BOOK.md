# 🚀 Quick Start: Children's Book Agentic Swarm

## For Agents: Access TaskMaster

```python
from agents.tools.taskmaster_accessor import get_taskmaster_accessor

# In any agent
tm = get_taskmaster_accessor()

# Get next task to work on
next_task = tm.get_next_task()
print(f"Next: {next_task['title']}")

# Check if a task is ready
if tm.are_dependencies_satisfied(101):
    print("Task 101 ready!")

# Get progress
progress = tm.get_task_progress()
print(f"{progress['completion_percentage']:.1f}% complete")
```

## For Developers: Manage Tasks

```bash
# View all tasks
task-master list

# View children's book tasks only
task-master list | grep -E "10[0-9]|11[0-2]"

# Show next task
task-master next

# Show specific task
task-master show 100

# Mark task complete
task-master set-status --id=100 --status=done

# Start work on a task
task-master set-status --id=100 --status=in-progress
```

## Task Workflow

**Current State:**
- ✅ Task 100 (KG Schema) - READY TO START
- 🚫 Tasks 101-112 - Blocked until 100 completes

**To Unblock Everything:**
1. Implement Task 100 (create `kg/schemas/childrens_book_ontology.ttl`)
2. Run: `task-master set-status --id=100 --status=done`
3. Task 101 automatically unblocks!
4. Continue sequentially

## File Locations

```
.taskmaster/
  tasks/
    tasks.json                    # All tasks stored here

agents/
  tools/
    taskmaster_accessor.py        # Agent access API
  domain/
    (create agents here)          # Tasks 101-110

kg/
  schemas/
    childrens_book_ontology.ttl   # Task 100 - CREATE THIS
  services/
    image_embedding_service.py    # ✅ Already done!

scripts/
  add_childrens_book_tasks.py     # ✅ Already ran
  verify_taskmaster_access.py     # Verification script
  generate_childrens_book.py      # Task 112 - CLI (future)
```

## Orchestrator Pattern

```python
class ChildrensBookOrchestrator(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__("book_orchestrator", **kwargs)
        self.tm = get_taskmaster_accessor()
    
    async def run(self):
        # Check prerequisites
        if not self.tm.are_dependencies_satisfied(101):
            raise RuntimeError("Need Task 100 complete!")
        
        # Execute workflow
        await self.download_images()    # Task 101
        await self.pair_images()        # Task 102
        await self.sequence_story()     # Task 103
        # ... etc
```

## Key Commands

```bash
# Start here
task-master show 100

# After implementing Task 100
task-master set-status --id=100 --status=done

# Check what's ready
task-master next

# View all children's book tasks
PYTHONPATH=$PWD python3 scripts/verify_taskmaster_access.py

# Read full docs
cat CHILDRENS_BOOK_TASKMASTER_SUMMARY.md
```

## Implementation Order

1. **Task 100** - KG Schema (no deps) ← **START HERE**
2. **Task 101** - Image Ingestion (deps: 100)
3. **Task 102** - Image Pairing (deps: 101)
4. **Task 103** - Story Sequencing (deps: 102)
5. **Task 104** - Color Arrangement (deps: 101)
6. **Task 105** - Grid Layout (deps: 104)
7. **Task 106** - Story Writer (deps: 103)
8. **Task 107** - Page Design (deps: 102, 105, 106)
9. **Task 108** - Design Review (deps: 107)
10. **Task 109** - PDF Generator (deps: 108)
11. **Task 110** - Orchestrator (deps: 101-109)
12. **Task 111** - Tests (deps: 110)
13. **Task 112** - CLI (deps: 110)

---

**Ready? Start with Task 100!** 🚀

```bash
task-master show 100
```

