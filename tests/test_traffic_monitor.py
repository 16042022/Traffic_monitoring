# tests/test_traffic_monitor.py
import unittest
from unittest.mock import Mock, MagicMock

from test_base import BaseTestCase
from models.components.traffic_monitor import TrafficMonitor
from models.components.vehicle_tracker import VehicleTracker
from models.entities import Detection, TrafficData


class TestTrafficMonitor(BaseTestCase):
    """Test TrafficMonitor component"""
    
    def setUp(self):
        super().setUp()
        self.virtual_line_config = {
            "p1_x": 400,
            "p1_y": 100,
            "p2_x": 400,
            "p2_y": 500,
            "counting_direction": "right"
        }
        self.monitor = TrafficMonitor(self.virtual_line_config)
        self.tracker = VehicleTracker()
        
    def test_virtual_line_parsing(self):
        """Test virtual line configuration parsing"""
        line = self.monitor.virtual_line
        self.assertEqual(line[0], (400, 100))  # Start point
        self.assertEqual(line[1], (400, 500))  # End point
        self.assertEqual(line[2], "right")     # Direction
        
    def test_vehicle_counting_on_crossing(self):
        """Test vehicles are counted when crossing line"""
        # Setup mock tracker
        mock_tracker = Mock(spec=VehicleTracker)
        
        # First detection - not crossed yet
        detection1 = Detection(
            id="car_1",
            class_name="car",
            confidence=0.9,
            bbox=(350, 300, 390, 340)
        )
        mock_tracker.check_line_crossing.return_value = False
        
        self.monitor.process_frame_detections([detection1], mock_tracker, 1.0)
        self.assertEqual(self.monitor.traffic_data.total_vehicles, 0)
        self.assertEqual(self.monitor.traffic_data.car_count, 0)
        
        # Second detection - crossed line
        detection2 = Detection(
            id="car_1",
            class_name="car",
            confidence=0.9,
            bbox=(410, 300, 450, 340)
        )
        mock_tracker.check_line_crossing.return_value = True
        
        self.monitor.process_frame_detections([detection2], mock_tracker, 2.0)
        self.assertEqual(self.monitor.traffic_data.total_vehicles, 1)
        self.assertEqual(self.monitor.traffic_data.car_count, 1)
        
    def test_multiple_vehicle_types_counting(self):
        """Test counting different vehicle types"""
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.check_line_crossing.return_value = True
        
        # Different vehicle types
        detections = [
            Detection(id="car_1", class_name="car", confidence=0.9, bbox=(410, 100, 450, 140)),
            Detection(id="bike_1", class_name="motorbike", confidence=0.8, bbox=(410, 200, 430, 220)),
            Detection(id="truck_1", class_name="truck", confidence=0.85, bbox=(410, 300, 460, 350)),
            Detection(id="bus_1", class_name="bus", confidence=0.9, bbox=(410, 400, 460, 450))
        ]
        
        self.monitor.process_frame_detections(detections, mock_tracker, 1.0)
        
        # Check counts
        self.assertEqual(self.monitor.traffic_data.total_vehicles, 4)
        self.assertEqual(self.monitor.traffic_data.car_count, 1)
        self.assertEqual(self.monitor.traffic_data.motorbike_count, 1)
        self.assertEqual(self.monitor.traffic_data.truck_count, 1)
        self.assertEqual(self.monitor.traffic_data.bus_count, 1)
        
    def test_direction_specific_counting(self):
        """Test that only vehicles moving in specified direction are counted"""
        # Test with real tracker for accurate direction checking
        tracker = VehicleTracker()
        
        # Car moving right (should be counted)
        for x in [350, 380, 420, 450]:
            det = Detection(id="", class_name="car", confidence=0.9,
                          bbox=(x, 300, x+40, 340))
            updated = tracker.update_tracks([det], timestamp=x/100)
            
            # Process with monitor
            self.monitor.process_frame_detections(updated, tracker, x/100)
        
        self.assertEqual(self.monitor.traffic_data.car_count, 1)
        
        # Motorbike moving left (should NOT be counted)
        for x in [450, 420, 380, 350]:
            det = Detection(id="", class_name="motorbike", confidence=0.9,
                          bbox=(x, 200, x+30, 230))
            updated = tracker.update_tracks([det], timestamp=x/100 + 10)
            
            # Process with monitor
            self.monitor.process_frame_detections(updated, tracker, x/100 + 10)
        
        self.assertEqual(self.monitor.traffic_data.motorbike_count, 0)
        
    def test_hourly_statistics_update(self):
        """Test hourly statistics aggregation"""
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.check_line_crossing.return_value = False
        
        # Hour 0 (0-3599 seconds)
        detections1 = [
            Detection(id="car_1", class_name="car", confidence=0.9, bbox=(100, 100, 200, 200)),
            Detection(id="car_2", class_name="car", confidence=0.9, bbox=(200, 100, 300, 200))
        ]
        self.monitor.process_frame_detections(detections1, mock_tracker, 1800.0)  # 30 min
        
        # Hour 1 (3600-7199 seconds)
        detections2 = [
            Detection(id="truck_1", class_name="truck", confidence=0.9, bbox=(100, 100, 200, 200)),
            Detection(id="truck_2", class_name="truck", confidence=0.9, bbox=(200, 100, 300, 200)),
            Detection(id="truck_3", class_name="truck", confidence=0.9, bbox=(300, 100, 400, 200))
        ]
        self.monitor.process_frame_detections(detections2, mock_tracker, 3700.0)  # 1h 1m
        
        # Check hourly stats
        hourly = self.monitor.traffic_data.hourly_counts
        self.assertIn(0, hourly)
        self.assertIn(1, hourly)
        self.assertEqual(hourly[0]["car"], 2)
        self.assertEqual(hourly[1]["truck"], 3)
        
    def test_statistics_retrieval(self):
        """Test getting current statistics"""
        # Add some data
        self.monitor.traffic_data.total_vehicles = 100
        self.monitor.traffic_data.car_count = 50
        self.monitor.traffic_data.motorbike_count = 30
        self.monitor.traffic_data.truck_count = 15
        self.monitor.traffic_data.bus_count = 5
        
        stats = self.monitor.get_statistics()
        
        self.assertEqual(stats["total_vehicles"], 100)
        self.assertEqual(stats["vehicle_counts"]["car"], 50)
        self.assertEqual(stats["vehicle_counts"]["motorbike"], 30)
        self.assertEqual(stats["vehicle_counts"]["truck"], 15)
        self.assertEqual(stats["vehicle_counts"]["bus"], 5)
        
        # Check virtual line info included
        self.assertIn("virtual_line", stats)
        self.assertEqual(stats["virtual_line"]["start"], (400, 100))
        self.assertEqual(stats["virtual_line"]["end"], (400, 500))
        self.assertEqual(stats["virtual_line"]["direction"], "right")
        
    def test_density_level_calculation(self):
        """Test traffic density level calculation"""
        # Test different vehicle counts
        test_cases = [
            (3, "low"),        # < 5
            (10, "medium"),    # 5-14
            (20, "high"),      # 15-24
            (30, "very_high")  # >= 25
        ]
        
        for count, expected_level in test_cases:
            level = self.monitor.get_density_level(count)
            self.assertEqual(level, expected_level, 
                           f"Count {count} should give level {expected_level}")
    
    def test_reset_functionality(self):
        """Test reset clears all data"""
        # Add some data
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.check_line_crossing.return_value = True
        
        detections = [
            Detection(id="car_1", class_name="car", confidence=0.9, bbox=(410, 300, 450, 340))
        ]
        self.monitor.process_frame_detections(detections, mock_tracker, 1.0)
        
        # Verify data exists
        self.assertEqual(self.monitor.traffic_data.total_vehicles, 1)
        self.assertEqual(self.monitor.traffic_data.car_count, 1)
        
        # Reset
        self.monitor.reset()
        
        # Verify reset - check actual values, not comparing old vs new
        self.assertEqual(self.monitor.traffic_data.total_vehicles, 0)
        self.assertEqual(self.monitor.traffic_data.car_count, 0)
        self.assertEqual(self.monitor.traffic_data.motorbike_count, 0)
        self.assertEqual(self.monitor.traffic_data.truck_count, 0)
        self.assertEqual(self.monitor.traffic_data.bus_count, 0)
        self.assertEqual(self.monitor.traffic_data.video_id, 0)  # Should be reset to 0
        
    def test_non_vehicle_objects_not_counted(self):
        """Test that non-vehicle objects are not counted in traffic"""
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.check_line_crossing.return_value = True
        
        # Mix of vehicles and non-vehicles
        detections = [
            Detection(id="car_1", class_name="car", confidence=0.9, bbox=(410, 100, 450, 140)),
            Detection(id="person_1", class_name="person", confidence=0.9, bbox=(410, 200, 430, 250)),
            Detection(id="dog_1", class_name="dog", confidence=0.8, bbox=(410, 300, 430, 320)),
            Detection(id="bike_1", class_name="motorbike", confidence=0.9, bbox=(410, 400, 430, 420))
        ]
        
        self.monitor.process_frame_detections(detections, mock_tracker, 1.0)
        
        # Only vehicles should be counted
        self.assertEqual(self.monitor.traffic_data.total_vehicles, 2)
        self.assertEqual(self.monitor.traffic_data.car_count, 1)
        self.assertEqual(self.monitor.traffic_data.motorbike_count, 1)
        
        # Person and dog should not affect vehicle counts
        summary = self.monitor.traffic_data.get_summary()
        self.assertNotIn("person", summary)
        self.assertNotIn("dog", summary)


if __name__ == '__main__':
    unittest.main()