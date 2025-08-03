# models/repositories/video_repository.py
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy import desc, and_
from sqlalchemy.orm import joinedload, selectinload

from dal.models import Video
from .base_repository import BaseRepository


class VideoRepository(BaseRepository[Video]):
    """
    Repository for Video operations
    """
    
    def __init__(self):
        super().__init__(Video)
    
    def get_with_all_data(self, video_id: int) -> Optional[Video]:
        """
        Get video with all related data (eager loading)
        
        Args:
            video_id: Video ID
            
        Returns:
            Video with all relationships loaded
        """
        try:
            return (
                self.session.query(Video)
                .options(
                    joinedload(Video.traffic_data),
                    selectinload(Video.detection_events),
                    selectinload(Video.anomaly_events)
                )
                .filter(Video.id == video_id)
                .first()
            )
        except Exception as e:
            self.logger.error(f"Error getting video with data: {e}")
            raise
    
    def get_recent_videos(self, limit: int = 10, days: int = 30) -> List[Video]:
        """
        Get recently processed videos
        
        Args:
            limit: Number of videos to return
            days: Look back period in days
            
        Returns:
            List of recent videos
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            return (
                self.session.query(Video)
                .filter(Video.upload_timestamp >= cutoff_date)
                .order_by(desc(Video.upload_timestamp))
                .limit(limit)
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error getting recent videos: {e}")
            raise
    
    def get_by_status(self, status: str) -> List[Video]:
        """
        Get videos by processing status
        
        Args:
            status: Status (pending, processing, completed, failed)
            
        Returns:
            List of videos with given status
        """
        return self.filter_by(status=status)
    
    def get_completed_videos(self, include_stats: bool = True) -> List[Video]:
        """
        Get all completed videos
        
        Args:
            include_stats: Whether to include traffic statistics
            
        Returns:
            List of completed videos
        """
        try:
            query = self.session.query(Video).filter(Video.status == 'completed')
            
            if include_stats:
                query = query.options(joinedload(Video.traffic_data))
            
            return query.order_by(desc(Video.processing_timestamp)).all()
        except Exception as e:
            self.logger.error(f"Error getting completed videos: {e}")
            raise
    
    def search_videos(self, search_term: str) -> List[Video]:
        """
        Search videos by filename
        
        Args:
            search_term: Search term
            
        Returns:
            List of matching videos
        """
        try:
            return (
                self.session.query(Video)
                .filter(Video.file_name.ilike(f"%{search_term}%"))
                .order_by(desc(Video.upload_timestamp))
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error searching videos: {e}")
            raise
    
    def update_status(self, video_id: int, status: str, 
                     processing_duration: Optional[float] = None) -> Optional[Video]:
        """
        Update video processing status
        
        Args:
            video_id: Video ID
            status: New status
            processing_duration: Processing time in seconds
            
        Returns:
            Updated video
        """
        update_data = {"status": status}
        
        if status == "completed" and processing_duration:
            update_data["processing_timestamp"] = datetime.now()
            update_data["processing_duration"] = processing_duration
        
        return self.update(video_id, **update_data)
    
    def get_statistics(self) -> Dict:
        """
        Get overall video statistics
        
        Returns:
            Dictionary with statistics
        """
        try:
            total = self.count()
            completed = self.count(status='completed')
            failed = self.count(status='failed')
            processing = self.count(status='processing')
            pending = self.count(status='pending')
            
            # Average processing time for completed videos
            avg_time_result = (
                self.session.query(Video.processing_duration)
                .filter(and_(
                    Video.status == 'completed',
                    Video.processing_duration.isnot(None)
                ))
                .all()
            )
            
            avg_processing_time = 0
            if avg_time_result:
                times = [r[0] for r in avg_time_result if r[0]]
                avg_processing_time = sum(times) / len(times) if times else 0
            
            return {
                "total_videos": total,
                "completed": completed,
                "failed": failed,
                "processing": processing,
                "pending": pending,
                "average_processing_time": avg_processing_time
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            raise