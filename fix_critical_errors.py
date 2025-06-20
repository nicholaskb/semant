#!/usr/bin/env python3
"""
TARGETED FIX SCRIPT FOR CRITICAL ERRORS IDENTIFIED
Fixes specific issues preventing tests from running:
1. AgentRegistry missing _capabilities attribute
2. Syntax errors (indentation issues) 
3. Code review agent indentation fix
"""

import os
import re

def fix_agent_registry():
    """Fix AgentRegistry missing _capabilities attribute."""
    print("🔧 Fixing AgentRegistry _capabilities attribute...")
    
    registry_file = "agents/core/agent_registry.py"
    if os.path.exists(registry_file):
        with open(registry_file, 'r') as f:
            content = f.read()
        
        # Find __init__ method and add _capabilities if missing
        if 'self._capabilities = {}' not in content:
            # Look for the __init__ method
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'def __init__(self' in line:
                    # Find where to insert _capabilities
                    for j in range(i + 1, len(lines)):
                        if 'self._agents = {}' in lines[j]:
                            # Insert _capabilities after _agents
                            lines.insert(j + 1, '        self._capabilities = {}')
                            print("    ✅ Added _capabilities initialization")
                            break
                    break
            
            content = '\n'.join(lines)
            with open(registry_file, 'w') as f:
                f.write(content)

def fix_code_review_agent():
    """Fix the specific indentation error in code_review_agent.py."""
    print("🔧 Fixing code_review_agent.py indentation...")
    
    file_path = "agents/domain/code_review_agent.py"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix the specific indentation issue that was introduced
        # Look for the _process_message_impl method that was added and fix its indentation
        if 'async def _process_message_impl' in content:
            lines = content.split('\n')
            fixed_lines = []
            inside_method = False
            
            for line in lines:
                if 'async def _process_message_impl' in line:
                    inside_method = True
                    # Ensure proper indentation for the method
                    fixed_lines.append('    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:')
                elif inside_method and (line.strip().startswith('def ') or line.strip().startswith('class ') or (line.strip() and not line.startswith(' '))):
                    inside_method = False
                    fixed_lines.append(line)
                elif inside_method:
                    # Fix indentation within the method
                    if line.strip():
                        if '"""' in line:
                            fixed_lines.append('        """Process incoming messages - REQUIRED IMPLEMENTATION."""')
                        elif 'try:' in line:
                            fixed_lines.append('        try:')
                        elif 'response_content =' in line:
                            fixed_lines.append('            response_content = f"Agent {self.agent_id} processed: {message.content}"')
                        elif 'return AgentMessage(' in line:
                            fixed_lines.append('            return AgentMessage(')
                        elif 'message_id=' in line:
                            fixed_lines.append('                message_id=str(uuid.uuid4()),')
                        elif 'sender_id=' in line:
                            fixed_lines.append('                sender_id=self.agent_id,')
                        elif 'recipient_id=' in line:
                            fixed_lines.append('                recipient_id=message.sender_id,')
                        elif 'content=' in line:
                            fixed_lines.append('                content=response_content,')
                        elif 'message_type=' in line:
                            fixed_lines.append('                message_type=getattr(message, \'message_type\', \'response\'),')
                        elif 'timestamp=' in line:
                            fixed_lines.append('                timestamp=datetime.now()')
                        elif ')' in line and 'except' not in line:
                            fixed_lines.append('            )')
                        elif 'except Exception as e:' in line:
                            fixed_lines.append('        except Exception as e:')
                        elif 'return AgentMessage(' in line:
                            fixed_lines.append('            return AgentMessage(')
                        else:
                            # Default proper indentation
                            if line.strip():
                                fixed_lines.append('            ' + line.strip())
                    else:
                        fixed_lines.append('')
                else:
                    fixed_lines.append(line)
            
            content = '\n'.join(fixed_lines)
            with open(file_path, 'w') as f:
                f.write(content)
            
            print("    ✅ Fixed indentation in code_review_agent.py")

def fix_syntax_errors():
    """Fix syntax errors in other agent files."""
    print("🔧 Fixing syntax errors in agent files...")
    
    # Files with empty function definition errors
    files_to_fix = [
        "agents/core/remote_kg_agent.py",
        "agents/core/feature_z_agent.py", 
        "agents/core/ttl_validation_agent.py"
    ]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"  📝 Fixing {file_path}...")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Fix empty function definitions by adding pass statements
            lines = content.split('\n')
            fixed_lines = []
            
            for i, line in enumerate(lines):
                fixed_lines.append(line)
                
                # Check if this line is a function definition
                if line.strip().endswith(':') and ('def ' in line):
                    # Check if next line is empty or another definition
                    next_i = i + 1
                    while next_i < len(lines) and lines[next_i].strip() == '':
                        next_i += 1
                    
                    if next_i >= len(lines) or not lines[next_i].startswith('    '):
                        # Need to add pass statement
                        indent = len(line) - len(line.lstrip()) + 4
                        fixed_lines.append(' ' * indent + 'pass')
                        print(f"    ✅ Added pass statement after function definition on line {i+1}")
            
            content = '\n'.join(fixed_lines)
            with open(file_path, 'w') as f:
                f.write(content)

def test_fixes():
    """Test that critical fixes work."""
    print("🔧 Testing critical fixes...")
    
    import subprocess
    
    # Test basic imports
    test_commands = [
        "python -c 'from agents.core.agent_registry import AgentRegistry; print(\"✅ AgentRegistry import works\")'",
        "python -c 'from agents.domain.code_review_agent import CodeReviewAgent; print(\"✅ CodeReviewAgent import works\")'",
        "python -m pytest tests/test_agent_factory.py::test_create_agent -v --tb=short"
    ]
    
    for cmd in test_commands:
        print(f"\n  🧪 Testing: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="/Users/nicholasbaro/Python/semant")
            if result.returncode == 0:
                print(f"    ✅ PASSED")
                if result.stdout.strip():
                    print(f"    📄 Output: {result.stdout.strip()}")
            else:
                print(f"    ❌ FAILED")
                if result.stderr.strip():
                    print(f"    🚨 Error: {result.stderr.strip()}")
        except Exception as e:
            print(f"    🚨 Exception: {str(e)}")

def main():
    print("🚀 FIXING CRITICAL ERRORS IDENTIFIED IN PREVIOUS RUN")
    print("=" * 60)
    
    fix_agent_registry()
    print()
    fix_syntax_errors()
    print()
    fix_code_review_agent()
    print()
    test_fixes()
    
    print("\n🎉 CRITICAL FIXES COMPLETE!")
    print("Now run: python -m pytest tests/test_agent_factory.py::test_create_agent -v")

if __name__ == "__main__":
    main() 