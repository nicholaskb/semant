#!/usr/bin/env python3

import os
import sys
import subprocess
import json
from typing import Dict, List, Any
from pathlib import Path

class ImplementationVerifier:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.docs_dir = self.root_dir / "docs"
        self.agents_dir = self.root_dir / "agents"
        self.tests_dir = self.root_dir / "tests"
        
    def check_documentation_files(self) -> Dict[str, bool]:
        """Check if all required documentation files exist."""
        required_files = [
            "docs/developer_guide.md",
            "docs/technical_architecture.md",
            "README.md"
        ]
        
        results = {}
        for file in required_files:
            path = self.root_dir / file
            results[file] = path.exists()
            
        return results
    
    def check_documentation_sections(self) -> Dict[str, List[str]]:
        """Check for key sections in documentation files."""
        results = {}
        for file in ["developer_guide.md", "technical_architecture.md", "README.md"]:
            path = self.docs_dir / file if file != "README.md" else self.root_dir / file
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()
                    sections = [line.strip() for line in content.split('\n') if line.startswith('## ')]
                    results[file] = sections
            else:
                results[file] = []
                
        return results
    
    def check_code_components(self) -> Dict[str, List[str]]:
        """Check for documented components in code."""
        results = {
            "classes": [],
            "functions": []
        }
        
        for root, _, files in os.walk(self.agents_dir):
            for file in files:
                if file.endswith('.py'):
                    path = Path(root) / file
                    with open(path, 'r') as f:
                        content = f.read()
                        for line in content.split('\n'):
                            if line.startswith('class '):
                                results["classes"].append(line.strip())
                            elif line.startswith('def '):
                                results["functions"].append(line.strip())
                                
        return results
    
    def run_tests(self) -> Dict[str, Any]:
        """Run the test suite."""
        try:
            result = subprocess.run(
                ["pytest", "tests/", "-v"],
                capture_output=True,
                text=True
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": str(e)
            }
    
    def check_code_quality(self) -> Dict[str, Any]:
        """Run code quality checks."""
        results = {}
        
        # Run flake8
        try:
            flake8_result = subprocess.run(
                ["flake8", "agents/"],
                capture_output=True,
                text=True
            )
            results["flake8"] = {
                "success": flake8_result.returncode == 0,
                "output": flake8_result.stdout
            }
        except Exception as e:
            results["flake8"] = {
                "success": False,
                "output": str(e)
            }
        
        # Run pylint
        try:
            pylint_result = subprocess.run(
                ["pylint", "agents/"],
                capture_output=True,
                text=True
            )
            results["pylint"] = {
                "success": pylint_result.returncode == 0,
                "output": pylint_result.stdout
            }
        except Exception as e:
            results["pylint"] = {
                "success": False,
                "output": str(e)
            }
            
        return results
    
    def verify_implementation(self) -> Dict[str, Any]:
        """Run all verification steps."""
        return {
            "documentation_files": self.check_documentation_files(),
            "documentation_sections": self.check_documentation_sections(),
            "code_components": self.check_code_components(),
            "tests": self.run_tests(),
            "code_quality": self.check_code_quality()
        }
    
    def print_results(self, results: Dict[str, Any]) -> None:
        """Print verification results in a readable format."""
        print("\n=== Implementation Verification Results ===\n")
        
        # Documentation Files
        print("Documentation Files:")
        for file, exists in results["documentation_files"].items():
            print(f"  {file}: {'✓' if exists else '✗'}")
        print()
        
        # Documentation Sections
        print("Documentation Sections:")
        for file, sections in results["documentation_sections"].items():
            print(f"\n  {file}:")
            for section in sections:
                print(f"    {section}")
        print()
        
        # Code Components
        print("Code Components:")
        print(f"  Classes: {len(results['code_components']['classes'])}")
        print(f"  Functions: {len(results['code_components']['functions'])}")
        print()
        
        # Tests
        print("Test Results:")
        print(f"  Success: {'✓' if results['tests']['success'] else '✗'}")
        if not results['tests']['success']:
            print("  Errors:")
            print(results['tests']['errors'])
        print()
        
        # Code Quality
        print("Code Quality:")
        for tool, result in results["code_quality"].items():
            print(f"  {tool}: {'✓' if result['success'] else '✗'}")
            if not result['success']:
                print(f"    {result['output']}")
        print()

def main():
    verifier = ImplementationVerifier()
    results = verifier.verify_implementation()
    verifier.print_results(results)
    
    # Save results to file
    with open('verification_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Exit with appropriate code
    sys.exit(0 if results['tests']['success'] else 1)

if __name__ == "__main__":
    main() 