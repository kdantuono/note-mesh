#!/usr/bin/env python3
"""Test script to verify API endpoints are properly configured."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_app_creation():
    """Test that the FastAPI app can be created without database connection."""

    print("Testing FastAPI app creation...")

    try:
        # Mock database functions to avoid DB connection
        import src.notemesh.database

        # Mock create_tables to do nothing
        async def mock_create_tables():
            print("Mock: Tables would be created here")
            pass

        # Replace the real function
        src.notemesh.database.create_tables = mock_create_tables

        # Import app
        from src.notemesh.main import app
        print("✓ FastAPI app created successfully")

        return True

    except Exception as e:
        print(f"✗ App creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_route_collection():
    """Test that all expected routes are registered."""

    print("\nTesting route collection...")

    try:
        # Mock database functions
        import src.notemesh.database

        async def mock_create_tables():
            pass

        src.notemesh.database.create_tables = mock_create_tables

        from src.notemesh.main import app

        # Collect all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                for method in route.methods:
                    routes.append((method, route.path))
            elif hasattr(route, 'path'):
                routes.append(('INCLUDE', route.path))

        # Expected key endpoints
        expected_endpoints = [
            ('POST', '/api/auth/register'),
            ('POST', '/api/auth/login'),
            ('GET', '/api/auth/me'),
            ('POST', '/api/notes/'),
            ('GET', '/api/notes/'),
            ('GET', '/api/search/notes'),
            ('GET', '/api/search/tags/suggest'),
            ('GET', '/api/health/'),
            ('POST', '/api/sharing/'),
            ('GET', '/api/sharing/'),
        ]

        print(f"Total routes found: {len(routes)}")

        missing_endpoints = []
        for method, path in expected_endpoints:
            found = False
            for route_method, route_path in routes:
                if route_method == method and route_path == path:
                    found = True
                    break

            if not found:
                missing_endpoints.append((method, path))

        if missing_endpoints:
            print(f"✗ Missing endpoints: {missing_endpoints}")
            return False

        print("✓ All expected endpoints found")

        # Print first few routes as sample
        print(f"Sample routes: {routes[:10]}")

        return True

    except Exception as e:
        print(f"✗ Route collection error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== NoteMesh API Endpoint Tests ===")

    app_ok = test_app_creation()
    routes_ok = test_route_collection()

    if app_ok and routes_ok:
        print("\n🎉 All API tests passed!")
        print("Note: Database-dependent tests require proper DB setup")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)