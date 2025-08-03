# controllers/video_controller.py
from typing import Optional
from pathlib import Path
from PyQt5.QtCore import pyqtSignal, QTimer, QThread, pyqtSlot, QMutex, QMutexLocker
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import cv2
import numpy as np
import time
import logging

from .base_controller import BaseController
from utils import is_video_file, get_video_info, format_duration
from models.entities import VideoInfo, ProcessingState


class VideoPlaybackThread(QThread):
    """
    Safe video playback thread with proper error handling
    """
    frame_ready = pyqtSignal(np.ndarray, int, float)  # frame, frame_id, timestamp
    playback_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self.video_processor = None
        self.orchestrator = None
        self.is_playing = False
        self.should_stop = False
        self.target_fps = 30
        self.mutex = QMutex()
        self.last_frame_time = 0

    def set_orchestrator(self, orchestrator):
        self.orchestrator = orchestrator
        
    def set_video_processor(self, processor):
        with QMutexLocker(self.mutex):
            self.video_processor = processor
        
    def play(self):
        with QMutexLocker(self.mutex):
            self.is_playing = True
            self.should_stop = False
        
    def pause(self):
        with QMutexLocker(self.mutex):
            self.is_playing = False
        
    def stop(self):
        with QMutexLocker(self.mutex):
            self.should_stop = True
            self.is_playing = False
        
        # Wait for thread to finish
        if self.isRunning():
            self.quit()
            if not self.wait(5000):  # 5 second timeout
                self.terminate()
                self.wait()
        
    def run(self):
        """Safe playback loop with frame timing"""
        try:
            if not self.video_processor:
                self.error_occurred.emit("No video processor set")
                return
            
            # Get actual FPS from video
            if self.video_processor.video_info:
                self.target_fps = self.video_processor.video_info.fps
            
            frame_interval = 1.0 / self.target_fps  # seconds
            
            while True:
                # Check if should stop
                with QMutexLocker(self.mutex):
                    if self.should_stop:
                        break
                    playing = self.is_playing
                
                if playing:
                    # Calculate timing
                    current_time = time.time()
                    time_since_last_frame = current_time - self.last_frame_time
                    
                    # Read frame
                    try:
                        result = self.video_processor.read_frame()
                        
                        if result:
                            frame_id, timestamp, frame = result
                            
                            # Emit frame
                            self.frame_ready.emit(frame.copy(), frame_id, timestamp)
                            
                            # Frame timing control
                            self.last_frame_time = current_time
                            
                            # Sleep to maintain FPS
                            sleep_time = frame_interval - time_since_last_frame
                            if sleep_time > 0:
                                self.msleep(int(sleep_time * 1000))
                        else:
                            # End of video
                            self.playback_finished.emit()
                            break
                            
                    except Exception as e:
                        self.error_occurred.emit(f"Error reading frame: {str(e)}")
                        break
                else:
                    # Paused - check periodically
                    self.msleep(50)
                    
        except Exception as e:
            self.error_occurred.emit(f"Playback error: {str(e)}")
        finally:
            # Ensure playing state is false
            with QMutexLocker(self.mutex):
                self.is_playing = False


class VideoController(BaseController):
    """
    Improved video controller with better error handling
    """
    
    # Signals (additional to base class)
    video_loaded = pyqtSignal(VideoInfo)
    video_closed = pyqtSignal()
    playback_state_changed = pyqtSignal(str)
    frame_processed = pyqtSignal(int, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_video_info: Optional[VideoInfo] = None
        self.playback_thread = VideoPlaybackThread()
        self.is_processing = False
        
        # Connect thread signals
        self.playback_thread.frame_ready.connect(self._on_frame_ready)
        self.playback_thread.playback_finished.connect(self._on_playback_finished)
        self.playback_thread.error_occurred.connect(self._on_playback_error)
        
    def _connect_view_signals(self):
        """Connect view signals - override from base"""
        if not self._view:
            return
            
        # Connect playback controls
        if hasattr(self._view, 'btn_play'):
            self._view.btn_play.clicked.connect(self.play_video)
        if hasattr(self._view, 'btn_pause'):
            self._view.btn_pause.clicked.connect(self.pause_video)
        if hasattr(self._view, 'btn_stop'):
            self._view.btn_stop.clicked.connect(self.stop_playback)
            
        # Connect slider
        if hasattr(self._view, 'slider_progress'):
            self._view.slider_progress.sliderMoved.connect(self.seek_to_frame)
    
    def _connect_model_callbacks(self):
        """Connect model callbacks - override from base"""
        if self._model:
            # VideoProcessor is part of the model
            self.playback_thread.set_video_processor(self._model.video_processor)
            
            # Set any callbacks if needed
            # For example: self._model.on_video_loaded = self._on_model_video_loaded
    
    def open_video_dialog(self):
        """Open file dialog to select video - for menu action"""
        self.load_video()

    def load_video(self, file_path: str = None):
        """Load video file with error handling"""
        try:
            # Get file path if not provided
            if not file_path:
                main_window = self.parent()._view if hasattr(self.parent(), "_view") else None
                file_path, _ = QFileDialog.getOpenFileName(
                    main_window,
                    "Select Video File",
                    "",
                    "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)")
                
                if not file_path:
                    return
            
            # Validate file
            if not is_video_file(file_path):
                raise ValueError("Selected file is not a valid video format")
            
            # Stop current playback if any
            if self.playback_thread.isRunning():
                self.stop_playback()
            
            # Load video in model
            self.logger.info(f"Loading video: {file_path}")
            # Check if model is set
            if not self._model:
                raise ValueError("Model not set in VideoController")
            video_info = self._model.video_processor.open_video(file_path)
            
            # Set up playback thread
            self.playback_thread.set_video_processor(self._model.video_processor)
            
            # Update state
            self.current_video_info = video_info

            # Update model's current video info
            if self._model:
                self._model.current_video_info = video_info

            # Update view with video info
            if self.view:
                # Update labels
                if hasattr(self.view, 'lbl_video_name'):
                    self.view.lbl_video_name.setText(video_info.file_name)
                if hasattr(self.view, 'lbl_video_info'):
                    self.view.lbl_video_info.setText(f"{video_info.resolution} @ {video_info.fps}fps")
                if hasattr(self.view, 'lbl_total_time'):
                    self.view.lbl_total_time.setText(format_duration(video_info.duration))
                    
                # Enable controls
                if hasattr(self.view, 'btn_play'):
                    self.view.btn_play.setEnabled(True)
                if hasattr(self.view, 'btn_pause'):
                    self.view.btn_pause.setEnabled(True)
                if hasattr(self.view, 'btn_stop'):
                    self.view.btn_stop.setEnabled(True)
                if hasattr(self.view, 'slider_progress'):
                    self.view.slider_progress.setEnabled(True)
                    self.view.slider_progress.setMaximum(video_info.frame_count - 1)
                    
                # Display first frame
                result = self._model.video_processor.read_frame()
                if result:
                    frame_id, timestamp, frame = result
                    self._display_frame(frame)
                    # Reset to beginning after displaying first frame
                    self._model.video_processor.seek_frame(0)
            
            # Emit signal
            self.video_loaded.emit(video_info)
            self.playback_state_changed.emit("loaded")
            
            self.logger.info(f"Video loaded successfully: {video_info.file_name}")
            
        except Exception as e:
            error_msg = f"Failed to load video: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            
            # Show error dialog
            if self.view:
                QMessageBox.critical(
                    self.view,
                    "Error Loading Video",
                    error_msg
                )
    
    def play_video(self):
        """Start or resume video playback"""
        try:
            if not self.current_video_info:
                self.logger.warning("No video loaded")
                return
            
            # Start playback thread if not running
            if not self.playback_thread.isRunning():
                self.playback_thread.start()
            
            # Resume playback
            self.playback_thread.play()
            self.playback_state_changed.emit("playing")

            # Update button states
            if self.view:
                if hasattr(self.view, 'btn_play'):
                    self.view.btn_play.setEnabled(False)
                if hasattr(self.view, 'btn_pause'):
                    self.view.btn_pause.setEnabled(True)
                if hasattr(self.view, 'btn_stop'):
                    self.view.btn_stop.setEnabled(True)
            
        except Exception as e:
            error_msg = f"Failed to play video: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def pause_video(self):
        """Pause video playback"""
        try:
            self.playback_thread.pause()
            self.playback_state_changed.emit("paused")

            # Update button states
            if self.view:
                if hasattr(self.view, 'btn_play'):
                    self.view.btn_play.setEnabled(True)
                if hasattr(self.view, 'btn_pause'):
                    self.view.btn_pause.setEnabled(False)

        except Exception as e:
            self.logger.error(f"Error pausing video: {e}")
    
    def stop_playback(self):
        """Stop video playback completely"""
        try:
            self.logger.info("Stopping video playback")
            
            # Stop playback thread
            self.playback_thread.stop()
            
            # Reset to beginning
            if self._model and self._model.video_processor:
                self._model.video_processor.seek_frame(0)
                
                # Display first frame
                result = self._model.video_processor.read_frame()
                if result:
                    frame_id, timestamp, frame = result
                    self._display_frame(frame)
                    self._model.video_processor.seek_frame(0)
            
            # Update state
            self.playback_state_changed.emit("stopped")

            # Update button states
            if self.view:
                if hasattr(self.view, 'btn_play'):
                    self.view.btn_play.setEnabled(True)
                if hasattr(self.view, 'btn_pause'):
                    self.view.btn_pause.setEnabled(False)
                if hasattr(self.view, 'btn_stop'):
                    self.view.btn_stop.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Error stopping playback: {e}")
    
    def seek_to_frame(self, frame_number: int):
        """Seek to specific frame"""
        try:
            if not self.current_video_info:
                return
            
            # Validate frame number
            if 0 <= frame_number < self.current_video_info.frame_count:
                # Pause during seek
                was_playing = self.playback_thread.is_playing
                if was_playing:
                    self.pause_video()
                
                # Seek
                success = self.model.video_processor.seek_frame(frame_number)
                
                if success:
                    # Get and display the frame
                    result = self._model.video_processor.read_frame()
                    if result:
                        frame_id, timestamp, frame = result
                        self._on_frame_ready(frame, frame_id, timestamp)
                
                # Resume if was playing
                if was_playing:
                    self.play_video()
                    
        except Exception as e:
            self.logger.error(f"Error seeking to frame {frame_number}: {e}")
    
    def close_video(self):
        """Close current video and cleanup"""
        try:
            self.logger.info("Closing video")
            
            # Stop playback
            self.stop_playback()
            
            # Close video in model
            if self._model and self._model.video_processor:
                self._model.video_processor.close_video()
            
            # Clear state
            self.current_video_info = None
            
            # Clear view
            if self.view:
                if hasattr(self.view, 'clear_video_info'):
                    self.view.clear_video_info()
                if hasattr(self.view, 'clear_display'):
                    self.view.clear_display()
            
            # Emit signal
            self.video_closed.emit()
            self.playback_state_changed.emit("closed")

        except Exception as e:
            self.logger.error(f"Error closing video: {e}")
    
    def start_analysis(self):
        """Start video analysis"""
        try:
            if not self.current_video_info:
                self.logger.warning("No video loaded for analysis")
                return
            
            if self.is_processing:
                self.logger.warning("Analysis already in progress")
                return
            
            self.logger.info("Starting video analysis")
            self.is_processing = True
            
            # Start analysis in model
            self._model.start_processing()
            
        except Exception as e:
            error_msg = f"Failed to start analysis: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_processing = False
    
    def stop_analysis(self):
        """Stop video analysis"""
        try:
            self.logger.info("Stopping video analysis")
            self.is_processing = False
            
            # Stop analysis in model
            self._model.stop_processing()
            
        except Exception as e:
            self.logger.error(f"Error stopping analysis: {e}")
    
    @pyqtSlot(np.ndarray, int, float)
    def _on_frame_ready(self, frame: np.ndarray, frame_id: int, timestamp: float):
        """Handle frame ready from playback thread"""
        try:
            # Display frame
            self._display_frame(frame)
            
            # Get analysis results if processing
            if self.is_processing and hasattr(self._model, 'get_frame_results'):
                results = self._model.get_frame_results(frame_id)
                if results:
                    # Draw overlays
                    overlays = self._prepare_overlays(results)
                    frame_with_overlays = self._model.video_processor.draw_on_frame(frame, overlays)
                    self._display_frame(frame_with_overlays)
            
            # Update timeline
            if self.view:
                if hasattr(self.view, 'slider_progress'):
                    self.view.slider_progress.setValue(frame_id)
                if hasattr(self.view, 'lbl_current_time'):
                    self.view.lbl_current_time.setText(format_duration(timestamp))
            
            # Emit progress
            self.frame_processed.emit(frame_id, timestamp)
            
        except Exception as e:
            self.logger.error(f"Error processing frame {frame_id}: {e}")
    
    def _display_frame(self, frame: np.ndarray):
        """Display frame in video widget"""
        if self.view and hasattr(self.view, 'display_frame'):
            self.view.display_frame(frame)
        elif self.view and hasattr(self.view, 'video_display'):
            self.view.video_display.display_frame(frame)
    
    @pyqtSlot()
    def _on_playback_finished(self):
        """Handle playback finished"""
        self.logger.info("Video playback finished")
        self.playback_state_changed.emit("finished")
        
        # Auto-stop if processing
        if self.is_processing:
            self.stop_analysis()
    
    @pyqtSlot(str)
    def _on_playback_error(self, error_msg: str):
        """Handle playback error"""
        self.logger.error(f"Playback error: {error_msg}")
        self.error_occurred.emit(error_msg)
        
        # Stop playback on error
        self.stop_playback()
    
    def _prepare_overlays(self, results: dict) -> dict:
        """Prepare overlay data from analysis results"""
        overlays = {
            'boxes': [],
            'lines': [],
            'texts': []
        }
        
        try:
            # Add detection boxes
            if 'detections' in results:
                for det in results['detections']:
                    color = (0, 255, 0)  # Green for vehicles
                    if det.get('type') == 'person':
                        color = (255, 0, 0)  # Red for persons
                    elif det.get('type') == 'obstacle':
                        color = (0, 0, 255)  # Blue for obstacles
                    
                    overlays['boxes'].append({
                        'bbox': det['bbox'],
                        'label': f"{det['type']} {det.get('id', '')}",
                        'color': color
                    })
            
            # Add traffic statistics
            if 'statistics' in results:
                stats = results['statistics']
                y_pos = 30
                for key, value in stats.items():
                    overlays['texts'].append({
                        'content': f"{key}: {value}",
                        'position': (10, y_pos),
                        'color': (255, 255, 255),
                        'scale': 0.6
                    })
                    y_pos += 25
            
        except Exception as e:
            self.logger.error(f"Error preparing overlays: {e}")
        
        return overlays
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.logger.info("Cleaning up VideoController")
            
            # Stop and clean up playback thread
            if self.playback_thread.isRunning():
                self.playback_thread.stop()
            
            # Close video
            self.close_video()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor"""
        try:
            self.cleanup()
        except:
            pass