# tests/test_traffic_data_repository.py
import unittest
from datetime import datetime, timedelta

from test_base import BaseTestCase
from models.repositories import TrafficDataRepository
from dal.models import TrafficData, Video


class TestTrafficDataRepository(BaseTestCase):
    """Test TrafficDataRepository CRUD operations"""
    
    def setUp(self):
        super().setUp()
        self.repo = TrafficDataRepository()
        # Create test video
        self.video = self.create_test_video()
        
    def test_create_traffic_data(self):
        """Test creating traffic data record"""
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=150,
            car_count=80,
            motorbike_count=50,
            truck_count=15,
            bus_count=5,
            avg_vehicles_per_minute=30.0,
            peak_vehicles_per_minute=45,
            congestion_level="medium"
        )
        
        self.assertIsNotNone(traffic_data.id)
        self.assertEqual(traffic_data.video_id, self.video.id)
        self.assertEqual(traffic_data.total_vehicles, 150)
        self.assertEqual(traffic_data.congestion_level, "medium")
        
    def test_get_by_video_id(self):
        """Test retrieving traffic data by video ID"""
        # Create traffic data
        created = self.repo.create(
            video_id=self.video.id,
            total_vehicles=100,
            car_count=60,
            motorbike_count=30,
            truck_count=8,
            bus_count=2
        )
        
        # Retrieve
        retrieved = self.repo.get_by_video_id(self.video.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, created.id)
        self.assertEqual(retrieved.total_vehicles, 100)
        
    def test_create_or_update(self):
        """Test create or update functionality"""
        # First call - should create
        traffic_data = self.repo.create_or_update(
            self.video.id,
            total_vehicles=50,
            car_count=30
        )
        
        self.assertIsNotNone(traffic_data)
        self.assertEqual(traffic_data.total_vehicles, 50)
        original_id = traffic_data.id
        
        # Second call - should update
        updated = self.repo.create_or_update(
            self.video.id,
            total_vehicles=100,
            car_count=60,
            motorbike_count=30
        )
        
        self.assertEqual(updated.id, original_id)  # Same record
        self.assertEqual(updated.total_vehicles, 100)
        self.assertEqual(updated.car_count, 60)
        self.assertEqual(updated.motorbike_count, 30)
        
    def test_update_time_aggregations(self):
        """Test updating time-based aggregations"""
        # Create traffic data
        traffic_data = self.repo.create(video_id=self.video.id)
        
        # Update aggregations
        minute_data = {
            "0": {"car": 5, "motorbike": 3, "truck": 1, "bus": 0},
            "1": {"car": 8, "motorbike": 5, "truck": 2, "bus": 1},
            "2": {"car": 10, "motorbike": 7, "truck": 1, "bus": 0}
        }
        
        hour_data = {
            "0": {"car": 200, "motorbike": 150, "truck": 30, "bus": 10}
        }
        
        updated = self.repo.update_time_aggregations(
            self.video.id,
            minute_data,
            hour_data
        )
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.minute_aggregations, minute_data)
        self.assertEqual(updated.hour_aggregations, hour_data)
        
        # Test accessing specific minute/hour
        self.assertEqual(updated.get_minute_counts(1)["car"], 8)
        self.assertEqual(updated.get_hour_counts(0)["motorbike"], 150)
        
    def test_get_vehicle_counts(self):
        """Test getting vehicle counts as dictionary"""
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=100,
            car_count=50,
            motorbike_count=30,
            truck_count=15,
            bus_count=5
        )
        
        counts = traffic_data.get_vehicle_counts()
        
        self.assertEqual(counts["total"], 100)
        self.assertEqual(counts["car"], 50)
        self.assertEqual(counts["motorbike"], 30)
        self.assertEqual(counts["truck"], 15)
        self.assertEqual(counts["bus"], 5)
        
    def test_get_top_traffic_videos(self):
        """Test getting videos with highest traffic"""
        # Create multiple videos with traffic data
        for i in range(5):
            video = self.create_test_video(file_name=f"video_{i}.mp4")
            self.repo.create(
                video_id=video.id,
                total_vehicles=(i + 1) * 50,  # 50, 100, 150, 200, 250
                avg_vehicles_per_minute=(i + 1) * 10
            )
        
        # Get top 3
        top_videos = self.repo.get_top_traffic_videos(limit=3)
        
        self.assertEqual(len(top_videos), 3)
        # Should be ordered by total_vehicles descending
        self.assertEqual(top_videos[0]["total_vehicles"], 250)
        self.assertEqual(top_videos[1]["total_vehicles"], 200)
        self.assertEqual(top_videos[2]["total_vehicles"], 150)
        
        # Check structure
        for video in top_videos:
            self.assertIn("video_id", video)
            self.assertIn("file_name", video)
            self.assertIn("total_vehicles", video)
            self.assertIn("avg_vehicles_per_minute", video)
    
    def test_get_congestion_summary(self):
        """Test getting congestion level summary"""
        # Create videos with different congestion levels
        congestion_levels = ["low", "low", "medium", "medium", "medium", "high", "very_high"]
        
        for i, level in enumerate(congestion_levels):
            video = self.create_test_video(file_name=f"video_{i}.mp4")
            self.repo.create(
                video_id=video.id,
                total_vehicles=50,
                congestion_level=level
            )
        
        summary = self.repo.get_congestion_summary()
        
        self.assertEqual(summary["low"], 2)
        self.assertEqual(summary["medium"], 3)
        self.assertEqual(summary["high"], 1)
        self.assertEqual(summary["very_high"], 1)
    
    def test_calculate_statistics(self):
        """Test calculating comprehensive statistics"""
        # Create traffic data
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=100,
            car_count=50,
            motorbike_count=30,
            truck_count=15,
            bus_count=5,
            avg_vehicles_per_minute=20.0,
            peak_vehicles_per_minute=35,
            congestion_level="medium"
        )
        
        stats = self.repo.calculate_statistics(self.video.id)
        
        # Check basic stats
        self.assertEqual(stats["total_vehicles"], 100)
        self.assertEqual(stats["avg_per_minute"], 20.0)
        self.assertEqual(stats["peak_minute"], 35)
        self.assertEqual(stats["congestion_level"], "medium")
        
        # Check vehicle breakdown
        self.assertEqual(stats["vehicle_breakdown"]["car"], 50)
        self.assertEqual(stats["vehicle_breakdown"]["total"], 100)
        
        # Check percentages
        self.assertEqual(stats["car_percentage"], 50.0)
        self.assertEqual(stats["motorbike_percentage"], 30.0)
        self.assertEqual(stats["truck_percentage"], 15.0)
        self.assertEqual(stats["bus_percentage"], 5.0)
    
    def test_calculate_statistics_no_data(self):
        """Test calculating statistics for video without traffic data"""
        new_video = self.create_test_video(file_name="no_traffic_data.mp4")
        
        stats = self.repo.calculate_statistics(new_video.id)
        
        self.assertEqual(stats, {})
    
    def test_lane_data_storage(self):
        """Test storing lane-specific data"""
        lane_data = {
            "lane_1": {"car": 30, "motorbike": 20, "truck": 5, "bus": 2},
            "lane_2": {"car": 20, "motorbike": 10, "truck": 10, "bus": 3}
        }
        
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=100,
            lane_data=lane_data
        )
        
        self.assertEqual(traffic_data.lane_data, lane_data)
        self.assertEqual(traffic_data.lane_data["lane_1"]["car"], 30)
        self.assertEqual(traffic_data.lane_data["lane_2"]["truck"], 10)
    
    def test_update_existing_record(self):
        """Test updating existing traffic data record"""
        # Create initial
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=50,
            car_count=30
        )
        
        # Update
        updated = self.repo.update(
            traffic_data.id,
            total_vehicles=100,
            car_count=60,
            avg_vehicles_per_minute=25.5,
            congestion_level="high"
        )
        
        self.assertEqual(updated.total_vehicles, 100)
        self.assertEqual(updated.car_count, 60)
        self.assertEqual(updated.avg_vehicles_per_minute, 25.5)
        self.assertEqual(updated.congestion_level, "high")
    
    def test_delete_traffic_data(self):
        """Test deleting traffic data"""
        # Create
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=100
        )
        
        # Delete
        result = self.repo.delete(traffic_data.id)
        self.assertTrue(result)
        
        # Verify deleted
        retrieved = self.repo.get_by_id(traffic_data.id)
        self.assertIsNone(retrieved)
    
    def test_filter_by_congestion_level(self):
        """Test filtering by congestion level"""
        # Create multiple records
        levels = ["low", "medium", "high", "medium"]
        for i, level in enumerate(levels):
            video = self.create_test_video(file_name=f"video_{i}.mp4")
            self.repo.create(
                video_id=video.id,
                congestion_level=level
            )
        
        # Filter
        medium_congestion = self.repo.filter_by(congestion_level="medium")
        self.assertEqual(len(medium_congestion), 2)
        
        high_congestion = self.repo.filter_by(congestion_level="high")
        self.assertEqual(len(high_congestion), 1)
    
    def test_edge_case_zero_vehicles(self):
        """Test handling zero vehicle count"""
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=0,
            car_count=0,
            motorbike_count=0,
            truck_count=0,
            bus_count=0
        )
        
        # Calculate statistics should not divide by zero
        stats = self.repo.calculate_statistics(self.video.id)
        
        self.assertEqual(stats["total_vehicles"], 0)
        self.assertEqual(stats.get("car_percentage", 0), 0)
        
    def test_timestamps(self):
        """Test created_at and updated_at timestamps"""
        # Create
        traffic_data = self.repo.create(
            video_id=self.video.id,
            total_vehicles=50
        )
        
        self.assertIsNotNone(traffic_data.created_at)
        self.assertIsNotNone(traffic_data.updated_at)
        created_time = traffic_data.created_at
        
        # Wait a bit and update
        import time
        time.sleep(0.1)
        
        updated = self.repo.update(
            traffic_data.id,
            total_vehicles=100
        )
        
        # created_at should not change significantly (allow small delta for DB precision)
        # Use timedelta to allow for small differences
        time_diff = abs(updated.created_at - created_time)
        self.assertLess(time_diff, timedelta(seconds=0.1))
        
        # updated_at should be greater than created_at
        self.assertGreater(updated.updated_at, created_time)


if __name__ == '__main__':
    unittest.main()