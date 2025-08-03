"""
Main Window - Cửa sổ chính của ứng dụng với phân tích TỰ ĐỘNG
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMenu, QAction,
    QMessageBox, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
import logging
from typing import Optional

from views.video_player_widget import VideoPlayerWidget
from views.analysis_panel import AnalysisPanel
from views.history_widget import HistoryWidget
from utils.logger import get_logger

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng Traffic Monitoring
    """
    
    # Signals
    closing = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("Hệ thống Giám sát Giao thông Thông minh - Phân tích Tự động")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Video Player
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.video_player = VideoPlayerWidget()
        left_layout.addWidget(self.video_player)
        
        splitter.addWidget(left_widget)
        
        # Right side - Analysis and History tabs
        right_widget = QTabWidget()
        
        # Analysis tab
        self.analysis_panel = AnalysisPanel()
        right_widget.addTab(self.analysis_panel, "Phân tích Tự động")
        
        # History tab
        self.history_widget = HistoryWidget()
        right_widget.addTab(self.history_widget, "Lịch sử")
        
        splitter.addWidget(right_widget)
        
        # Set splitter sizes (60% video, 40% panels)
        splitter.setSizes([840, 560])
        
        main_layout.addWidget(splitter)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status("Sẵn sàng")
        
        # Connect signals
        self._connect_signals()
        
        # Apply stylesheet
        self._apply_stylesheet()
        
        logger.info("MainWindow initialized")
    
    def _create_menu_bar(self):
        """Tạo menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Mở Video...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.video_player.browse_video)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Thoát", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Analysis menu
        analysis_menu = menubar.addMenu("Phân tích")
        
        start_action = QAction("Bắt đầu phân tích", self)
        start_action.setShortcut("F5")
        start_action.triggered.connect(self.analysis_panel.start_analysis_requested.emit)
        analysis_menu.addAction(start_action)
        
        stop_action = QAction("Dừng phân tích", self)
        stop_action.setShortcut("F6")
        stop_action.triggered.connect(self.analysis_panel.stop_analysis_requested.emit)
        analysis_menu.addAction(stop_action)
        
        # View menu
        view_menu = menubar.addMenu("Hiển thị")
        
        fullscreen_action = QAction("Toàn màn hình", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # Help menu
        help_menu = menubar.addMenu("Trợ giúp")
        
        about_action = QAction("Về chương trình", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """Kết nối các signals"""
        # Video player signals
        self.video_player.video_loaded.connect(self._on_video_loaded)
        
        # Analysis panel signals
        self.analysis_panel.start_analysis_requested.connect(self._on_start_analysis)
        
    def _apply_stylesheet(self):
        """Áp dụng stylesheet cho ứng dụng"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #2196F3;
            }
            
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #cccccc;
            }
        """)
    
    @pyqtSlot(str)
    def _on_video_loaded(self, video_path: str):
        """Xử lý khi video được load"""
        self.update_status(f"Đã tải video: {video_path}")
        # Reset analysis panel
        self.analysis_panel.reset()
        
    def _on_start_analysis(self):
        """Xử lý khi bắt đầu phân tích"""
        if not self.video_player.get_video_path():
            QMessageBox.warning(
                self,
                "Cảnh báo",
                "Vui lòng chọn video trước khi phân tích!"
            )
            return
    
    def _toggle_fullscreen(self, checked: bool):
        """Toggle chế độ toàn màn hình"""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()
    
    def _show_about(self):
        """Hiển thị thông tin về chương trình"""
        about_text = """
        <h2>Hệ thống Giám sát Giao thông Thông minh</h2>
        <p>Phiên bản: 1.0.0</p>
        <p>Phần mềm phân tích video giao thông tự động với các tính năng:</p>
        <ul>
            <li>Phân tích TỰ ĐỘNG toàn bộ video</li>
            <li>Nhận diện và đếm phương tiện</li>
            <li>Phát hiện bất thường</li>
            <li>Lưu trữ và xem lại kết quả</li>
        </ul>
        <p>Được phát triển bởi: Nhóm CNTT</p>
        """
        
        QMessageBox.about(self, "Về chương trình", about_text)
    
    @pyqtSlot(str)
    def update_status(self, message: str):
        """
        Cập nhật status bar
        
        Args:
            message: Thông báo hiển thị
        """
        self.status_bar.showMessage(message)
    
    @pyqtSlot(dict)
    def on_progress_updated(self, progress_data: dict):
        """Cập nhật tiến trình phân tích"""
        self.analysis_panel.update_progress(progress_data)
        
        # Update status bar
        percent = progress_data.get('percent_complete', 0)
        status = progress_data.get('status', '')
        if status == 'analyzing':
            self.update_status(f"Đang phân tích: {percent:.1f}%")
        elif status == 'completed':
            self.update_status("Phân tích hoàn tất!")
        elif status == 'error':
            self.update_status("Lỗi trong quá trình phân tích")
    
    @pyqtSlot(dict)
    def on_stats_updated(self, stats_data: dict):
        """Cập nhật thống kê real-time"""
        self.analysis_panel.update_statistics(stats_data)
    
    @pyqtSlot(object)
    def on_frame_updated(self, frame):
        """Cập nhật frame hiển thị"""
        self.video_player.update_analysis_frame(frame)
    
    @pyqtSlot(dict)
    def on_analysis_completed(self, results: dict):
        """Xử lý khi phân tích hoàn tất"""
        self.analysis_panel.show_final_results(results)
        
        # Refresh history
        self.history_widget.clear_all()
        
        # Show completion message
        total_vehicles = results.get('traffic_statistics', {}).get('total_vehicles', 0)
        QMessageBox.information(
            self,
            "Phân tích hoàn tất",
            f"Đã hoàn tất phân tích video!\n\n"
            f"Tổng số phương tiện phát hiện: {total_vehicles}\n\n"
            f"Kết quả đã được lưu vào cơ sở dữ liệu."
        )
    
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        reply = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc muốn thoát chương trình?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.closing.emit()
            event.accept()
            logger.info("Application closing")
        else:
            event.ignore()
