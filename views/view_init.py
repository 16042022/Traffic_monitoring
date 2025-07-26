# views/__init__.py
from .base_view import BaseView
from .main_window import MainWindow
from .video_player_widget import VideoPlayerWidget, VideoDisplay
from .analysis_panel import AnalysisPanel
from .history_widget import HistoryWidget

__all__ = [
    'BaseView',
    'MainWindow',
    'VideoPlayerWidget',
    'VideoDisplay',
    'AnalysisPanel',
    'HistoryWidget'
]