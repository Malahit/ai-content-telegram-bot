#!/usr/bin/env python3
"""
Initialize the first admin user for the bot.
This script should be run once to create the first admin account.

Usage:
    python init_admin.py <telegram_user_id> "<user_name>"

Example:
    python init_admin.py 123456789 "Admin Name"
"""

import asyncio
import sys
from database import db


async def create_admin(user_id: int, name: str):
    """Create an admin user"""
    print("Initializing database...")
    await db.init_db()
    
    print(f"\nCreating admin user:")
    print(f"  User ID: {user_id}")
    print(f"  Name: {name}")
    
    # Add user as admin
    user = await db.add_user(user_id, name, role='admin', status='active')
    
    if user:
        print(f"\n✅ Admin user created successfully!")
        print(f"   You can now use admin commands in the bot.")
        
        # Log the action
        await db.add_log(user_id, f"Admin user created via init_admin.py")
    else:
        # User might already exist, update their role
        print(f"\n⚠️  User already exists. Updating to admin role...")
        success = await db.update_user_role(user_id, 'admin')
        if success:
            print(f"✅ User role updated to admin!")
            await db.add_log(user_id, f"Role updated to admin via init_admin.py")
        else:
            print(f"❌ Failed to update user role")
    
    await db.close()


def main():
    if len(sys.argv) != 3:
        print("Usage: python init_admin.py <telegram_user_id> \"<user_name>\"")
        print("\nExample:")
        print("  python init_admin.py 123456789 \"Admin Name\"")
        print("\nTo find your Telegram user ID:")
        print("  1. Start a chat with @userinfobot on Telegram")
        print("  2. The bot will reply with your user ID")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        name = sys.argv[2]
    except ValueError:
        print("❌ Error: User ID must be a number")
        sys.exit(1)
    
    asyncio.run(create_admin(user_id, name))


if __name__ == "__main__":
    main()
