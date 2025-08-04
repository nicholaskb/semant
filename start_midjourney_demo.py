#!/usr/bin/env python3
"""
Quick startup script for testing Midjourney integration.
This script checks your environment and starts the FastAPI server.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_environment():
    """Check if the environment is properly set up."""
    print("🔍 Checking environment setup...")
    
    # Check for MIDJOURNEY_API_TOKEN
    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        print("❌ MIDJOURNEY_API_TOKEN environment variable not set!")
        print("\nTo set it:")
        print("  export MIDJOURNEY_API_TOKEN='your-goapi-token-here'")
        print("\nOr create a .env file with:")
        print("  MIDJOURNEY_API_TOKEN=your-goapi-token-here")
        return False
    else:
        print("✅ MIDJOURNEY_API_TOKEN is set")
    
    # Check if required packages are installed
    try:
        import fastapi
        import httpx
        import uvicorn
        print("✅ Required packages are installed")
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        return False
    
    # Check if static files exist
    if not Path("static/chat.html").exists():
        print("❌ static/chat.html not found!")
        return False
    else:
        print("✅ Static files found")
    
    return True

def start_server():
    """Start the FastAPI server."""
    print("\n🚀 Starting FastAPI server...")
    print("\n" + "="*60)
    print("📍 Server will be available at: http://localhost:8000")
    print("🎨 Midjourney UI at: http://localhost:8000/static/chat.html")
    print("="*60 + "\n")
    
    # Start the server
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped.")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

def main():
    print("🎨 Midjourney Integration Demo Startup")
    print("="*40)
    
    if not check_environment():
        print("\n⚠️  Please fix the issues above before starting the server.")
        sys.exit(1)
    
    print("\n✅ All checks passed!")
    
    # Load .env file if it exists
    if Path(".env").exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("📄 Loaded .env file")
        except ImportError:
            print("ℹ️  python-dotenv not installed, skipping .env file")
    
    start_server()

if __name__ == "__main__":
    main() 