"""
Analysis Controller - Điều khiển phân tích TỰ ĐỘNG toàn bộ video
"""

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from typing import Optional, Dict, Any
import logging
from pathlib import Path

from models.video_analysis_orchestrator import (
    VideoAnalysisOrchestrator, 
    AnalysisProgress, 
    RealTimeStats
)
from utils.logger import get_logger

logger = get_logger(__name__)

class AnalysisController(QObject):
    """
    Controller để điều khiển quá trình phân tích video TỰ ĐỘNG
    """
    
    # Signals để communicate với View
    progress_updated = pyqtSignal(dict)  # Tiến trình phân tích
    stats_updated = pyqtSignal(dict)     # Thống kê real-time
    frame_updated = pyqtSignal(object)   # Frame đã annotated
    analysis_started = pyqtSignal(str)   # Bắt đầu phân tích
    analysis_completed = pyqtSignal(dict) # Hoàn thành phân tích
    analysis_error = pyqtSignal(str)     # Lỗi phân tích
    status_message = pyqtSignal(str)     # Thông báo trạng thái
    
    def __init__(self):
        super().__init__()
        self.model: Optional[VideoAnalysisOrchestrator] = None
        self.view = None
        self.current_video_path: Optional[str] = None
        self.current_video_id: Optional[int] = None
        
        # Timer để poll updates từ model
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._poll_updates)
        self.update_timer.setInterval(50)  # Update mỗi 50ms cho smooth UI
        
        logger.debug("AnalysisController initialized")
    
    def set_model(self, model: VideoAnalysisOrchestrator):
        """Set model reference"""
        self.model = model
        # Set callbacks
        self.model.set_callbacks(
            progress_callback=self._on_progress_update,
            stats_callback=self._on_stats_update,
            frame_callback=self._on_frame_update
        )
        logger.debug("Model set for AnalysisController")
    
    def set_view(self, view):
        """Set view reference"""
        self.view = view
        self._connect_view_signals()
        logger.debug("View set for AnalysisController")
    
    def _connect_view_signals(self):
        """Kết nối signals từ view"""
        if hasattr(self.view, 'start_analysis_requested'):
            self.view.start_analysis_requested.connect(self.start_analysis)
        if hasattr(self.view, 'pause_analysis_requested'):
            self.view.pause_analysis_requested.connect(self.pause_analysis)
        if hasattr(self.view, 'resume_analysis_requested'):
            self.view.resume_analysis_requested.connect(self.resume_analysis)
        if hasattr(self.view, 'stop_analysis_requested'):
            self.view.stop_analysis_requested.connect(self.stop_analysis)
    
    def load_video(self, video_path: str):
        """Load video để chuẩn bị phân tích"""
        try:
            if not Path(video_path).exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            self.current_video_path = video_path
            self.status_message.emit(f"Đã tải video: {Path(video_path).name}")
            logger.info(f"Video loaded: {video_path}")
            
        except Exception as e:
            error_msg = f"Lỗi tải video: {str(e)}"
            self.analysis_error.emit(error_msg)
            logger.error(error_msg)
    
    def start_analysis(self):
        """
        BẮT ĐẦU PHÂN TÍCH TỰ ĐỘNG TOÀN BỘ VIDEO
        Khi người dùng nhấn nút Start, hệ thống sẽ tự động xử lý toàn bộ video
        """
        if not self.model:
            self.analysis_error.emit("Model chưa được khởi tạo")
            return
        
        if not self.current_video_path:
            self.analysis_error.emit("Chưa chọn video để phân tích")
            return
        
        if self.model.is_processing():
            self.status_message.emit("Đang có phân tích khác đang chạy")
            return
        
        try:
            # Emit signal bắt đầu phân tích
            self.analysis_started.emit(self.current_video_path)
            self.status_message.emit("Đang bắt đầu phân tích tự động...")
            
            # Start automatic analysis của TOÀN BỘ VIDEO
            self.current_video_id = self.model.start_full_video_analysis(
                self.current_video_path
            )
            
            if self.current_video_id > 0:
                # Start timer để poll updates
                self.update_timer.start()
                self.status_message.emit("Đang phân tích video... Vui lòng đợi")
                logger.info(f"Started automatic analysis for video ID: {self.current_video_id}")
            else:
                raise Exception("Failed to start analysis")
            
        except Exception as e:
            error_msg = f"Lỗi khi bắt đầu phân tích: {str(e)}"
            self.analysis_error.emit(error_msg)
            logger.error(error_msg)
    
    def pause_analysis(self):
        """Tạm dừng phân tích"""
        if self.model and self.model.is_processing():
            self.model.pause_analysis()
            self.status_message.emit("Đã tạm dừng phân tích")
            logger.info("Analysis paused")
    
    def resume_analysis(self):
        """Tiếp tục phân tích"""
        if self.model and self.model.is_processing():
            self.model.resume_analysis()
            self.status_message.emit("Tiếp tục phân tích...")
            logger.info("Analysis resumed")
    
    def stop_analysis(self):
        """Dừng phân tích hoàn toàn"""
        if self.model and self.model.is_processing():
            self.model.stop_analysis()
            self.update_timer.stop()
            self.status_message.emit("Đã dừng phân tích")
            logger.info("Analysis stopped")
    
    def _poll_updates(self):
        """Poll updates từ model (chạy theo timer)"""
        if not self.model:
            return
        
        # Get progress update
        progress = self.model.get_current_progress()
        if progress:
            self._on_progress_update(progress)
        
        # Get stats update
        stats = self.model.get_current_stats()
        if stats:
            self._on_stats_update(stats)
        
        # Get frame update
        frame = self.model.get_current_frame()
        if frame is not None:
            self._on_frame_update(frame)
    
    def _on_progress_update(self, progress: AnalysisProgress):
        """Xử lý cập nhật tiến trình"""
        progress_dict = {
            'current_frame': progress.current_frame,
            'total_frames': progress.total_frames,
            'percent_complete': progress.percent_complete,
            'current_time': progress.current_time,
            'total_duration': progress.total_duration,
            'fps': progress.fps,
            'status': progress.status
        }
        
        self.progress_updated.emit(progress_dict)
        
        # Cập nhật status message
        if progress.status == 'analyzing':
            msg = f"Đang phân tích: {progress.percent_complete:.1f}% - " \
                  f"Frame {progress.current_frame}/{progress.total_frames} - " \
                  f"FPS: {progress.fps:.1f}"
            self.status_message.emit(msg)
        
        elif progress.status == 'completed':
            self.update_timer.stop()
            self.status_message.emit("Phân tích hoàn tất!")
            self._on_analysis_completed()
        
        elif progress.status == 'error':
            self.update_timer.stop()
            self.analysis_error.emit("Có lỗi xảy ra trong quá trình phân tích")
    
    def _on_stats_update(self, stats: RealTimeStats):
        """Xử lý cập nhật thống kê real-time"""
        stats_dict = {
            'total_vehicles': stats.total_vehicles,
            'vehicles_by_type': stats.vehicles_by_type,
            'current_minute_count': stats.current_minute_count,
            'anomalies_detected': stats.anomalies_detected,
            'processing_fps': stats.processing_fps,
            'video_timestamp': stats.video_timestamp
        }
        
        self.stats_updated.emit(stats_dict)
    
    def _on_frame_update(self, frame):
        """Xử lý cập nhật frame"""
        self.frame_updated.emit(frame)
    
    def _on_analysis_completed(self):
        """Xử lý khi phân tích hoàn tất"""
        if not self.model or not self.current_video_id:
            return
        
        try:
            # Lấy kết quả phân tích
            results = self.model.get_analysis_results(self.current_video_id)
            
            # Emit signal với kết quả
            self.analysis_completed.emit(results)
            
            # Log summary
            if 'traffic_statistics' in results:
                total = results['traffic_statistics'].get('total_vehicles', 0)
                logger.info(f"Analysis completed. Total vehicles detected: {total}")
            
        except Exception as e:
            logger.error(f"Error getting analysis results: {e}")
    
    def get_current_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê hiện tại"""
        if self.model:
            stats = self.model.get_current_stats()
            if stats:
                return {
                    'total_vehicles': stats.total_vehicles,
                    'vehicles_by_type': stats.vehicles_by_type,
                    'current_minute_count': stats.current_minute_count,
                    'anomalies_detected': stats.anomalies_detected,
                    'video_timestamp': stats.video_timestamp
                }
        return {}
    
    def get_analysis_results(self) -> Dict[str, Any]:
        """Lấy kết quả phân tích cuối cùng"""
        if self.model and self.current_video_id:
            return self.model.get_analysis_results(self.current_video_id)
        return {}
        