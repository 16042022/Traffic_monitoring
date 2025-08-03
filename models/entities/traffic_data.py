# models/entities/traffic_data.py
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime


@dataclass
class VehicleCount:
    """Entity cho việc đếm xe"""
    vehicle_type: str
    count: int = 0
    
    def increment(self):
        """Tăng count"""
        self.count += 1


@dataclass
class TrafficData:
    """Entity chứa dữ liệu thống kê traffic cho video"""
    video_id: int
    total_vehicles: int = 0
    
    # Đếm theo loại xe - lưu trực tiếp số lượng
    car_count: int = 0
    motorbike_count: int = 0
    truck_count: int = 0
    bus_count: int = 0
    
    # Thống kê theo thời gian
    hourly_counts: Dict[int, Dict[str, int]] = field(default_factory=dict)
    
    # Metadata
    processing_time: float = 0.0  # Thời gian xử lý (seconds)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_vehicle(self, vehicle_type: str):
        """Thêm một xe vào thống kê"""
        if vehicle_type == "car":
            self.car_count += 1
        elif vehicle_type == "motorbike":
            self.motorbike_count += 1
        elif vehicle_type == "truck":
            self.truck_count += 1
        elif vehicle_type == "bus":
            self.bus_count += 1
        
        # Update total
        if vehicle_type in ["car", "motorbike", "truck", "bus"]:
            self.total_vehicles += 1
    
    def get_summary(self) -> Dict[str, int]:
        """Lấy summary counts"""
        return {
            "car": self.car_count,
            "motorbike": self.motorbike_count,
            "truck": self.truck_count,
            "bus": self.bus_count
        }
    
    @property
    def vehicle_counts(self) -> Dict[str, int]:
        """Property để tương thích với code cũ"""
        return self.get_summary()