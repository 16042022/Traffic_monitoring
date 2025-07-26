# tests/test_video_repository.py
import unittest
from datetime import datetime, timedelta

from test_base import BaseTestCase
from models.repositories import VideoRepository
from dal.models import Video


class TestVideoRepository(BaseTestCase):
    """Test VideoRepository CRUD operations"""
    
    def setUp(self):
        super().setUp()
        self.repo = VideoRepository()
        
    def test_create_video(self):
        """Test creating a video record"""
        video = self.repo.create(
            file_name="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            duration=300.0,
            fps=30.0,
            resolution="1920x1080",
            frame_count=9000,
            status="pending"
        )
        
        self.assertIsNotNone(video.id)
        self.assertEqual(video.file_name, "test_video.mp4")
        self.assertEqual(video.duration, 300.0)
        self.assertEqual(video.status, "pending")
        
    def test_get_by_id(self):
        """Test retrieving video by ID"""
        # Create video
        created = self.create_test_video()
        
        # Retrieve
        retrieved = self.repo.get_by_id(created.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, created.id)
        self.assertEqual(retrieved.file_name, created.file_name)
        
    def test_get_by_id_not_found(self):
        """Test retrieving non-existent video"""
        video = self.repo.get_by_id(9999)
        self.assertIsNone(video)
        
    def test_update_video(self):
        """Test updating video record"""
        # Create video
        video = self.create_test_video(status="pending")
        
        # Update
        updated = self.repo.update(
            video.id,
            status="completed",
            processing_duration=45.5
        )
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.processing_duration, 45.5)
        
    def test_delete_video(self):
        """Test deleting video record"""
        # Create video
        video = self.create_test_video()
        video_id = video.id
        
        # Delete
        result = self.repo.delete(video_id)
        self.assertTrue(result)
        
        # Verify deleted
        retrieved = self.repo.get_by_id(video_id)
        self.assertIsNone(retrieved)
        
    def test_delete_non_existent(self):
        """Test deleting non-existent video"""
        result = self.repo.delete(9999)
        self.assertFalse(result)
        
    def test_get_all_videos(self):
        """Test retrieving all videos"""
        # Create multiple videos
        for i in range(5):
            self.create_test_video(file_name=f"video_{i}.mp4")
        
        # Get all
        videos = self.repo.get_all()
        self.assertEqual(len(videos), 5)
        
    def test_get_all_with_limit(self):
        """Test retrieving videos with limit"""
        # Create multiple videos
        for i in range(10):
            self.create_test_video(file_name=f"video_{i}.mp4")
        
        # Get with limit
        videos = self.repo.get_all(limit=3)
        self.assertEqual(len(videos), 3)
        
        # Get with offset
        videos = self.repo.get_all(limit=3, offset=5)
        self.assertEqual(len(videos), 3)
        
    def test_get_by_status(self):
        """Test filtering videos by status"""
        # Create videos with different statuses
        self.create_test_video(file_name="pending1.mp4", status="pending")
        self.create_test_video(file_name="pending2.mp4", status="pending")
        self.create_test_video(file_name="completed1.mp4", status="completed")
        self.create_test_video(file_name="failed1.mp4", status="failed")
        
        # Get by status
        pending = self.repo.get_by_status("pending")
        completed = self.repo.get_by_status("completed")
        failed = self.repo.get_by_status("failed")
        
        self.assertEqual(len(pending), 2)
        self.assertEqual(len(completed), 1)
        self.assertEqual(len(failed), 1)
        
    def test_get_recent_videos(self):
        """Test retrieving recent videos"""
        # Create old video
        old_video = self.create_test_video(file_name="old_video.mp4")
        old_video.upload_timestamp = datetime.now() - timedelta(days=45)
        self.session.commit()
        
        # Create recent videos
        for i in range(3):
            video = self.create_test_video(file_name=f"recent_{i}.mp4")
            video.upload_timestamp = datetime.now() - timedelta(days=i)
            self.session.commit()
        
        # Get recent (within 30 days)
        recent = self.repo.get_recent_videos(limit=10, days=30)
        
        self.assertEqual(len(recent), 3)
        # Should be ordered by upload time (newest first)
        self.assertTrue(recent[0].upload_timestamp > recent[1].upload_timestamp)
        
    def test_get_completed_videos(self):
        """Test retrieving completed videos with stats"""
        # Create videos
        self.create_test_video(file_name="pending.mp4", status="pending")
        completed1 = self.create_test_video(file_name="completed1.mp4", status="completed")
        completed2 = self.create_test_video(file_name="completed2.mp4", status="completed")
        
        # Add traffic data to one completed video
        from dal.models import TrafficData
        traffic_data = TrafficData(
            video_id=completed1.id,
            total_vehicles=100,
            car_count=50
        )
        self.session.add(traffic_data)
        self.session.commit()
        
        # Get completed videos
        completed = self.repo.get_completed_videos(include_stats=True)
        
        self.assertEqual(len(completed), 2)
        # Check that traffic data is loaded
        video_with_stats = next(v for v in completed if v.id == completed1.id)
        self.assertIsNotNone(video_with_stats.traffic_data)
        self.assertEqual(video_with_stats.traffic_data.total_vehicles, 100)
        
    def test_search_videos(self):
        """Test searching videos by filename"""
        # Create videos
        self.create_test_video(file_name="traffic_morning.mp4")
        self.create_test_video(file_name="traffic_evening.mp4")
        self.create_test_video(file_name="highway_traffic.mp4")
        self.create_test_video(file_name="test_video.mp4")
        
        # Search
        traffic_videos = self.repo.search_videos("traffic")
        self.assertEqual(len(traffic_videos), 3)
        
        morning_videos = self.repo.search_videos("morning")
        self.assertEqual(len(morning_videos), 1)
        
        # Case insensitive
        highway_videos = self.repo.search_videos("HIGHWAY")
        self.assertEqual(len(highway_videos), 1)
        
    def test_update_status(self):
        """Test updating video processing status"""
        video = self.create_test_video(status="processing")
        
        # Update to completed with duration
        updated = self.repo.update_status(
            video.id, 
            "completed",
            processing_duration=120.5
        )
        
        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.processing_duration, 120.5)
        self.assertIsNotNone(updated.processing_timestamp)
        
        # Update to failed (no duration)
        updated = self.repo.update_status(video.id, "failed")
        self.assertEqual(updated.status, "failed")
        
    def test_get_statistics(self):
        """Test getting overall video statistics"""
        # Create videos with different statuses
        for _ in range(5):
            self.create_test_video(status="completed", processing_duration=100.0)
        for _ in range(3):
            self.create_test_video(status="pending")
        for _ in range(2):
            self.create_test_video(status="failed")
        for _ in range(1):
            self.create_test_video(status="processing")
            
        stats = self.repo.get_statistics()
        
        self.assertEqual(stats["total_videos"], 11)
        self.assertEqual(stats["completed"], 5)
        self.assertEqual(stats["failed"], 2)
        self.assertEqual(stats["processing"], 1)
        self.assertEqual(stats["pending"], 3)
        self.assertEqual(stats["average_processing_time"], 100.0)
        
    def test_get_with_all_data(self):
        """Test getting video with all related data"""
        # Create video with related data
        video = self.create_test_video()
        
        # Add traffic data
        from dal.models import TrafficData
        traffic_data = TrafficData(
            video_id=video.id,
            total_vehicles=150,
            car_count=80
        )
        self.session.add(traffic_data)
        
        # Add detection events
        from dal.models import DetectionEvent
        for i in range(3):
            event = DetectionEvent(
                video_id=video.id,
                event_id=f"car_{i}",
                frame_number=i * 100,
                timestamp_in_video=i * 3.33,
                object_type="car",
                crossed_line=True
            )
            self.session.add(event)
        
        # Add anomaly events
        from dal.models import AnomalyEvent
        anomaly = AnomalyEvent(
            video_id=video.id,
            anomaly_type="pedestrian",
            timestamp_in_video=50.0,
            alert_message="Person on road"
        )
        self.session.add(anomaly)
        
        self.session.commit()
        
        # Get with all data
        loaded = self.repo.get_with_all_data(video.id)
        
        self.assertIsNotNone(loaded)
        self.assertIsNotNone(loaded.traffic_data)
        self.assertEqual(loaded.traffic_data.total_vehicles, 150)
        self.assertEqual(len(loaded.detection_events), 3)
        self.assertEqual(len(loaded.anomaly_events), 1)
        
    def test_bulk_create(self):
        """Test bulk creating videos"""
        video_data = [
            {
                "file_name": f"bulk_video_{i}.mp4",
                "file_path": f"/path/bulk_video_{i}.mp4",
                "duration": 300.0,
                "fps": 30.0,
                "resolution": "1920x1080",
                "frame_count": 9000,
                "status": "pending"
            }
            for i in range(5)
        ]
        
        created = self.repo.bulk_create(video_data)
        
        self.assertEqual(len(created), 5)
        
        # Verify in database
        all_videos = self.repo.get_all()
        self.assertEqual(len(all_videos), 5)
        
    def test_exists(self):
        """Test checking if video exists"""
        # No videos
        self.assertFalse(self.repo.exists())
        
        # Create video
        video = self.create_test_video(file_name="test.mp4")
        
        # Check exists
        self.assertTrue(self.repo.exists())
        self.assertTrue(self.repo.exists(file_name="test.mp4"))
        self.assertFalse(self.repo.exists(file_name="nonexistent.mp4"))
        
    def test_count(self):
        """Test counting videos"""
        # No videos
        self.assertEqual(self.repo.count(), 0)
        
        # Create videos
        for i in range(7):
            status = "completed" if i < 4 else "pending"
            self.create_test_video(status=status)
        
        # Count all
        self.assertEqual(self.repo.count(), 7)
        
        # Count with filter
        self.assertEqual(self.repo.count(status="completed"), 4)
        self.assertEqual(self.repo.count(status="pending"), 3)


if __name__ == '__main__':
    unittest.main()