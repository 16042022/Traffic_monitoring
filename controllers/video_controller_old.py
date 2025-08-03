# controllers/video_controller.py
from typing import Optional
from pathlib import Path
from PyQt5.QtCore import pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtWidgets import QFileDialog
import cv2
import numpy as np

from .base_controller import BaseController
from utils import is_video_file, get_video_info, format_duration
from models.entities import VideoInfo, ProcessingState


class VideoPlaybackThread(QThread):
    """Thread for video playback"""
    frame_ready = pyqtSignal(np.ndarray, int, float)  # frame, frame_id, timestamp
    playback_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.video_processor = None
        self.is_playing = False
        self.target_fps = 30
        
    def set_video_processor(self, processor):
        self.video_processor = processor
        
    def play(self):
        self.is_playing = True
        
    def pause(self):
        self.is_playing = False
        
    def stop(self):
        self.is_playing = False
        self.quit()
        self.wait()
        
    def run(self):
        """Main playback loop"""
        if not self.video_processor:
            return
            
        frame_delay = int(1000 / self.target_fps)  # ms
        
        while self.video_processor.state != ProcessingState.STOPPED:
            if self.is_playing:
                result = self.video_processor.read_frame()
                if result:
                    frame_id, timestamp, frame = result
                    self.frame_ready.emit(frame, frame_id, timestamp)
                    self.msleep(frame_delay)
                else:
                    # End of video
                    self.playback_finished.emit()
                    break
            else:
                self.msleep(100)  # Check every 100ms when paused


class VideoController(BaseController):
    """
    Controller for video playback and display
    """
    
    # Signals
    video_loaded = pyqtSignal(VideoInfo)  # Video info
    video_closed = pyqtSignal()
    playback_state_changed = pyqtSignal(str)  # State name
    frame_processed = pyqtSignal(int, float)  # frame_id, timestamp
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_video_info: Optional[VideoInfo] = None
        self.playback_thread = VideoPlaybackThread()
        
        # Connect thread signals
        self.playback_thread.frame_ready.connect(self._on_frame_ready)
        self.playback_thread.playback_finished.connect(self._on_playback_finished)
        
    def _connect_view_signals(self):
        """Connect video player widget signals"""
        if self._view:
            # Control buttons
            self._view.btn_play.clicked.connect(self.play_video)
            self._view.btn_pause.clicked.connect(self.pause_video)
            self._view.btn_stop.clicked.connect(self.stop_video)
            
            # Slider
            self._view.slider_progress.sliderPressed.connect(self._on_slider_pressed)
            self._view.slider_progress.sliderReleased.connect(self._on_slider_released)
            self._view.slider_progress.valueChanged.connect(self._on_slider_moved)
            
            # Speed control
            self._view.speed_control.valueChanged.connect(self._on_speed_changed)
    
    def _connect_model_callbacks(self):
        """Connect model callbacks"""
        # No direct callbacks needed for video controller
        pass
    
    @pyqtSlot()
    def open_video_dialog(self):
        """Open file dialog to select video"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self._view,
                "Chọn video",
                "",
                "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)"
            )
            
            if file_path:
                self.load_video(file_path)
                
        except Exception as e:
            self._handle_error(e, "Lỗi mở video")
    
    def load_video(self, file_path: str):
        """
        Load video file
        
        Args:
            file_path: Path to video file
        """
        try:
            self._set_busy(True)
            
            # Validate file
            if not Path(file_path).exists():
                raise FileNotFoundError(f"File không tồn tại: {file_path}")
            
            if not is_video_file(file_path):
                raise ValueError("File không phải là video")
            
            # Load video in model
            video_info = self._model.load_video(file_path)
            self.current_video_info = video_info
            
            # Update playback thread
            self.playback_thread.set_video_processor(self._model.video_processor)
            self.playback_thread.target_fps = video_info.fps
            
            # Update view
            if self._view:
                self._view.set_video_info(video_info)
                self._view.slider_progress.setMaximum(video_info.frame_count - 1)
                self._view.btn_play.setEnabled(True)
                self._view.btn_stop.setEnabled(True)
            
            # Start thread
            if not self.playback_thread.isRunning():
                self.playback_thread.start()
            
            # Emit signal
            self.video_loaded.emit(video_info)
            self._show_info(f"Đã tải video: {video_info.file_name}")
            
        except Exception as e:
            self._handle_error(e, f"Lỗi tải video")
        finally:
            self._set_busy(False)
    
    @pyqtSlot()
    def play_video(self):
        """Play video"""
        if self.current_video_info:
            self.playback_thread.play()
            self._model.video_processor.state = ProcessingState.PLAYING
            
            if self._view:
                self._view.btn_play.setEnabled(False)
                self._view.btn_pause.setEnabled(True)
            
            self.playback_state_changed.emit("playing")
    
    @pyqtSlot()
    def pause_video(self):
        """Pause video"""
        self.playback_thread.pause()
        self._model.video_processor.state = ProcessingState.PAUSED
        
        if self._view:
            self._view.btn_play.setEnabled(True)
            self._view.btn_pause.setEnabled(False)
        
        self.playback_state_changed.emit("paused")
    
    @pyqtSlot()
    def stop_video(self):
        """Stop video"""
        self.playback_thread.stop()
        
        if self._model and self._model.video_processor:
            self._model.video_processor.seek_frame(0)
        
        if self._view:
            self._view.slider_progress.setValue(0)
            self._view.btn_play.setEnabled(True)
            self._view.btn_pause.setEnabled(False)
            self._view.clear_display()
        
        self.playback_state_changed.emit("stopped")
    
    def close_video(self):
        """Close current video"""
        try:
            # Stop playback
            self.stop_video()
            
            # Close in model
            if self._model:
                self._model.reset()
            
            # Clear view
            if self._view:
                self._view.clear_video_info()
                self._view.btn_play.setEnabled(False)
                self._view.btn_stop.setEnabled(False)
            
            self.current_video_info = None
            self.video_closed.emit()
            
        except Exception as e:
            self._handle_error(e, "Lỗi đóng video")
    
    @pyqtSlot(np.ndarray, int, float)
    def _on_frame_ready(self, frame: np.ndarray, frame_id: int, timestamp: float):
        """Handle frame ready from thread"""
        if self._view:
            # Update display
            self._view.display_frame(frame)
            
            # Update progress
            self._view.slider_progress.setValue(frame_id)
            self._view.lbl_current_time.setText(format_duration(timestamp))
            
            # Update FPS display
            if frame_id % 30 == 0:
                current_fps = self.playback_thread.target_fps
                self._view.lbl_fps.setText(f"FPS: {current_fps:.1f}")
        
        # Emit for other controllers
        self.frame_processed.emit(frame_id, timestamp)
    
    @pyqtSlot()
    def _on_playback_finished(self):
        """Handle playback finished"""
        self.stop_video()
        self._show_info("Phát video hoàn tất")
    
    def _on_slider_pressed(self):
        """Handle slider pressed"""
        # Pause during seeking
        self.was_playing = self.playback_thread.is_playing
        if self.was_playing:
            self.pause_video()
    
    def _on_slider_released(self):
        """Handle slider released"""
        # Resume if was playing
        if hasattr(self, 'was_playing') and self.was_playing:
            self.play_video()
    
    def _on_slider_moved(self, value: int):
        """Handle slider moved"""
        if self._model and self._model.video_processor:
            # Seek to frame
            if self._model.video_processor.seek_frame(value):
                # Update time display
                timestamp = value / self.current_video_info.fps
                if self._view:
                    self._view.lbl_current_time.setText(format_duration(timestamp))
    
    def _on_speed_changed(self, value: int):
        """Handle playback speed change"""
        # Speed multiplier: 0.5x to 2x
        speed_multiplier = value / 100.0
        if self.current_video_info:
            self.playback_thread.target_fps = self.current_video_info.fps * speed_multiplier
            if self._view:
                self._view.lbl_speed.setText(f"{speed_multiplier:.1f}x")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get current displayed frame"""
        if self._view:
            return self._view.get_current_frame()
        return None
    
    def cleanup(self):
        """Cleanup resources"""
        self.playback_thread.stop()
        if self.current_video_info:
            self.close_video()
        super().cleanup()