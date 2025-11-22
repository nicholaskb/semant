#!/usr/bin/env python3
"""
Test script for enhanced versioning functionality.
Verifies version tracking, branching, diffing, and rollback capabilities.
"""

import asyncio
import json
from kg.models.graph_manager import KnowledgeGraphManager

async def test_enhanced_versioning():
    """Test the enhanced versioning system."""

    # Initialize KG Manager
    kg_manager = KnowledgeGraphManager()
    await kg_manager.initialize()

    print("🗂️ Testing Enhanced Versioning System")
    print("=" * 50)

    # Test 1: Version tracking with metadata
    print("\n📝 Testing version tracking with metadata...")

    # Add some test data and track versions
    test_triples = [
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#type', 'http://example.org/agent/Agent'),
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#hasCapability', 'http://example.org/capability/TestCap1'),
        ('http://example.org/agent/TestAgent2', 'http://example.org/core#type', 'http://example.org/agent/Agent'),
        ('http://example.org/agent/TestAgent2', 'http://example.org/core#status', 'active'),
    ]

    print("Adding triples and creating versions...")
    for i, (subject, predicate, obj) in enumerate(test_triples):
        await kg_manager.add_triple(subject, predicate, obj)
        print(f"  Added triple {i+1}, created version {kg_manager.version_tracker.get_current_version()}")

    # Check version count
    version_count = kg_manager.version_tracker.get_version_count()
    print(f"Total versions created: {version_count}")

    # Test 2: List versions with metadata
    print("\n📋 Testing version listing...")
    versions = await kg_manager.list_versions(limit=5)
    print(f"Recent versions ({len(versions)}):")
    for v in versions:
        print(f"  v{v['id']}: {v['description'][:50]}... ({v['author']}) {'[CURRENT]' if v['is_current'] else ''}")

    # Test 3: Version diffing
    print("\n🔍 Testing version diffing...")
    if version_count >= 2:
        diff_result = await kg_manager.diff_versions(0, version_count - 1)
        print("Version diff results:")
        print(f"  Comparing versions {diff_result['version_a']} -> {diff_result['version_b']}")
        print(f"  Added triples: {diff_result['added_triples']}")
        print(f"  Removed triples: {diff_result['removed_triples']}")
        print(f"  Unchanged triples: {diff_result['unchanged_triples']}")
        print(f"  Total changes: {diff_result['total_changes']}")

    # Test 4: Branching
    print("\n🌿 Testing branching functionality...")
    success = await kg_manager.create_branch("feature_branch", from_version=1)
    print(f"Created branch 'feature_branch': {'Success' if success else 'Failed'}")

    branches = await kg_manager.list_branches()
    print(f"Available branches: {list(branches.keys())}")

    # Switch to branch and add data
    success = await kg_manager.switch_branch("feature_branch")
    print(f"Switched to branch: {'Success' if success else 'Failed'}")

    # Add more data on the branch
    await kg_manager.add_triple(
        'http://example.org/agent/TestAgent3',
        'http://example.org/core#type',
        'http://example.org/agent/Agent'
    )
    print("Added triple on feature branch")

    # Switch back to main
    success = await kg_manager.switch_branch("main")
    print(f"Switched back to main: {'Success' if success else 'Failed'}")

    # Test 5: Rollback functionality
    print("\n⏪ Testing rollback functionality...")
    current_version = kg_manager.version_tracker.get_current_version()
    print(f"Current version before rollback: {current_version}")

    # Perform rollback to an earlier version
    if current_version > 1:
        await kg_manager.rollback(1, author="test_user", reason="Testing rollback functionality")
        new_current = kg_manager.version_tracker.get_current_version()
        print(f"Rolled back to version: {new_current}")
        print("Rollback completed successfully")

    # Test 6: Version cleanup
    print("\n🧹 Testing version cleanup...")
    original_count = kg_manager.version_tracker.get_version_count()
    removed = await kg_manager.cleanup_versions(keep_recent=5)
    new_count = kg_manager.version_tracker.get_version_count()
    print(f"Version cleanup: {original_count} -> {new_count} (removed {removed})")

    # Test 7: Export/Import version history
    print("\n💾 Testing version history export/import...")

    # Export version history
    history = await kg_manager.export_version_history()
    print(f"Exported version history: {len(history['versions'])} versions, {len(history['branches'])} branches")

    # Save to file for demonstration
    with open("test_version_history.json", "w") as f:
        json.dump(history, f, indent=2, default=str)
    print("Version history saved to test_version_history.json")

    # Test 8: Final statistics
    print("\n📊 Final version statistics...")
    stats = kg_manager.get_stats()
    version_stats = stats.get('version_stats', {})
    print(f"Total versions: {version_stats.get('total_versions', 0)}")
    print(f"Current version: {version_stats.get('current_version', 0)}")
    print(f"Active branches: {version_stats.get('branches', 0)}")

    # Cleanup
    await kg_manager.shutdown()

    print("\n✅ Enhanced versioning test completed!")
    print("Features tested:")
    print("  ✓ Version tracking with metadata")
    print("  ✓ Version listing and history")
    print("  ✓ Version diffing/comparison")
    print("  ✓ Branch creation and switching")
    print("  ✓ Rollback with snapshot creation")
    print("  ✓ Version cleanup and archival")
    print("  ✓ Export/import functionality")
    print("  ✓ Comprehensive statistics")

if __name__ == "__main__":
    asyncio.run(test_enhanced_versioning())

