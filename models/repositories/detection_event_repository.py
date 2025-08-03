# models/repositories/detection_event_repository.py
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, text, Integer
from sqlalchemy.orm import Query

from dal.models import DetectionEvent
from .base_repository import BaseRepository


class DetectionEventRepository(BaseRepository[DetectionEvent]):
    """
    Repository for DetectionEvent operations
    Supports time-based queries for FR3.2.5-6
    """
    
    def __init__(self):
        super().__init__(DetectionEvent)
    
    def get_events_for_video(self, video_id: int, 
                            object_type: Optional[str] = None,
                            crossed_only: bool = False,
                            limit: Optional[int] = None) -> List[DetectionEvent]:
        """
        Get detection events for a video
        
        Args:
            video_id: Video ID
            object_type: Filter by object type
            crossed_only: Only events that crossed the line
            limit: Maximum number of results
            
        Returns:
            List of detection events
        """
        try:
            query = self.session.query(DetectionEvent).filter(
                DetectionEvent.video_id == video_id
            )
            
            if object_type:
                query = query.filter(DetectionEvent.object_type == object_type)
            
            if crossed_only:
                query = query.filter(DetectionEvent.crossed_line == True)
            
            query = query.order_by(DetectionEvent.timestamp_in_video)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            self.logger.error(f"Error getting events for video: {e}")
            raise
    
    def get_crossing_events(self, video_id: int) -> List[DetectionEvent]:
        """
        Get all line crossing events for a video
        
        Args:
            video_id: Video ID
            
        Returns:
            List of crossing events
        """
        return self.get_events_for_video(video_id, crossed_only=True)
    
    def count_by_type(self, video_id: int, crossed_only: bool = True) -> Dict[str, int]:
        """
        Count events by object type
        
        Args:
            video_id: Video ID
            crossed_only: Only count crossed events
            
        Returns:
            Dictionary with counts by type
        """
        try:
            query = self.session.query(
                DetectionEvent.object_type,
                func.count(DetectionEvent.id).label('count')
            ).filter(DetectionEvent.video_id == video_id)
            
            if crossed_only:
                query = query.filter(DetectionEvent.crossed_line == True)
            
            results = query.group_by(DetectionEvent.object_type).all()
            
            return {obj_type: count for obj_type, count in results}
        except Exception as e:
            self.logger.error(f"Error counting by type: {e}")
            raise
    
# Thêm method này vào class DetectionEventRepository để sửa lỗi

    def get_events_by_time_interval(self, video_id: int, 
                               interval_seconds: int = 60,
                               object_type: Optional[str] = None) -> Dict[int, Dict[str, int]]:
        """
        Get events aggregated by time interval (FR3.2.6)
        
        Args:
            video_id: Video ID
            interval_seconds: Interval size in seconds (default 60 for minutes)
            object_type: Filter by object type
            
        Returns:
            Dict with interval -> object_type -> count
        """
        try:            
            # Build query for interval aggregation
            # Sử dụng CAST để chuyển đổi timestamp_in_video / interval_seconds thành integer
            interval_expr = func.cast(
                DetectionEvent.timestamp_in_video / interval_seconds,
                type_=Integer
            ).label('interval')
            
            query = self.session.query(
                interval_expr,
                DetectionEvent.object_type,
                func.count(DetectionEvent.id).label('count')
            ).filter(
                DetectionEvent.video_id == video_id
            )
            
            if object_type:
                query = query.filter(DetectionEvent.object_type == object_type)
            
            # Group by interval and object_type
            results = query.group_by(interval_expr, DetectionEvent.object_type).all()
            
            # Format results as dict
            interval_data = {}
            for interval, obj_type, count in results:
                if interval not in interval_data:
                    interval_data[interval] = {}
                interval_data[interval][obj_type] = count
            
            return interval_data
            
        except Exception as e:
            self.logger.error(f"Error getting events by interval: {e}")
            # Return empty dict instead of raising to prevent crashes
            return {}

    def get_traffic_flow_timeline(self, video_id: int, 
                                interval_seconds: int = 60) -> List[Dict]:
        """
        Get traffic flow timeline with counts per interval
        
        Args:
            video_id: Video ID
            interval_seconds: Interval size
            
        Returns:
            List of dicts with interval info and counts
        """
        try:
            interval_data = self.get_events_by_time_interval(video_id, interval_seconds)
            
            # Handle empty data
            if not interval_data:
                return []
            
            timeline = []
            for interval, counts in sorted(interval_data.items()):
                timeline_entry = {
                    "interval": interval,
                    "start_time": interval * interval_seconds,
                    "end_time": (interval + 1) * interval_seconds,
                    "counts": counts,
                    "total": sum(counts.values()) if counts else 0
                }
                timeline.append(timeline_entry)
            
            return timeline
            
        except Exception as e:
            self.logger.error(f"Error getting traffic timeline: {e}")
            # Return empty list to prevent crashes
            return []

    def get_time_based_statistics(self, video_id: int, interval_minutes: int = 1) -> List[Dict]:
        """
        Get time-based statistics for a video
        
        Args:
            video_id: Video ID
            interval_minutes: Interval in minutes
            
        Returns:
            List of statistics by time interval
        """
        try:
            # Convert minutes to seconds
            interval_seconds = interval_minutes * 60
            
            # Get timeline data
            timeline = self.get_traffic_flow_timeline(video_id, interval_seconds)
            
            # Format for display
            formatted_stats = []
            for entry in timeline:
                formatted_entry = {
                    'interval': entry['interval'],
                    'time_range': f"{self._format_seconds(entry['start_time'])} - {self._format_seconds(entry['end_time'])}",
                    'vehicles': entry['counts'],
                    'total': entry['total']
                }
                formatted_stats.append(formatted_entry)
            
            return formatted_stats
            
        except Exception as e:
            self.logger.error(f"Error getting time-based statistics: {e}")
            return []

    def _format_seconds(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def get_peak_traffic_interval(self, video_id: int,
                                 interval_seconds: int = 60) -> Optional[Dict]:
        """
        Find peak traffic interval
        
        Args:
            video_id: Video ID
            interval_seconds: Interval size
            
        Returns:
            Dict with peak interval info
        """
        try:
            timeline = self.get_traffic_flow_timeline(video_id, interval_seconds)
            
            if not timeline:
                return None
            
            peak = max(timeline, key=lambda x: x['total'])
            return peak
        except Exception as e:
            self.logger.error(f"Error finding peak interval: {e}")
            raise
    
    def bulk_insert_detections(self, detections: List[Dict]) -> int:
        """
        Bulk insert detection events
        
        Args:
            detections: List of detection data
            
        Returns:
            Number of inserted records
        """
        try:
            # Use bulk_insert_mappings for performance
            self.session.bulk_insert_mappings(DetectionEvent, detections)
            self.session.commit()
            return len(detections)
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error bulk inserting detections: {e}")
            raise
    
    def get_entry_exit_points(self, video_id: int) -> Dict[str, List[Tuple[float, float]]]:
        """
        Get entry and exit points for tracked objects
        
        Args:
            video_id: Video ID
            
        Returns:
            Dict with entry and exit point lists
        """
        try:
            results = self.session.query(
                DetectionEvent.entry_x,
                DetectionEvent.entry_y,
                DetectionEvent.exit_x,
                DetectionEvent.exit_y
            ).filter(
                and_(
                    DetectionEvent.video_id == video_id,
                    DetectionEvent.crossed_line == True,
                    DetectionEvent.entry_x.isnot(None)
                )
            ).all()
            
            entry_points = []
            exit_points = []
            
            for entry_x, entry_y, exit_x, exit_y in results:
                if entry_x is not None and entry_y is not None:
                    entry_points.append((entry_x, entry_y))
                if exit_x is not None and exit_y is not None:
                    exit_points.append((exit_x, exit_y))
            
            return {
                "entry_points": entry_points,
                "exit_points": exit_points
            }
        except Exception as e:
            self.logger.error(f"Error getting entry/exit points: {e}")
            raise