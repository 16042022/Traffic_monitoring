# models/components/vehicle_tracker.py
import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from collections import deque
import logging

from ..entities import Detection


class VehicleTracker:
    """
    Component chịu trách nhiệm tracking vehicles (VT)
    Gán và duy trì ID cho objects qua các frames
    """
    
    def __init__(self, max_history: int = 30):
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        
        # Tracking data
        self.tracking_history: Dict[str, deque] = {}  # {object_id: deque[(x, y, timestamp)]}
        self.last_positions: Dict[str, Tuple[float, float]] = {}  # {object_id: (x, y)}
        self.next_id = 1
        
        # For counting
        self.counted_ids: Set[str] = set()
        
    def update_tracks(self, detections: List[Detection], timestamp: float) -> List[Detection]:
        """
        Update tracking cho các detections
        
        Args:
            detections: List các detections từ frame hiện tại
            timestamp: Timestamp của frame
            
        Returns:
            List detections với ID được gán
        """
        # Simple tracking: dựa trên khoảng cách gần nhất
        # Trong thực tế nên dùng algorithm phức tạp hơn như SORT, DeepSORT
        
        current_positions = {}
        unmatched_detections = []
        
        for detection in detections:
            center = detection.center
            if not center:
                continue
                
            # Tìm track gần nhất
            best_id = None
            min_distance = float('inf')
            
            for obj_id, last_pos in self.last_positions.items():
                distance = np.sqrt((center[0] - last_pos[0])**2 + 
                                 (center[1] - last_pos[1])**2)
                
                # Threshold distance (pixels) - có thể điều chỉnh
                if distance < 50 and distance < min_distance:
                    min_distance = distance
                    best_id = obj_id
            
            if best_id:
                # Match found - cập nhật existing track
                detection.id = best_id
                current_positions[best_id] = center
                self._update_history(best_id, center, timestamp)
            else:
                # No match - tạo track mới
                unmatched_detections.append(detection)
        
        # Tạo ID mới cho unmatched detections
        for detection in unmatched_detections:
            new_id = f"obj_{self.next_id}"
            self.next_id += 1
            detection.id = new_id
            
            center = detection.center
            if center:
                current_positions[new_id] = center
                self._update_history(new_id, center, timestamp)
        
        # Update last positions
        self.last_positions = current_positions
        
        # Clean up old tracks
        self._cleanup_old_tracks(timestamp)
        
        return detections
    
    def _update_history(self, obj_id: str, position: Tuple[float, float], timestamp: float):
        """Update history cho một object"""
        if obj_id not in self.tracking_history:
            self.tracking_history[obj_id] = deque(maxlen=self.max_history)
        
        self.tracking_history[obj_id].append((position[0], position[1], timestamp))
    
    def _cleanup_old_tracks(self, current_timestamp: float, max_age: float = 2.0):
        """Xóa các tracks cũ không còn active"""
        ids_to_remove = []
        
        for obj_id, history in self.tracking_history.items():
            if history and (current_timestamp - history[-1][2]) > max_age:
                ids_to_remove.append(obj_id)
        
        for obj_id in ids_to_remove:
            del self.tracking_history[obj_id]
            if obj_id in self.last_positions:
                del self.last_positions[obj_id]
    
    def check_line_crossing(self, obj_id: str, 
                           line_start: Tuple[int, int], 
                           line_end: Tuple[int, int],
                           direction: str = "down") -> bool:
        """
        Kiểm tra object có vượt qua line không
        
        Args:
            obj_id: Object ID
            line_start: Điểm đầu của line
            line_end: Điểm cuối của line
            direction: Hướng đếm (up/down/left/right)
            
        Returns:
            True nếu vượt qua line theo đúng hướng
        """
        if obj_id not in self.tracking_history:
            return False
        
        history = self.tracking_history[obj_id]
        if len(history) < 2:
            return False
        
        # Lấy 2 vị trí gần nhất
        prev_pos = history[-2][:2]
        curr_pos = history[-1][:2]
        
        # Kiểm tra intersection
        if not self._line_intersection(prev_pos, curr_pos, line_start, line_end):
            return False
        
        # Kiểm tra hướng
        if direction == "down" and curr_pos[1] <= prev_pos[1]:
            return False
        elif direction == "up" and curr_pos[1] >= prev_pos[1]:
            return False
        elif direction == "left" and curr_pos[0] >= prev_pos[0]:
            return False
        elif direction == "right" and curr_pos[0] <= prev_pos[0]:
            return False
        
        # Kiểm tra đã đếm chưa
        if obj_id in self.counted_ids:
            return False
        
        # Mark as counted
        self.counted_ids.add(obj_id)
        return True
    
    def _line_intersection(self, p1: Tuple[float, float], p2: Tuple[float, float],
                          p3: Tuple[int, int], p4: Tuple[int, int]) -> bool:
        """
        Kiểm tra 2 đoạn thẳng có cắt nhau không
        p1-p2: movement line
        p3-p4: counting line
        """
        def ccw(A, B, C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
        
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
    
    def get_movement_info(self, obj_id: str, time_window: float = 1.0) -> Dict[str, float]:
        """
        Lấy thông tin di chuyển của object
        
        Args:
            obj_id: Object ID
            time_window: Thời gian tính toán (seconds)
            
        Returns:
            Dict với speed, direction, distance
        """
        if obj_id not in self.tracking_history:
            return {"speed": 0, "distance": 0, "stopped": True}
        
        history = list(self.tracking_history[obj_id])
        if len(history) < 2:
            return {"speed": 0, "distance": 0, "stopped": True}
        
        # Lấy positions trong time window
        current_time = history[-1][2]
        positions_in_window = []
        
        for pos in reversed(history):
            if current_time - pos[2] <= time_window:
                positions_in_window.append(pos)
            else:
                break
        
        if len(positions_in_window) < 2:
            return {"speed": 0, "distance": 0, "stopped": True}
        
        # Tính total distance
        total_distance = 0
        for i in range(len(positions_in_window) - 1):
            dist = np.sqrt((positions_in_window[i][0] - positions_in_window[i+1][0])**2 + 
                          (positions_in_window[i][1] - positions_in_window[i+1][1])**2)
            total_distance += dist
        
        # Tính speed (pixels/second)
        time_elapsed = positions_in_window[0][2] - positions_in_window[-1][2]
        speed = total_distance / time_elapsed if time_elapsed > 0 else 0
        
        # Check if stopped (speed < threshold)
        stopped = speed < 5.0  # pixels/second
        
        return {
            "speed": speed,
            "distance": total_distance,
            "stopped": stopped
        }
    
    def reset(self):
        """Reset tất cả tracking data"""
        self.tracking_history.clear()
        self.last_positions.clear()
        self.counted_ids.clear()
        self.next_id = 1
        self.logger.info("Tracker reset")