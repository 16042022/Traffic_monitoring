# controllers/analysis_controller.py
from typing import Optional, Dict, List
from PyQt5.QtCore import pyqtSignal, QThread, pyqtSlot
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import numpy as np
import csv
import json
from datetime import datetime

from .base_controller import BaseController
from models.entities import VideoInfo, DetectionResult
from models.repositories import DetectionEventRepository, TrafficDataRepository
from utils import generate_export_filename, ensure_directory, format_duration


class AnalysisThread(QThread):
    """Thread for video analysis"""
    progress_updated = pyqtSignal(int, int)  # current, total
    frame_analyzed = pyqtSignal(object, np.ndarray)  # DetectionResult, display_frame
    statistics_updated = pyqtSignal(dict)  # stats
    analysis_completed = pyqtSignal(dict)  # final results
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.orchestrator = None
        self.should_stop = False
        
    def set_orchestrator(self, orchestrator):
        self.orchestrator = orchestrator
        
    def stop(self):
        self.should_stop = True
        if self.orchestrator:
            self.orchestrator.stop()
        self.quit()
        self.wait()
        
    def run(self):
        """Run analysis"""
        if not self.orchestrator:
            return
            
        try:
            # Set callbacks
            self.orchestrator.on_frame_processed = self._on_frame_processed
            self.orchestrator.on_statistics_updated = self._on_statistics_updated
            self.orchestrator.on_processing_complete = self._on_processing_complete
            
            # Run processing
            self.orchestrator.process_video(save_to_db=True)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _on_frame_processed(self, display_frame, result):
        """Handle frame processed callback"""
        if not self.should_stop:
            self.frame_analyzed.emit(result, display_frame)
            
            # Update progress
            if self.orchestrator.current_video_info:
                total = self.orchestrator.current_video_info.frame_count
                current = result.frame_id
                self.progress_updated.emit(current, total)
    
    def _on_statistics_updated(self, stats):
        """Handle statistics update"""
        if not self.should_stop:
            self.statistics_updated.emit(stats)
    
    def _on_processing_complete(self, results):
        """Handle processing complete"""
        self.analysis_completed.emit(results)


class AnalysisController(BaseController):
    """
    Controller for AI analysis operations
    """
    
    # Signals
    analysis_started = pyqtSignal()
    analysis_stopped = pyqtSignal()
    analysis_completed = pyqtSignal(int)  # video_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.analysis_thread = AnalysisThread()
        self.is_processing = False
        self.current_results: Optional[Dict] = None
        
        # Repositories
        self.detection_repo = DetectionEventRepository()
        self.traffic_repo = TrafficDataRepository()
        
        # Connect thread signals
        self.analysis_thread.progress_updated.connect(self._on_progress_updated)
        self.analysis_thread.frame_analyzed.connect(self._on_frame_analyzed)
        self.analysis_thread.statistics_updated.connect(self._on_statistics_updated)
        self.analysis_thread.analysis_completed.connect(self._on_analysis_completed)
        self.analysis_thread.error_occurred.connect(self._handle_error)
        
    def _connect_view_signals(self):
        """Connect analysis panel signals"""
        if self._view:
            # Control buttons
            self._view.btn_start_analysis.clicked.connect(self.start_analysis)
            self._view.btn_stop_analysis.clicked.connect(self.stop_analysis)
            self._view.btn_export_results.clicked.connect(self.export_results)
            
            # Settings
            self._view.confidence_slider.valueChanged.connect(self._on_confidence_changed)
            self._view.detection_classes.itemChanged.connect(self._on_classes_changed)
    
    def _connect_model_callbacks(self):
        """Connect model callbacks"""
        if self._model:
            self.analysis_thread.set_orchestrator(self._model)
    
    @pyqtSlot(VideoInfo)
    def on_video_loaded(self, video_info: VideoInfo):
        """Handle video loaded from video controller"""
        if self._view:
            self._view.btn_start_analysis.setEnabled(True)
            self._view.clear_results()
            
        self.current_results = None
    
    @pyqtSlot()
    def start_analysis(self):
        """Start video analysis"""
        try:
            if self.is_processing:
                self._show_info("Phân tích đang chạy")
                return
            
            if not self._model or not self._model.current_video_info:
                self._show_info("Vui lòng tải video trước")
                return
            
            self._set_busy(True)
            self.is_processing = True
            
            # Update UI
            if self._view:
                self._view.btn_start_analysis.setEnabled(False)
                self._view.btn_stop_analysis.setEnabled(True)
                self._view.progress_bar.setValue(0)
                self._view.clear_results()
            
            # Start analysis thread
            self.analysis_thread.start()
            
            self.analysis_started.emit()
            self._show_info("Bắt đầu phân tích video...")
            
        except Exception as e:
            self._handle_error(e, "Lỗi bắt đầu phân tích")
            self.is_processing = False
            self._set_busy(False)
    
    @pyqtSlot()
    def stop_analysis(self):
        """Stop video analysis"""
        try:
            if not self.is_processing:
                return
            
            self._show_info("Đang dừng phân tích...")
            self.analysis_thread.stop()
            
            # Will be cleaned up in _on_analysis_completed
            
        except Exception as e:
            self._handle_error(e, "Lỗi dừng phân tích")
    
    @pyqtSlot(int, int)
    def _on_progress_updated(self, current: int, total: int):
        """Handle progress update"""
        if self._view and total > 0:
            progress = int((current / total) * 100)
            self._view.progress_bar.setValue(progress)
            self._view.lbl_progress.setText(f"{current}/{total} frames")
    
    @pyqtSlot(object, np.ndarray)
    def _on_frame_analyzed(self, result: DetectionResult, display_frame: np.ndarray):
        """Handle frame analyzed"""
        if self._view:
            # Update video display
            self._view.display_analysis_frame(display_frame)
            
            # Update detection count
            total_detections = len(result.detections)
            self._view.lbl_detections.setText(f"Phát hiện: {total_detections}")
            
            # Update alerts
            if result.alerts:
                for alert in result.alerts:
                    self._view.add_alert(alert['message'], alert['type'])
    
    @pyqtSlot(dict)
    def _on_statistics_updated(self, stats: Dict):
        """Handle statistics update"""
        if self._view:
            # Update traffic statistics
            traffic_stats = stats.get('traffic', {})
            vehicle_counts = traffic_stats.get('vehicle_counts', {})
            
            self._view.update_statistics({
                'total_vehicles': traffic_stats.get('total_vehicles', 0),
                'cars': vehicle_counts.get('car', 0),
                'motorbikes': vehicle_counts.get('motorbike', 0),
                'trucks': vehicle_counts.get('truck', 0),
                'buses': vehicle_counts.get('bus', 0)
            })
            
            # Update minute stats (FR1.3.3)
            if 'current_timestamp' in stats:
                timestamp = stats['current_timestamp']
                minute = int(timestamp // 60)
                minute_data = stats.get('minute_aggregations', {}).get(str(minute), {})
                minute_total = sum(minute_data.values())
                
                self._view.update_realtime_stats({
                    'current_minute': minute,
                    'vehicles_per_minute': minute_total,
                    'timestamp': format_duration(timestamp)
                })
    
    @pyqtSlot(dict)
    def _on_analysis_completed(self, results: Dict):
        """Handle analysis completed"""
        try:
            self.current_results = results
            self.is_processing = False
            self._set_busy(False)
            
            # Update UI
            if self._view:
                self._view.btn_start_analysis.setEnabled(True)
                self._view.btn_stop_analysis.setEnabled(False)
                self._view.btn_export_results.setEnabled(True)
                self._view.progress_bar.setValue(100)
            
            # Show summary
            video_id = results.get('video_id')
            traffic_data = results.get('traffic_data')
            
            if traffic_data:
                summary = f"""
                Phân tích hoàn tất!
                
                Tổng số phương tiện: {traffic_data.total_vehicles}
                - Ô tô: {traffic_data.car_count}
                - Xe máy: {traffic_data.motorbike_count}
                - Xe tải: {traffic_data.truck_count}
                - Xe buýt: {traffic_data.bus_count}
                
                Thời gian xử lý: {format_duration(traffic_data.processing_time)}
                """
                
                QMessageBox.information(self._view, "Hoàn tất", summary)
            
            # Emit completion signal
            if video_id:
                self.analysis_completed.emit(video_id)
            
            self.analysis_stopped.emit()
            
        except Exception as e:
            self._handle_error(e, "Lỗi hoàn tất phân tích")
    
    @pyqtSlot()
    def export_results(self):
        """Export analysis results"""
        try:
            if not self.current_results:
                self._show_info("Không có kết quả để xuất")
                return
            
            # Ask for export format
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self._view,
                "Xuất kết quả",
                generate_export_filename("traffic_analysis"),
                "CSV Files (*.csv);;JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                return
            
            if selected_filter.startswith("CSV"):
                self._export_csv(file_path)
            else:
                self._export_json(file_path)
            
            self._show_info(f"Đã xuất kết quả: {file_path}")
            
        except Exception as e:
            self._handle_error(e, "Lỗi xuất kết quả")
    
    def _export_csv(self, file_path: str):
        """Export results to CSV"""
        video_id = self.current_results.get('video_id')
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header info
            writer.writerow(["Traffic Analysis Report"])
            writer.writerow(["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow([])
            
            # Traffic summary
            traffic_data = self.traffic_repo.get_by_video_id(video_id)
            if traffic_data:
                writer.writerow(["Traffic Summary"])
                writer.writerow(["Vehicle Type", "Count", "Percentage"])
                
                total = traffic_data.total_vehicles
                for vtype, count in traffic_data.get_vehicle_counts().items():
                    if vtype != 'total':
                        percentage = (count / total * 100) if total > 0 else 0
                        writer.writerow([vtype, count, f"{percentage:.1f}%"])
                
                writer.writerow([])
            
            # Time-based data
            writer.writerow(["Traffic by Minute"])
            writer.writerow(["Minute", "Car", "Motorbike", "Truck", "Bus", "Total"])
            
            timeline = self.detection_repo.get_traffic_flow_timeline(video_id, 60)
            for entry in timeline:
                counts = entry['counts']
                writer.writerow([
                    entry['interval'],
                    counts.get('car', 0),
                    counts.get('motorbike', 0),
                    counts.get('truck', 0),
                    counts.get('bus', 0),
                    entry['total']
                ])
    
    def _export_json(self, file_path: str):
        """Export results to JSON"""
        export_data = {
            "metadata": {
                "generated": datetime.now().isoformat(),
                "version": "1.0"
            },
            "video_info": self.current_results.get('video_info', {}),
            "statistics": self.current_results.get('statistics', {}),
            "traffic_data": self.current_results.get('traffic_data').__dict__ if self.current_results.get('traffic_data') else {}
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
    
    def _on_confidence_changed(self, value: int):
        """Handle confidence threshold change"""
        confidence = value / 100.0
        if self._model:
            self._model.object_detector.set_confidence_threshold(confidence)
            self._view.lbl_confidence.setText(f"{confidence:.2f}")
    
    def _on_classes_changed(self, item):
        """Handle detection class selection change"""
        # TODO: Implement class filtering
        pass
    
    def has_results(self) -> bool:
        """Check if analysis has results"""
        return self.current_results is not None
    
    def cleanup(self):
        """Cleanup resources"""
        if self.is_processing:
            self.stop_analysis()
        self.analysis_thread.wait()
        super().cleanup()