# models/entities/detection_result.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class Detection:
    """Entity cho một object detection"""
    id: str  # Unique ID cho tracking
    class_name: str  # car, motorbike, person, etc.
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center: Optional[Tuple[float, float]] = None  # Center point
    
    def __post_init__(self):
        """Tính center point nếu chưa có"""
        if self.center is None and self.bbox:
            x1, y1, x2, y2 = self.bbox
            self.center = ((x1 + x2) / 2, (y1 + y2) / 2)


@dataclass
class DetectionResult:
    """Entity chứa kết quả detection cho một frame"""
    frame_id: int
    timestamp: float  # Timestamp trong video (seconds)
    detections: List[Detection] = field(default_factory=list)
    
    # Thống kê frame hiện tại
    vehicle_counts: Dict[str, int] = field(default_factory=lambda: {
        "car": 0,
        "motorbike": 0,
        "truck": 0,
        "bus": 0
    })
    
    # Alerts cho frame này
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_detection(self, detection: Detection):
        """Thêm detection và cập nhật counts"""
        self.detections.append(detection)
        if detection.class_name in self.vehicle_counts:
            self.vehicle_counts[detection.class_name] += 1
    
    def add_alert(self, alert_type: str, message: str, 
                  object_id: Optional[str] = None,
                  position: Optional[Tuple[float, float]] = None):
        """Thêm alert"""
        self.alerts.append({
            "type": alert_type,
            "message": message,
            "object_id": object_id,
            "position": position,
            "timestamp": self.timestamp
        })