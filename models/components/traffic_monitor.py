# models/components/traffic_monitor.py
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

from ..entities import Detection, TrafficData
from .vehicle_tracker import VehicleTracker


class TrafficMonitor:
    """
    Component giám sát và thống kê traffic (TMD)
    Đếm lưu lượng, tính toán mật độ
    """
    
    def __init__(self, virtual_line_config: Dict):
        self.logger = logging.getLogger(__name__)
        
        # Virtual line configuration
        self.virtual_line = self._parse_virtual_line(virtual_line_config)
        
        # Traffic data - khởi tạo với các thuộc tính đếm xe
        self.traffic_data = TrafficData(video_id=0)
        
        # Hourly tracking
        self.current_hour = -1
        
    def _parse_virtual_line(self, config: Dict) -> Tuple[Tuple[int, int], Tuple[int, int], str]:
        """Parse virtual line từ config"""
        p1 = (config.get("p1_x", 100), config.get("p1_y", 300))
        p2 = (config.get("p2_x", 800), config.get("p2_y", 300))
        direction = config.get("counting_direction", "down")
        
        self.logger.info(f"Virtual line: {p1} -> {p2}, direction: {direction}")
        
        return (p1, p2, direction)
    
    def process_frame_detections(self, detections: List[Detection], 
                               tracker: VehicleTracker,
                               timestamp: float):
        """
        Process detections cho một frame
        
        Args:
            detections: List detections đã có ID
            tracker: VehicleTracker instance
            timestamp: Video timestamp
        """
        # Count vehicles in current frame
        frame_counts = {"car": 0, "motorbike": 0, "truck": 0, "bus": 0}
        
        for detection in detections:
            # Only count vehicles
            if detection.class_name in frame_counts:
                frame_counts[detection.class_name] += 1
                
                # Check line crossing
                if self._check_vehicle_crossing(detection, tracker):
                    self.traffic_data.add_vehicle(detection.class_name)
                    self.logger.info(f"Vehicle crossed: {detection.class_name} (ID: {detection.id})")
        
        # Update hourly statistics
        self._update_hourly_stats(timestamp, frame_counts)
    
    def _check_vehicle_crossing(self, detection: Detection, 
                              tracker: VehicleTracker) -> bool:
        """Check if vehicle crossed the virtual line"""
        line_start, line_end, direction = self.virtual_line
        
        return tracker.check_line_crossing(
            detection.id,
            line_start,
            line_end,
            direction
        )
    
    def _update_hourly_stats(self, timestamp: float, frame_counts: Dict[str, int]):
        """Update hourly statistics"""
        hour = int(timestamp // 3600)
        
        if hour not in self.traffic_data.hourly_counts:
            self.traffic_data.hourly_counts[hour] = {
                "car": 0, "motorbike": 0, "truck": 0, "bus": 0
            }
        
        # This is simplified - in reality you'd aggregate differently
        # For now, just track max count per hour
        for vehicle_type, count in frame_counts.items():
            current = self.traffic_data.hourly_counts[hour].get(vehicle_type, 0)
            self.traffic_data.hourly_counts[hour][vehicle_type] = max(current, count)
    
    def get_statistics(self) -> Dict:
        """
        Lấy thống kê hiện tại
        
        Returns:
            Dict chứa các thống kê
        """
        return {
            "total_vehicles": self.traffic_data.total_vehicles,
            "vehicle_counts": self.traffic_data.get_summary(),
            "hourly_counts": self.traffic_data.hourly_counts,
            "virtual_line": {
                "start": self.virtual_line[0],
                "end": self.virtual_line[1],
                "direction": self.virtual_line[2]
            }
        }
    
    def get_density_level(self, current_vehicle_count: int) -> str:
        """
        Xác định mức độ mật độ giao thông
        
        Args:
            current_vehicle_count: Số xe hiện tại trong frame
            
        Returns:
            Mức độ: "low", "medium", "high", "very_high"
        """
        if current_vehicle_count < 5:
            return "low"
        elif current_vehicle_count < 15:
            return "medium"
        elif current_vehicle_count < 25:
            return "high"
        else:
            return "very_high"
    
    def reset(self):
        """Reset traffic data"""
        self.traffic_data = TrafficData(video_id=0)
        self.current_hour = -1
        self.logger.info("Traffic monitor reset")