# tests/test_anomaly_event_repository.py
import unittest
from datetime import datetime, timedelta

from test_base import BaseTestCase
from models.repositories import AnomalyEventRepository
from dal.models import AnomalyEvent


class TestAnomalyEventRepository(BaseTestCase):
    """Test AnomalyEventRepository CRUD operations"""
    
    def setUp(self):
        super().setUp()
        self.repo = AnomalyEventRepository()
        # Create test video
        self.video = self.create_test_video()
        
    def test_create_anomaly_event(self):
        """Test creating anomaly event record"""
        anomaly = self.repo.create(
            video_id=self.video.id,
            anomaly_type="pedestrian",
            severity_level="medium",
            timestamp_in_video=45.5,
            detection_area="lane_1",
            object_id="person_1",
            object_class="person",
            confidence_score=0.95,
            alert_message="Người đi bộ tại vị trí (125, 150)",
            bbox_x=100,
            bbox_y=125,
            bbox_width=50,
            bbox_height=75
        )
        
        self.assertIsNotNone(anomaly.id)
        self.assertEqual(anomaly.video_id, self.video.id)
        self.assertEqual(anomaly.anomaly_type, "pedestrian")
        self.assertEqual(anomaly.severity_level, "medium")
        self.assertEqual(anomaly.timestamp_in_video, 45.5)
        self.assertEqual(anomaly.alert_status, "active")  # Default
        
    def test_get_anomalies_for_video(self):
        """Test retrieving anomalies for a video"""
        # Create multiple anomalies
        anomalies_data = [
            ("pedestrian", "medium", 10.0),
            ("animal", "low", 20.0),
            ("stopped_vehicle", "high", 30.0),
            ("obstacle", "medium", 40.0)
        ]
        
        for atype, severity, timestamp in anomalies_data:
            self.repo.create(
                video_id=self.video.id,
                anomaly_type=atype,
                severity_level=severity,
                timestamp_in_video=timestamp
            )
        
        # Get all anomalies
        anomalies = self.repo.get_anomalies_for_video(self.video.id)
        self.assertEqual(len(anomalies), 4)
        
        # Should be ordered by timestamp
        for i in range(len(anomalies) - 1):
            self.assertLess(
                anomalies[i].timestamp_in_video,
                anomalies[i + 1].timestamp_in_video
            )
    
    def test_filter_anomalies_by_type(self):
        """Test filtering anomalies by type"""
        # Create anomalies of different types
        for i in range(3):
            self.repo.create(
                video_id=self.video.id,
                anomaly_type="pedestrian",
                timestamp_in_video=i * 10.0
            )
        
        for i in range(2):
            self.repo.create(
                video_id=self.video.id,
                anomaly_type="stopped_vehicle",
                timestamp_in_video=i * 15.0
            )
        
        # Filter by type
        pedestrians = self.repo.get_anomalies_for_video(
            self.video.id,
            anomaly_type="pedestrian"
        )
        stopped = self.repo.get_anomalies_for_video(
            self.video.id,
            anomaly_type="stopped_vehicle"
        )
        
        self.assertEqual(len(pedestrians), 3)
        self.assertEqual(len(stopped), 2)
    
    def test_filter_anomalies_by_severity(self):
        """Test filtering anomalies by severity"""
        severities = ["low", "medium", "high", "medium", "critical"]
        
        for i, severity in enumerate(severities):
            self.repo.create(
                video_id=self.video.id,
                anomaly_type="test",
                severity_level=severity,
                timestamp_in_video=i * 10.0
            )
        
        # Filter by severity
        medium = self.repo.get_anomalies_for_video(
            self.video.id,
            severity="medium"
        )
        high_critical = self.repo.filter_by(
            video_id=self.video.id,
            severity_level="high"
        ) + self.repo.filter_by(
            video_id=self.video.id,
            severity_level="critical"
        )
        
        self.assertEqual(len(medium), 2)
        self.assertEqual(len(high_critical), 2)
    
    def test_get_active_anomalies_only(self):
        """Test retrieving only active anomalies"""
        # Create anomalies with different statuses
        active1 = self.repo.create(
            video_id=self.video.id,
            anomaly_type="pedestrian",
            timestamp_in_video=10.0,
            alert_status="active"
        )
        
        resolved = self.repo.create(
            video_id=self.video.id,
            anomaly_type="animal",
            timestamp_in_video=20.0,
            alert_status="resolved"
        )
        
        active2 = self.repo.create(
            video_id=self.video.id,
            anomaly_type="obstacle",
            timestamp_in_video=30.0,
            alert_status="active"
        )
        
        # Get active only
        active = self.repo.get_anomalies_for_video(
            self.video.id,
            active_only=True
        )
        
        self.assertEqual(len(active), 2)
        self.assertTrue(all(a.alert_status == "active" for a in active))
    
    def test_count_by_type_and_severity(self):
        """Test counting anomalies by type and severity"""
        # Create various anomalies
        test_data = [
            ("pedestrian", "medium"),
            ("pedestrian", "high"),
            ("pedestrian", "medium"),
            ("animal", "low"),
            ("stopped_vehicle", "high"),
            ("stopped_vehicle", "critical"),
            ("obstacle", "medium")
        ]
        
        for atype, severity in test_data:
            self.repo.create(
                video_id=self.video.id,
                anomaly_type=atype,
                severity_level=severity,
                timestamp_in_video=10.0
            )
        
        counts = self.repo.count_by_type_and_severity(self.video.id)
        
        self.assertEqual(counts["pedestrian"]["medium"], 2)
        self.assertEqual(counts["pedestrian"]["high"], 1)
        self.assertEqual(counts["animal"]["low"], 1)
        self.assertEqual(counts["stopped_vehicle"]["high"], 1)
        self.assertEqual(counts["stopped_vehicle"]["critical"], 1)
        self.assertEqual(counts["obstacle"]["medium"], 1)
    
    def test_get_active_anomalies_across_videos(self):
        """Test getting all active anomalies across all videos"""
        # Create anomalies for multiple videos
        video2 = self.create_test_video(file_name="video2.mp4")
        
        for i in range(3):
            self.repo.create(
                video_id=self.video.id,
                anomaly_type="test",
                timestamp_in_video=i * 10.0,
                alert_status="active"
            )
        
        for i in range(2):
            self.repo.create(
                video_id=video2.id,
                anomaly_type="test",
                timestamp_in_video=i * 10.0,
                alert_status="active"
            )
        
        # Get all active
        active = self.repo.get_active_anomalies(limit=10)
        
        self.assertEqual(len(active), 5)
        # Should be ordered by created_at descending (newest first)
        
    def test_get_critical_anomalies(self):
        """Test getting critical anomalies from recent hours"""
        # Create old critical anomaly
        old_critical = self.repo.create(
            video_id=self.video.id,
            anomaly_type="stopped_vehicle",
            severity_level="critical",
            timestamp_in_video=100.0
        )
        old_critical.created_at = datetime.now() - timedelta(hours=48)
        self.session.commit()
        
        # Create recent anomalies
        recent_high = self.repo.create(
            video_id=self.video.id,
            anomaly_type="stopped_vehicle",
            severity_level="high",
            timestamp_in_video=200.0
        )
        
        recent_critical = self.repo.create(
            video_id=self.video.id,
            anomaly_type="obstacle",
            severity_level="critical",
            timestamp_in_video=300.0
        )
        
        # Get critical from last 24 hours
        critical = self.repo.get_critical_anomalies(hours=24)
        
        self.assertEqual(len(critical), 2)  # high and critical
        self.assertIn(recent_high, critical)
        self.assertIn(recent_critical, critical)
        self.assertNotIn(old_critical, critical)
    
    def test_resolve_anomaly(self):
        """Test marking anomaly as resolved"""
        anomaly = self.repo.create(
            video_id=self.video.id,
            anomaly_type="pedestrian",
            timestamp_in_video=50.0
        )
        
        self.assertEqual(anomaly.alert_status, "active")
        self.assertIsNone(anomaly.resolved_at)
        
        # Resolve
        resolved = self.repo.resolve_anomaly(anomaly.id)
        
        self.assertEqual(resolved.alert_status, "resolved")
        self.assertIsNotNone(resolved.resolved_at)
        self.assertTrue(resolved.resolved_at <= datetime.now())
    
    def test_acknowledge_anomaly(self):
        """Test marking anomaly as acknowledged"""
        anomaly = self.repo.create(
            video_id=self.video.id,
            anomaly_type="animal",
            timestamp_in_video=30.0
        )
        
        # Acknowledge
        acknowledged = self.repo.acknowledge_anomaly(anomaly.id)
        
        self.assertEqual(acknowledged.alert_status, "acknowledged")
    
    def test_get_anomaly_timeline(self):
        """Test getting anomaly timeline for video"""
        # Create anomalies with different attributes
        anomalies_data = [
            ("pedestrian", "medium", 10.0, None, "active"),
            ("stopped_vehicle", "high", 30.0, 25.0, "active"),
            ("obstacle", "low", 50.0, None, "resolved")
        ]
        
        for atype, severity, timestamp, duration, status in anomalies_data:
            self.repo.create(
                video_id=self.video.id,
                anomaly_type=atype,
                severity_level=severity,
                timestamp_in_video=timestamp,
                duration=duration,
                alert_status=status,
                alert_message=f"Test {atype}"
            )
        
        timeline = self.repo.get_anomaly_timeline(self.video.id)
        
        self.assertEqual(len(timeline), 3)
        
        # Check structure
        for event in timeline:
            self.assertIn("id", event)
            self.assertIn("timestamp", event)
            self.assertIn("type", event)
            self.assertIn("severity", event)
            self.assertIn("message", event)
            self.assertIn("duration", event)
            self.assertIn("status", event)
        
        # Check specific values
        self.assertEqual(timeline[1]["duration"], 25.0)
        self.assertEqual(timeline[2]["status"], "resolved")
    
    def test_get_stopped_vehicle_events(self):
        """Test getting stopped vehicle events exceeding duration"""
        # Create stopped vehicle anomalies with different durations
        durations = [10.0, 15.0, 25.0, 30.0, 5.0]
        
        for i, duration in enumerate(durations):
            self.repo.create(
                video_id=self.video.id,
                anomaly_type="stopped_vehicle",
                timestamp_in_video=i * 60.0,
                duration=duration,
                object_class="car"
            )
        
        # Also create non-stopped vehicle anomaly
        self.repo.create(
            video_id=self.video.id,
            anomaly_type="pedestrian",
            timestamp_in_video=500.0
        )
        
        # Get stopped vehicles with duration >= 20 seconds
        stopped = self.repo.get_stopped_vehicle_events(
            self.video.id,
            min_duration=20.0
        )
        
        self.assertEqual(len(stopped), 2)  # 25.0 and 30.0
        # Should be ordered by duration descending
        self.assertEqual(stopped[0].duration, 30.0)
        self.assertEqual(stopped[1].duration, 25.0)
    
    def test_bulk_insert_anomalies(self):
        """Test bulk inserting anomaly events"""
        anomalies_data = [
            {
                "video_id": self.video.id,
                "anomaly_type": "pedestrian",
                "severity_level": "medium",
                "timestamp_in_video": i * 10.0,
                "alert_message": f"Person detected at {i * 10.0}s"
            }
            for i in range(5)
        ]
        
        count = self.repo.bulk_insert_anomalies(anomalies_data)
        
        self.assertEqual(count, 5)
        
        # Verify in database
        anomalies = self.repo.get_anomalies_for_video(self.video.id)
        self.assertEqual(len(anomalies), 5)
    
    def test_update_anomaly(self):
        """Test updating anomaly event"""
        anomaly = self.repo.create(
            video_id=self.video.id,
            anomaly_type="obstacle",
            severity_level="low",
            timestamp_in_video=60.0
        )
        
        # Update
        updated = self.repo.update(
            anomaly.id,
            severity_level="high",
            alert_message="Updated: Large obstacle detected"
        )
        
        self.assertEqual(updated.severity_level, "high")
        self.assertEqual(updated.alert_message, "Updated: Large obstacle detected")
    
    def test_delete_anomaly(self):
        """Test deleting anomaly event"""
        anomaly = self.repo.create(
            video_id=self.video.id,
            anomaly_type="test",
            timestamp_in_video=10.0
        )
        
        # Delete
        result = self.repo.delete(anomaly.id)
        self.assertTrue(result)
        
        # Verify deleted
        retrieved = self.repo.get_by_id(anomaly.id)
        self.assertIsNone(retrieved)
    
    def test_edge_case_no_anomalies(self):
        """Test handling video with no anomalies"""
        anomalies = self.repo.get_anomalies_for_video(self.video.id)
        self.assertEqual(len(anomalies), 0)
        
        timeline = self.repo.get_anomaly_timeline(self.video.id)
        self.assertEqual(len(timeline), 0)
        
        counts = self.repo.count_by_type_and_severity(self.video.id)
        self.assertEqual(counts, {})


if __name__ == '__main__':
    unittest.main()