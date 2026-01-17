"""
Unit tests for user service module.

Tests user management and subscription functions.
"""

import unittest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database.models import Base, User
from services.user_service import add_user, get_user, activate_subscription, is_premium, count_premium


class TestUserService(unittest.TestCase):
    """Test cases for user service functions."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        cls.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )
        cls.SessionLocal = async_sessionmaker(
            cls.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    def setUp(self):
        """Set up test data before each test."""
        asyncio.run(self._setup_db())
    
    async def _setup_db(self):
        """Create tables for testing."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    def tearDown(self):
        """Clean up after each test."""
        asyncio.run(self._teardown_db())
    
    async def _teardown_db(self):
        """Drop tables after testing."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    def test_add_user(self):
        """Test adding a new user."""
        async def _test():
            # Override the session factory in user_service
            import services.user_service as us
            original_session = us.AsyncSessionLocal
            us.AsyncSessionLocal = self.SessionLocal
            
            try:
                user = User(
                    telegram_id=123456789,
                    username="testuser",
                    first_name="Test",
                    last_name="User"
                )
                
                added_user = await add_user(user)
                
                self.assertIsNotNone(added_user.id)
                self.assertEqual(added_user.telegram_id, 123456789)
                self.assertEqual(added_user.username, "testuser")
                self.assertFalse(added_user.is_premium)
            finally:
                us.AsyncSessionLocal = original_session
        
        asyncio.run(_test())
    
    def test_get_user(self):
        """Test retrieving a user by telegram_id."""
        async def _test():
            import services.user_service as us
            original_session = us.AsyncSessionLocal
            us.AsyncSessionLocal = self.SessionLocal
            
            try:
                # Add a user first
                user = User(
                    telegram_id=987654321,
                    username="getuser",
                    first_name="Get",
                    last_name="User"
                )
                await add_user(user)
                
                # Retrieve the user
                retrieved_user = await get_user(987654321)
                
                self.assertIsNotNone(retrieved_user)
                self.assertEqual(retrieved_user.telegram_id, 987654321)
                self.assertEqual(retrieved_user.username, "getuser")
                
                # Test non-existent user
                non_existent = await get_user(999999999)
                self.assertIsNone(non_existent)
            finally:
                us.AsyncSessionLocal = original_session
        
        asyncio.run(_test())
    
    def test_activate_subscription(self):
        """Test activating a user's subscription."""
        async def _test():
            import services.user_service as us
            original_session = us.AsyncSessionLocal
            us.AsyncSessionLocal = self.SessionLocal
            
            try:
                # Add a user first
                user = User(
                    telegram_id=111222333,
                    username="subuser",
                    first_name="Sub",
                    last_name="User"
                )
                await add_user(user)
                
                # Activate subscription for 1 month
                updated_user = await activate_subscription(111222333, months=1)
                
                self.assertIsNotNone(updated_user)
                self.assertTrue(updated_user.is_premium)
                self.assertIsNotNone(updated_user.subscription_end)
                
                # Check that subscription end is approximately 30 days from now
                expected_end = datetime.utcnow() + timedelta(days=30)
                time_diff = abs((updated_user.subscription_end - expected_end).total_seconds())
                self.assertLess(time_diff, 5)  # Within 5 seconds
                
                # Test extending subscription
                updated_user2 = await activate_subscription(111222333, months=1)
                self.assertIsNotNone(updated_user2)
                # Should be extended from previous end date
                expected_end2 = updated_user.subscription_end + timedelta(days=30)
                time_diff2 = abs((updated_user2.subscription_end - expected_end2).total_seconds())
                self.assertLess(time_diff2, 5)
            finally:
                us.AsyncSessionLocal = original_session
        
        asyncio.run(_test())
    
    def test_is_premium(self):
        """Test checking if user has premium access."""
        async def _test():
            import services.user_service as us
            original_session = us.AsyncSessionLocal
            us.AsyncSessionLocal = self.SessionLocal
            
            try:
                # Add a user
                user = User(
                    telegram_id=444555666,
                    username="premiumuser",
                    first_name="Premium",
                    last_name="User"
                )
                await add_user(user)
                
                # Initially not premium
                self.assertFalse(await is_premium(444555666))
                
                # Activate subscription
                await activate_subscription(444555666, months=1)
                
                # Should be premium now
                self.assertTrue(await is_premium(444555666))
                
                # Test non-existent user
                self.assertFalse(await is_premium(999999999))
            finally:
                us.AsyncSessionLocal = original_session
        
        asyncio.run(_test())
    
    def test_count_premium(self):
        """Test counting premium users."""
        async def _test():
            import services.user_service as us
            original_session = us.AsyncSessionLocal
            us.AsyncSessionLocal = self.SessionLocal
            
            try:
                # Initially zero
                count = await count_premium()
                self.assertEqual(count, 0)
                
                # Add non-premium user
                user1 = User(
                    telegram_id=100100100,
                    username="user1",
                    first_name="User",
                    last_name="One"
                )
                await add_user(user1)
                
                count = await count_premium()
                self.assertEqual(count, 0)
                
                # Add premium user
                user2 = User(
                    telegram_id=200200200,
                    username="user2",
                    first_name="User",
                    last_name="Two"
                )
                await add_user(user2)
                await activate_subscription(200200200, months=1)
                
                count = await count_premium()
                self.assertEqual(count, 1)
                
                # Add another premium user
                user3 = User(
                    telegram_id=300300300,
                    username="user3",
                    first_name="User",
                    last_name="Three"
                )
                await add_user(user3)
                await activate_subscription(300300300, months=1)
                
                count = await count_premium()
                self.assertEqual(count, 2)
            finally:
                us.AsyncSessionLocal = original_session
        
        asyncio.run(_test())


if __name__ == '__main__':
    unittest.main()
