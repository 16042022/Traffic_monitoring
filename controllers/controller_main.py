# controllers/main_controller.py
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal

from .base_controller import BaseController
from .video_controller import VideoController
from .analysis_controller import AnalysisController
from .history_controller import HistoryController
from utils import config_manager, setup_logger
from dal import db_manager


class MainController(BaseController):
    """
    Main controller - orchestrates all sub-controllers
    Entry point for the application logic
    """
    
    # Additional signals
    application_ready = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize configuration
        self.config = config_manager.load_config()
        
        # Setup logging
        log_file = self.config.get('paths.log_path', './logs') + '/traffic_monitoring.log'
        setup_logger(
            name="traffic_monitoring",
            log_level=self.config.get('logging.level', 'INFO'),
            log_file=log_file
        )
        
        # Initialize database
        self._init_database()
        
        # Sub-controllers
        self.video_controller = VideoController(self)
        self.analysis_controller = AnalysisController(self)
        self.history_controller = HistoryController(self)
        
        # Connect inter-controller signals
        self._connect_controllers()
        
    def _init_database(self):
        """Initialize database connection"""
        try:
            db_url = self.config.get('database.url', 'sqlite:///traffic_monitoring.db')
            db_manager.initialize(db_url, echo=False)
            db_manager.create_all_tables()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self._handle_error(e, "Lỗi khởi tạo cơ sở dữ liệu")
            raise
    
    def _connect_controllers(self):
        """Connect signals between controllers"""
        # When video is loaded, enable analysis
        self.video_controller.video_loaded.connect(
            self.analysis_controller.on_video_loaded
        )
        
        # When analysis completes, refresh history
        self.analysis_controller.analysis_completed.connect(
            self.history_controller.refresh_history
        )
        
        # Error propagation
        for controller in [self.video_controller, 
                          self.analysis_controller, 
                          self.history_controller]:
            controller.error_occurred.connect(self.error_occurred)
            controller.info_message.connect(self.info_message)
    
    def set_main_view(self, main_view):
        """
        Set main view and distribute sub-views
        
        Args:
            main_view: Main window instance
        """
        self._view = main_view
        
        # Set sub-views
        self.video_controller.set_view(main_view.video_player_widget)
        self.analysis_controller.set_view(main_view.analysis_panel)
        self.history_controller.set_view(main_view.history_widget)
        
        # Connect main view signals
        self._connect_view_signals()
        
        # Application is ready
        self.application_ready.emit()
        self._show_info("Ứng dụng sẵn sàng")
    
    def set_model(self, orchestrator):
        """
        Set model (VideoAnalysisOrchestrator)
        
        Args:
            orchestrator: VideoAnalysisOrchestrator instance
        """
        self._model = orchestrator
        
        # Share model with sub-controllers
        self.video_controller.set_model(orchestrator)
        self.analysis_controller.set_model(orchestrator)
        # History controller uses repositories directly
        
        self._connect_model_callbacks()
    
    def _connect_view_signals(self):
        """Connect main view signals"""
        if self._view:
            # File menu actions
            self._view.action_open_video.triggered.connect(
                self.video_controller.open_video_dialog
            )
            self._view.action_export_results.triggered.connect(
                self.export_results
            )
            self._view.action_settings.triggered.connect(
                self.show_settings
            )
            self._view.action_exit.triggered.connect(
                self.shutdown_application
            )
            
            # View menu actions
            self._view.action_show_history.triggered.connect(
                self.history_controller.toggle_history_view
            )
    
    def _connect_model_callbacks(self):
        """Connect model callbacks"""
        # Model callbacks are handled by sub-controllers
        pass
    
    def export_results(self):
        """Export current results"""
        try:
            if self.analysis_controller.has_results():
                self.analysis_controller.export_results()
            else:
                self._show_info("Không có kết quả để xuất")
        except Exception as e:
            self._handle_error(e, "Lỗi xuất kết quả")
    
    def show_settings(self):
        """Show settings dialog"""
        try:
            # TODO: Implement settings dialog
            self._show_info("Tính năng cài đặt đang được phát triển")
        except Exception as e:
            self._handle_error(e, "Lỗi hiển thị cài đặt")
    
    def shutdown_application(self):
        """Shutdown application gracefully"""
        try:
            self.logger.info("Shutting down application...")
            
            # Stop any ongoing processing
            if self.analysis_controller.is_processing:
                self.analysis_controller.stop_analysis()
            
            # Cleanup controllers
            self.video_controller.cleanup()
            self.analysis_controller.cleanup()
            self.history_controller.cleanup()
            
            # Close database
            db_manager.close()
            
            # Save config
            config_manager.save_config()
            
            self.logger.info("Application shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def on_language_changed(self, language: str):
        """
        Handle language change
        
        Args:
            language: Language code (vi, en)
        """
        config_manager.set('ui.language', language)
        config_manager.save_config()
        self._show_info("Vui lòng khởi động lại ứng dụng để áp dụng ngôn ngữ mới")