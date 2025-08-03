"""
Analysis Panel - Giao diện hiển thị phân tích TỰ ĐỘNG
Hiển thị progress bar, thống kê real-time, và trạng thái phân tích
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QHeaderView, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from typing import Dict, Optional
import logging
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)

class AnalysisPanel(QWidget):
    """
    Panel hiển thị thông tin phân tích TỰ ĐỘNG
    """
    
    # Signals
    start_analysis_requested = pyqtSignal()
    pause_analysis_requested = pyqtSignal()
    resume_analysis_requested = pyqtSignal()
    stop_analysis_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_analyzing = False
        self.is_paused = False
        self.init_ui()
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 1. Control Panel - Các nút điều khiển
        control_group = QGroupBox("Điều khiển phân tích")
        control_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("▶ Bắt đầu phân tích")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.btn_start.clicked.connect(self._on_start_clicked)
        
        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        
        self.btn_stop = QPushButton("⏹ Dừng")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton:enabled {
                background-color: #f44336;
                color: white;
            }
        """)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_pause)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 2. Progress Panel - Hiển thị tiến trình
        progress_group = QGroupBox("Tiến trình phân tích")
        progress_layout = QVBoxLayout()
        
        # Status label
        self.lbl_status = QLabel("Sẵn sàng phân tích")
        self.lbl_status.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                background-color: #e3f2fd;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.lbl_status)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - Frame %v/%m")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # Time info
        time_layout = QHBoxLayout()
        self.lbl_video_time = QLabel("Thời gian video: 00:00:00 / 00:00:00")
        self.lbl_fps = QLabel("FPS xử lý: 0.0")
        time_layout.addWidget(self.lbl_video_time)
        time_layout.addStretch()
        time_layout.addWidget(self.lbl_fps)
        progress_layout.addLayout(time_layout)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 3. Statistics Panel - Thống kê real-time
        stats_group = QGroupBox("Thống kê thời gian thực")
        stats_layout = QVBoxLayout()
        
        # Summary stats
        summary_layout = QHBoxLayout()
        
        # Total vehicles
        total_frame = QFrame()
        total_frame.setFrameStyle(QFrame.Box)
        total_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        total_layout = QVBoxLayout(total_frame)
        self.lbl_total_vehicles = QLabel("0")
        self.lbl_total_vehicles.setAlignment(Qt.AlignCenter)
        self.lbl_total_vehicles.setStyleSheet("font-size: 36px; font-weight: bold; color: #2196F3;")
        total_layout.addWidget(self.lbl_total_vehicles)
        total_layout.addWidget(QLabel("Tổng số xe", alignment=Qt.AlignCenter))
        summary_layout.addWidget(total_frame)
        
        # Current minute count
        minute_frame = QFrame()
        minute_frame.setFrameStyle(QFrame.Box)
        minute_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        minute_layout = QVBoxLayout(minute_frame)
        self.lbl_minute_count = QLabel("0")
        self.lbl_minute_count.setAlignment(Qt.AlignCenter)
        self.lbl_minute_count.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50;")
        minute_layout.addWidget(self.lbl_minute_count)
        minute_layout.addWidget(QLabel("Xe/phút hiện tại", alignment=Qt.AlignCenter))
        summary_layout.addWidget(minute_frame)
        
        # Anomalies
        anomaly_frame = QFrame()
        anomaly_frame.setFrameStyle(QFrame.Box)
        anomaly_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        anomaly_layout = QVBoxLayout(anomaly_frame)
        self.lbl_anomalies = QLabel("0")
        self.lbl_anomalies.setAlignment(Qt.AlignCenter)
        self.lbl_anomalies.setStyleSheet("font-size: 24px; font-weight: bold; color: #f44336;")
        anomaly_layout.addWidget(self.lbl_anomalies)
        anomaly_layout.addWidget(QLabel("Cảnh báo", alignment=Qt.AlignCenter))
        summary_layout.addWidget(anomaly_frame)
        
        stats_layout.addLayout(summary_layout)
        
        # Vehicle type breakdown
        self.vehicle_table = QTableWidget()
        self.vehicle_table.setColumnCount(2)
        self.vehicle_table.setHorizontalHeaderLabels(["Loại xe", "Số lượng"])
        self.vehicle_table.horizontalHeader().setStretchLastSection(True)
        self.vehicle_table.setMaximumHeight(150)
        self.vehicle_table.setAlternatingRowColors(True)
        stats_layout.addWidget(QLabel("Phân loại phương tiện:"))
        stats_layout.addWidget(self.vehicle_table)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 4. Alerts Panel - Cảnh báo
        alerts_group = QGroupBox("Cảnh báo bất thường")
        alerts_layout = QVBoxLayout()
        
        self.alerts_text = QTextEdit()
        self.alerts_text.setReadOnly(True)
        self.alerts_text.setMaximumHeight(100)
        self.alerts_text.setStyleSheet("""
            QTextEdit {
                background-color: #fff3e0;
                border: 1px solid #ffb74d;
                border-radius: 3px;
            }
        """)
        alerts_layout.addWidget(self.alerts_text)
        
        alerts_group.setLayout(alerts_layout)
        layout.addWidget(alerts_group)
        
        layout.addStretch()
    
    def _on_start_clicked(self):
        """Xử lý khi nhấn nút Start"""
        self.is_analyzing = True
        self.is_paused = False
        self._update_button_states()
        self.start_analysis_requested.emit()
    
    def _on_pause_clicked(self):
        """Xử lý khi nhấn nút Pause"""
        if self.is_paused:
            # Resume
            self.is_paused = False
            self.btn_pause.setText("⏸ Tạm dừng")
            self.resume_analysis_requested.emit()
        else:
            # Pause
            self.is_paused = True
            self.btn_pause.setText("▶ Tiếp tục")
            self.pause_analysis_requested.emit()
        self._update_button_states()
    
    def _on_stop_clicked(self):
        """Xử lý khi nhấn nút Stop"""
        self.is_analyzing = False
        self.is_paused = False
        self._update_button_states()
        self.stop_analysis_requested.emit()
    
    def _update_button_states(self):
        """Cập nhật trạng thái các nút"""
        self.btn_start.setEnabled(not self.is_analyzing)
        self.btn_pause.setEnabled(self.is_analyzing)
        self.btn_stop.setEnabled(self.is_analyzing)
    
    def update_progress(self, progress_data: Dict):
        """
        Cập nhật tiến trình phân tích
        
        Args:
            progress_data: Dict chứa thông tin tiến trình
        """
        # Update progress bar
        total_frames = progress_data.get('total_frames', 1)
        current_frame = progress_data.get('current_frame', 0)
        self.progress_bar.setMaximum(total_frames)
        self.progress_bar.setValue(current_frame)
        
        # Update time info
        current_time = progress_data.get('current_time', 0)
        total_duration = progress_data.get('total_duration', 0)
        self.lbl_video_time.setText(
            f"Thời gian video: {self._format_time(current_time)} / {self._format_time(total_duration)}"
        )
        
        # Update FPS
        fps = progress_data.get('fps', 0)
        self.lbl_fps.setText(f"FPS xử lý: {fps:.1f}")
        
        # Update status
        status = progress_data.get('status', '')
        if status == 'analyzing':
            percent = progress_data.get('percent_complete', 0)
            self.lbl_status.setText(f"Đang phân tích... {percent:.1f}%")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    background-color: #fff3cd;
                    border-radius: 3px;
                }
            """)
        elif status == 'completed':
            self.lbl_status.setText("Phân tích hoàn tất!")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    background-color: #d4edda;
                    border-radius: 3px;
                }
            """)
            self.is_analyzing = False
            self._update_button_states()
        elif status == 'error':
            self.lbl_status.setText("Lỗi trong quá trình phân tích")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    background-color: #f8d7da;
                    border-radius: 3px;
                }
            """)
            self.is_analyzing = False
            self._update_button_states()
    
    def update_statistics(self, stats_data: Dict):
        """
        Cập nhật thống kê real-time
        
        Args:
            stats_data: Dict chứa thống kê
        """
        # Update total vehicles
        total = stats_data.get('total_vehicles', 0)
        self.lbl_total_vehicles.setText(str(total))
        
        # Update current minute count
        minute_count = stats_data.get('current_minute_count', 0)
        self.lbl_minute_count.setText(str(minute_count))
        
        # Update anomalies
        anomalies = stats_data.get('anomalies_detected', 0)
        self.lbl_anomalies.setText(str(anomalies))
        
        # Update vehicle breakdown table
        vehicles_by_type = stats_data.get('vehicles_by_type', {})
        self.vehicle_table.setRowCount(len(vehicles_by_type))
        
        for i, (vehicle_type, count) in enumerate(vehicles_by_type.items()):
            self.vehicle_table.setItem(i, 0, QTableWidgetItem(vehicle_type))
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.vehicle_table.setItem(i, 1, count_item)
        
        # Update video timestamp if available
        video_timestamp = stats_data.get('video_timestamp', '')
        if video_timestamp and hasattr(self, 'lbl_video_timestamp'):
            self.lbl_video_timestamp.setText(f"Timestamp: {video_timestamp}")
    
    def add_alert(self, alert_text: str):
        """Thêm cảnh báo mới"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.alerts_text.append(f"[{timestamp}] {alert_text}")
        # Auto scroll to bottom
        scrollbar = self.alerts_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_alerts(self):
        """Xóa tất cả cảnh báo"""
        self.alerts_text.clear()
    
    def reset(self):
        """Reset panel về trạng thái ban đầu"""
        self.is_analyzing = False
        self.is_paused = False
        self._update_button_states()
        
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Sẵn sàng phân tích")
        self.lbl_status.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                background-color: #e3f2fd;
                border-radius: 3px;
            }
        """)
        
        self.lbl_total_vehicles.setText("0")
        self.lbl_minute_count.setText("0")
        self.lbl_anomalies.setText("0")
        self.lbl_video_time.setText("Thời gian video: 00:00:00 / 00:00:00")
        self.lbl_fps.setText("FPS xử lý: 0.0")
        
        self.vehicle_table.setRowCount(0)
        self.clear_alerts()
    
    def show_final_results(self, results: Dict):
        """
        Hiển thị kết quả cuối cùng sau khi phân tích xong
        
        Args:
            results: Dict chứa kết quả phân tích
        """
        # Show completion message
        self.lbl_status.setText("Phân tích hoàn tất! Xem kết quả bên dưới")
        
        # Add summary to alerts
        if 'traffic_statistics' in results:
            stats = results['traffic_statistics']
            summary = f"TỔNG KẾT: Tổng số xe: {stats.get('total_vehicles', 0)}, "
            summary += f"Cảnh báo: {stats.get('total_anomalies', 0)}"
            self.add_alert(summary)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds thành HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
