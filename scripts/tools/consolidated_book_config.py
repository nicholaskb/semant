#!/usr/bin/env python3
"""
CONSOLIDATED BOOK GENERATOR CONFIGURATION
🎯 Configuration system for the unified book generator
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

class BookGeneratorConfig:
    """
    Configuration system for the consolidated book generator.

    Handles:
    - Environment variables
    - Default settings per mode
    - User preferences
    - Output configurations
    """

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file or "consolidated_book_config.json")
        self.config_dir = self.config_file.parent
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self._load_config()

        # Set environment-based defaults
        self._load_environment_defaults()

    def _load_config(self):
        """Load existing configuration or create defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"⚠️ Could not load config file: {e}")
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()
            self._save_config()

    def _load_environment_defaults(self):
        """Set defaults from environment variables."""
        # Midjourney settings
        self.config["midjourney"]["api_token"] = os.getenv("MIDJOURNEY_API_TOKEN", "")
        self.config["midjourney"]["process_mode"] = os.getenv("MIDJOURNEY_PROCESS_MODE", "relax")
        self.config["midjourney"]["default_version"] = os.getenv("MIDJOURNEY_VERSION", "v6")

        # GCS settings
        self.config["gcs"]["bucket_name"] = os.getenv("GCS_BUCKET_NAME", "")
        self.config["gcs"]["credentials_file"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

        # Output settings
        self.config["output"]["base_dir"] = os.getenv("BOOK_OUTPUT_DIR", "consolidated_books")
        self.config["output"]["auto_open"] = os.getenv("BOOK_AUTO_OPEN", "true").lower() == "true"

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration structure."""
        return {
            "version": "1.0.0",
            "created": "2025-01-23",

            "midjourney": {
                "api_token": "",
                "process_mode": "relax",  # relax, fast, turbo
                "default_version": "v6",  # v6, v7, niji
                "aspect_ratio": "16:9",
                "quality": "standard",
                "style": "vivid",
                "max_pages": 6,
                "timeout": 180
            },

            "gcs": {
                "bucket_name": "",
                "credentials_file": "",
                "auto_upload": True,
                "public_access": True
            },

            "output": {
                "base_dir": "consolidated_books",
                "auto_open": True,
                "format": ["html", "markdown", "json"],
                "include_images": True,
                "include_metadata": True
            },

            "modes": {
                "quick": {
                    "description": "Simple template editing",
                    "max_pages": 5,
                    "fallback_to_placeholders": True,
                    "auto_save_state": True
                },
                "universal": {
                    "description": "Any story with AI prompts",
                    "interactive": True,
                    "max_pages": 10,
                    "ai_prompt_generation": True
                },
                "one_click": {
                    "description": "Pre-built Quacky story",
                    "pages": 6,
                    "character_reference": True,
                    "auto_fallback": True
                },
                "complete": {
                    "description": "Full Quacky with KG integration",
                    "pages": 12,
                    "knowledge_graph": True,
                    "gcs_upload": True
                },
                "agent_tool": {
                    "description": "Programmatic agent use",
                    "max_pages": 6,
                    "knowledge_graph": True,
                    "cost_control": True
                }
            },

            "quality": {
                "image_resolution": "4K",
                "prompt_complexity": "high",
                "character_consistency": True,
                "style_consistency": True
            },

            "performance": {
                "rate_limiting": True,
                "batch_size": 3,
                "retry_attempts": 3,
                "timeout_seconds": 300
            }
        }

    def _save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save config: {e}")

    def get_mode_config(self, mode: str) -> Dict[str, Any]:
        """Get configuration for a specific mode."""
        return self.config.get("modes", {}).get(mode, {})

    def update_mode_config(self, mode: str, updates: Dict[str, Any]):
        """Update configuration for a specific mode."""
        if "modes" not in self.config:
            self.config["modes"] = {}
        if mode not in self.config["modes"]:
            self.config["modes"][mode] = {}

        self.config["modes"][mode].update(updates)
        self._save_config()

    def get_midjourney_config(self) -> Dict[str, Any]:
        """Get Midjourney-specific configuration."""
        return self.config.get("midjourney", {})

    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.config.get("output", {})

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Check required environment variables
        if not self.config["midjourney"]["api_token"]:
            issues.append("MIDJOURNEY_API_TOKEN not set")

        if not self.config["gcs"]["bucket_name"]:
            issues.append("GCS_BUCKET_NAME not set")

        return issues

    def print_config_summary(self):
        """Print a summary of the current configuration."""
        print("\n📋 CONSOLIDATED BOOK GENERATOR CONFIGURATION")
        print("=" * 60)

        print(f"📁 Config File: {self.config_file}")
        print(f"🎯 Version: {self.config.get('version', 'unknown')}")

        print("\n🖼️ Midjourney Settings:")
        mj = self.config.get("midjourney", {})
        print(f"  • Process Mode: {mj.get('process_mode', 'unknown')}")
        print(f"  • Default Version: {mj.get('default_version', 'unknown')}")
        print(f"  • Aspect Ratio: {mj.get('aspect_ratio', 'unknown')}")
        print(f"  • Max Pages: {mj.get('max_pages', 'unknown')}")

        print("\n📦 Storage Settings:")
        gcs = self.config.get("gcs", {})
        print(f"  • Bucket: {gcs.get('bucket_name', 'not set')}")
        print(f"  • Auto Upload: {gcs.get('auto_upload', False)}")

        print("\n📁 Output Settings:")
        output = self.config.get("output", {})
        print(f"  • Base Directory: {output.get('base_dir', 'unknown')}")
        print(f"  • Auto Open: {output.get('auto_open', False)}")
        print(f"  • Formats: {', '.join(output.get('format', []))}")

        # Show mode configurations
        print("\n📋 Mode Settings:")
        modes = self.config.get("modes", {})
        for mode, settings in modes.items():
            print(f"  • {mode.upper()}: {settings.get('description', 'No description')}")

        # Check for issues
        issues = self.validate_config()
        if issues:
            print("\n⚠️ Configuration Issues:")
            for issue in issues:
                print(f"  • {issue}")

        print("\n" + "=" * 60)


# 🎯 UTILITY FUNCTIONS

def get_config() -> BookGeneratorConfig:
    """Get the global configuration instance."""
    return BookGeneratorConfig()

def create_default_config():
    """Create a default configuration file."""
    config = BookGeneratorConfig()
    config._save_config()
    print(f"✅ Created default configuration at: {config.config_file}")

def validate_environment():
    """Validate that required environment variables are set."""
    config = BookGeneratorConfig()
    issues = config.validate_config()

    if issues:
        print("❌ Environment validation failed:")
        for issue in issues:
            print(f"  • {issue}")
        return False

    print("✅ Environment validation passed!")
    return True

def update_config(updates: Dict[str, Any]):
    """Update configuration with new values."""
    config = BookGeneratorConfig()
    config.config.update(updates)
    config._save_config()
    print("✅ Configuration updated")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        config = BookGeneratorConfig()
        config.print_config_summary()
    elif sys.argv[1] == "create":
        create_default_config()
    elif sys.argv[1] == "validate":
        validate_environment()
    elif sys.argv[1] == "update":
        if len(sys.argv) < 3:
            print("Usage: python3 consolidated_book_config.py update <json_file>")
        else:
            try:
                with open(sys.argv[2]) as f:
                    updates = json.load(f)
                update_config(updates)
            except Exception as e:
                print(f"Error updating config: {e}")
    else:
        print("Usage:")
        print("  python3 consolidated_book_config.py              # Show current config")
        print("  python3 consolidated_book_config.py create         # Create default config")
        print("  python3 consolidated_book_config.py validate       # Validate environment")
        print("  python3 consolidated_book_config.py update <file>  # Update from JSON file")
