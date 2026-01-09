"""
Database module for user management and logging.
Uses SQLAlchemy with SQLite for persistent storage.
"""
import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class User(Base):
    """User model for storing Telegram user data"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, nullable=False)  # Telegram user ID
    name = Column(Text, nullable=False)  # User's display name
    role = Column(Text, nullable=False, default='user')  # admin, user, guest
    status = Column(Text, nullable=False, default='active')  # active, banned
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', role='{self.role}', status='{self.status}')>"


class Log(Base):
    """Log model for audit trail of user actions"""
    __tablename__ = 'logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)  # Telegram user ID
    action = Column(Text, nullable=False)  # Description of action
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Log(id={self.id}, user_id={self.user_id}, action='{self.action}', timestamp={self.timestamp})>"


class Database:
    """Database manager with async support"""
    
    def __init__(self, db_url: str = "sqlite+aiosqlite:///bot_database.db"):
        """
        Initialize database connection.
        
        Args:
            db_url: Database connection URL (default: SQLite)
        """
        self.db_url = db_url
        self.engine = None
        self.async_session_maker = None
        
    async def init_db(self):
        """Initialize database connection and create tables"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.db_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
            )
            
            # Create session maker
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Database initialized successfully")
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    def get_session(self) -> AsyncSession:
        """Get a new database session"""
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self.async_session_maker()
    
    async def add_user(self, user_id: int, name: str, role: str = 'user', status: str = 'active') -> Optional[User]:
        """
        Add a new user to the database.
        
        Args:
            user_id: Telegram user ID
            name: User's display name
            role: User role (admin, user, guest)
            status: User status (active, banned)
            
        Returns:
            User object if successful, None otherwise
        """
        try:
            async with self.get_session() as session:
                # Check if user already exists
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    logger.info(f"User {user_id} already exists, skipping registration")
                    return existing_user
                
                # Create new user
                user = User(
                    id=user_id,
                    name=name,
                    role=role,
                    status=status
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                logger.info(f"✅ User added: {user}")
                return user
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error adding user {user_id}: {e}")
            return None
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting user {user_id}: {e}")
            return None
    
    async def update_user_role(self, user_id: int, role: str) -> bool:
        """
        Update user's role.
        
        Args:
            user_id: Telegram user ID
            role: New role (admin, user, guest)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return False
                
                old_role = user.role
                user.role = role
                await session.commit()
                
                logger.info(f"✅ User {user_id} role updated: {old_role} → {role}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error updating role for user {user_id}: {e}")
            return False
    
    async def update_user_status(self, user_id: int, status: str) -> bool:
        """
        Update user's status.
        
        Args:
            user_id: Telegram user ID
            status: New status (active, banned)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return False
                
                old_status = user.status
                user.status = status
                await session.commit()
                
                logger.info(f"✅ User {user_id} status updated: {old_status} → {status}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error updating status for user {user_id}: {e}")
            return False
    
    async def get_all_users(self) -> List[User]:
        """
        Get all users from the database.
        
        Returns:
            List of User objects
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(select(User))
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting all users: {e}")
            return []
    
    async def add_log(self, user_id: int, action: str) -> Optional[Log]:
        """
        Add a log entry.
        
        Args:
            user_id: Telegram user ID
            action: Description of the action
            
        Returns:
            Log object if successful, None otherwise
        """
        try:
            async with self.get_session() as session:
                log = Log(
                    user_id=user_id,
                    action=action
                )
                session.add(log)
                await session.commit()
                await session.refresh(log)
                
                logger.info(f"📝 Log added: user={user_id}, action='{action}'")
                return log
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error adding log: {e}")
            return None
    
    async def get_user_logs(self, user_id: int, limit: int = 100) -> List[Log]:
        """
        Get logs for a specific user.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of logs to retrieve
            
        Returns:
            List of Log objects
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(Log)
                    .where(Log.user_id == user_id)
                    .order_by(Log.timestamp.desc())
                    .limit(limit)
                )
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting logs for user {user_id}: {e}")
            return []
    
    async def get_all_logs(self, limit: int = 100) -> List[Log]:
        """
        Get all logs from the database.
        
        Args:
            limit: Maximum number of logs to retrieve
            
        Returns:
            List of Log objects
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(Log)
                    .order_by(Log.timestamp.desc())
                    .limit(limit)
                )
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting all logs: {e}")
            return []


# Global database instance
db = Database()
