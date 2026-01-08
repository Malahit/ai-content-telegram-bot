#!/usr/bin/env python3
"""
Database setup script for AI Content Telegram Bot.
Run this script to initialize the database and create the first admin user.
"""
import asyncio
import sys
from database import db


async def setup_database():
    """Initialize the database."""
    print("🔧 Initializing database...")
    await db.init_db()
    print("✅ Database initialized successfully!")
    print(f"📁 Database file: {db.db_path}")
    

async def create_admin(user_id: int, name: str):
    """Create an admin user."""
    print(f"\n👑 Creating admin user...")
    success = await db.register_user(user_id, name, 'admin')
    if success:
        print(f"✅ Admin user created:")
        print(f"   ID: {user_id}")
        print(f"   Name: {name}")
        print(f"   Role: admin")
        print(f"   Status: active")
    else:
        print("❌ Failed to create admin user")
    

async def list_all_users():
    """List all users in the database."""
    users = await db.list_users()
    
    if not users:
        print("\n📋 No users in database")
        return
    
    print(f"\n👥 Users in database ({len(users)}):")
    print("-" * 60)
    for user in users:
        status_emoji = "✅" if user['status'] == 'active' else "🚫"
        role_emoji = "👑" if user['role'] == 'admin' else "👤" if user['role'] == 'user' else "👻"
        print(f"{status_emoji} {role_emoji} {user['name']}")
        print(f"   ID: {user['id']} | Role: {user['role']} | Status: {user['status']}")
        print(f"   Created: {user['created_at']}")
        print()


async def main():
    if len(sys.argv) < 2:
        print("🚀 AI Content Telegram Bot - Database Setup")
        print("\nUsage:")
        print("  python setup_db.py init                    - Initialize database")
        print("  python setup_db.py create_admin <id> <name> - Create admin user")
        print("  python setup_db.py list                    - List all users")
        print("\nExample:")
        print("  python setup_db.py init")
        print("  python setup_db.py create_admin 123456789 'John Admin'")
        print("  python setup_db.py list")
        return
    
    command = sys.argv[1]
    
    if command == "init":
        await setup_database()
    elif command == "create_admin":
        if len(sys.argv) < 4:
            print("❌ Error: Missing arguments")
            print("Usage: python setup_db.py create_admin <user_id> <name>")
            return
        
        try:
            user_id = int(sys.argv[2])
            name = sys.argv[3]
            await setup_database()  # Ensure DB exists
            await create_admin(user_id, name)
        except ValueError:
            print("❌ Error: user_id must be a number")
    elif command == "list":
        await list_all_users()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: init, create_admin, list")


if __name__ == "__main__":
    asyncio.run(main())
