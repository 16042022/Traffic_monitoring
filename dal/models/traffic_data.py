# dal/models/traffic_data.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class TrafficData(Base):
    """
    Traffic data table - stores aggregated traffic statistics
    Supports time-based summaries (FR3.2.5)
    """
    __tablename__ = 'traffic_data'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to video (one-to-one)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Overall vehicle counts
    total_vehicles = Column(Integer, default=0)
    car_count = Column(Integer, default=0)
    motorbike_count = Column(Integer, default=0)
    truck_count = Column(Integer, default=0)
    bus_count = Column(Integer, default=0)
    
    # Traffic density metrics
    avg_vehicles_per_minute = Column(Float)
    peak_vehicles_per_minute = Column(Integer)
    peak_minute_timestamp = Column(Float)  # Timestamp of peak traffic
    
    # Time-based aggregations (stored as JSON)
    # Format: {"0": {"car": 5, "motorbike": 3}, "1": {...}, ...}
    minute_aggregations = Column(JSON)  # Counts per minute
    hour_aggregations = Column(JSON)    # Counts per hour
    
    # Lane-specific data (if applicable)
    lane_data = Column(JSON)  # {"lane_1": {"car": 10, ...}, ...}
    
    # Traffic flow metrics
    avg_speed = Column(Float)  # If speed detection is implemented
    congestion_level = Column(String(20))  # low, medium, high, very_high
    
    # Processing metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship
    video = relationship("Video", back_populates="traffic_data")
    
    def __repr__(self):
        return f"<TrafficData(id={self.id}, video_id={self.video_id}, total_vehicles={self.total_vehicles})>"
    
    def get_vehicle_counts(self):
        """Get vehicle counts as dictionary"""
        return {
            "car": self.car_count,
            "motorbike": self.motorbike_count,
            "truck": self.truck_count,
            "bus": self.bus_count,
            "total": self.total_vehicles
        }
    
    def get_minute_counts(self, minute: int):
        """Get counts for specific minute"""
        if self.minute_aggregations:
            return self.minute_aggregations.get(str(minute), {})
        return {}
    
    def get_hour_counts(self, hour: int):
        """Get counts for specific hour"""
        if self.hour_aggregations:
            return self.hour_aggregations.get(str(hour), {})
        return {}