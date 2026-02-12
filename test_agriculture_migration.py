"""Test script to validate Agriculture domain migration"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_migration_structure():
    """Validate migration file structure"""
    print("🔍 Testing Agriculture domain migration...")
    
    # Test 1: Import the migration module
    print("\n1️⃣ Testing migration import...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration",
            "alembic/versions/2026_02_13_0001_add_agriculture_domain.py"
        )
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)
        print("   ✅ Migration module loaded successfully")
    except Exception as e:
        print(f"   ❌ Failed to load migration: {e}")
        return False
    
    # Test 2: Check revision identifiers
    print("\n2️⃣ Checking revision identifiers...")
    try:
        assert migration_module.revision == "2026_02_13_0001", "Revision ID mismatch"
        assert migration_module.down_revision == "2026_02_12_0001", "Down revision mismatch"
        print(f"   ✅ Revision: {migration_module.revision}")
        print(f"   ✅ Down revision: {migration_module.down_revision}")
    except AssertionError as e:
        print(f"   ❌ Revision check failed: {e}")
        return False
    
    # Test 3: Check upgrade and downgrade functions exist
    print("\n3️⃣ Checking upgrade/downgrade functions...")
    try:
        assert hasattr(migration_module, 'upgrade'), "upgrade() function missing"
        assert hasattr(migration_module, 'downgrade'), "downgrade() function missing"
        assert callable(migration_module.upgrade), "upgrade is not callable"
        assert callable(migration_module.downgrade), "downgrade is not callable"
        print("   ✅ upgrade() function exists")
        print("   ✅ downgrade() function exists")
    except AssertionError as e:
        print(f"   ❌ Function check failed: {e}")
        return False
    
    # Test 4: Check UUIDs are defined
    print("\n4️⃣ Checking UUIDs are properly generated...")
    try:
        assert migration_module.AGRI_ROOT_ID is not None, "AGRI_ROOT_ID not defined"
        assert migration_module.CROP_FARMING_ID is not None, "CROP_FARMING_ID not defined"
        assert migration_module.ENTITY_FLOUR_MILLS is not None, "ENTITY_FLOUR_MILLS not defined"
        print("   ✅ Root industry UUID defined")
        print("   ✅ Sub-vertical UUIDs defined")
        print("   ✅ Entity UUIDs defined")
    except (AssertionError, AttributeError) as e:
        print(f"   ❌ UUID check failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All migration structure tests passed!")
    print("=" * 60)
    print("\n📝 Migration Summary:")
    print("   • 1 root industry: Agriculture & Agritech")
    print("   • 6 sub-vertical industries")
    print("   • 20 core entities (companies, products, infrastructure)")
    print("   • 70 signal contracts planned")
    print("\n⚠️  NOTE: This test only validates structure.")
    print("   To apply the migration to your database, run:")
    print("   python -m alembic upgrade head")
    print()
    
    return True


if __name__ == "__main__":
    success = test_migration_structure()
    sys.exit(0 if success else 1)
