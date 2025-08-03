"""
Video Player Widget - Hiển thị video với kết quả phân tích TỰ ĐỘNG
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSlider, QFileDialog, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
import cv2
import numpy as np
from pathlib import Path
import logging
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

class VideoPlayerWidget(QWidget):
    """
    Widget để hiển thị video và kết quả phân tích real-time
    """
    
    # Signals
    video_loaded = pyqtSignal(str)  # Emit khi load video mới
    frame_updated = pyqtSignal(int)  # Emit khi frame thay đổi
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_path: Optional[str] = None
        self.is_playing = False
        self.current_frame = None
        self.init_ui()
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        layout = QVBoxLayout(self)
        
        # Video display area
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 2px solid #333333;
                border-radius: 5px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setScaledContents(False)
        
        # Hiển thị text mặc định
        self.video_label.setText("Chọn video để bắt đầu phân tích")
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #ffffff;
                font-size: 18px;
                border: 2px dashed #555555;
                border-radius: 5px;
            }
        """)
        
        layout.addWidget(self.video_label)
        
        # Control panel
        control_group = QGroupBox("Điều khiển video")
        control_layout = QVBoxLayout()
        
        # File selection
        file_layout = QHBoxLayout()
        self.btn_browse = QPushButton("📁 Chọn video")
        self.btn_browse.clicked.connect(self.browse_video)
        self.lbl_filename = QLabel("Chưa chọn file")
        self.lbl_filename.setStyleSheet("color: #666666;")
        
        file_layout.addWidget(self.btn_browse)
        file_layout.addWidget(self.lbl_filename)
        file_layout.addStretch()
        control_layout.addLayout(file_layout)
        
        # Video info
        info_layout = QHBoxLayout()
        self.lbl_video_info = QLabel("Thông tin video: --")
        self.lbl_video_info.setStyleSheet("font-size: 12px; color: #888888;")
        info_layout.addWidget(self.lbl_video_info)
        info_layout.addStretch()
        control_layout.addLayout(info_layout)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Playback info (ẩn khi phân tích tự động)
        self.lbl_playback_info = QLabel("Chế độ phân tích tự động - Video sẽ được xử lý toàn bộ khi nhấn Start")
        self.lbl_playback_info.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1976d2;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.lbl_playback_info)
    
    def browse_video(self):
        """Mở dialog chọn file video"""
        file_filter = "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file video",
            "",
            file_filter
        )
        
        if file_path:
            self.load_video(file_path)
    
    def load_video(self, video_path: str):
        """
        Load video và hiển thị frame đầu tiên
        
        Args:
            video_path: Đường dẫn file video
        """
        try:
            # Kiểm tra file tồn tại
            if not Path(video_path).exists():
                logger.error(f"Video file not found: {video_path}")
                return
            
            self.video_path = video_path
            
            # Đọc frame đầu tiên để hiển thị
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    self.display_frame(frame)
                
                # Lấy thông tin video
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps > 0 else 0
                
                # Cập nhật UI
                self.lbl_filename.setText(Path(video_path).name)
                self.lbl_filename.setStyleSheet("color: #000000; font-weight: bold;")
                
                info_text = f"Độ phân giải: {width}x{height} | "
                info_text += f"FPS: {fps:.1f} | "
                info_text += f"Số frame: {frame_count} | "
                info_text += f"Thời lượng: {self._format_duration(duration)}"
                self.lbl_video_info.setText(info_text)
                
                cap.release()
                
                # Emit signal
                self.video_loaded.emit(video_path)
                logger.info(f"Video loaded: {video_path}")
                
            else:
                logger.error("Failed to open video")
                
        except Exception as e:
            logger.error(f"Error loading video: {e}")
    
    @pyqtSlot(object)
    def display_frame(self, frame):
        """
        Hiển thị frame (đã được annotated từ model)
        
        Args:
            frame: numpy array của frame
        """
        if frame is None:
            return
        
        try:
            # Store current frame
            self.current_frame = frame.copy()
            
            # Convert to RGB
            if len(frame.shape) == 3:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                rgb_frame = frame
            
            # Resize to fit display area while maintaining aspect ratio
            display_size = (self.video_label.width() - 4, self.video_label.height() - 4)
            
            h, w = rgb_frame.shape[:2]
            aspect_ratio = w / h
            
            if display_size[0] / display_size[1] > aspect_ratio:
                # Fit to height
                new_height = display_size[1]
                new_width = int(new_height * aspect_ratio)
            else:
                # Fit to width
                new_width = display_size[0]
                new_height = int(new_width / aspect_ratio)
            
            # Resize frame
            if new_width > 0 and new_height > 0:
                rgb_frame = cv2.resize(rgb_frame, (new_width, new_height))
                
                # Convert to QImage and display
                height, width, channel = rgb_frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(
                    rgb_frame.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format_RGB888
                )
                
                pixmap = QPixmap.fromImage(q_image)
                self.video_label.setPixmap(pixmap)
                self.video_label.setStyleSheet("""
                    QLabel {
                        background-color: #000000;
                        border: 2px solid #333333;
                        border-radius: 5px;
                    }
                """)
                
        except Exception as e:
            logger.error(f"Error displaying frame: {e}")
    
    def update_analysis_frame(self, frame):
        """
        Cập nhật frame từ quá trình phân tích tự động
        
        Args:
            frame: Frame đã được annotated với detections
        """
        self.display_frame(frame)
    
    def save_current_frame(self):
        """Lưu frame hiện tại"""
        if self.current_frame is not None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"frame_{timestamp}.jpg"
            cv2.imwrite(filename, self.current_frame)
            logger.info(f"Frame saved: {filename}")
    
    def get_video_path(self) -> Optional[str]:
        """Lấy đường dẫn video hiện tại"""
        return self.video_path
    
    def reset(self):
        """Reset player về trạng thái ban đầu"""
        self.video_path = None
        self.current_frame = None
        self.video_label.clear()
        self.video_label.setText("Chọn video để bắt đầu phân tích")
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #ffffff;
                font-size: 18px;
                border: 2px dashed #555555;
                border-radius: 5px;
            }
        """)
        self.lbl_filename.setText("Chưa chọn file")
        self.lbl_filename.setStyleSheet("color: #666666;")
        self.lbl_video_info.setText("Thông tin video: --")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration từ seconds sang HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"