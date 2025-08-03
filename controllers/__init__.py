# controllers/__init__.py
"""
Controllers package
Import order matters to avoid circular imports
"""

# Import base controller first
from .base_controller import BaseController

# Then import specific controllers
from .video_controller import VideoController
from .analysis_controller import AnalysisController
from .history_controller import HistoryController

# Import main controller last (it uses other controllers)
from .main_controller import MainController

__all__ = [
    'BaseController',
    'VideoController',
    'AnalysisController',
    'HistoryController',
    'MainController'  # MainController ở cuối
]