# controllers/base_controller.py
from typing import Optional
import logging
from PyQt5.QtCore import QObject, pyqtSignal


class BaseController(QObject):
    """
    Base controller class without ABC
    Provides common functionality for all controllers
    """
    
    # Common signals
    error_occurred = pyqtSignal(str)  # Error message
    info_message = pyqtSignal(str)   # Info message
    busy_state_changed = pyqtSignal(bool)  # Busy state
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize logger
        self._setup_logger()
        
        # Initialize attributes
        self._view = None
        self._model = None
        self._is_busy = False
        
    def _setup_logger(self):
        """Setup logger for this controller"""
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        
    @property
    def view(self):
        """Get view component"""
        return self._view
        
    @property 
    def model(self):
        """Get model component"""
        return self._model
        
    def set_view(self, view):
        """
        Set the view component
        
        Args:
            view: View instance
        """
        self._view = view
        try:
            self._connect_view_signals()
            self.logger.debug(f"View set for {self.__class__.__name__}")
        except Exception as e:
            self.logger.error(f"Error connecting view signals: {e}")
    
    def set_model(self, model):
        """
        Set the model component
        
        Args:
            model: Model instance
        """
        self._model = model
        try:
            self._connect_model_callbacks()
            self.logger.debug(f"Model set for {self.__class__.__name__}")
        except Exception as e:
            self.logger.error(f"Error connecting model callbacks: {e}")
    
    def _connect_view_signals(self):
        """
        Connect view signals to controller slots
        Override this method in subclasses
        """
        # Default implementation - does nothing
        # Subclasses should override this method
        pass
    
    def _connect_model_callbacks(self):
        """
        Set model callbacks
        Override this method in subclasses
        """
        # Default implementation - does nothing
        # Subclasses should override this method
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
        
        self.logger.error(f"Error in {self.__class__.__name__}: {message}", exc_info=True)
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
        """
        Cleanup resources
        Override this method in subclasses if needed
        """
        self.logger.debug(f"Cleaning up {self.__class__.__name__}")
        
        # Clean up view connections
        if self._view:
            try:
                # Disconnect any signals if needed
                pass
            except:
                pass
                
        # Clean up model
        if self._model:
            try:
                # Any model cleanup
                pass
            except:
                pass