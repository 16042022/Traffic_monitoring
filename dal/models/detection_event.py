# dal/models/detection_event.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class DetectionEvent(Base):
    """
    Detection events table - stores individual vehicle crossing events
    Updated to support FR3.1.1 (individual traffic count events)
    """
    __tablename__ = 'detection_events'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to video
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Event details
    event_id = Column(String(50))  # Unique ID for tracking (e.g., "obj_123")
    frame_number = Column(Integer, nullable=False, index=True)
    timestamp_in_video = Column(Float, nullable=False, index=True)  # Seconds from video start
    
    # Object information
    object_type = Column(String(50), nullable=False, index=True)  # car, motorbike, truck, bus, person, etc.
    confidence_score = Column(Float)
    
    # Bounding box coordinates
    bbox_x = Column(Integer)
    bbox_y = Column(Integer)
    bbox_width = Column(Integer)
    bbox_height = Column(Integer)
    
    # For traffic counting - NEW
    crossed_line = Column(Boolean, default=False, index=True)  # Whether crossed virtual line
    crossing_direction = Column(String(20))  # up, down, left, right
    lane_id = Column(Integer)  # If multiple lanes
    
    # Entry point for tracking
    entry_x = Column(Float)
    entry_y = Column(Float)
    exit_x = Column(Float)
    exit_y = Column(Float)
    
    # Timestamp when recorded
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    video = relationship("Video", back_populates="detection_events")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_video_frame', 'video_id', 'frame_number'),
        Index('idx_video_time', 'video_id', 'timestamp_in_video'),
        Index('idx_video_object', 'video_id', 'object_type'),
        Index('idx_video_crossed', 'video_id', 'crossed_line'),
        Index('idx_time_interval', 'video_id', 'timestamp_in_video', 'object_type'),  # For time-based queries
    )
    
    def __repr__(self):
        return f"<DetectionEvent(id={self.id}, video_id={self.video_id}, object_type='{self.object_type}', frame={self.frame_number})>"
    
    @property
    def bbox(self):
        """Get bounding box as tuple"""
        return (self.bbox_x, self.bbox_y, self.bbox_width, self.bbox_height)
    
    @property
    def center(self):
        """Get center point of bounding box"""
        if all(v is not None for v in [self.bbox_x, self.bbox_y, self.bbox_width, self.bbox_height]):
            return (
                self.bbox_x + self.bbox_width // 2,
                self.bbox_y + self.bbox_height // 2
            )
        return None