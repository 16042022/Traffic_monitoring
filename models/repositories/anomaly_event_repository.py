# models/repositories/anomaly_event_repository.py
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc, func

from dal.models import AnomalyEvent
from .base_repository import BaseRepository


class AnomalyEventRepository(BaseRepository[AnomalyEvent]):
    """
    Repository for AnomalyEvent operations
    """
    
    def __init__(self):
        super().__init__(AnomalyEvent)
    
    def get_anomalies_for_video(self, video_id: int,
                               anomaly_type: Optional[str] = None,
                               severity: Optional[str] = None,
                               active_only: bool = False) -> List[AnomalyEvent]:
        """
        Get anomalies for a video with filters
        
        Args:
            video_id: Video ID
            anomaly_type: Filter by type
            severity: Filter by severity
            active_only: Only active anomalies
            
        Returns:
            List of anomaly events
        """
        try:
            query = self.session.query(AnomalyEvent).filter(
                AnomalyEvent.video_id == video_id
            )
            
            if anomaly_type:
                query = query.filter(AnomalyEvent.anomaly_type == anomaly_type)
            
            if severity:
                query = query.filter(AnomalyEvent.severity_level == severity)
            
            if active_only:
                query = query.filter(AnomalyEvent.alert_status == 'active')
            
            return query.order_by(AnomalyEvent.timestamp_in_video).all()
        except Exception as e:
            self.logger.error(f"Error getting anomalies: {e}")
            raise
    
    def count_by_type_and_severity(self, video_id: int) -> Dict[str, Dict[str, int]]:
        """
        Count anomalies by type and severity
        
        Args:
            video_id: Video ID
            
        Returns:
            Nested dict: type -> severity -> count
        """
        try:
            results = (
                self.session.query(
                    AnomalyEvent.anomaly_type,
                    AnomalyEvent.severity_level,
                    func.count(AnomalyEvent.id)
                )
                .filter(AnomalyEvent.video_id == video_id)
                .group_by(AnomalyEvent.anomaly_type, AnomalyEvent.severity_level)
                .all()
            )
            
            counts = {}
            for atype, severity, count in results:
                if atype not in counts:
                    counts[atype] = {}
                counts[atype][severity] = count
            
            return counts
        except Exception as e:
            self.logger.error(f"Error counting anomalies: {e}")
            raise
    
    def get_active_anomalies(self, limit: int = 50) -> List[AnomalyEvent]:
        """
        Get all active anomalies across all videos
        
        Args:
            limit: Maximum results
            
        Returns:
            List of active anomalies
        """
        try:
            return (
                self.session.query(AnomalyEvent)
                .filter(AnomalyEvent.alert_status == 'active')
                .order_by(desc(AnomalyEvent.created_at))
                .limit(limit)
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error getting active anomalies: {e}")
            raise
    
    def get_critical_anomalies(self, hours: int = 24) -> List[AnomalyEvent]:
        """
        Get critical anomalies from recent hours
        
        Args:
            hours: Look back period
            
        Returns:
            List of critical anomalies
        """
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            return (
                self.session.query(AnomalyEvent)
                .filter(and_(
                    AnomalyEvent.severity_level.in_(['high', 'critical']),
                    AnomalyEvent.created_at >= cutoff
                ))
                .order_by(desc(AnomalyEvent.created_at))
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error getting critical anomalies: {e}")
            raise
    
    def resolve_anomaly(self, anomaly_id: int) -> Optional[AnomalyEvent]:
        """
        Mark anomaly as resolved
        
        Args:
            anomaly_id: Anomaly ID
            
        Returns:
            Updated anomaly
        """
        anomaly = self.get_by_id(anomaly_id)
        if anomaly:
            anomaly.alert_status = 'resolved'
            anomaly.resolved_at = datetime.now()
            self.session.commit()
            self.session.refresh(anomaly)
        return anomaly
    
    def acknowledge_anomaly(self, anomaly_id: int) -> Optional[AnomalyEvent]:
        """
        Mark anomaly as acknowledged
        
        Args:
            anomaly_id: Anomaly ID
            
        Returns:
            Updated anomaly
        """
        return self.update(anomaly_id, alert_status='acknowledged')
    
    def get_anomaly_timeline(self, video_id: int) -> List[Dict]:
        """
        Get timeline of anomalies for a video
        
        Args:
            video_id: Video ID
            
        Returns:
            List of anomaly events with timing
        """
        try:
            anomalies = self.get_anomalies_for_video(video_id)
            
            timeline = []
            for anomaly in anomalies:
                timeline.append({
                    "id": anomaly.id,
                    "timestamp": anomaly.timestamp_in_video,
                    "type": anomaly.anomaly_type,
                    "severity": anomaly.severity_level,
                    "message": anomaly.alert_message,
                    "duration": anomaly.duration,
                    "status": anomaly.alert_status
                })
            
            return timeline
        except Exception as e:
            self.logger.error(f"Error getting anomaly timeline: {e}")
            raise
    
    def get_stopped_vehicle_events(self, video_id: int, 
                                  min_duration: float = 20.0) -> List[AnomalyEvent]:
        """
        Get stopped vehicle anomalies exceeding duration threshold
        
        Args:
            video_id: Video ID
            min_duration: Minimum stop duration in seconds
            
        Returns:
            List of stopped vehicle anomalies
        """
        try:
            return (
                self.session.query(AnomalyEvent)
                .filter(and_(
                    AnomalyEvent.video_id == video_id,
                    AnomalyEvent.anomaly_type == 'stopped_vehicle',
                    AnomalyEvent.duration >= min_duration
                ))
                .order_by(desc(AnomalyEvent.duration))
                .all()
            )
        except Exception as e:
            self.logger.error(f"Error getting stopped vehicles: {e}")
            raise
    
    def bulk_insert_anomalies(self, anomalies: List[Dict]) -> int:
        """
        Bulk insert anomaly events
        
        Args:
            anomalies: List of anomaly data
            
        Returns:
            Number of inserted records
        """
        try:
            self.session.bulk_insert_mappings(AnomalyEvent, anomalies)
            self.session.commit()
            return len(anomalies)
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error bulk inserting anomalies: {e}")
            raise

    def get_summary_by_video(self, video_id: int) -> Dict[str, Any]:
        """
        Get anomaly summary for a video
        
        Args:
            video_id: Video ID
            
        Returns:
            Summary dict with counts by type and severity
        """
        try:
            # Count anomalies by type
            type_counts = self.session.query(
                AnomalyEvent.anomaly_type,
                func.count(AnomalyEvent.id).label('count')
            ).filter(
                AnomalyEvent.video_id == video_id
            ).group_by(
                AnomalyEvent.anomaly_type
            ).all()
            
            # Count by severity
            severity_counts = self.session.query(
                AnomalyEvent.severity_level,
                func.count(AnomalyEvent.id).label('count')
            ).filter(
                AnomalyEvent.video_id == video_id
            ).group_by(
                AnomalyEvent.severity_level
            ).all()
            
            # Total count
            total = self.session.query(AnomalyEvent).filter(
                AnomalyEvent.video_id == video_id
            ).count()
            
            return {
                'total_anomalies': total,
                'by_type': {atype: count for atype, count in type_counts},
                'by_severity': {sev: count for sev, count in severity_counts}
            }
            
        except Exception as e:
            self.logger.error(f"Error getting anomaly summary: {e}")
            return {
                'total_anomalies': 0,
                'by_type': {},
                'by_severity': {}
            }
      
    def create(self, **kwargs) -> AnomalyEvent:
        """
        Create anomaly event with proper relationships
        """
        try:
            # Extract video_id if provided (for direct relationship)
            video_id = kwargs.get('video_id')
            
            # Create anomaly event
            anomaly = super().create(**kwargs)
            
            # If video_id provided but no detection_event_id, create detection event
            if video_id and not kwargs.get('detection_event_id'):
                # Create a detection event for this anomaly
                from .detection_event_repository import DetectionEventRepository
                detection_repo = DetectionEventRepository()
                
                detection = detection_repo.create(
                    video_id=video_id,
                    frame_number=kwargs.get('frame_number', 0),
                    timestamp_in_video=kwargs.get('timestamp_in_video', 0.0),
                    object_type='anomaly',
                    bbox_x=0,
                    bbox_y=0, 
                    bbox_width=0,
                    bbox_height=0,
                    confidence_score=1.0,
                    crossed_line=False,
                )
                
                # Update anomaly with detection_event_id
                anomaly.detection_event_id = detection.id
                self.session.commit()
                
            return anomaly
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error creating anomaly event: {e}")
            raise