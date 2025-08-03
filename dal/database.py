# dal/database.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
import logging
from typing import Optional
from contextlib import contextmanager

# Base class for all models
Base = declarative_base()

class DatabaseManager:
    """
    Quản lý database connection và sessions
    Singleton pattern để đảm bảo chỉ có 1 instance
    """
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def initialize(self, db_url: str = "sqlite:///traffic_monitoring.db", 
                  echo: bool = False):
        """
        Initialize database connection
        
        Args:
            db_url: Database URL (SQLite by default)
            echo: Whether to log SQL statements
        """
        if self._engine is not None:
            return
            
        self.logger.info(f"Initializing database: {db_url}")
        
        # Create engine with optimizations
        if db_url.startswith("sqlite"):
            # SQLite specific optimizations
            self._engine = create_engine(
                db_url,
                echo=echo,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 15
                }
            )
            
            # Enable SQLite optimizations
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL or other databases
            self._engine = create_engine(
                db_url,
                echo=echo,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True
            )
        
        # Create session factory
        self._session_factory = scoped_session(
            sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False
            )
        )
        
        self.logger.info("Database initialized successfully")
    
    def create_all_tables(self):
        """Create all tables in database"""
        if self._engine is None:
            raise RuntimeError("Database not initialized")
            
        Base.metadata.create_all(self._engine)
        self.logger.info("All tables created")
    
    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        if self._engine is None:
            raise RuntimeError("Database not initialized")
            
        Base.metadata.drop_all(self._engine)
        self.logger.info("All tables dropped")
    
    @property
    def engine(self):
        """Get database engine"""
        if self._engine is None:
            raise RuntimeError("Database not initialized")
        return self._engine
    
    @property
    def session(self):
        """Get database session"""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        return self._session_factory()
    
    @contextmanager
    def session_scope(self):
        """
        Provide transactional scope for database operations
        
        Usage:
            with db_manager.session_scope() as session:
                session.add(object)
        """
        session = self.session
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """Close database connections"""
        if self._session_factory:
            self._session_factory.remove()
        if self._engine:
            self._engine.dispose()
        
        self._engine = None
        self._session_factory = None
        
        self.logger.info("Database closed")


# Global instance
db_manager = DatabaseManager()