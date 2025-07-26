# tests/test_anomaly_detector.py
import unittest
from unittest.mock import Mock, MagicMock
import time

from test_base import BaseTestCase
from models.components.anomaly_detector import AnomalyDetector
from models.components.vehicle_tracker import VehicleTracker
from models.entities import Detection


class TestAnomalyDetector(BaseTestCase):
    """Test AnomalyDetector component"""
    
    def setUp(self):
        super().setUp()
        self.detector = AnomalyDetector(stop_time_threshold=20.0)
        self.tracker = VehicleTracker()
        
    def test_pedestrian_detection(self):
        """Test pedestrian anomaly detection"""
        detection = Detection(
            id="person_1",
            class_name="person",
            confidence=0.9,
            bbox=(100, 100, 150, 200),
            center=(125, 150)
        )
        
        anomalies = self.detector.detect_anomalies([detection], self.tracker, 10.0)
        
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["type"], "pedestrian")
        self.assertIn("Phát hiện người đi bộ", anomalies[0]["message"])
        self.assertIn("(125, 150)", anomalies[0]["message"])
        
    def test_animal_detection(self):
        """Test animal anomaly detection"""
        # Test different animal types
        animal_classes = ["dog", "cat", "bird", "animal"]
        
        for animal_class in animal_classes:
            detection = Detection(
                id=f"{animal_class}_1",
                class_name=animal_class,
                confidence=0.8,
                bbox=(200, 200, 250, 250)
            )
            
            anomalies = self.detector.detect_anomalies([detection], self.tracker, 10.0)
            
            self.assertEqual(len(anomalies), 1)
            self.assertEqual(anomalies[0]["type"], "animal")
            self.assertIn("Phát hiện động vật", anomalies[0]["message"])
            self.assertIn(animal_class, anomalies[0]["message"])
            
    def test_obstacle_detection(self):
        """Test obstacle anomaly detection"""
        obstacle_classes = ["obstacle", "debris", "rock", "tree", "garbage"]
        
        for obstacle_class in obstacle_classes:
            detection = Detection(
                id=f"{obstacle_class}_1",
                class_name=obstacle_class,
                confidence=0.7,
                bbox=(300, 300, 400, 400)
            )
            
            anomalies = self.detector.detect_anomalies([detection], self.tracker, 10.0)
            
            self.assertEqual(len(anomalies), 1)
            self.assertEqual(anomalies[0]["type"], "obstacle")
            self.assertIn("Phát hiện vật cản", anomalies[0]["message"])
            
    def test_stopped_vehicle_detection(self):
        """Test stopped vehicle anomaly detection with 20-second threshold"""
        # Mock tracker to return stopped status
        mock_tracker = Mock(spec=VehicleTracker)
        
        car_detection = Detection(
            id="car_1",
            class_name="car",
            confidence=0.9,
            bbox=(100, 100, 200, 200)
        )
        
        # Test 1: Vehicle just stopped (should not trigger alert)
        mock_tracker.get_movement_info.return_value = {
            "speed": 0.0,
            "distance": 0.0,
            "stopped": True
        }
        
        anomalies = self.detector.detect_anomalies([car_detection], mock_tracker, 5.0)
        self.assertEqual(len(anomalies), 0)
        
        # Verify vehicle is being tracked
        self.assertIn("car_1", self.detector.stopped_vehicles)
        self.assertEqual(self.detector.stopped_vehicles["car_1"]["start_time"], 5.0)
        
        # Test 2: Vehicle stopped for 10 seconds (still under threshold)
        anomalies = self.detector.detect_anomalies([car_detection], mock_tracker, 15.0)
        self.assertEqual(len(anomalies), 0)
        
        # Test 3: Vehicle stopped for exactly 20 seconds (at threshold)
        anomalies = self.detector.detect_anomalies([car_detection], mock_tracker, 25.0)
        self.assertEqual(len(anomalies), 0)  # Not exceeding yet
        
        # Test 4: Vehicle stopped for 21 seconds (exceeds threshold)
        anomalies = self.detector.detect_anomalies([car_detection], mock_tracker, 26.0)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["type"], "stopped_vehicle")
        self.assertIn("Xe car dừng bất thường", anomalies[0]["message"])
        self.assertIn("(21s)", anomalies[0]["message"])
        self.assertEqual(anomalies[0]["severity"], "high")
        
    def test_stopped_vehicle_resume_movement(self):
        """Test vehicle resuming movement clears stopped status"""
        mock_tracker = Mock(spec=VehicleTracker)
        
        car_detection = Detection(
            id="car_1",
            class_name="car",
            confidence=0.9,
            bbox=(100, 100, 200, 200)
        )
        
        # Vehicle stopped
        mock_tracker.get_movement_info.return_value = {
            "speed": 0.0,
            "distance": 0.0,
            "stopped": True
        }
        
        self.detector.detect_anomalies([car_detection], mock_tracker, 5.0)
        self.assertIn("car_1", self.detector.stopped_vehicles)
        
        # Vehicle starts moving
        mock_tracker.get_movement_info.return_value = {
            "speed": 15.0,
            "distance": 20.0,
            "stopped": False
        }
        
        anomalies = self.detector.detect_anomalies([car_detection], mock_tracker, 10.0)
        
        # Should be removed from stopped vehicles
        self.assertNotIn("car_1", self.detector.stopped_vehicles)
        self.assertEqual(len(anomalies), 0)
        
    def test_multiple_vehicle_types_stopped(self):
        """Test different vehicle types can be tracked as stopped"""
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.get_movement_info.return_value = {
            "speed": 0.0,
            "distance": 0.0,
            "stopped": True
        }
        
        vehicle_types = ["car", "motorbike", "truck", "bus"]
        detections = []
        
        for i, vtype in enumerate(vehicle_types):
            det = Detection(
                id=f"{vtype}_1",
                class_name=vtype,
                confidence=0.9,
                bbox=(100*i, 100, 100*i+80, 180)
            )
            detections.append(det)
        
        # First detection - all vehicles stop
        self.detector.detect_anomalies(detections, mock_tracker, 5.0)
        self.assertEqual(len(self.detector.stopped_vehicles), 4)
        
        # After 25 seconds - all should trigger alerts
        anomalies = self.detector.detect_anomalies(detections, mock_tracker, 30.0)
        self.assertEqual(len(anomalies), 4)
        
        for anomaly in anomalies:
            self.assertEqual(anomaly["type"], "stopped_vehicle")
            self.assertEqual(anomaly["severity"], "high")
            self.assertIn("(25s)", anomaly["message"])
            
    def test_mixed_anomalies_detection(self):
        """Test detecting multiple types of anomalies simultaneously"""
        mock_tracker = Mock(spec=VehicleTracker)
        
        # Setup various detections
        detections = [
            Detection(id="person_1", class_name="person", confidence=0.9, 
                     bbox=(100, 100, 150, 200)),
            Detection(id="dog_1", class_name="dog", confidence=0.8,
                     bbox=(200, 200, 250, 250)),
            Detection(id="car_1", class_name="car", confidence=0.9,
                     bbox=(300, 300, 400, 400)),
            Detection(id="debris_1", class_name="debris", confidence=0.7,
                     bbox=(500, 500, 600, 600))
        ]
        
        # Car is stopped for 25 seconds
        def movement_info_side_effect(obj_id):
            if obj_id == "car_1":
                return {"speed": 0.0, "distance": 0.0, "stopped": True}
            return {"speed": 10.0, "distance": 10.0, "stopped": False}
        
        mock_tracker.get_movement_info.side_effect = movement_info_side_effect
        
        # First pass - register stopped car
        self.detector.detect_anomalies([detections[2]], mock_tracker, 5.0)
        
        # Second pass - all detections after 25 seconds
        anomalies = self.detector.detect_anomalies(detections, mock_tracker, 30.0)
        
        # Should have 4 anomalies
        self.assertEqual(len(anomalies), 4)
        
        # Check each type
        anomaly_types = [a["type"] for a in anomalies]
        self.assertIn("pedestrian", anomaly_types)
        self.assertIn("animal", anomaly_types)
        self.assertIn("stopped_vehicle", anomaly_types)
        self.assertIn("obstacle", anomaly_types)
        
    def test_anomaly_severity_levels(self):
        """Test different severity levels for anomalies"""
        # Pedestrian - medium severity
        person = Detection(id="person_1", class_name="person", 
                          confidence=0.9, bbox=(100, 100, 150, 200))
        anomalies = self.detector.detect_anomalies([person], self.tracker, 10.0)
        self.assertEqual(anomalies[0]["severity"], "medium")
        
        # Stopped vehicle - high severity
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.get_movement_info.return_value = {
            "speed": 0.0, "distance": 0.0, "stopped": True
        }
        
        car = Detection(id="car_1", class_name="car",
                       confidence=0.9, bbox=(200, 200, 300, 300))
        
        # Register as stopped
        self.detector.detect_anomalies([car], mock_tracker, 5.0)
        
        # Check after threshold
        anomalies = self.detector.detect_anomalies([car], mock_tracker, 30.0)
        self.assertEqual(anomalies[0]["severity"], "high")
        
    def test_get_active_anomalies(self):
        """Test retrieving currently active anomalies"""
        # Add some stopped vehicles
        self.detector.stopped_vehicles = {
            "car_1": {
                "vehicle_type": "car",
                "position": (100, 100),
                "start_time": 10.0
            },
            "truck_1": {
                "vehicle_type": "truck", 
                "position": (200, 200),
                "start_time": 15.0
            }
        }
        
        active = self.detector.get_active_anomalies()
        
        self.assertIn("stopped_vehicles", active)
        self.assertEqual(len(active["stopped_vehicles"]), 2)
        
        # Check structure
        for vehicle in active["stopped_vehicles"]:
            self.assertIn("id", vehicle)
            self.assertIn("type", vehicle)
            self.assertIn("position", vehicle)
            
    def test_reset_functionality(self):
        """Test reset clears all anomaly data"""
        # Add some data
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.get_movement_info.return_value = {
            "speed": 0.0, "distance": 0.0, "stopped": True
        }
        
        car = Detection(id="car_1", class_name="car",
                       confidence=0.9, bbox=(100, 100, 200, 200))
        
        self.detector.detect_anomalies([car], mock_tracker, 5.0)
        
        # Verify data exists
        self.assertEqual(len(self.detector.stopped_vehicles), 1)
        
        # Reset
        self.detector.reset()
        
        # Verify cleared
        self.assertEqual(len(self.detector.stopped_vehicles), 0)
        
    def test_stop_duration_accuracy(self):
        """Test accurate calculation of stop duration"""
        mock_tracker = Mock(spec=VehicleTracker)
        mock_tracker.get_movement_info.return_value = {
            "speed": 0.0, "distance": 0.0, "stopped": True
        }
        
        car = Detection(id="car_1", class_name="car",
                       confidence=0.9, bbox=(100, 100, 200, 200))
        
        # Start at 5 seconds
        self.detector.detect_anomalies([car], mock_tracker, 5.0)
        
        # Check at various times
        test_times = [
            (15.0, 10, False),  # 10s - no alert
            (20.0, 15, False),  # 15s - no alert
            (25.0, 20, False),  # 20s - at threshold, no alert
            (26.0, 21, True),   # 21s - alert
            (30.0, 25, True),   # 25s - alert
            (45.0, 40, True)    # 40s - alert
        ]
        
        for current_time, expected_duration, should_alert in test_times:
            anomalies = self.detector.detect_anomalies([car], mock_tracker, current_time)
            
            if should_alert:
                self.assertEqual(len(anomalies), 1)
                # Check duration in message
                self.assertIn(f"({expected_duration}s)", anomalies[0]["message"])
            else:
                self.assertEqual(len(anomalies), 0)
                
    def test_edge_case_empty_detections(self):
        """Test handling empty detection list"""
        anomalies = self.detector.detect_anomalies([], self.tracker, 10.0)
        self.assertEqual(len(anomalies), 0)
        
    def test_edge_case_none_values(self):
        """Test handling None values and edge cases in detection"""
        # Case 1: Detection with None bbox (should not calculate center)
        detection1 = Detection(
            id="test_1",
            class_name="person",
            confidence=0.9,
            bbox=None,
            center=None
        )
        
        # Should handle gracefully with position as None
        anomalies = self.detector.detect_anomalies([detection1], self.tracker, 10.0)
        self.assertEqual(len(anomalies), 1)
        self.assertIn("Phát hiện người đi bộ tại unknown", anomalies[0]["message"])
        self.assertIsNone(anomalies[0]["position"])
        
        # Case 2: Detection with empty bbox tuple
        detection2 = Detection(
            id="test_2", 
            class_name="dog",
            confidence=0.8,
            bbox=(),
            center=None
        )
        
        anomalies = self.detector.detect_anomalies([detection2], self.tracker, 10.0)
        self.assertEqual(len(anomalies), 1)
        self.assertIn("Phát hiện động vật", anomalies[0]["message"])
        
        # Case 3: Detection with valid bbox but forced None center
        # This tests the case where center is explicitly set to None despite having bbox
        detection3 = Detection(
            id="test_3",
            class_name="person",
            confidence=0.9,
            bbox=(100, 100, 150, 200),
            center=None  # Will be auto-calculated in __post_init__
        )
        # After __post_init__, center should be calculated
        self.assertIsNotNone(detection3.center)
        self.assertEqual(detection3.center, (125.0, 150.0))
        
        anomalies = self.detector.detect_anomalies([detection3], self.tracker, 10.0)
        self.assertEqual(len(anomalies), 1)
        self.assertIn("(125, 150)", anomalies[0]["message"])


if __name__ == '__main__':
    unittest.main()