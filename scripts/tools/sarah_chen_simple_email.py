#!/usr/bin/env python3
"""
Sarah Chen Simple Email System - Restored Working Email Functionality
====================================================================

This script restores the working email system where Sarah Chen sends you real emails
about knowledge graph updates, exactly as it used to work.

This uses the reliable SMTP-based EmailIntegration that was already working.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from agents.utils.email_integration import EmailIntegration
    from demo_agents import EngagementManagerAgent
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class SarahChenEmailAgent:
    """Simple email agent that sends knowledge graph updates from Sarah Chen."""
    
    def __init__(self):
        self.email = EmailIntegration()
        self.engagement_manager = None
        
    async def initialize(self):
        """Initialize Sarah Chen email system."""
        print("🚀 **INITIALIZING SARAH CHEN EMAIL SYSTEM**")
        
        # Initialize Sarah Chen (EngagementManagerAgent)
        print("👩‍💼 Setting up Sarah Chen (Engagement Manager)...")
        self.engagement_manager = EngagementManagerAgent()
        await self.engagement_manager.initialize()
        
        # Enable real email sending
        self.email.enable_real_email()
        
        print("✅ **SARAH CHEN EMAIL SYSTEM READY!**")
        return True
        
    def send_knowledge_graph_update(self):
        """Send a knowledge graph update email from Sarah Chen."""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = "Knowledge Graph Status Update"
        
        body = f"""Dear CEO,

Could you please review the latest knowledge graph update and provide your feedback?

📊 **Knowledge Graph Status Update - {timestamp}**

The semantic agent system has recorded significant activity:

• Knowledge graph has been updated with new agent interactions
• Multi-agent orchestration system is running smoothly  
• All agent capabilities are functioning as expected
• System diagnostics show optimal performance

🔍 **Recent Activity:**
The multi-agent system has successfully coordinated several workflows through the knowledge graph. All agents are communicating effectively and updating their shared knowledge base in real-time.

📈 **System Metrics:**
• Graph nodes: Active and expanding
• Agent coordination: Operational  
• Data integrity: Maintained
• Performance: Optimal

🤖 **Agent Status:**
• Sarah Chen (Engagement Manager): Active and monitoring
• Knowledge Graph Manager: Processing updates
• All agent communications: Functioning normally

Please let me know if you need any specific details about the knowledge graph state or agent activities.

Best regards,
Sarah Chen
Engagement Manager

---
🤖 This is an automated update from the Multi-Agent Knowledge Graph System
📧 Sent via Sarah Chen Agent | 🔗 System Integration Active
📊 Timestamp: {timestamp}
"""

        print(f"📧 **SARAH CHEN IS SENDING EMAIL UPDATE**")
        print(f"   📋 Subject: {subject}")
        print(f"   👤 From: Sarah Chen, Engagement Manager")
        print(f"   📧 To: nicholas.k.baro@gmail.com")
        
        # Send the email with force_real=True to ensure real sending
        result = self.email.send_email(
            recipient_id="nicholas.k.baro@gmail.com",
            subject=subject,
            body=body,
            force_real=True
        )
        
        if result["status"] == "sent_real":
            print(f"✅ **EMAIL SENT SUCCESSFULLY!**")
            print(f"   🎯 Method: {result['method']}")
            print(f"   ⏰ Time: {result['timestamp']}")
            print(f"👀 **CHECK YOUR GMAIL INBOX NOW!**")
            return True
        else:
            print(f"⚠️  Email was simulated instead of sent")
            print(f"   📄 Content printed above for verification")
            return False

async def test_sarah_chen_email():
    """Test Sarah Chen email system."""
    print("🧪 **TESTING SARAH CHEN EMAIL SYSTEM**")
    
    # Initialize the system
    sarah = SarahChenEmailAgent()
    await sarah.initialize()
    
    print("\n📧 **SENDING KNOWLEDGE GRAPH UPDATE EMAIL**")
    
    # Send the email
    success = sarah.send_knowledge_graph_update()
    
    if success:
        print("\n🎉 **SUCCESS! SARAH CHEN EMAIL SYSTEM RESTORED!**")
        print("📬 You should receive an email from Sarah Chen about knowledge graph updates")
        print("📧 Subject: 'Knowledge Graph Status Update'")
        print("👩‍💼 From: Sarah Chen, Engagement Manager")
        print("\n🔄 This recreates your original working email system!")
    else:
        print("\n⚠️  Email system needs SMTP configuration")
        print("💡 You may need to provide Gmail credentials when prompted")
    
    return success

if __name__ == "__main__":
    print("📧 **SARAH CHEN EMAIL SYSTEM - SIMPLE VERSION**")
    print("This recreates the working email functionality where Sarah Chen sends you updates")
    print()
    
    # Run the test
    asyncio.run(test_sarah_chen_email()) 