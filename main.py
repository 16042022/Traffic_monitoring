# main.py
"""
Traffic Monitoring System - Main Application Entry Point
Hệ thống Giám sát Giao thông Thông minh

This is the main entry point for the application.
Run this file to start the traffic monitoring system.
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QSplashScreen, QProgressBar, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QPalette, QColor

# Import monitoring first
from utils.app_monitor import get_app_monitor

# Import components
from views import MainWindow
from controllers import MainController
from models.video_analysis_orchestrator import VideoAnalysisOrchestrator
from utils import setup_logger, config_manager
from dal import db_manager

# Setup logging
def setup_logging():
    """Configure logging for the application"""
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Log file with timestamp
    log_file = f"logs/traffic_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers
    logging.getLogger('models').setLevel(logging.DEBUG)
    logging.getLogger('controllers').setLevel(logging.DEBUG)
    logging.getLogger('views').setLevel(logging.INFO)
    
    return log_file

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_modules = [
        'cv2',
        'numpy',
        'PyQt5',
        'torch',
        'ultralytics',
        'psutil'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    return missing

def show_startup_errors(errors):
    """Show startup errors in a message box"""
    app = QApplication([])
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Startup Error")
    msg.setText("Failed to start application due to missing dependencies:")
    msg.setDetailedText("\n".join(errors))
    msg.exec_()
    sys.exit(1)

class SplashScreen(QSplashScreen):
    """Custom splash screen with progress"""
    
    def __init__(self):
        super().__init__()
        
        # Create splash pixmap (you can replace with actual image)
        pixmap = QPixmap(600, 400)
        pixmap.fill(QColor(33, 150, 243))  # Material Blue
        
        self.setPixmap(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Add progress bar
        self.progress = QProgressBar(self)
        self.progress.setGeometry(50, 320, 500, 30)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.3);
                border: none;
                border-radius: 15px;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: white;
                border-radius: 15px;
            }
        """)
        
        # Add title
        self.showMessage(
            "Hệ thống Giám sát Giao thông Thông minh\n\nĐang khởi động...",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )
        
    def set_progress(self, value: int):
        """Update progress"""
        self.progress.setValue(value)
        QApplication.processEvents()


class TrafficMonitoringApp:
    """Main application class"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Traffic Monitoring System")
        self.app.setOrganizationName("University")

        # Get monitor instance
        self.monitor = get_app_monitor()
        
        # Connect monitor signals
        self.monitor.warning_raised.connect(self._on_monitor_warning)
        self.monitor.error_detected.connect(self._on_monitor_error)
        
        # Set style
        self._set_app_style()
        
        # Exception handling
        sys.excepthook = self._handle_exception
        
        # Set application style
        self.app.setStyle('Fusion')
        
        # Set color palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        self.app.setPalette(palette)
        
        # Components
        self.splash = None
        self.main_window = None
        self.main_controller = None
        self.orchestrator = None
        self.logger = None
        
    def _set_app_style(self):
        """Set application style with dark mode option"""
        # You can toggle this based on config
        use_dark_mode = False  # Set from config if needed
        
        if use_dark_mode:
            dark_palette = """
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                padding: 5px;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #555;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            """
            self.app.setStyleSheet(dark_palette)
    
    def _on_monitor_warning(self, warning: str):
        """Handle monitor warnings"""
        if self.logger:
            self.logger.warning(f"Monitor warning: {warning}")
        else:
            print(f"Monitor warning: {warning}")
    
    def _on_monitor_error(self, error: str):
        """Handle monitor errors"""
        if self.logger:
            self.logger.error(f"Monitor error: {error}")
        else:
            print(f"Monitor error: {error}")
    
    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """Global exception handler"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log exception using monitor
        self.monitor.log_error(
            exc_value,
            f"Uncaught exception: {exc_type.__name__}"
        )
        
        # Show error dialog with proper parent
        parent = self.main_window if hasattr(self, 'main_window') else None
        QMessageBox.critical(
            parent,
            "Critical Error",
            f"An unexpected error occurred:\n{exc_value}\n\nCheck logs for details."
        )
        
    def initialize(self):
        """Initialize application"""
        # Show splash screen
        self.splash = SplashScreen()
        self.splash.show()
        
        try:
            # Step 1: Check dependencies first
            self.splash.set_progress(5)
            self.splash.showMessage("Đang kiểm tra dependencies...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            missing_deps = check_dependencies()
            if missing_deps:
                error_msg = f"Missing dependencies: {', '.join(missing_deps)}"
                raise RuntimeError(error_msg)
            
            # Step 2: Check system requirements
            self.splash.set_progress(8)
            self.splash.showMessage("Đang kiểm tra hệ thống...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            sys_check = self.monitor.check_system_requirements()
            failed_checks = [k for k, v in sys_check.items() if not v]
            if failed_checks:
                logging.warning(f"System requirements not met: {failed_checks}")
            
            # Step 3: Load configuration
            self.splash.set_progress(10)
            self.splash.showMessage("Đang tải cấu hình...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            config = config_manager.load_config()
            
            # Step 4: Setup logging
            self.splash.set_progress(20)
            self.splash.showMessage("Đang khởi tạo logging...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            log_path = config.get('paths.log_path', './logs')
            Path(log_path).mkdir(parents=True, exist_ok=True)
            
            self.logger = setup_logger(
                name="traffic_monitoring",
                log_level=config.get('logging.level', 'INFO'),
                log_file=f"{log_path}/traffic_monitoring.log"
            )
            self.logger.info("="*50)
            self.logger.info("Application starting...")
            self.logger.info(f"System check: {sys_check}")
            self.logger.info("="*50)
            
            # Step 5: Initialize database
            self.splash.set_progress(30)
            self.splash.showMessage("Đang kết nối cơ sở dữ liệu...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            db_url = config.get('database.url', 'sqlite:///traffic_monitoring.db')
            db_manager.initialize(db_url, echo=False)
            db_manager.create_all_tables()
            
            # Step 6: Create model
            self.splash.set_progress(50)
            self.splash.showMessage("Đang tải mô hình AI...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            # Update config to use yolov8 if still set to yolov5
            if config.get('ai_model.type') == 'yolov5':
                config_manager.set('ai_model.type', 'yolov8')
                config_manager.save_config()
            self.orchestrator = VideoAnalysisOrchestrator()
            
            # Step 7: Create controller
            self.splash.set_progress(70)
            self.splash.showMessage("Đang khởi tạo controller...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            self.main_controller = MainController()
            self.main_controller.set_model(self.orchestrator)
            
            # Step 8: Create view
            self.splash.set_progress(90)
            self.splash.showMessage("Đang tạo giao diện...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            self.main_window = MainWindow()
            self.main_controller.set_main_view(self.main_window)
            
            # Connect error handling
            self.main_controller.error_occurred.connect(self.main_window.update_status)
            self.main_controller.info_message.connect(self.main_window.update_status)
            
            # Step 9: Start monitoring
            self.splash.set_progress(95)
            self.splash.showMessage("Đang khởi động monitoring...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            self.monitor.start_monitoring()
            
            # Setup performance logging timer
            self.perf_timer = QTimer()
            self.perf_timer.timeout.connect(self._log_performance)
            self.perf_timer.start(60000)  # Every minute
            
            # Step 10: Show main window
            self.splash.set_progress(100)
            self.splash.showMessage("Hoàn tất!", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            
            # Small delay before showing main window
            QTimer.singleShot(500, self.show_main_window)
            
            self.logger.info("Application initialized successfully")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize application: {e}", exc_info=True)
            else:
                print(f"Failed to initialize application: {e}")
            
            self.splash.close()
            QMessageBox.critical(None, "Lỗi khởi động", 
                               f"Không thể khởi động ứng dụng:\n{str(e)}")
            sys.exit(1)
    
    def _log_performance(self):
        """Log performance metrics periodically"""
        try:
            summary = self.monitor.get_performance_summary()
            if summary and self.logger:
                self.logger.info(
                    f"Performance: CPU {summary['avg_cpu']:.1f}% (max {summary['max_cpu']:.1f}%), "
                    f"Memory {summary['avg_memory_mb']:.1f}MB (max {summary['max_memory_mb']:.1f}MB), "
                    f"FPS {summary['avg_fps']:.1f} (min {summary['min_fps']:.1f})"
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error logging performance: {e}")
    
    def show_main_window(self):
        """Show main window and close splash"""
        self.splash.close()
        self.main_window.show()
        
        # Initialize history
        self.main_controller.history_controller.initialize()
        
        # Add debug panel (hidden by default, show with F12)
        try:
            from views.widgets.debug_widget import DebugWidget
            from PyQt5.QtWidgets import QDockWidget
            from PyQt5.QtGui import QKeySequence
            from PyQt5.QtWidgets import QShortcut
            
            self.debug_widget = DebugWidget()
            self.debug_dock = QDockWidget("Debug Monitor", self.main_window)
            self.debug_dock.setWidget(self.debug_widget)
            self.main_window.addDockWidget(Qt.RightDockWidgetArea, self.debug_dock)
            
            # Hide by default
            self.debug_dock.hide()
            
            # Shortcut to toggle debug
            debug_shortcut = QShortcut(QKeySequence("F12"), self.main_window)
            debug_shortcut.activated.connect(self.debug_dock.toggleViewAction().trigger)
            
            self.logger.info("Debug panel available (press F12 to toggle)")
        except Exception as e:
            self.logger.warning(f"Could not add debug panel: {e}")
    
    def run(self):
        """Run application"""
        self.initialize()
        
        # Handle application exit
        self.app.aboutToQuit.connect(self.cleanup)
        
        # Run event loop
        return self.app.exec_()
    
    def cleanup(self):
        """Cleanup resources before exit"""
        try:
            self.logger.info("Shutting down application...")
            
            # Stop performance timer
            if hasattr(self, 'perf_timer') and self.perf_timer:
                self.perf_timer.stop()
            
            # Stop monitoring
            self.monitor.stop_monitoring()
            
            # Save final performance report
            summary = self.monitor.get_performance_summary()
            if summary and self.logger:
                self.logger.info(f"Final performance summary: {summary}")
            
            # Cleanup controller
            if self.main_controller:
                self.main_controller.cleanup()
            
            # Stop any ongoing processing
            if self.orchestrator:
                self.orchestrator.stop()
            
            # Close database
            db_manager.close()
            
            self.logger.info("Application closed successfully")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main entry point"""
    # Setup basic logging first
    log_file = setup_logging()
    
    # Set high DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create and run application
    app = TrafficMonitoringApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()