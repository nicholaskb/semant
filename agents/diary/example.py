from diary_agent import DiaryAgent, AgentMessage
import time

def main():
    # Create a diary agent
    agent = DiaryAgent(
        name="Personal Assistant",
        instructions="You are a personal assistant that helps users organize their thoughts and memories.",
        diary_dir="diary_entries",
        auto_save_responses=True
    )
    
    # Example 1: Write some entries to the diary
    entries = [
        "Today I learned about vector databases and their applications in AI.",
        "Had a productive meeting about the new project architecture.",
        "Started reading a new book about machine learning fundamentals."
    ]
    
    print("Writing entries to diary...")
    for entry in entries:
        agent.write_to_diary(entry)
        print(f"Wrote: {entry}")
    
    # Example 2: Query the diary
    print("\nQuerying diary for 'learning'...")
    results = agent.query_diary("learning")
    print("Found entries:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result}")
    
    # Example 3: Process a message
    print("\nProcessing a message...")
    message = AgentMessage(
        sender="user",
        recipient="Personal Assistant",
        content={"text": "Remember to follow up on the project proposal tomorrow."},
        timestamp=time.time(),
        message_type="reminder"
    )
    
    response = agent.process_message(message)
    print(f"Response: {response.content}")
    
    # Example 4: Get diary summary
    print("\nGetting diary summary...")
    summary = agent.get_diary_summary()
    print(f"Total entries: {summary['total_entries']}")
    print(f"Latest entry: {summary['latest_entry']}")
    print(f"Diary path: {summary['diary_path']}")

if __name__ == "__main__":
    main() 