"""
Main Controller - Điều phối chính cho ứng dụng với phân tích TỰ ĐỘNG
"""

from PyQt5.QtCore import QObject, pyqtSignal
import logging
from typing import Optional

from .base_controller import BaseController
from controllers.video_controller import VideoController
from controllers.analysis_controller import AnalysisController
from controllers.history_controller import HistoryController
from models.video_analysis_orchestrator import VideoAnalysisOrchestrator
from dal.database import db_manager
from utils.config_manager import config_manager
from utils.logger import get_logger, setup_logger

logger = get_logger(__name__)

class MainController(QObject):
    """
    Controller chính điều phối toàn bộ ứng dụng
    """
    
    # Signals
    error_occurred = pyqtSignal(str)
    info_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Initialize sub-controllers
        self.video_controller = VideoController()
        self.analysis_controller = AnalysisController()
        self.history_controller = HistoryController()

        # Initialize configuration
        self.config = config_manager.load_config()

        # Setup logging
        log_file = self.config.get('paths.log_path', './logs') + '/traffic_monitoring.log'
        setup_logger(
            name="traffic_monitoring",
            log_level=self.config.get('logging.level', 'INFO'),
            log_file=log_file
        )
        
        # Model reference
        self.model: Optional[VideoAnalysisOrchestrator] = None
        
        # Initialize database
        self._init_database()
        
        # Connect internal signals
        self._connect_internal_signals()
        
        logger.info("MainController initialized")
    
    def _init_database(self):
        """Khởi tạo database"""
        try:
            db_url = self.config.get('database.url', 'sqlite:///traffic_monitoring.db')
            db_manager.initialize(db_url, echo=False)
            db_manager.create_all_tables()
            logger.info("Database initialized successfully")
                
        except Exception as e:
            error_msg = f"Database initialization failed: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _connect_internal_signals(self):
        """Kết nối signals giữa các controllers"""
        # Video controller -> Analysis controller
        self.video_controller.video_loaded.connect(
            self.analysis_controller.load_video
        )
        
        # Analysis controller signals
        self.analysis_controller.analysis_error.connect(
            self.error_occurred.emit
        )
        self.analysis_controller.status_message.connect(
            self.info_message.emit
        )
    
    def set_model(self, model: VideoAnalysisOrchestrator):
        """
        Set model cho tất cả controllers
        
        Args:
            model: VideoAnalysisOrchestrator instance
        """
        self.model = model
        
        # Set model for sub-controllers
        self.video_controller.set_model(model)
        self.analysis_controller.set_model(model)
        self.history_controller.set_model(model)
        
        logger.debug("Model set for all controllers")
    
    def set_main_view(self, main_window):
        """
        Set main view và kết nối với sub-controllers
        
        Args:
            main_window: MainWindow instance
        """
        # Set views for sub-controllers
        self.video_controller.set_view(main_window.video_player)
        self.analysis_controller.set_view(main_window.analysis_panel)
        self.history_controller.set_view(main_window.history_widget)
        
        # Connect main window signals
        main_window.closing.connect(self._on_app_closing)
        
        # Connect analysis signals to main window
        self.analysis_controller.progress_updated.connect(
            main_window.on_progress_updated
        )
        self.analysis_controller.stats_updated.connect(
            main_window.on_stats_updated
        )
        self.analysis_controller.frame_updated.connect(
            main_window.on_frame_updated
        )
        self.analysis_controller.analysis_completed.connect(
            main_window.on_analysis_completed
        )
        
        # Connect video player to analysis
        main_window.video_player.video_loaded.connect(
            self._on_video_loaded_in_view
        )
        
        logger.info("Main view connected to controllers")
    
    def _on_video_loaded_in_view(self, video_path: str):
        """Xử lý khi video được load trong view"""
        # Forward to analysis controller
        self.analysis_controller.load_video(video_path)
        
        # Update info message
        self.info_message.emit(f"Video đã sẵn sàng để phân tích: {video_path}")
    
    def _on_app_closing(self):
        """Xử lý khi ứng dụng đóng"""
        logger.info("Application closing - cleaning up resources")
        
        # Stop any ongoing analysis
        if self.model and self.model.is_processing():
            self.model.stop_analysis()
        
        # Close database connections
        db_manager.close()
        
        logger.info("Cleanup completed")
    
    def start_analysis(self):
        """Bắt đầu phân tích tự động"""
        self.analysis_controller.start_analysis()
    
    def stop_analysis(self):
        """Dừng phân tích"""
        self.analysis_controller.stop_analysis()
    
    def get_current_status(self) -> str:
        """Lấy trạng thái hiện tại của ứng dụng"""
        if self.model and self.model.is_processing():
            return "Đang phân tích..."
        return "Sẵn sàng"
       
# Thêm vào class MainController:

    def cleanup(self):
        """Cleanup all resources"""
        logger.info("Cleaning up MainController...")
        
        try:
            # Stop any ongoing analysis
            if self.model and self.model.is_processing():
                logger.info("Stopping ongoing analysis...")
                self.model.stop_analysis()
                self.model.reset()
            
            # Cleanup sub-controllers
            if hasattr(self.video_controller, 'cleanup'):
                self.video_controller.cleanup()
            
            if hasattr(self.analysis_controller, 'cleanup'):
                self.analysis_controller.cleanup()
                
            if hasattr(self.history_controller, 'cleanup'):
                self.history_controller.cleanup()
            
            # Close database connections
            if db_manager:
                logger.info("Closing database connections...")
                db_manager.close()
            
            logger.info("MainController cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during MainController cleanup: {e}")