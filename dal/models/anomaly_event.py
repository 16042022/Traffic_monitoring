# dal/models/anomaly_event.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class AnomalyEvent(Base):
    """
    Anomaly events table - stores detected anomalies
    """
    __tablename__ = 'anomaly_events'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to video
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Anomaly details
    anomaly_type = Column(String(50), nullable=False, index=True)  # pedestrian, animal, obstacle, stopped_vehicle
    severity_level = Column(String(20), default='medium')  # low, medium, high, critical
    
    # Timing information
    timestamp_in_video = Column(Float, nullable=False, index=True)  # Seconds from video start
    duration = Column(Float)  # Duration of anomaly (for stopped vehicles)
    
    # Location information
    detection_area = Column(String(50))  # e.g., "lane_1", "intersection"
    bbox_x = Column(Integer)
    bbox_y = Column(Integer)
    bbox_width = Column(Integer)
    bbox_height = Column(Integer)
    
    # Detection details
    object_id = Column(String(50))  # Tracking ID if available
    object_class = Column(String(50))  # Specific class (e.g., "person", "dog", "debris")
    confidence_score = Column(Float)
    
    # Alert information
    alert_status = Column(String(20), default='active')  # active, acknowledged, resolved
    alert_message = Column(Text)
    
    # Additional metadata
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime)
    
    # Relationship
    video = relationship("Video", back_populates="anomaly_events")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_video_anomaly_type', 'video_id', 'anomaly_type'),
        Index('idx_video_anomaly_time', 'video_id', 'timestamp_in_video'),
        Index('idx_anomaly_severity', 'video_id', 'severity_level'),
        Index('idx_alert_status', 'alert_status'),
    )
    
    def __repr__(self):
        return f"<AnomalyEvent(id={self.id}, type='{self.anomaly_type}', severity='{self.severity_level}')>"
    
    @property
    def bbox(self):
        """Get bounding box as tuple"""
        return (self.bbox_x, self.bbox_y, self.bbox_width, self.bbox_height)
    
    @property
    def is_active(self):
        """Check if anomaly is still active"""
        return self.alert_status == 'active'
    
    def resolve(self):
        """Mark anomaly as resolved"""
        self.alert_status = 'resolved'
        self.resolved_at = func.now()