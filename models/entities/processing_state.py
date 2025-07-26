# models/entities/processing_state.py
from enum import Enum


class ProcessingState(Enum):
    """Enum định nghĩa các trạng thái xử lý video"""
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"