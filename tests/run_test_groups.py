import pytest
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_execution.log'),
        logging.StreamHandler()
    ]
)

# Test groups configuration
TEST_GROUPS = {
    'group1_core_framework': [
        'test_agents.py',
        'test_agent_integrator.py',
        'test_agent_recovery.py'
    ],
    'group2_data_management': [
        'test_knowledge_graph.py',
        'test_workflow_persistence.py',
        'test_graph_optimizations.py',
        'test_graph_monitoring.py',
        'test_graph_performance.py',
        'test_remote_graph_manager.py',
        'test_graphdb_integration.py'
    ],
    'group3_capabilities': [
        'test_capability_management.py',
        'test_capability_handling.py',
        'test_integration_management.py',
        'test_dynamic_agents.py'
    ],
    'group4_workflows': [
        'test_workflow_manager.py',
        'test_reasoner.py',
        'test_consulting_agents.py'
    ],
    'group5_performance_security': [
        'test_performance.py',
        'test_security_audit.py',
        'test_prompt_agent.py'
    ],
    'group6_integration': [
        'test_main_api.py',
        'test_chat_endpoint.py',
        'test_research_agent.py'
    ]
}

class TestGroupRunner:
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_group(self, group_name, test_files):
        """Run a group of tests and return results."""
        logging.info(f"Starting test group: {group_name}")
        group_start = datetime.now()
        
        results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        for test_file in test_files:
            try:
                # Run pytest for the test file with asyncio mode
                exit_code = pytest.main([
                    f'tests/{test_file}',
                    '-v',
                    '--tb=short',
                    '--asyncio-mode=strict'
                ])
                
                if exit_code == 0:
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed: {test_file}")
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error in {test_file}: {str(e)}")
        
        group_end = datetime.now()
        duration = (group_end - group_start).total_seconds()
        
        self.results[group_name] = {
            **results,
            'duration': duration
        }
        
        logging.info(f"Completed test group: {group_name}")
        logging.info(f"Results: {results}")
        logging.info(f"Duration: {duration} seconds")
        
        return results['failed'] == 0
    
    def run_all_groups(self):
        """Run all test groups in sequence."""
        self.start_time = datetime.now()
        logging.info("Starting test execution")
        
        # Run groups in order
        for group_name, test_files in TEST_GROUPS.items():
            success = self.run_group(group_name, test_files)
            if not success:
                logging.error(f"Group {group_name} failed, stopping execution")
                break
        
        self.end_time = datetime.now()
        self._generate_report()
    
    def _generate_report(self):
        """Generate a test execution report."""
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        report = f"""
Test Execution Report
====================
Start Time: {self.start_time}
End Time: {self.end_time}
Total Duration: {total_duration} seconds

Group Results:
"""
        
        for group_name, results in self.results.items():
            report += f"""
{group_name}:
  Duration: {results['duration']} seconds
  Passed: {results['passed']}
  Failed: {results['failed']}
  Skipped: {results['skipped']}
"""
            if results['errors']:
                report += "  Errors:\n"
                for error in results['errors']:
                    report += f"    - {error}\n"
        
        # Save report
        with open('test_execution_report.txt', 'w') as f:
            f.write(report)
        
        logging.info("Test execution report generated")

def main():
    runner = TestGroupRunner()
    runner.run_all_groups()

if __name__ == '__main__':
    main() 