#!/usr/bin/env python3
"""
Initial Admin Setup Script

This script helps set up the first admin user for the bot.
Run this once to create an admin account.

Usage:
    python3 setup_admin.py USER_ID FULL_NAME [USERNAME]

Example:
    python3 setup_admin.py 123456789 "John Doe" johndoe
    python3 setup_admin.py 123456789 "John Doe"
"""

import sys
import os

# Ensure we can import the database module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

def setup_admin():
    """Create the first admin user."""
    
    if len(sys.argv) < 3:
        print("❌ Error: Missing required arguments")
        print("\nUsage:")
        print("    python3 setup_admin.py USER_ID FULL_NAME [USERNAME]")
        print("\nExample:")
        print("    python3 setup_admin.py 123456789 'John Doe' johndoe")
        print("    python3 setup_admin.py 123456789 'John Doe'")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("❌ Error: USER_ID must be a number")
        sys.exit(1)
    
    full_name = sys.argv[2]
    username = sys.argv[3] if len(sys.argv) > 3 else None
    
    if len(full_name) < 2:
        print("❌ Error: Full name must be at least 2 characters")
        sys.exit(1)
    
    print("🔧 Admin Setup Script")
    print("=" * 50)
    print(f"User ID:   {user_id}")
    print(f"Full Name: {full_name}")
    print(f"Username:  {username or 'Not provided'}")
    print("=" * 50)
    
    # Initialize database
    print("\n1. Initializing database...")
    database.init_database()
    print("   ✅ Database initialized")
    
    # Check if user already exists
    existing_user = database.get_user(user_id)
    if existing_user:
        print(f"\n2. User already exists:")
        print(f"   Name: {existing_user['full_name']}")
        print(f"   Role: {existing_user['role']}")
        
        if existing_user['role'] == 'admin':
            print("\n   ⚠️ User is already an admin. No changes needed.")
            sys.exit(0)
        
        # Upgrade to admin
        print("\n3. Upgrading user to admin...")
        # Temporarily bypass the admin check by directly updating
        from datetime import datetime, timezone
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                UPDATE users 
                SET role = 'admin', updated_at = ?
                WHERE user_id = ?
            """, (now, user_id))
        print("   ✅ User upgraded to admin")
    else:
        # Register new admin user
        print("\n2. Registering new user...")
        success = database.register_user(user_id, username, full_name)
        if not success:
            print("   ❌ Failed to register user")
            sys.exit(1)
        print("   ✅ User registered")
        
        print("\n3. Setting admin role...")
        # Directly set admin role
        from datetime import datetime, timezone
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                UPDATE users 
                SET role = 'admin', updated_at = ?
                WHERE user_id = ?
            """, (now, user_id))
        print("   ✅ Admin role set")
    
    # Verify
    print("\n4. Verifying admin status...")
    is_admin = database.is_user_admin(user_id)
    if is_admin:
        print("   ✅ Admin status confirmed")
    else:
        print("   ❌ Admin status verification failed")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ Admin setup complete!")
    print("=" * 50)
    print(f"\n👤 {full_name} (ID: {user_id}) is now an admin")
    print("\nYou can now use admin commands in the bot:")
    print("  /set_role - Assign roles to users")
    print("  /list_users - View all users")
    print("  /ban - Ban users")
    print("  /unban - Unban users")
    print()

if __name__ == "__main__":
    setup_admin()
