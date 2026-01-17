"""
Unit tests for payment service module.

Tests payment-related functions.
"""

import unittest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database.models import Base, User, Payment, PaymentStatus
from services.payment_service import create_invoice, handle_pre_checkout, handle_success
from services.user_service import add_user


class TestPaymentService(unittest.TestCase):
    """Test cases for payment service functions."""
    
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
    
    def test_create_invoice(self):
        """Test creating a payment invoice."""
        async def _test():
            # Mock bot
            bot = AsyncMock()
            bot.send_invoice = AsyncMock()
            
            # Create invoice
            await create_invoice(bot, chat_id=123456, months=1, provider_token="test_token")
            
            # Verify send_invoice was called
            bot.send_invoice.assert_called_once()
            call_args = bot.send_invoice.call_args[1]
            
            self.assertEqual(call_args['chat_id'], 123456)
            self.assertEqual(call_args['currency'], 'USD')
            self.assertIn('1 month', call_args['title'])
            self.assertEqual(call_args['provider_token'], 'test_token')
            
            # Verify payload
            payload_data = json.loads(call_args['payload'])
            self.assertEqual(payload_data['user_id'], 123456)
            self.assertEqual(payload_data['months'], 1)
        
        asyncio.run(_test())
    
    def test_create_invoice_multiple_months(self):
        """Test creating invoice for multiple months with discount."""
        async def _test():
            bot = AsyncMock()
            bot.send_invoice = AsyncMock()
            
            # Create invoice for 3 months
            await create_invoice(bot, chat_id=789012, months=3, provider_token="test_token")
            
            bot.send_invoice.assert_called_once()
            call_args = bot.send_invoice.call_args[1]
            
            # Verify discount pricing
            self.assertEqual(call_args['prices'][0].amount, 120000)  # $12.00 for 3 months
        
        asyncio.run(_test())
    
    def test_handle_pre_checkout(self):
        """Test handling pre-checkout query."""
        async def _test():
            import services.payment_service as ps
            import services.user_service as us
            original_session = ps.AsyncSessionLocal
            ps.AsyncSessionLocal = self.SessionLocal
            us.AsyncSessionLocal = self.SessionLocal
            
            try:
                # Create mock query
                query = AsyncMock()
                query.from_user.id = 123456
                query.total_amount = 50000
                query.currency = 'USD'
                query.provider_payment_charge_id = 'test_charge'
                query.invoice_payload = json.dumps({
                    'user_id': 123456,
                    'months': 1,
                    'timestamp': datetime.utcnow().isoformat()
                })
                query.answer = AsyncMock()
                
                # Handle pre-checkout
                await handle_pre_checkout(query)
                
                # Verify answer was called with ok=True
                query.answer.assert_called_once()
                call_args = query.answer.call_args[1]
                self.assertTrue(call_args['ok'])
                
                # Verify payment record was created
                async with self.SessionLocal() as session:
                    from sqlalchemy import select
                    result = await session.execute(select(Payment))
                    payments = result.scalars().all()
                    
                    self.assertEqual(len(payments), 1)
                    self.assertEqual(payments[0].user_id, 123456)
                    self.assertEqual(payments[0].amount, 50000)
                    self.assertEqual(payments[0].status, PaymentStatus.PENDING)
            finally:
                ps.AsyncSessionLocal = original_session
                us.AsyncSessionLocal = original_session
        
        asyncio.run(_test())
    
    def test_handle_success(self):
        """Test handling successful payment."""
        async def _test():
            import services.payment_service as ps
            import services.user_service as us
            original_session = ps.AsyncSessionLocal
            ps.AsyncSessionLocal = self.SessionLocal
            us.AsyncSessionLocal = self.SessionLocal
            
            try:
                # Add a user first
                user = User(
                    telegram_id=654321,
                    username="payuser",
                    first_name="Pay",
                    last_name="User"
                )
                await add_user(user)
                
                # Create a pending payment
                async with self.SessionLocal() as session:
                    payment = Payment(
                        user_id=654321,
                        amount=50000,
                        currency='USD',
                        status=PaymentStatus.PENDING,
                        provider='test'
                    )
                    session.add(payment)
                    await session.commit()
                
                # Create mock message with successful payment
                message = AsyncMock()
                message.from_user.id = 654321
                message.from_user.username = "payuser"
                message.from_user.first_name = "Pay"
                message.from_user.last_name = "User"
                message.answer = AsyncMock()
                
                successful_payment = Mock()
                successful_payment.invoice_payload = json.dumps({
                    'user_id': 654321,
                    'months': 1,
                    'timestamp': datetime.utcnow().isoformat()
                })
                successful_payment.total_amount = 50000
                successful_payment.provider_payment_charge_id = 'success_charge'
                
                message.successful_payment = successful_payment
                
                # Handle successful payment
                await handle_success(message)
                
                # Verify confirmation message was sent
                message.answer.assert_called_once()
                
                # Verify user is now premium
                from services.user_service import is_premium
                self.assertTrue(await is_premium(654321))
                
                # Verify payment status is updated
                async with self.SessionLocal() as session:
                    from sqlalchemy import select
                    result = await session.execute(
                        select(Payment).where(Payment.user_id == 654321)
                    )
                    payment = result.scalar_one()
                    
                    self.assertEqual(payment.status, PaymentStatus.SUCCESS)
                    self.assertIsNotNone(payment.paid_at)
            finally:
                ps.AsyncSessionLocal = original_session
                us.AsyncSessionLocal = original_session
        
        asyncio.run(_test())


if __name__ == '__main__':
    unittest.main()
