# utils/helpers.py
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Union, Tuple, Optional
import cv2
import numpy as np


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if not
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to HH:MM:SS
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_timestamp(timestamp: Union[float, datetime]) -> str:
    """
    Format timestamp for display
    
    Args:
        timestamp: Timestamp (float or datetime)
        
    Returns:
        Formatted string
    """
    if isinstance(timestamp, float):
        return format_duration(timestamp)
    elif isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return str(timestamp)


def parse_resolution(resolution: str) -> Tuple[int, int]:
    """
    Parse resolution string to tuple
    
    Args:
        resolution: Resolution string (e.g., "1920x1080")
        
    Returns:
        Tuple (width, height)
    """
    try:
        width, height = map(int, resolution.split('x'))
        return width, height
    except:
        return 1920, 1080  # Default


def resize_frame_maintain_aspect(frame: np.ndarray, 
                                target_size: Tuple[int, int]) -> np.ndarray:
    """
    Resize frame maintaining aspect ratio
    
    Args:
        frame: Input frame
        target_size: Target (width, height)
        
    Returns:
        Resized frame
    """
    target_width, target_height = target_size
    h, w = frame.shape[:2]
    
    # Calculate scaling factor
    scale = min(target_width / w, target_height / h)
    
    # Calculate new dimensions
    new_width = int(w * scale)
    new_height = int(h * scale)
    
    # Resize
    resized = cv2.resize(frame, (new_width, new_height), 
                        interpolation=cv2.INTER_AREA)
    
    # Create canvas and center the image
    canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    y_offset = (target_height - new_height) // 2
    x_offset = (target_width - new_width) // 2
    
    canvas[y_offset:y_offset+new_height, 
           x_offset:x_offset+new_width] = resized
    
    return canvas


def is_video_file(file_path: Union[str, Path]) -> bool:
    """
    Check if file is a video
    
    Args:
        file_path: File path
        
    Returns:
        True if video file
    """
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    path = Path(file_path)
    return path.suffix.lower() in video_extensions


def get_video_info(file_path: Union[str, Path]) -> Optional[dict]:
    """
    Get video file information
    
    Args:
        file_path: Video file path
        
    Returns:
        Dict with video info or None
    """
    try:
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            return None
            
        info = {
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
        }
        
        cap.release()
        return info
        
    except Exception:
        return None


def generate_export_filename(prefix: str = "traffic_analysis", 
                           extension: str = "csv") -> str:
    """
    Generate export filename with timestamp
    
    Args:
        prefix: Filename prefix
        extension: File extension
        
    Returns:
        Generated filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def calculate_iou(box1: Tuple[int, int, int, int], 
                 box2: Tuple[int, int, int, int]) -> float:
    """
    Calculate Intersection over Union of two boxes
    
    Args:
        box1: First box (x1, y1, x2, y2)
        box2: Second box (x1, y1, x2, y2)
        
    Returns:
        IoU value
    """
    # Calculate intersection
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    # Calculate union
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0


def point_in_polygon(point: Tuple[float, float], 
                    polygon: list) -> bool:
    """
    Check if point is inside polygon
    
    Args:
        point: (x, y) coordinates
        polygon: List of (x, y) vertices
        
    Returns:
        True if inside
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside