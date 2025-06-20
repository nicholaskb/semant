#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to check command status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
    fi
}

# Create verification directory
VERIFICATION_DIR="verification_results"
mkdir -p $VERIFICATION_DIR

# Start verification process
echo -e "${YELLOW}Starting Agent System Verification${NC}"
echo "Results will be saved in $VERIFICATION_DIR/"

# 1. Documentation Verification
print_section "Documentation Verification"

# Check documentation files
echo "Checking documentation files..."
ls -l docs/developer_guide.md docs/technical_architecture.md README.md
check_status "Documentation files check"

# Check documentation content
echo "Checking documentation content..."
grep -n "## " docs/developer_guide.md > $VERIFICATION_DIR/developer_guide_sections.txt
grep -n "## " docs/technical_architecture.md > $VERIFICATION_DIR/technical_architecture_sections.txt
grep -n "## " README.md > $VERIFICATION_DIR/readme_sections.txt
check_status "Documentation content check"

# 2. Implementation Verification
print_section "Implementation Verification"

# Check core components
echo "Checking core components..."
ls -l agents/core/ agents/domain/ agents/utils/
check_status "Core components check"

# Run Python verification script
echo "Running Python verification script..."
python3 scripts/verify_implementation.py
check_status "Python verification script"

# 3. Test Coverage
print_section "Test Coverage"

# Run tests with coverage
echo "Running test suite..."
pytest tests/ -v --cov=agents > $VERIFICATION_DIR/test_results.txt
check_status "Test suite"

# 4. Code Quality
print_section "Code Quality"

# Run linting
echo "Running flake8..."
flake8 agents/ > $VERIFICATION_DIR/flake8_results.txt
check_status "Flake8"

echo "Running pylint..."
pylint agents/ > $VERIFICATION_DIR/pylint_results.txt
check_status "Pylint"

# 5. Generate Summary
print_section "Verification Summary"

# Count test results
TESTS_PASSED=$(grep -c "PASSED" $VERIFICATION_DIR/test_results.txt)
TESTS_FAILED=$(grep -c "FAILED" $VERIFICATION_DIR/test_results.txt)
TESTS_ERRORS=$(grep -c "ERROR" $VERIFICATION_DIR/test_results.txt)

# Count linting issues
FLAKE8_ISSUES=$(grep -c "^" $VERIFICATION_DIR/flake8_results.txt)
PYLINT_ISSUES=$(grep -c "^" $VERIFICATION_DIR/pylint_results.txt)

# Print summary
echo "Test Results:"
echo "  Passed: $TESTS_PASSED"
echo "  Failed: $TESTS_FAILED"
echo "  Errors: $TESTS_ERRORS"
echo
echo "Code Quality Issues:"
echo "  Flake8: $FLAKE8_ISSUES"
echo "  Pylint: $PYLINT_ISSUES"

# Final status
if [ $TESTS_FAILED -eq 0 ] && [ $TESTS_ERRORS -eq 0 ] && [ $FLAKE8_ISSUES -eq 0 ] && [ $PYLINT_ISSUES -eq 0 ]; then
    echo -e "\n${GREEN}✓ All verifications passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some verifications failed. Check $VERIFICATION_DIR/ for details.${NC}"
    exit 1
fi 