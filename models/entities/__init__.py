# models/entities/__init__.py
from .video_info import VideoInfo
from .detection_result import DetectionResult, Detection
from .traffic_data import TrafficData, VehicleCount
from .processing_state import ProcessingState

__all__ = [
    'VideoInfo', 
    'DetectionResult', 
    'Detection',
    'TrafficData', 
    'VehicleCount',
    'ProcessingState'
]