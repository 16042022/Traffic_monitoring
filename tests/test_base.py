# tests/test_base.py
import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import from project modules
try:
    from dal.database import db_manager, Base
except ImportError:
    # If dal module not found, try direct import
    import dal
    from dal.database import db_manager, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class BaseTestCase(unittest.TestCase):
    """Base test case with database setup"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        # Use in-memory SQLite for tests
        cls.test_db_url = "sqlite:///:memory:"
        
    def setUp(self):
        """Set up before each test"""
        # Initialize test database
        db_manager.initialize(self.test_db_url, echo=False)
        db_manager.create_all_tables()
        
        # Get session
        self.session = db_manager.session
        
    def tearDown(self):
        """Clean up after each test"""
        # Clear all data
        self.session.rollback()
        self.session.close()
        
        # Drop all tables
        db_manager.drop_all_tables()
        db_manager.close()
        
    def create_test_video(self, **kwargs):
        """Helper to create test video"""
        from dal.models.video import Video
        
        defaults = {
            'file_name': 'test_video.mp4',
            'file_path': '/test/test_video.mp4',
            'duration': 300.0,
            'fps': 30.0,
            'resolution': '1920x1080',
            'frame_count': 9000,
            'status': 'completed'
        }
        defaults.update(kwargs)
        
        video = Video(**defaults)
        self.session.add(video)
        self.session.commit()
        return video


class MockDetection:
    """Mock detection object for testing"""
    
    def __init__(self, id, class_name, confidence, bbox, center=None):
        self.id = id
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox
        self.center = center or ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)