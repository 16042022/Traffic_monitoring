# dal/models/video.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from ..database import Base


class Video(Base):
    """
    Video table - stores processed video information
    """
    __tablename__ = 'videos'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Video metadata
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))  # Full path to video file
    upload_timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Video properties
    duration = Column(Float, nullable=False)  # Duration in seconds
    fps = Column(Float, nullable=False)  # Frames per second
    resolution = Column(String(20))  # e.g., "1920x1080"
    frame_count = Column(Integer)
    
    # Processing metadata
    processing_timestamp = Column(DateTime)
    processing_duration = Column(Float)  # Processing time in seconds
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    
    # Storage path for processed results (if needed)
    storage_path = Column(String(500))
    
    # Relationships
    detection_events = relationship("DetectionEvent", back_populates="video", cascade="all, delete-orphan")
    traffic_data = relationship("TrafficData", back_populates="video", uselist=False, cascade="all, delete-orphan")
    anomaly_events = relationship("AnomalyEvent", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Video(id={self.id}, file_name='{self.file_name}', status='{self.status}')>"
    
    @property
    def duration_formatted(self):
        """Get duration in HH:MM:SS format"""
        if self.duration:
            hours = int(self.duration // 3600)
            minutes = int((self.duration % 3600) // 60)
            seconds = int(self.duration % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"