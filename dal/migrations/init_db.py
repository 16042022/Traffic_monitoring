# dal/migrations/init_db.py
"""
Initial database setup script
Creates all tables and indexes
"""

import logging
import sys
from pathlib import Path
from sqlalchemy import text

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dal.database import db_manager
from dal.models import Video, DetectionEvent, TrafficData, AnomalyEvent


def init_database(db_url: str = "sqlite:///traffic_monitoring.db", 
                 drop_existing: bool = False):
    """
    Initialize database with all tables
    
    Args:
        db_url: Database URL
        drop_existing: Whether to drop existing tables
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize database
        logger.info(f"Initializing database: {db_url}")
        db_manager.initialize(db_url)
        
        # Drop existing tables if requested
        if drop_existing:
            logger.warning("Dropping existing tables...")
            db_manager.drop_all_tables()
        
        # Create all tables
        logger.info("Creating tables...")
        db_manager.create_all_tables()
        
        # Verify tables
        with db_manager.session_scope() as session:
            # Check if tables exist
            if db_url.startswith("sqlite"):
                result = session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
                tables = [r[0] for r in result]
            else:
                # PostgreSQL
                result = session.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                ).fetchall()
                tables = [r[0] for r in result]
            
            logger.info(f"Created tables: {tables}")
            
            # Check indexes
            if db_url.startswith("sqlite"):
                result = session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='index'")
                ).fetchall()
                indexes = [r[0] for r in result]
                logger.info(f"Created indexes: {indexes}")
        
        logger.info("Database initialization complete!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        db_manager.close()


def seed_test_data():
    """
    Seed database with test data
    """
    logger = logging.getLogger(__name__)
    
    try:
        db_manager.initialize()
        
        with db_manager.session_scope() as session:
            # Create test video
            video = Video(
                file_name="test_traffic_video.mp4",
                file_path="/videos/test_traffic_video.mp4",
                duration=300.0,  # 5 minutes
                fps=30.0,
                resolution="1920x1080",
                frame_count=9000,
                status="completed"
            )
            session.add(video)
            session.flush()  # Get video ID
            
            # Create traffic data
            traffic_data = TrafficData(
                video_id=video.id,
                total_vehicles=150,
                car_count=80,
                motorbike_count=50,
                truck_count=15,
                bus_count=5,
                avg_vehicles_per_minute=30,
                peak_vehicles_per_minute=45,
                congestion_level="medium"
            )
            session.add(traffic_data)
            
            logger.info("Test data seeded successfully!")
            
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize traffic monitoring database")
    parser.add_argument("--db-url", default="sqlite:///traffic_monitoring.db",
                       help="Database URL (default: sqlite:///traffic_monitoring.db)")
    parser.add_argument("--drop", action="store_true",
                       help="Drop existing tables before creating")
    parser.add_argument("--seed", action="store_true",
                       help="Seed test data after initialization")
    
    args = parser.parse_args()
    
    # Initialize database
    init_database(args.db_url, args.drop)
    
    # Seed test data if requested
    if args.seed:
        seed_test_data()
        
    print("Database setup complete!")