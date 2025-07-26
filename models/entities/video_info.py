# models/entities/video_info.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class VideoInfo:
    """Entity class chứa thông tin về video"""
    id: Optional[int] = None  # Database ID
    file_name: str = ""
    file_path: str = ""
    fps: float = 0.0
    frame_count: int = 0
    width: int = 0
    height: int = 0
    duration: float = 0.0  # seconds
    upload_timestamp: Optional[datetime] = None
    processing_timestamp: Optional[datetime] = None
    status: str = "pending"  # pending, processing, completed, failed
    
    @property
    def resolution(self) -> str:
        """Trả về resolution dạng string"""
        return f"{self.width}x{self.height}"
    
    @property
    def duration_formatted(self) -> str:
        """Trả về duration dạng HH:MM:SS"""
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"