# controllers/base_controller.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
import logging
from PyQt5.QtCore import QObject, pyqtSignal

from utils import LoggerMixin


class BaseController(QObject, LoggerMixin, ABC):
    """
    Abstract base controller class
    Provides common functionality for all controllers
    """
    
    # Common signals
    error_occurred = pyqtSignal(str)  # Error message
    info_message = pyqtSignal(str)   # Info message
    busy_state_changed = pyqtSignal(bool)  # Busy state
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = None
        self._model = None
        self._is_busy = False
        
    def set_view(self, view):
        """
        Set the view component
        
        Args:
            view: View instance
        """
        self._view = view
        self._connect_view_signals()
        self.logger.debug(f"View set for {self.__class__.__name__}")
    
    def set_model(self, model):
        """
        Set the model component
        
        Args:
            model: Model instance
        """
        self._model = model
        self._connect_model_callbacks()
        self.logger.debug(f"Model set for {self.__class__.__name__}")
    
    @abstractmethod
    def _connect_view_signals(self):
        """Connect view signals to controller slots"""
        pass
    
    @abstractmethod
    def _connect_model_callbacks(self):
        """Set model callbacks"""
        pass
    
    def _set_busy(self, busy: bool):
        """
        Set busy state
        
        Args:
            busy: Whether controller is busy
        """
        self._is_busy = busy
        self.busy_state_changed.emit(busy)
    
    def _handle_error(self, error: Exception, message: str = None):
        """
        Handle error uniformly
        
        Args:
            error: Exception object
            message: Custom error message
        """
        if message is None:
            message = str(error)
        
        self.logger.error(f"Error in {self.__class__.__name__}: {message}")
        self.error_occurred.emit(message)
    
    def _show_info(self, message: str):
        """
        Show info message
        
        Args:
            message: Info message
        """
        self.logger.info(message)
        self.info_message.emit(message)
    
    @property
    def is_busy(self) -> bool:
        """Check if controller is busy"""
        return self._is_busy
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.debug(f"Cleaning up {self.__class__.__name__}")
        # Override in subclasses if needed