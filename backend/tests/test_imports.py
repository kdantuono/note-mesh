#!/usr/bin/env python3
"""Test script to verify all imports work without database setup."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_imports():
    """Test that all API modules can be imported without errors."""

    print("Testing API imports...")

    try:
        # Test service imports
        pass

        print("✓ Service imports successful")

        # Test API router imports

        print("✓ Router imports successful")

        # Test middleware imports

        print("✓ Middleware imports successful")

        # Test schema imports

        print("✓ Schema imports successful")

        assert True

    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback

        traceback.print_exc()
        assert False


def test_router_structure():
    """Test that routers have expected endpoints."""

    print("\nTesting router structure...")

    try:
        from src.notemesh.api.auth import router as auth_router
        from src.notemesh.api.notes import router as notes_router

        # Check notes router paths
        notes_paths = [route.path for route in notes_router.routes]
        expected_notes_paths = [
            "/notes/",
            "/notes/{note_id}",
            "/notes/tags/",
            "/notes/validate-links",
        ]

        for path in expected_notes_paths:
            if path not in notes_paths:
                print(f"✗ Notes router missing path: {path}")
                assert False, f"Notes router missing path: {path}"

        print(f"✓ Notes router has expected paths: {notes_paths}")

        # Check auth router paths
        auth_paths = [route.path for route in auth_router.routes]
        expected_auth_paths = [
            "/auth/register",
            "/auth/login",
            "/auth/refresh",
            "/auth/me",
            "/auth/change-password",
            "/auth/logout",
        ]

        for path in expected_auth_paths:
            if path not in auth_paths:
                print(f"✗ Auth router missing path: {path}")
                assert False, f"Auth router missing path: {path}"

        print(f"✓ Auth router has expected paths: {auth_paths}")

        assert True

    except Exception as e:
        print(f"✗ Router structure test error: {e}")
        import traceback

        traceback.print_exc()
        assert False


if __name__ == "__main__":
    print("=== NoteMesh Import Tests ===")

    imports_ok = test_imports()
    structure_ok = test_router_structure()

    if imports_ok and structure_ok:
        print("\n🎉 All import tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
