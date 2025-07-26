# tests/test_vehicle_tracker.py
import unittest
from collections import deque

from test_base import BaseTestCase, MockDetection
from models.components.vehicle_tracker import VehicleTracker
from models.entities import Detection


class TestVehicleTracker(BaseTestCase):
    """Test VehicleTracker component"""
    
    def setUp(self):
        super().setUp()
        self.tracker = VehicleTracker(max_history=30)
        
    def test_unique_id_assignment(self):
        """Test that each object gets unique ID"""
        # Create detections without IDs
        detections = [
            Detection(id="", class_name="car", confidence=0.9, bbox=(100, 100, 200, 200)),
            Detection(id="", class_name="motorbike", confidence=0.8, bbox=(300, 300, 400, 400)),
            Detection(id="", class_name="truck", confidence=0.85, bbox=(500, 500, 600, 600))
        ]
        
        # Update tracks
        updated = self.tracker.update_tracks(detections, timestamp=1.0)
        
        # Check unique IDs assigned
        ids = [d.id for d in updated]
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)  # All unique
        self.assertTrue(all(id.startswith("obj_") for id in ids))
        
    def test_id_persistence_across_frames(self):
        """Test that same object keeps same ID across frames"""
        # Frame 1
        det1 = Detection(id="", class_name="car", confidence=0.9, bbox=(100, 100, 200, 200))
        updated1 = self.tracker.update_tracks([det1], timestamp=1.0)
        car_id = updated1[0].id
        
        # Frame 2 - same car moved slightly
        det2 = Detection(id="", class_name="car", confidence=0.9, bbox=(110, 110, 210, 210))
        updated2 = self.tracker.update_tracks([det2], timestamp=2.0)
        
        # Should have same ID
        self.assertEqual(updated2[0].id, car_id)
        
    def test_tracking_history_maintenance(self):
        """Test tracking history is maintained correctly"""
        # Track object across multiple frames
        positions = [(100, 100), (110, 110), (120, 120), (130, 130)]
        
        car_id = None
        for i, (x, y) in enumerate(positions):
            det = Detection(id="", class_name="car", confidence=0.9, 
                          bbox=(x, y, x+100, y+100))
            updated = self.tracker.update_tracks([det], timestamp=float(i))
            
            if car_id is None:
                car_id = updated[0].id
        
        # Check history
        self.assertIn(car_id, self.tracker.tracking_history)
        history = self.tracker.tracking_history[car_id]
        self.assertEqual(len(history), 4)
        
        # Verify positions in history
        for i, (x, y, t) in enumerate(history):
            expected_x = positions[i][0] + 50  # Center of bbox
            expected_y = positions[i][1] + 50
            self.assertAlmostEqual(x, expected_x, places=1)
            self.assertAlmostEqual(y, expected_y, places=1)
            self.assertEqual(t, float(i))
    
    def test_max_history_limit(self):
        """Test that history doesn't exceed max limit"""
        # Track object for more than max_history frames
        car_id = None
        for i in range(40):  # More than max_history=30
            det = Detection(id="", class_name="car", confidence=0.9, 
                          bbox=(100+i, 100+i, 200+i, 200+i))
            updated = self.tracker.update_tracks([det], timestamp=float(i))
            
            if car_id is None:
                car_id = updated[0].id
        
        # History should be capped at max_history
        history = self.tracker.tracking_history[car_id]
        self.assertEqual(len(history), 30)
        
        # Should contain latest 30 entries
        self.assertEqual(history[-1][2], 39.0)  # Last timestamp
        self.assertEqual(history[0][2], 10.0)   # First timestamp (39-29)
    
    def test_multiple_object_tracking(self):
        """Test tracking multiple objects simultaneously"""
        # Frame with multiple objects
        detections = [
            Detection(id="", class_name="car", confidence=0.9, bbox=(100, 100, 200, 200)),
            Detection(id="", class_name="motorbike", confidence=0.8, bbox=(300, 100, 350, 150)),
            Detection(id="", class_name="truck", confidence=0.85, bbox=(500, 100, 600, 200))
        ]
        
        # Track across frames
        for frame in range(5):
            # Move each object differently
            moved_detections = []
            for i, det in enumerate(detections):
                new_bbox = (
                    det.bbox[0] + frame * 10 * (i + 1),  # Different speeds
                    det.bbox[1],
                    det.bbox[2] + frame * 10 * (i + 1),
                    det.bbox[3]
                )
                moved_det = Detection(
                    id="", 
                    class_name=det.class_name,
                    confidence=det.confidence,
                    bbox=new_bbox
                )
                moved_detections.append(moved_det)
            
            updated = self.tracker.update_tracks(moved_detections, timestamp=float(frame))
            
            # Should maintain 3 separate tracks
            self.assertEqual(len(updated), 3)
            self.assertEqual(len(self.tracker.tracking_history), 3)
    
    def test_old_track_cleanup(self):
        """Test that old inactive tracks are cleaned up"""
        # Create a track
        det1 = Detection(id="", class_name="car", confidence=0.9, bbox=(100, 100, 200, 200))
        updated1 = self.tracker.update_tracks([det1], timestamp=1.0)
        car_id = updated1[0].id
        
        # Verify track exists
        self.assertIn(car_id, self.tracker.tracking_history)
        
        # Update without this car (simulating it left the scene)
        det2 = Detection(id="", class_name="truck", confidence=0.9, bbox=(300, 300, 400, 400))
        self.tracker.update_tracks([det2], timestamp=4.0)  # 3 seconds later
        
        # Old track should be cleaned up (max_age=2.0 seconds)
        self.assertNotIn(car_id, self.tracker.tracking_history)
    
    def test_line_crossing_detection(self):
        """Test virtual line crossing detection"""
        # Define virtual line
        line_start = (400, 100)
        line_end = (400, 500)
        direction = "right"  # Count objects moving right
        
        # Object moving left to right across the line
        positions = [(350, 300), (380, 300), (420, 300), (450, 300)]
        
        car_id = None
        crossed = False
        
        for i, (x, y) in enumerate(positions):
            det = Detection(id="", class_name="car", confidence=0.9,
                          bbox=(x-50, y-50, x+50, y+50))
            updated = self.tracker.update_tracks([det], timestamp=float(i))
            
            if car_id is None:
                car_id = updated[0].id
            
            # Check crossing
            if self.tracker.check_line_crossing(car_id, line_start, line_end, direction):
                crossed = True
                crossing_frame = i
        
        self.assertTrue(crossed)
        self.assertEqual(crossing_frame, 2)  # Crossed between frame 1 and 2
        
        # Should only count once
        self.assertIn(car_id, self.tracker.counted_ids)
        
        # Further checks should return False
        det = Detection(id="", class_name="car", confidence=0.9,
                      bbox=(500, 250, 600, 350))
        updated = self.tracker.update_tracks([det], timestamp=5.0)
        self.assertFalse(
            self.tracker.check_line_crossing(car_id, line_start, line_end, direction)
        )
    
    def test_movement_info_calculation(self):
        """Test movement info (speed, distance, stopped) calculation"""
        # Stationary object
        car_id = None
        for i in range(5):
            det = Detection(id="", class_name="car", confidence=0.9,
                          bbox=(100, 100, 200, 200))  # Same position
            updated = self.tracker.update_tracks([det], timestamp=float(i))
            if car_id is None:
                car_id = updated[0].id
        
        movement = self.tracker.get_movement_info(car_id, time_window=1.0)
        self.assertTrue(movement['stopped'])
        self.assertEqual(movement['speed'], 0.0)
        self.assertEqual(movement['distance'], 0.0)
        
        # Moving object
        truck_id = None
        for i in range(5):
            det = Detection(id="", class_name="truck", confidence=0.9,
                          bbox=(100+i*20, 100, 200+i*20, 200))  # Moving right
            updated = self.tracker.update_tracks([det], timestamp=float(i))
            if truck_id is None:
                truck_id = updated[0].id
        
        movement = self.tracker.get_movement_info(truck_id, time_window=1.0)
        self.assertFalse(movement['stopped'])
        self.assertGreater(movement['speed'], 0.0)
        self.assertGreater(movement['distance'], 0.0)
    
    def test_reset_functionality(self):
        """Test reset clears all tracking data"""
        # Add some tracking data
        detections = [
            Detection(id="", class_name="car", confidence=0.9, bbox=(100, 100, 200, 200)),
            Detection(id="", class_name="truck", confidence=0.8, bbox=(300, 300, 400, 400))
        ]
        
        updated = self.tracker.update_tracks(detections, timestamp=1.0)
        car_id = updated[0].id
        
        # Mark as counted
        self.tracker.counted_ids.add(car_id)
        
        # Verify data exists
        self.assertEqual(len(self.tracker.tracking_history), 2)
        self.assertEqual(len(self.tracker.counted_ids), 1)
        self.assertGreater(self.tracker.next_id, 1)
        
        # Reset
        self.tracker.reset()
        
        # Verify all cleared
        self.assertEqual(len(self.tracker.tracking_history), 0)
        self.assertEqual(len(self.tracker.last_positions), 0)
        self.assertEqual(len(self.tracker.counted_ids), 0)
        self.assertEqual(self.tracker.next_id, 1)


if __name__ == '__main__':
    unittest.main()