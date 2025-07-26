# models/components/anomaly_detector.py
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

from ..entities import Detection, DetectionResult
from .vehicle_tracker import VehicleTracker


class AnomalyDetector:
    """
    Component phát hiện các bất thường (OAD)
    - Người đi bộ trên đường
    - Động vật
    - Vật cản
    - Xe dừng bất thường
    """
    
    def __init__(self, stop_time_threshold: float = 20.0):
        self.logger = logging.getLogger(__name__)
        self.stop_time_threshold = stop_time_threshold
        
        # Track stopped vehicles
        self.stopped_vehicles: Dict[str, Dict] = {}  # {obj_id: {"start_time": t, "position": (x,y)}}
        
        # Anomaly categories
        self.anomaly_classes = {
            "pedestrian": ["person"],
            "animal": ["dog", "cat", "bird", "animal"],
            "obstacle": ["obstacle", "debris", "rock", "tree", "garbage"],
            "stopped_vehicle": ["car", "motorbike", "truck", "bus"]
        }
        
    def detect_anomalies(self, detections: List[Detection], 
                        tracker: VehicleTracker,
                        timestamp: float) -> List[Dict]:
        """
        Detect anomalies trong frame
        
        Args:
            detections: List detections 
            tracker: VehicleTracker instance
            timestamp: Video timestamp
            
        Returns:
            List các anomalies detected
        """
        anomalies = []
        
        for detection in detections:
            # Check pedestrians
            if detection.class_name in self.anomaly_classes["pedestrian"]:
                anomaly = self._create_anomaly(
                    "pedestrian",
                    f"Phát hiện người đi bộ tại {self._format_position(detection.center)}",
                    detection,
                    timestamp
                )
                anomalies.append(anomaly)
                
            # Check animals
            elif detection.class_name in self.anomaly_classes["animal"]:
                anomaly = self._create_anomaly(
                    "animal",
                    f"Phát hiện động vật trên đường: {detection.class_name}",
                    detection,
                    timestamp
                )
                anomalies.append(anomaly)
                
            # Check obstacles
            elif detection.class_name in self.anomaly_classes["obstacle"]:
                anomaly = self._create_anomaly(
                    "obstacle",
                    f"Phát hiện vật cản: {detection.class_name}",
                    detection,
                    timestamp
                )
                anomalies.append(anomaly)
                
            # Check stopped vehicles
            elif detection.class_name in self.anomaly_classes["stopped_vehicle"]:
                stopped_anomaly = self._check_stopped_vehicle(
                    detection, tracker, timestamp
                )
                if stopped_anomaly:
                    anomalies.append(stopped_anomaly)
        
        return anomalies
    
    def _check_stopped_vehicle(self, detection: Detection,
                             tracker: VehicleTracker,
                             timestamp: float) -> Optional[Dict]:
        """Check if vehicle is stopped abnormally"""
        movement_info = tracker.get_movement_info(detection.id)
        
        if movement_info["stopped"]:
            # Vehicle is stopped
            if detection.id not in self.stopped_vehicles:
                # Start tracking stopped time
                self.stopped_vehicles[detection.id] = {
                    "start_time": timestamp,
                    "position": detection.center,
                    "vehicle_type": detection.class_name
                }
                self.logger.info(f"Vehicle {detection.id} started stopping at {timestamp:.1f}s")
            else:
                # Check duration
                stop_duration = timestamp - self.stopped_vehicles[detection.id]["start_time"]
                
                if stop_duration > self.stop_time_threshold:
                    # Abnormal stop detected
                    return self._create_anomaly(
                        "stopped_vehicle",
                        f"Xe {detection.class_name} dừng bất thường ({int(stop_duration)}s)",
                        detection,
                        timestamp,
                        severity="high",
                        additional_info={
                            "stop_duration": stop_duration,
                            "vehicle_type": detection.class_name
                        }
                    )
        else:
            # Vehicle is moving, remove from stopped list
            if detection.id in self.stopped_vehicles:
                del self.stopped_vehicles[detection.id]
                self.logger.info(f"Vehicle {detection.id} resumed moving")
        
        return None
    
    def _create_anomaly(self, anomaly_type: str, message: str,
                       detection: Detection, timestamp: float,
                       severity: str = "medium",
                       additional_info: Optional[Dict] = None) -> Dict:
        """Create anomaly record"""
        anomaly = {
            "type": anomaly_type,
            "message": message,
            "timestamp": timestamp,
            "object_id": detection.id,
            "object_class": detection.class_name,
            "position": detection.center,
            "bbox": detection.bbox,
            "severity": severity,
            "detected_at": datetime.now()
        }
        
        if additional_info:
            anomaly.update(additional_info)
            
        return anomaly
    
    def _format_position(self, position: Optional[Tuple[float, float]]) -> str:
        """Format position for display"""
        if position is None:
            return "unknown"
        if position:
            return f"({int(position[0])}, {int(position[1])})"
        return "unknown"
    
    def get_active_anomalies(self) -> Dict:
        """Get currently active anomalies"""
        return {
            "stopped_vehicles": [
                {
                    "id": obj_id,
                    "type": info["vehicle_type"],
                    "position": info["position"],
                    "duration": info.get("current_duration", 0)
                }
                for obj_id, info in self.stopped_vehicles.items()
            ]
        }
    
    def reset(self):
        """Reset anomaly detector"""
        self.stopped_vehicles.clear()
        self.logger.info("Anomaly detector reset")