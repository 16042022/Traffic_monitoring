# views/history_widget.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                            QTreeWidgetItem, QTabWidget, QTextBrowser,
                            QTableWidget, QTableWidgetItem, QGroupBox,
                            QPushButton, QLineEdit, QComboBox, QDateEdit,
                            QLabel, QListWidget, QListWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from .base_view import BaseView


class HistoryWidget(BaseView):
    """
    Widget for viewing historical analysis data
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout()
        
        # Filter section
        filter_group = QGroupBox("Bộ lọc")
        filter_layout = QHBoxLayout()
        
        # Search box
        filter_layout.addWidget(QLabel("Tìm kiếm:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Nhập tên file...")
        filter_layout.addWidget(self.search_box)
        
        # Date filter
        filter_layout.addWidget(QLabel("Từ ngày:"))
        self.date_filter = QDateEdit()
        self.date_filter.setDate(QDate.currentDate().addMonths(-1))
        self.date_filter.setCalendarPopup(True)
        filter_layout.addWidget(self.date_filter)
        
        # Status filter
        filter_layout.addWidget(QLabel("Trạng thái:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tất cả", "Hoàn thành", "Đang xử lý", "Lỗi"])
        filter_layout.addWidget(self.status_filter)
        
        # Refresh button
        self.btn_refresh = QPushButton("🔄 Làm mới")
        filter_layout.addWidget(self.btn_refresh)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        # Main content - Video list and details
        content_layout = QHBoxLayout()
        
        # Left: Video list
        list_widget = QWidget()
        list_layout = QVBoxLayout()
        
        list_layout.addWidget(QLabel("Danh sách video đã xử lý:"))
        
        self.video_list = QTreeWidget()
        self.video_list.setHeaderLabels(["Tên file", "Ngày xử lý", "Tổng xe", "Thời lượng"])
        self.video_list.setAlternatingRowColors(True)
        self.video_list.setSortingEnabled(True)
        
        # Adjust column widths
        header = self.video_list.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        list_layout.addWidget(self.video_list)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.btn_view_details = QPushButton("👁 Xem chi tiết")
        self.btn_delete = QPushButton("🗑 Xóa")
        
        action_layout.addWidget(self.btn_view_details)
        action_layout.addWidget(self.btn_delete)
        action_layout.addStretch()
        
        list_layout.addLayout(action_layout)
        list_widget.setLayout(list_layout)
        
        # Right: Details tabs
        self.tab_widget = QTabWidget()
        
        # Tab 1: General info
        self.info_display = QTextBrowser()
        self.tab_widget.addTab(self.info_display, "Thông tin")
        
        # Tab 2: Statistics
        self.stats_display = QTextBrowser()
        self.tab_widget.addTab(self.stats_display, "Thống kê")
        
        # Tab 3: Time-based data (FR3.2.5)
        time_widget = QWidget()
        time_layout = QVBoxLayout()
        
        self.lbl_peak_time = QLabel("Thời điểm cao điểm: --")
        time_layout.addWidget(self.lbl_peak_time)
        
        self.time_table = QTableWidget()
        self.time_table.setColumnCount(7)
        self.time_table.setHorizontalHeaderLabels([
            "Phút", "Thời gian", "Ô tô", "Xe máy", "Xe tải", "Xe buýt", "Tổng"
        ])
        self.time_table.setAlternatingRowColors(True)
        self.time_table.setSortingEnabled(True)
        
        time_layout.addWidget(self.time_table)
        time_widget.setLayout(time_layout)
        self.tab_widget.addTab(time_widget, "Dữ liệu theo thời gian")
        
        # Tab 4: Anomalies
        anomaly_widget = QWidget()
        anomaly_layout = QVBoxLayout()
        
        self.lbl_anomaly_summary = QLabel("Tổng cộng: 0 bất thường")
        anomaly_layout.addWidget(self.lbl_anomaly_summary)
        
        self.anomaly_list = QListWidget()
        anomaly_layout.addWidget(self.anomaly_list)
        
        anomaly_widget.setLayout(anomaly_layout)
        self.tab_widget.addTab(anomaly_widget, "Bất thường")
        
        # Add to main layout
        content_layout.addWidget(list_widget, 1)
        content_layout.addWidget(self.tab_widget, 2)
        
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)
        
    def add_video_item(self, video_info: dict):
        """Add video to list"""
        item = QTreeWidgetItem([
            video_info['file_name'],
            video_info['processing_date'],
            str(video_info['total_vehicles']),
            video_info['duration']
        ])
        
        # Store video ID
        item.setData(0, 1, video_info['id'])  # Column 0, Role 1
        
        # Color code by status
        if video_info['status'] == 'completed':
            color = QColor(76, 175, 80)  # Green
        elif video_info['status'] == 'failed':
            color = QColor(244, 67, 54)  # Red
        else:
            color = QColor(33, 150, 243)  # Blue
            
        item.setBackground(0, color.lighter(180))
        
        self.video_list.addTopLevelItem(item)
        
    def clear_all(self):
        """Clear all data"""
        self.video_list.clear()
        self.info_display.clear()
        self.stats_display.clear()
        self.time_table.clearContents()
        self.time_table.setRowCount(0)
        self.anomaly_list.clear()
        self.lbl_peak_time.setText("Thời điểm cao điểm: --")
        self.lbl_anomaly_summary.setText("Tổng cộng: 0 bất thường")
        
    def add_anomaly_item(self, text: str, severity: str):
        """Add anomaly to list"""
        item = QListWidgetItem(text)
        
        # Color by severity
        colors = {
            'low': QColor(76, 175, 80),      # Green
            'medium': QColor(255, 152, 0),   # Orange
            'high': QColor(244, 67, 54),     # Red
            'critical': QColor(156, 39, 176) # Purple
        }
        
        color = colors.get(severity, QColor(33, 150, 243))
        item.setBackground(color.lighter(180))
        
        self.anomaly_list.addItem(item)