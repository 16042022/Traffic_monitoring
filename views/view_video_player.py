# views/video_player_widget.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                            QSlider, QLabel, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
import cv2
import numpy as np

from .base_view import BaseView
from models.entities import VideoInfo


class VideoDisplay(QLabel):
    """Custom widget for video display"""
    
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #000;
                border: 2px solid #333;
                border-radius: 5px;
            }
        """)
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.current_frame = None
        
        # Display placeholder
        self.setText("Không có video")
        self.setStyleSheet(self.styleSheet() + "color: #666;")
        
    def display_frame(self, frame: np.ndarray):
        """Display a frame"""
        self.current_frame = frame
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        
        # Convert to QImage
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        q_image = q_image.rgbSwapped()  # BGR to RGB
        
        # Scale to widget size
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        self.setPixmap(scaled_pixmap)
        
    def clear_display(self):
        """Clear video display"""
        self.clear()
        self.setText("Không có video")
        self.current_frame = None


class VideoPlayerWidget(BaseView):
    """
    Video player widget with controls
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Video display
        self.video_display = VideoDisplay()
        layout.addWidget(self.video_display)
        
        # Video info bar
        info_layout = QHBoxLayout()
        self.lbl_video_name = QLabel("Chưa có video")
        self.lbl_video_info = QLabel("")
        self.lbl_fps = QLabel("FPS: 0")
        
        info_layout.addWidget(self.lbl_video_name)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_video_info)
        info_layout.addWidget(QFrame())  # Separator
        info_layout.addWidget(self.lbl_fps)
        
        layout.addLayout(info_layout)
        
        # Progress slider
        self.slider_progress = QSlider(Qt.Horizontal)
        self.slider_progress.setEnabled(False)
        layout.addWidget(self.slider_progress)
        
        # Time labels
        time_layout = QHBoxLayout()
        self.lbl_current_time = QLabel("00:00:00")
        self.lbl_total_time = QLabel("00:00:00")
        
        time_layout.addWidget(self.lbl_current_time)
        time_layout.addStretch()
        time_layout.addWidget(self.lbl_total_time)
        
        layout.addLayout(time_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.btn_play = QPushButton("▶ Phát")
        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_stop = QPushButton("⏹ Dừng")
        
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        
        # Style buttons
        button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #2196F3;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """
        
        for btn in [self.btn_play, self.btn_pause, self.btn_stop]:
            btn.setStyleSheet(button_style)
            
        control_layout.addWidget(self.btn_play)
        control_layout.addWidget(self.btn_pause)
        control_layout.addWidget(self.btn_stop)
        
        # Speed control
        control_layout.addStretch()
        control_layout.addWidget(QLabel("Tốc độ:"))
        
        self.speed_control = QSlider(Qt.Horizontal)
        self.speed_control.setRange(50, 200)  # 0.5x to 2x
        self.speed_control.setValue(100)  # 1x
        self.speed_control.setTickPosition(QSlider.TicksBelow)
        self.speed_control.setTickInterval(50)
        self.speed_control.setMaximumWidth(150)
        
        self.lbl_speed = QLabel("1.0x")
        
        control_layout.addWidget(self.speed_control)
        control_layout.addWidget(self.lbl_speed)
        
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
        
    def set_video_info(self, video_info: VideoInfo):
        """Set video information"""
        self.lbl_video_name.setText(video_info.file_name)
        self.lbl_video_info.setText(f"{video_info.resolution} @ {video_info.fps:.1f}fps")
        self.lbl_total_time.setText(video_info.duration_formatted)
        
        self.slider_progress.setEnabled(True)
        self.slider_progress.setMaximum(video_info.frame_count - 1)
        
    def clear_video_info(self):
        """Clear video information"""
        self.lbl_video_name.setText("Chưa có video")
        self.lbl_video_info.setText("")
        self.lbl_current_time.setText("00:00:00")
        self.lbl_total_time.setText("00:00:00")
        self.lbl_fps.setText("FPS: 0")
        
        self.slider_progress.setValue(0)
        self.slider_progress.setEnabled(False)
        
    def display_frame(self, frame: np.ndarray):
        """Display frame"""
        self.video_display.display_frame(frame)
        
    def clear_display(self):
        """Clear display"""
        self.video_display.clear_display()
        
    def get_current_frame(self) -> np.ndarray:
        """Get current displayed frame"""
        return self.video_display.current_frame