#!/usr/bin/env python3
"""
Quick verification script for brainrot pipeline setup.
Checks dependencies and verifies pipeline can initialize.
"""
import sys
from pathlib import Path

# Add user site-packages to path
import site
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

# Add workspace to path
workspace = Path(__file__).parent.parent.parent
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

def check_imports():
    """Check all required imports."""
    missing = []
    
    try:
        import dotenv
        print("✅ python-dotenv")
    except ImportError:
        missing.append("python-dotenv")
        print("❌ python-dotenv")
    
    try:
        import loguru
        print("✅ loguru")
    except ImportError:
        missing.append("loguru")
        print("❌ loguru")
    
    try:
        from google.cloud import bigquery
        print("✅ google-cloud-bigquery")
    except ImportError:
        missing.append("google-cloud-bigquery")
        print("❌ google-cloud-bigquery")
    
    try:
        from google.cloud import storage
        print("✅ google-cloud-storage")
    except ImportError:
        missing.append("google-cloud-storage")
        print("❌ google-cloud-storage")
    
    try:
        from googleapiclient.discovery import build
        print("✅ google-api-python-client")
    except ImportError:
        missing.append("google-api-python-client")
        print("❌ google-api-python-client")
    
    try:
        import pytrends
        print("✅ pytrends")
    except ImportError:
        missing.append("pytrends")
        print("❌ pytrends (optional)")
    
    try:
        import nltk
        print("✅ nltk")
    except ImportError:
        missing.append("nltk")
        print("❌ nltk")
    
    try:
        import better_profanity
        print("✅ better-profanity")
    except ImportError:
        missing.append("better-profanity")
        print("❌ better-profanity")
    
    return missing

def check_pipeline():
    """Check if pipeline can be imported."""
    try:
        from scripts.brainrot.main_pipeline import BrainRotPipeline
        pipeline = BrainRotPipeline(skip_images=True)
        print("✅ Pipeline initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Brainrot Pipeline Setup Verification")
    print("=" * 60)
    print()
    
    print("Checking dependencies...")
    missing = check_imports()
    print()
    
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        print("Install with: pip3 install " + " ".join(missing))
        print()
    
    print("Checking pipeline initialization...")
    pipeline_ok = check_pipeline()
    print()
    
    if pipeline_ok and not missing:
        print("=" * 60)
        print("✅ All checks passed! Pipeline is ready.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("⚠️  Some checks failed. See above for details.")
        print("=" * 60)
        sys.exit(1)
