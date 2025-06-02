import pytest
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Import test groups from run_test_groups
from run_test_groups import TEST_GROUPS, TestGroupRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_group_execution.log'),
        logging.StreamHandler()
    ]
)

def run_single_group(group_name):
    """Run a single test group."""
    if group_name not in TEST_GROUPS:
        logging.error(f"Unknown test group: {group_name}")
        logging.info("Available groups:")
        for name in TEST_GROUPS.keys():
            logging.info(f"  - {name}")
        return False
    
    runner = TestGroupRunner()
    success = runner.run_group(group_name, TEST_GROUPS[group_name])
    
    if success:
        logging.info(f"Group {group_name} completed successfully")
    else:
        logging.error(f"Group {group_name} failed")
    
    return success

def main():
    parser = argparse.ArgumentParser(description='Run a specific test group')
    parser.add_argument('group', help='Name of the test group to run')
    args = parser.parse_args()
    
    run_single_group(args.group)

if __name__ == '__main__':
    main() 