# models/repositories/traffic_data_repository.py
from typing import Optional, List, Dict
from sqlalchemy import desc, func

from dal.models import TrafficData, Video
from .base_repository import BaseRepository


class TrafficDataRepository(BaseRepository[TrafficData]):
    """
    Repository for TrafficData operations
    """
    
    def __init__(self):
        super().__init__(TrafficData)
    
    def get_by_video_id(self, video_id: int) -> Optional[TrafficData]:
        """
        Get traffic data for a video
        
        Args:
            video_id: Video ID
            
        Returns:
            TrafficData or None
        """
        return self.session.query(TrafficData).filter(
            TrafficData.video_id == video_id
        ).first()
    
    def create_or_update(self, video_id: int, **kwargs) -> TrafficData:
        """
        Create or update traffic data for a video
        
        Args:
            video_id: Video ID
            **kwargs: Traffic data attributes
            
        Returns:
            TrafficData instance
        """
        try:
            traffic_data = self.get_by_video_id(video_id)
            
            if traffic_data:
                # Update existing
                for key, value in kwargs.items():
                    if hasattr(traffic_data, key):
                        setattr(traffic_data, key, value)
            else:
                # Create new
                traffic_data = TrafficData(video_id=video_id, **kwargs)
                self.session.add(traffic_data)
            
            self.session.commit()
            self.session.refresh(traffic_data)
            
            return traffic_data
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error creating/updating traffic data: {e}")
            raise
    
    def get_top_traffic_videos(self, limit: int = 10) -> List[Dict]:
        """
        Get videos with highest traffic
        
        Args:
            limit: Number of results
            
        Returns:
            List of dicts with video info and traffic counts
        """
        try:
            results = (
                self.session.query(
                    Video.id,
                    Video.file_name,
                    Video.processing_timestamp,
                    TrafficData.total_vehicles,
                    TrafficData.avg_vehicles_per_minute
                )
                .join(TrafficData, Video.id == TrafficData.video_id)
                .order_by(desc(TrafficData.total_vehicles))
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "video_id": r[0],
                    "file_name": r[1],
                    "processing_timestamp": r[2],
                    "total_vehicles": r[3],
                    "avg_vehicles_per_minute": r[4]
                }
                for r in results
            ]
        except Exception as e:
            self.logger.error(f"Error getting top traffic videos: {e}")
            raise
    
    def get_congestion_summary(self) -> Dict[str, int]:
        """
        Get summary of congestion levels across all videos
        
        Returns:
            Dict with congestion level counts
        """
        try:
            results = (
                self.session.query(
                    TrafficData.congestion_level,
                    func.count(TrafficData.id)
                )
                .group_by(TrafficData.congestion_level)
                .all()
            )
            
            return {level: count for level, count in results if level}
        except Exception as e:
            self.logger.error(f"Error getting congestion summary: {e}")
            raise
    
    def update_time_aggregations(self, video_id: int, 
                               minute_data: Dict, 
                               hour_data: Dict) -> Optional[TrafficData]:
        """
        Update time-based aggregations
        
        Args:
            video_id: Video ID
            minute_data: Minute aggregation data
            hour_data: Hour aggregation data
            
        Returns:
            Updated TrafficData
        """
        return self.create_or_update(
            video_id,
            minute_aggregations=minute_data,
            hour_aggregations=hour_data
        )
    
    def calculate_statistics(self, video_id: int) -> Dict:
        """
        Calculate comprehensive traffic statistics
        
        Args:
            video_id: Video ID
            
        Returns:
            Dict with calculated statistics
        """
        try:
            traffic_data = self.get_by_video_id(video_id)
            
            if not traffic_data:
                return {}
            
            stats = {
                "total_vehicles": traffic_data.total_vehicles,
                "vehicle_breakdown": traffic_data.get_vehicle_counts(),
                "avg_per_minute": traffic_data.avg_vehicles_per_minute,
                "peak_minute": traffic_data.peak_vehicles_per_minute,
                "congestion_level": traffic_data.congestion_level
            }
            
            # Add percentage breakdown
            if traffic_data.total_vehicles > 0:
                for vehicle_type, count in stats["vehicle_breakdown"].items():
                    if vehicle_type != "total":
                        percentage = (count / traffic_data.total_vehicles) * 100
                        stats[f"{vehicle_type}_percentage"] = round(percentage, 2)
            
            return stats
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {e}")
            raise