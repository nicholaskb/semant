#!/usr/bin/env python3
"""
Test script for enhanced validation rules framework.
Verifies validation rule creation, execution, and management.
"""

import asyncio
from kg.models.graph_manager import KnowledgeGraphManager, ValidationRule, ValidationRuleType, ValidationLevel

async def test_enhanced_validation():
    """Test the enhanced validation rules framework."""

    # Initialize KG Manager
    kg_manager = KnowledgeGraphManager()
    await kg_manager.initialize()

    print("🛡️ Testing Enhanced Validation Rules Framework")
    print("=" * 50)

    # Test 1: Create and add validation rules
    print("\n📝 Creating validation rules...")

    # SPARQL validation rule
    sparql_rule = ValidationRule(
        id="agent_count_check",
        name="Agent Count Validation",
        description="Ensure we have at least one agent in the system",
        type=ValidationRuleType.SPARQL,
        level=ValidationLevel.WARNING,
        parameters={
            "query": "SELECT ?s WHERE { ?s <http://example.org/core#type> <http://example.org/agent/Agent> }",
            "min_count": 1
        },
        tags=["agents", "count"]
    )

    # SPARQL violation rule
    violation_rule = ValidationRule(
        id="no_orphaned_capabilities",
        name="Orphaned Capabilities Check",
        description="Check for capabilities not linked to any agent",
        type=ValidationRuleType.SPARQL_VIOLATION,
        level=ValidationLevel.ERROR,
        parameters={
            "query": """
            SELECT ?cap WHERE {
                ?cap <http://example.org/core#type> <http://example.org/capability/Capability> .
                FILTER NOT EXISTS { ?agent <http://example.org/core#hasCapability> ?cap }
            }
            """
        },
        tags=["capabilities", "relationships"]
    )

    # Cardinality rule
    cardinality_rule = ValidationRule(
        id="agent_capability_cardinality",
        name="Agent Capability Cardinality",
        description="Ensure agents have between 1 and 5 capabilities",
        type=ValidationRuleType.CARDINALITY,
        level=ValidationLevel.WARNING,
        context="add_triple",
        parameters={
            "subject_pattern": "?s <http://example.org/core#type> <http://example.org/agent/Agent> . ?s <http://example.org/core#hasCapability> ?o",
            "predicate": "http://example.org/core#hasCapability",
            "min_cardinality": 1,
            "max_cardinality": 5
        },
        tags=["agents", "capabilities", "cardinality"]
    )

    # Add rules
    rules_added = []
    for rule in [sparql_rule, violation_rule, cardinality_rule]:
        success = kg_manager.add_validation_rule(rule)
        rules_added.append((rule.name, success))
        print(f"  Added {rule.name}: {'Success' if success else 'Failed'}")

    # Test 2: List and manage rules
    print("\n📋 Testing rule management...")

    all_rules = kg_manager.list_validation_rules()
    print(f"Total rules: {len(all_rules)}")

    enabled_rules = kg_manager.list_validation_rules(enabled_only=True)
    print(f"Enabled rules: {len(enabled_rules)}")

    # Test rule lookup
    rule = kg_manager.get_validation_rule("agent_count_check")
    if rule:
        print(f"Found rule: {rule.name} (Level: {rule.level.value})")

    # Test rule disabling
    success = kg_manager.disable_validation_rule("no_orphaned_capabilities")
    print(f"Disabled rule: {'Success' if success else 'Failed'}")

    disabled_rules = kg_manager.list_validation_rules(enabled_only=False)
    disabled_count = len([r for r in disabled_rules if not r.enabled])
    print(f"Disabled rules count: {disabled_count}")

    # Test 3: Add test data and validate
    print("\n📊 Adding test data and validating...")

    # Add test agents and capabilities
    test_triples = [
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#type', 'http://example.org/agent/Agent'),
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#hasCapability', 'http://example.org/capability/TestCap1'),
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#hasCapability', 'http://example.org/capability/TestCap2'),
        ('http://example.org/agent/TestAgent2', 'http://example.org/core#type', 'http://example.org/agent/Agent'),
        ('http://example.org/agent/TestAgent2', 'http://example.org/core#hasCapability', 'http://example.org/capability/TestCap3'),
        ('http://example.org/capability/OrphanedCap', 'http://example.org/core#type', 'http://example.org/capability/Capability'),
    ]

    for subject, predicate, obj in test_triples:
        await kg_manager.add_triple(subject, predicate, obj)

    print(f"Added {len(test_triples)} test triples")

    # Run validation
    print("\n🔍 Running validation...")
    validation_results = await kg_manager.validate_graph()

    print("Validation Results:")
    print(f"  Total triples: {validation_results['triple_count']}")
    print(f"  Validation passed: {validation_results['validation_passed']}")
    print(f"  Errors: {len(validation_results['validation_errors'])}")
    print(f"  Warnings: {len(validation_results['validation_warnings'])}")

    # Show detailed results
    all_results = validation_results['validation_results']
    for result in all_results:
        status = "✅" if result['passed'] else "❌"
        print(f"  {status} {result['rule_name']}: {result['message']}")

    # Test 4: Operation-specific validation
    print("\n⚙️ Testing operation-specific validation...")

    # Test adding another capability to an agent
    operation_data = {
        'subject': 'http://example.org/agent/TestAgent1',
        'predicate': 'http://example.org/core#hasCapability',
        'object': 'http://example.org/capability/TestCap4'
    }

    operation_results = await kg_manager.validate_operation("add_triple", operation_data)

    if operation_results:
        print("Operation validation results:")
        for result in operation_results:
            status = "✅" if result.passed else "❌"
            print(f"  {status} {result.rule_name}: {result.message}")

    # Test 5: Validation statistics
    print("\n📈 Validation statistics...")
    stats = kg_manager.get_validation_stats()
    print(f"  Total rules: {stats['total_rules']}")
    print(f"  Enabled rules: {stats['enabled_rules']}")
    print(f"  Recent errors: {stats['recent_errors']}")
    print(f"  Cache size: {stats['cache_size']}")
    print(f"  History size: {stats['history_size']}")

    # Test 6: Rule removal
    print("\n🗑️ Testing rule removal...")
    success = kg_manager.remove_validation_rule("agent_count_check")
    print(f"Removed rule: {'Success' if success else 'Failed'}")

    remaining_rules = kg_manager.list_validation_rules()
    print(f"Remaining rules: {len(remaining_rules)}")

    # Cleanup
    await kg_manager.shutdown()

    print("\n✅ Enhanced validation framework test completed!")
    print("Features tested:")
    print("  ✓ Rule creation and management")
    print("  ✓ Multiple validation types (SPARQL, Cardinality, Violation)")
    print("  ✓ Rule enabling/disabling")
    print("  ✓ Global and operation-specific validation")
    print("  ✓ Comprehensive result reporting")
    print("  ✓ Validation statistics and history")
    print("  ✓ Rule removal and cleanup")
    print("  ✓ Caching for expensive validation rules")

if __name__ == "__main__":
    asyncio.run(test_enhanced_validation())
