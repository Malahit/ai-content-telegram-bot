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
from database.database import init_db
from database.models import UserRole, UserStatus
from services.user_service import register_or_get_user, update_user_role, add_log


async def create_admin(user_id: int, name: str):
    """Create an admin user"""
    print("Initializing database...")
    await init_db()
    
    print(f"\nCreating admin user:")
    print(f"  User ID: {user_id}")
    print(f"  Name: {name}")
    
    # Register or get user
    user = await register_or_get_user(
        telegram_id=user_id,
        first_name=name,
        role=UserRole.USER  # Start as USER, then upgrade
    )
    
    # Update to admin role
    print(f"\n⚙️  Setting admin role...")
    success = await update_user_role(user_id, UserRole.ADMIN)
    
    if success:
        print(f"✅ Admin user created successfully!")
        print(f"   You can now use admin commands in the bot.")
        
        # Log the action
        await add_log(user_id, "Admin user created via init_admin.py")
    else:
        print(f"❌ Failed to create admin user")


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
