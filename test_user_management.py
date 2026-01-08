#!/usr/bin/env python3
"""
Test script for user management functionality.
This script tests the database operations and user management features.
"""
import asyncio
import os
import sys
import tempfile
from database import Database

# Use test database in temp directory
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "test_bot_users.db")


async def test_database_init():
    """Test 1: Database initialization"""
    print("📝 Test 1: Database initialization")
    db = Database(TEST_DB_PATH)
    await db.init_db()
    
    # Check if database file exists
    assert os.path.exists(TEST_DB_PATH), "Database file should exist"
    print("✅ Test 1 passed: Database initialized successfully\n")
    return db


async def test_user_registration(db):
    """Test 2: User registration"""
    print("📝 Test 2: User registration")
    
    # Register a new user
    success = await db.register_user(123456789, "Test User", "guest")
    assert success, "User registration should succeed"
    
    # Verify user exists
    user = await db.get_user(123456789)
    assert user is not None, "User should exist after registration"
    assert user['id'] == 123456789, "User ID should match"
    assert user['name'] == "Test User", "User name should match"
    assert user['role'] == "guest", "User role should be guest"
    assert user['status'] == "active", "User status should be active"
    
    print("✅ Test 2 passed: User registered successfully")
    print(f"   User: {user}\n")
    return user


async def test_user_role_update(db):
    """Test 3: Update user role"""
    print("📝 Test 3: Update user role")
    
    # Update role to user
    success = await db.update_user_role(123456789, "user")
    assert success, "Role update should succeed"
    
    # Verify role change
    user = await db.get_user(123456789)
    assert user['role'] == "user", "User role should be updated to user"
    
    # Update role to admin
    success = await db.update_user_role(123456789, "admin")
    assert success, "Role update to admin should succeed"
    
    user = await db.get_user(123456789)
    assert user['role'] == "admin", "User role should be updated to admin"
    
    print("✅ Test 3 passed: Role updated successfully")
    print(f"   New role: {user['role']}\n")


async def test_ban_unban(db):
    """Test 4: Ban and unban user"""
    print("📝 Test 4: Ban and unban user")
    
    # Ban user
    success = await db.ban_user(123456789)
    assert success, "Ban should succeed"
    
    user = await db.get_user(123456789)
    assert user['status'] == "banned", "User should be banned"
    
    # Unban user
    success = await db.unban_user(123456789)
    assert success, "Unban should succeed"
    
    user = await db.get_user(123456789)
    assert user['status'] == "active", "User should be active after unban"
    
    print("✅ Test 4 passed: Ban/unban functionality works")
    print(f"   Final status: {user['status']}\n")


async def test_list_users(db):
    """Test 5: List users"""
    print("📝 Test 5: List users")
    
    # Register additional users
    await db.register_user(987654321, "Another User", "user")
    await db.register_user(111222333, "Guest User", "guest")
    
    # List all users
    users = await db.list_users()
    assert len(users) == 3, f"Should have 3 users, got {len(users)}"
    
    # List only active users
    users_active = await db.list_users(status="active")
    assert len(users_active) == 3, "All users should be active"
    
    # Ban one user and list again
    await db.ban_user(111222333)
    users_active = await db.list_users(status="active")
    assert len(users_active) == 2, "Should have 2 active users after ban"
    
    users_banned = await db.list_users(status="banned")
    assert len(users_banned) == 1, "Should have 1 banned user"
    
    print("✅ Test 5 passed: User listing works correctly")
    print(f"   Total users: {len(users)}")
    print(f"   Active users: {len(users_active)}")
    print(f"   Banned users: {len(users_banned)}\n")


async def test_duplicate_registration(db):
    """Test 6: Duplicate registration (should update)"""
    print("📝 Test 6: Duplicate registration")
    
    # Register user with same ID but different name
    success = await db.register_user(123456789, "Updated Name", "user")
    assert success, "Update should succeed"
    
    user = await db.get_user(123456789)
    assert user['name'] == "Updated Name", "User name should be updated"
    # Role should remain as it was before (admin from earlier tests)
    assert user['role'] == "admin", "Role should not change on re-registration"
    
    print("✅ Test 6 passed: Duplicate registration updates user name")
    print(f"   Updated name: {user['name']}\n")


async def test_invalid_operations(db):
    """Test 7: Invalid operations"""
    print("📝 Test 7: Invalid operations")
    
    # Try to update role with invalid value
    success = await db.update_user_role(123456789, "invalid_role")
    assert not success, "Invalid role should fail"
    
    # Try to update status with invalid value
    success = await db.update_user_status(123456789, "invalid_status")
    assert not success, "Invalid status should fail"
    
    # Try to get non-existent user
    user = await db.get_user(999999999)
    assert user is None, "Non-existent user should return None"
    
    print("✅ Test 7 passed: Invalid operations handled correctly\n")


async def cleanup():
    """Clean up test database"""
    print("🧹 Cleaning up test database...")
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    print("✅ Cleanup complete\n")


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Running User Management Tests")
    print("=" * 60 + "\n")
    
    try:
        # Clean up before tests
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        
        db = await test_database_init()
        await test_user_registration(db)
        await test_user_role_update(db)
        await test_ban_unban(db)
        await test_list_users(db)
        await test_duplicate_registration(db)
        await test_invalid_operations(db)
        
        print("=" * 60)
        print("✅ All tests passed successfully!")
        print("=" * 60)
        
        return True
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup()


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
