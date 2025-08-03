# controllers/history_controller.py
from typing import List, Dict, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QModelIndex, Qt
from PyQt5.QtWidgets import QMessageBox
from datetime import datetime

from .base_controller import BaseController
from models.repositories import (
    VideoRepository, 
    DetectionEventRepository,
    TrafficDataRepository,
    AnomalyEventRepository
)
from dal.models import Video
from utils import format_duration, format_timestamp


class HistoryController(BaseController):
    """
    Controller for historical data viewing and management
    """
    
    # Signals
    video_selected = pyqtSignal(int)  # video_id
    data_refreshed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Repositories
        self.video_repo = VideoRepository()
        self.detection_repo = DetectionEventRepository()
        self.traffic_repo = TrafficDataRepository()
        self.anomaly_repo = AnomalyEventRepository()
        
        # Current selection
        self.selected_video_id: Optional[int] = None
        self.video_list: List[Video] = []
        
    def _connect_view_signals(self):
        """Connect history view signals"""
        if self._view:
            # Video list selection
            self._view.video_list.itemSelectionChanged.connect(
                self._on_video_selected
            )
            
            # Filter controls
            self._view.date_filter.dateChanged.connect(self._apply_filters)
            self._view.status_filter.currentTextChanged.connect(self._apply_filters)
            self._view.search_box.textChanged.connect(self._apply_filters)
            
            # Action buttons
            self._view.btn_refresh.clicked.connect(self.refresh_history)
            self._view.btn_delete.clicked.connect(self._delete_selected)
            self._view.btn_view_details.clicked.connect(self._view_details)
            
            # Tab changes
            self._view.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _connect_model_callbacks(self):
        """Connect model callbacks"""
        # History controller works directly with repositories
        pass
    
    def initialize(self):
        """Initialize history view with data"""
        self.refresh_history()
    
    @pyqtSlot()
    def refresh_history(self):
        """Refresh video history list"""
        try:
            self._set_busy(True)
            
            # Get completed videos
            self.video_list = self.video_repo.get_completed_videos(include_stats=True)
            
            # Update view
            if self._view:
                self._view.clear_all()
                self._populate_video_list()
            
            self.data_refreshed.emit()
            self._show_info(f"Đã tải {len(self.video_list)} video")
            
        except Exception as e:
            self._handle_error(e, "Lỗi tải lịch sử")
        finally:
            self._set_busy(False)
    
    def _populate_video_list(self):
        """Populate video list in view"""
        for video in self.video_list:
            # Format video info
            info = {
                'id': video.id,
                'file_name': video.file_name,
                'processing_date': format_timestamp(video.processing_timestamp),
                'duration': format_duration(video.duration),
                'total_vehicles': video.traffic_data.total_vehicles if video.traffic_data else 0,
                'status': video.status
            }
            
            self._view.add_video_item(info)
    
    @pyqtSlot()
    def _on_video_selected(self):
        """Handle video selection"""
        try:
            selected_items = self._view.video_list.selectedItems()
            if not selected_items:
                return
            
            # Get video ID from item data
            item = selected_items[0]
            video_id = item.data(0, 1)  # Role 1 stores ID
            
            if video_id != self.selected_video_id:
                self.selected_video_id = video_id
                self._load_video_details(video_id)
                self.video_selected.emit(video_id)
                
        except Exception as e:
            self._handle_error(e, "Lỗi chọn video")
    
    def _load_video_details(self, video_id: int):
        """Load details for selected video"""
        try:
            # Get video with all data
            video = self.video_repo.get_with_all_data(video_id)
            if not video:
                return
            
            # Update info tab
            if self._view:
                info_text = f"""
                <h3>{video.file_name}</h3>
                <p><b>Ngày xử lý:</b> {format_timestamp(video.processing_timestamp)}</p>
                <p><b>Thời lượng:</b> {format_duration(video.duration)}</p>
                <p><b>Độ phân giải:</b> {video.resolution}</p>
                <p><b>FPS:</b> {video.fps}</p>
                <p><b>Thời gian xử lý:</b> {format_duration(video.processing_duration) if video.processing_duration else 'N/A'}</p>
                """
                self._view.info_display.setHtml(info_text)
            
            # Load traffic statistics
            self._load_traffic_statistics(video_id)
            
            # Load time-based data
            self._load_time_data(video_id)
            
            # Load anomalies
            self._load_anomalies(video_id)
            
        except Exception as e:
            self._handle_error(e, "Lỗi tải chi tiết video")
    
# Trong HistoryController._load_traffic_statistics, sửa phần format string:

    def _load_traffic_statistics(self, video_id: int):
        """Load traffic statistics for selected video"""
        try:
            # Get traffic data
            traffic_data = self.traffic_repo.get_by_video_id(video_id)
            
            if self._view and traffic_data:
                # Calculate percentages với giá trị mặc định
                total = traffic_data.total_vehicles or 0
                car_count = traffic_data.car_count or 0
                motorbike_count = traffic_data.motorbike_count or 0
                truck_count = traffic_data.truck_count or 0
                bus_count = traffic_data.bus_count or 0
                
                car_pct = (car_count / total * 100) if total > 0 else 0
                motorbike_pct = (motorbike_count / total * 100) if total > 0 else 0
                truck_pct = (truck_count / total * 100) if total > 0 else 0
                bus_pct = (bus_count / total * 100) if total > 0 else 0
                
                # Create stats dictionary
                stats = {
                    'total_vehicles': total,
                    'vehicle_breakdown': {
                        'car': car_count,
                        'motorbike': motorbike_count,
                        'truck': truck_count,
                        'bus': bus_count
                    },
                    'car_percentage': car_pct,
                    'motorbike_percentage': motorbike_pct,
                    'truck_percentage': truck_pct,
                    'bus_percentage': bus_pct,
                    'avg_per_minute': 0,  # Calculate if needed
                    'peak_minute': 0,
                    'congestion_level': traffic_data.congestion_level or 'unknown'
                }
                
                # Format HTML
                stats_html = f"""
                <h3>Thống kê giao thông</h3>
                <p><b>Tổng số phương tiện:</b> {stats['total_vehicles']}</p>
                <table>
                <tr><td><b>Ô tô:</b></td><td>{stats['vehicle_breakdown']['car']} ({stats['car_percentage']:.1f}%)</td></tr>
                <tr><td><b>Xe máy:</b></td><td>{stats['vehicle_breakdown']['motorbike']} ({stats['motorbike_percentage']:.1f}%)</td></tr>
                <tr><td><b>Xe tải:</b></td><td>{stats['vehicle_breakdown']['truck']} ({stats['truck_percentage']:.1f}%)</td></tr>
                <tr><td><b>Xe buýt:</b></td><td>{stats['vehicle_breakdown']['bus']} ({stats['bus_percentage']:.1f}%)</td></tr>
                </table>
                <p><b>TB phương tiện/phút:</b> {stats.get('avg_per_minute', 0):.1f}</p>
                <p><b>Cao điểm:</b> {stats.get('peak_minute', 0)} xe/phút</p>
                <p><b>Mức độ tắc nghẽn:</b> {self._translate_congestion(stats.get('congestion_level', 'unknown'))}</p>
                """
                
                self._view.stats_display.setHtml(stats_html)
            else:
                # No data case
                self._view.stats_display.setHtml("<p>Chưa có dữ liệu thống kê</p>")
                
        except Exception as e:
            self._handle_error(e, "Lỗi tải thống kê")
    
    def _load_time_data(self, video_id: int):
        """Load time-based traffic data"""
        try:
            # Get timeline data (FR3.2.5)
            timeline = self.detection_repo.get_traffic_flow_timeline(video_id, 60)
            
            if self._view:
                self._view.time_table.clearContents()
                self._view.time_table.setRowCount(len(timeline))
                
                for row, entry in enumerate(timeline):
                    # Minute
                    self._view.time_table.setItem(row, 0, 
                        self._create_table_item(str(entry['interval'])))
                    
                    # Time range
                    time_range = f"{format_duration(entry['start_time'])} - {format_duration(entry['end_time'])}"
                    self._view.time_table.setItem(row, 1,
                        self._create_table_item(time_range))
                    
                    # Vehicle counts
                    counts = entry['counts']
                    self._view.time_table.setItem(row, 2,
                        self._create_table_item(str(counts.get('car', 0))))
                    self._view.time_table.setItem(row, 3,
                        self._create_table_item(str(counts.get('motorbike', 0))))
                    self._view.time_table.setItem(row, 4,
                        self._create_table_item(str(counts.get('truck', 0))))
                    self._view.time_table.setItem(row, 5,
                        self._create_table_item(str(counts.get('bus', 0))))
                    
                    # Total
                    self._view.time_table.setItem(row, 6,
                        self._create_table_item(str(entry['total'])))
                
                # Find and highlight peak minute
                peak = self.detection_repo.get_peak_traffic_interval(video_id)
                if peak:
                    self._view.lbl_peak_time.setText(
                        f"Thời điểm cao điểm: Phút {peak['interval']} ({peak['total']} xe)"
                    )
                    
        except Exception as e:
            self._handle_error(e, "Lỗi tải dữ liệu theo thời gian")
    
    def _load_anomalies(self, video_id: int):
        """Load anomaly events"""
        try:
            anomalies = self.anomaly_repo.get_anomalies_for_video(video_id)
            
            if self._view:
                self._view.anomaly_list.clear()
                
                for anomaly in anomalies:
                    # Format anomaly info
                    time_str = format_duration(anomaly.timestamp_in_video)
                    type_str = self._translate_anomaly_type(anomaly.anomaly_type)
                    severity_str = self._translate_severity(anomaly.severity_level)
                    
                    item_text = f"[{time_str}] {type_str} - {severity_str}"
                    if anomaly.alert_message:
                        item_text += f"\n{anomaly.alert_message}"
                    
                    self._view.add_anomaly_item(item_text, anomaly.severity_level)
                
                # Update summary
                counts = self.anomaly_repo.count_by_type_and_severity(video_id)
                self._view.lbl_anomaly_summary.setText(
                    f"Tổng cộng: {len(anomalies)} bất thường"
                )
                
        except Exception as e:
            self._handle_error(e, "Lỗi tải danh sách bất thường")
    
    @pyqtSlot()
    def _apply_filters(self):
        """Apply filters to video list"""
        try:
            # Get filter values
            search_text = self._view.search_box.text().lower()
            status_filter = self._view.status_filter.currentText()
            date_filter = self._view.date_filter.date().toPyDate()
            
            # Filter video list
            for i in range(self._view.video_list.topLevelItemCount()):
                item = self._view.video_list.topLevelItem(i)
                video_id = item.data(0, 1)
                
                # Find video in list
                video = next((v for v in self.video_list if v.id == video_id), None)
                if not video:
                    continue
                
                # Apply filters
                show = True
                
                # Search filter
                if search_text and search_text not in video.file_name.lower():
                    show = False
                
                # Status filter
                if status_filter != "Tất cả" and video.status != status_filter.lower():
                    show = False
                
                # Date filter
                if video.processing_timestamp.date() < date_filter:
                    show = False
                
                item.setHidden(not show)
                
        except Exception as e:
            self._handle_error(e, "Lỗi áp dụng bộ lọc")
    
    @pyqtSlot()
    def _delete_selected(self):
        """Delete selected video"""
        if not self.selected_video_id:
            self._show_info("Vui lòng chọn video cần xóa")
            return
        
        # Get parent widget for QMessageBox (use view, not controller)
        parent_widget = self._view if self._view else None
        
        # Confirm deletion
        reply = QMessageBox.question(
            parent_widget,
            "Xác nhận xóa",
            "Bạn có chắc muốn xóa video này và tất cả dữ liệu liên quan?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.video_repo.delete(self.selected_video_id)
                self._show_info("Đã xóa video thành công")
                self.refresh_history()
            except Exception as e:
                self._handle_error(e, "Lỗi xóa video")
    
    @pyqtSlot()
    def _view_details(self):
        """View detailed report"""
        if not self.selected_video_id:
            self._show_info("Vui lòng chọn video để xem chi tiết")
            return
        
        # TODO: Open detailed report dialog
        self._show_info("Tính năng xem chi tiết đang được phát triển")
    
    @pyqtSlot(int)
    def _on_tab_changed(self, index: int):
        """Handle tab change"""
        # Refresh data for new tab if needed
        if self.selected_video_id:
            if index == 1:  # Statistics tab
                self._load_traffic_statistics(self.selected_video_id)
            elif index == 2:  # Time data tab
                self._load_time_data(self.selected_video_id)
            elif index == 3:  # Anomalies tab
                self._load_anomalies(self.selected_video_id)
    
    def toggle_history_view(self):
        """Toggle history view visibility"""
        if self._view:
            self._view.setVisible(not self._view.isVisible())
            if self._view.isVisible():
                self.refresh_history()
    
    def _create_table_item(self, text: str):
        """Create table widget item"""
        from PyQt5.QtWidgets import QTableWidgetItem
        from PyQt5.QtCore import Qt
        
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item
    
    def _translate_congestion(self, level: str) -> str:
        """Translate congestion level"""
        translations = {
            'low': 'Thấp',
            'medium': 'Trung bình',
            'high': 'Cao',
            'very_high': 'Rất cao',
            'unknown': 'Không xác định'
        }
        return translations.get(level, level)
    
    def _translate_anomaly_type(self, atype: str) -> str:
        """Translate anomaly type"""
        translations = {
            'pedestrian': 'Người đi bộ',
            'animal': 'Động vật',
            'obstacle': 'Vật cản',
            'stopped_vehicle': 'Xe dừng bất thường'
        }
        return translations.get(atype, atype)
    
    def _translate_severity(self, severity: str) -> str:
        """Translate severity level"""
        translations = {
            'low': 'Thấp',
            'medium': 'Trung bình',
            'high': 'Cao',
            'critical': 'Nghiêm trọng'
        }
        return translations.get(severity, severity)
    
    def cleanup(self):
        """Cleanup resources"""
        self.selected_video_id = None
        self.video_list.clear()
        super().cleanup()