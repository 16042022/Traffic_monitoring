# main.py
"""
Traffic Monitoring System - Main Application Entry Point
Hệ thống Giám sát Giao thông Thông minh

This is the main entry point for the application.
Run this file to start the traffic monitoring system.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QSplashScreen, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QPalette, QColor

# Import components
from views import MainWindow
from controllers import MainController
from models.video_analysis_orchestrator import VideoAnalysisOrchestrator
from utils import setup_logger, config_manager
from dal import db_manager


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
        
    def initialize(self):
        """Initialize application"""
        # Show splash screen
        self.splash = SplashScreen()
        self.splash.show()
        
        try:
            # Step 1: Load configuration
            self.splash.set_progress(10)
            self.splash.showMessage("Đang tải cấu hình...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            config = config_manager.load_config()
            
            # Step 2: Setup logging
            self.splash.set_progress(20)
            self.splash.showMessage("Đang khởi tạo logging...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            log_path = config.get('paths.log_path', './logs')
            Path(log_path).mkdir(parents=True, exist_ok=True)
            
            logger = setup_logger(
                name="traffic_monitoring",
                log_level=config.get('logging.level', 'INFO'),
                log_file=f"{log_path}/traffic_monitoring.log"
            )
            logger.info("Application starting...")
            
            # Step 3: Initialize database
            self.splash.set_progress(30)
            self.splash.showMessage("Đang kết nối cơ sở dữ liệu...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            db_url = config.get('database.url', 'sqlite:///traffic_monitoring.db')
            db_manager.initialize(db_url, echo=False)
            db_manager.create_all_tables()
            
            # Step 4: Create model
            self.splash.set_progress(50)
            self.splash.showMessage("Đang tải mô hình AI...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            self.orchestrator = VideoAnalysisOrchestrator()
            
            # Step 5: Create controller
            self.splash.set_progress(70)
            self.splash.showMessage("Đang khởi tạo controller...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            self.main_controller = MainController()
            self.main_controller.set_model(self.orchestrator)
            
            # Step 6: Create view
            self.splash.set_progress(90)
            self.splash.showMessage("Đang tạo giao diện...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            self.main_window = MainWindow()
            self.main_controller.set_main_view(self.main_window)
            
            # Connect error handling
            self.main_controller.error_occurred.connect(self.main_window.update_status)
            self.main_controller.info_message.connect(self.main_window.update_status)
            
            # Step 7: Show main window
            self.splash.set_progress(100)
            self.splash.showMessage("Hoàn tất!", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            
            # Small delay before showing main window
            QTimer.singleShot(500, self.show_main_window)
            
            logger.info("Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            self.splash.close()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Lỗi khởi động", 
                               f"Không thể khởi động ứng dụng:\n{str(e)}")
            sys.exit(1)
    
    def show_main_window(self):
        """Show main window and close splash"""
        self.splash.close()
        self.main_window.show()
        
        # Initialize history
        self.main_controller.history_controller.initialize()
    
    def run(self):
        """Run application"""
        self.initialize()
        
        # Handle application exit
        self.app.aboutToQuit.connect(self.cleanup)
        
        # Run event loop
        return self.app.exec_()
    
    def cleanup(self):
        """Cleanup before exit"""
        if self.main_controller:
            self.main_controller.shutdown_application()


def main():
    """Main entry point"""
    # Set high DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create and run application
    app = TrafficMonitoringApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()