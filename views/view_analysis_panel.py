# views/analysis_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                            QPushButton, QProgressBar, QLabel, QSlider,
                            QListWidget, QTextEdit, QSplitter, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import numpy as np

from .base_view import BaseView
from .video_player_widget import VideoDisplay


class AnalysisPanel(BaseView):
    """
    Panel for AI analysis controls and results
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout()
        
        # Control section
        control_group = QGroupBox("Điều khiển phân tích")
        control_layout = QVBoxLayout()
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_start_analysis = QPushButton("🚀 Bắt đầu phân tích")
        self.btn_stop_analysis = QPushButton("⏹ Dừng phân tích")
        self.btn_export_results = QPushButton("💾 Xuất kết quả")
        
        self.btn_start_analysis.setEnabled(False)
        self.btn_stop_analysis.setEnabled(False)
        self.btn_export_results.setEnabled(False)
        
        # Style buttons
        start_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """
        
        stop_style = """
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #da190b; }
            QPushButton:disabled { background-color: #cccccc; }
        """
        
        self.btn_start_analysis.setStyleSheet(start_style)
        self.btn_stop_analysis.setStyleSheet(stop_style)
        
        btn_layout.addWidget(self.btn_start_analysis)
        btn_layout.addWidget(self.btn_stop_analysis)
        btn_layout.addWidget(self.btn_export_results)
        
        control_layout.addLayout(btn_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.lbl_progress = QLabel("Sẵn sàng")
        
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.lbl_progress)
        
        # Settings
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Ngưỡng tin cậy:"))
        
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(10, 90)
        self.confidence_slider.setValue(50)
        self.confidence_slider.setTickPosition(QSlider.TicksBelow)
        self.confidence_slider.setTickInterval(10)
        
        self.lbl_confidence = QLabel("0.50")
        
        settings_layout.addWidget(self.confidence_slider)
        settings_layout.addWidget(self.lbl_confidence)
        settings_layout.addStretch()
        
        # Detection classes
        settings_layout.addWidget(QLabel("Đối tượng:"))
        self.detection_classes = QListWidget()
        self.detection_classes.setMaximumHeight(80)
        self.detection_classes.setFlow(QListWidget.LeftToRight)
        
        # Add detection classes
        for class_name in ["Ô tô", "Xe máy", "Xe tải", "Xe buýt", "Người", "Động vật"]:
            item = self.detection_classes.addItem(class_name)
        
        settings_layout.addWidget(self.detection_classes)
        
        control_layout.addLayout(settings_layout)
        control_group.setLayout(control_layout)
        
        main_layout.addWidget(control_group)
        
        # Results section - Splitter for video and stats
        results_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Analysis video display
        video_group = QGroupBox("Video phân tích")
        video_layout = QVBoxLayout()
        
        self.analysis_display = VideoDisplay()
        self.analysis_display.setMinimumSize(480, 360)
        video_layout.addWidget(self.analysis_display)
        
        # Detection info
        detection_layout = QHBoxLayout()
        self.lbl_detections = QLabel("Phát hiện: 0")
        self.lbl_timestamp = QLabel("00:00:00")
        
        detection_layout.addWidget(self.lbl_detections)
        detection_layout.addStretch()
        detection_layout.addWidget(self.lbl_timestamp)
        
        video_layout.addLayout(detection_layout)
        video_group.setLayout(video_layout)
        
        # Right: Statistics and alerts
        stats_widget = QWidget()
        stats_layout = QVBoxLayout()
        
        # Statistics group
        stats_group = QGroupBox("Thống kê")
        stats_inner_layout = QVBoxLayout()
        
        # Overall statistics
        self.stats_labels = {}
        stats_items = [
            ('total_vehicles', 'Tổng phương tiện:'),
            ('cars', 'Ô tô:'),
            ('motorbikes', 'Xe máy:'),
            ('trucks', 'Xe tải:'),
            ('buses', 'Xe buýt:')
        ]
        
        for key, label in stats_items:
            layout = QHBoxLayout()
            layout.addWidget(QLabel(label))
            layout.addStretch()
            value_label = QLabel("0")
            value_label.setFont(QFont("Arial", 12, QFont.Bold))
            self.stats_labels[key] = value_label
            layout.addWidget(value_label)
            stats_inner_layout.addLayout(layout)
        
        # Real-time stats (FR1.3.3)
        stats_inner_layout.addWidget(QFrame())  # Separator
        
        realtime_layout = QHBoxLayout()
        realtime_layout.addWidget(QLabel("Phút hiện tại:"))
        realtime_layout.addStretch()
        self.lbl_current_minute = QLabel("0")
        realtime_layout.addWidget(self.lbl_current_minute)
        stats_inner_layout.addLayout(realtime_layout)
        
        vehicles_per_min_layout = QHBoxLayout()
        vehicles_per_min_layout.addWidget(QLabel("Xe/phút:"))
        vehicles_per_min_layout.addStretch()
        self.lbl_vehicles_per_minute = QLabel("0")
        self.lbl_vehicles_per_minute.setFont(QFont("Arial", 12, QFont.Bold))
        vehicles_per_min_layout.addWidget(self.lbl_vehicles_per_minute)
        stats_inner_layout.addLayout(vehicles_per_min_layout)
        
        stats_group.setLayout(stats_inner_layout)
        stats_layout.addWidget(stats_group)
        
        # Alerts group
        alerts_group = QGroupBox("Cảnh báo")
        alerts_layout = QVBoxLayout()
        
        self.alerts_list = QTextEdit()
        self.alerts_list.setReadOnly(True)
        self.alerts_list.setMaximumHeight(150)
        
        alerts_layout.addWidget(self.alerts_list)
        alerts_group.setLayout(alerts_layout)
        
        stats_layout.addWidget(alerts_group)
        stats_widget.setLayout(stats_layout)
        
        # Add to splitter
        results_splitter.addWidget(video_group)
        results_splitter.addWidget(stats_widget)
        results_splitter.setStretchFactor(0, 2)  # Video takes more space
        results_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(results_splitter)
        
        self.setLayout(main_layout)
        
    def display_analysis_frame(self, frame: np.ndarray):
        """Display analysis frame with overlays"""
        self.analysis_display.display_frame(frame)
        
    def update_statistics(self, stats: dict):
        """Update statistics display"""
        for key, label in self.stats_labels.items():
            if key in stats:
                label.setText(str(stats[key]))
                
    def update_realtime_stats(self, stats: dict):
        """Update real-time statistics (FR1.3.3)"""
        if 'current_minute' in stats:
            self.lbl_current_minute.setText(str(stats['current_minute']))
        if 'vehicles_per_minute' in stats:
            self.lbl_vehicles_per_minute.setText(str(stats['vehicles_per_minute']))
        if 'timestamp' in stats:
            self.lbl_timestamp.setText(stats['timestamp'])
            
    def add_alert(self, message: str, alert_type: str = "info"):
        """Add alert message"""
        color_map = {
            'info': '#2196F3',
            'warning': '#FF9800',
            'error': '#F44336',
            'pedestrian': '#E91E63',
            'animal': '#9C27B0',
            'obstacle': '#FF5722',
            'stopped_vehicle': '#795548'
        }
        
        color = color_map.get(alert_type, '#2196F3')
        timestamp = QTimer().interval()
        
        html = f'<p style="color: {color}; margin: 2px;">[{self.lbl_timestamp.text()}] {message}</p>'
        self.alerts_list.append(html)
        
        # Auto scroll to bottom
        scrollbar = self.alerts_list.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def clear_results(self):
        """Clear all results"""
        self.analysis_display.clear_display()
        self.alerts_list.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("Sẵn sàng")
        self.lbl_detections.setText("Phát hiện: 0")
        
        for label in self.stats_labels.values():
            label.setText("0")
            
        self.lbl_current_minute.setText("0")
        self.lbl_vehicles_per_minute.setText("0")