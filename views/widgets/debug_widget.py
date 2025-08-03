# views/widgets/debug_widget.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QGroupBox, QTextEdit, QPushButton, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont, QTextCursor
import pyqtgraph as pg
from collections import deque
from datetime import datetime

from utils.app_monitor import get_app_monitor, PerformanceMetrics


class DebugWidget(QWidget):
    """
    Widget for debugging and performance monitoring
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitor = get_app_monitor()
        
        # Data storage for graphs
        self.cpu_data = deque(maxlen=100)
        self.memory_data = deque(maxlen=100)
        self.fps_data = deque(maxlen=100)
        self.time_data = deque(maxlen=100)
        
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Debug & Performance Monitor")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.enable_checkbox = QCheckBox("Enable Monitoring")
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.toggled.connect(self._toggle_monitoring)
        controls_layout.addWidget(self.enable_checkbox)
        
        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self._clear_logs)
        controls_layout.addWidget(self.clear_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Performance metrics
        metrics_group = QGroupBox("Real-time Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # CPU Graph
        self.cpu_plot = pg.PlotWidget(title="CPU Usage (%)")
        self.cpu_plot.setLabel('left', 'CPU %')
        self.cpu_plot.setLabel('bottom', 'Time (s)')
        self.cpu_plot.setYRange(0, 100)
        self.cpu_curve = self.cpu_plot.plot(pen='y')
        metrics_layout.addWidget(self.cpu_plot)
        
        # Memory Graph
        self.memory_plot = pg.PlotWidget(title="Memory Usage (MB)")
        self.memory_plot.setLabel('left', 'Memory (MB)')
        self.memory_plot.setLabel('bottom', 'Time (s)')
        self.memory_curve = self.memory_plot.plot(pen='g')
        metrics_layout.addWidget(self.memory_plot)
        
        # FPS Graph
        self.fps_plot = pg.PlotWidget(title="FPS")
        self.fps_plot.setLabel('left', 'FPS')
        self.fps_plot.setLabel('bottom', 'Time (s)')
        self.fps_plot.setYRange(0, 60)
        self.fps_curve = self.fps_plot.plot(pen='c')
        metrics_layout.addWidget(self.fps_plot)
        
        layout.addWidget(metrics_group)
        
        # Current values display
        values_group = QGroupBox("Current Values")
        values_layout = QHBoxLayout(values_group)
        
        self.cpu_label = QLabel("CPU: 0%")
        self.memory_label = QLabel("Memory: 0 MB")
        self.fps_label = QLabel("FPS: 0")
        self.threads_label = QLabel("Threads: 0")
        
        values_layout.addWidget(self.cpu_label)
        values_layout.addWidget(self.memory_label)
        values_layout.addWidget(self.fps_label)
        values_layout.addWidget(self.threads_label)
        
        layout.addWidget(values_group)
        
        # Log display
        log_group = QGroupBox("Debug Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(150)
        log_layout.addWidget(self.log_display)
        
        layout.addWidget(log_group)
        
    def _connect_signals(self):
        """Connect monitor signals"""
        self.monitor.metrics_updated.connect(self._update_metrics)
        self.monitor.warning_raised.connect(self._add_warning)
        self.monitor.error_detected.connect(self._add_error)
        
    @pyqtSlot(PerformanceMetrics)
    def _update_metrics(self, metrics: PerformanceMetrics):
        """Update metrics display"""
        # Update labels
        self.cpu_label.setText(f"CPU: {metrics.cpu_percent:.1f}%")
        self.memory_label.setText(f"Memory: {metrics.memory_mb:.1f} MB")
        self.fps_label.setText(f"FPS: {metrics.fps:.1f}")
        self.threads_label.setText(f"Threads: {metrics.thread_count}")
        
        # Add data to graphs
        current_time = len(self.time_data)
        self.time_data.append(current_time)
        self.cpu_data.append(metrics.cpu_percent)
        self.memory_data.append(metrics.memory_mb)
        self.fps_data.append(metrics.fps)
        
        # Update graphs
        if len(self.time_data) > 1:
            self.cpu_curve.setData(self.time_data, self.cpu_data)
            self.memory_curve.setData(self.time_data, self.memory_data)
            self.fps_curve.setData(self.time_data, self.fps_data)
        
        # Apply warning colors
        if metrics.cpu_percent > 80:
            self.cpu_label.setStyleSheet("color: red;")
        elif metrics.cpu_percent > 60:
            self.cpu_label.setStyleSheet("color: orange;")
        else:
            self.cpu_label.setStyleSheet("")
            
        if metrics.memory_percent > 85:
            self.memory_label.setStyleSheet("color: red;")
        elif metrics.memory_percent > 70:
            self.memory_label.setStyleSheet("color: orange;")
        else:
            self.memory_label.setStyleSheet("")
            
    @pyqtSlot(str)
    def _add_warning(self, warning: str):
        """Add warning to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._add_log_entry(f"[{timestamp}] WARNING: {warning}", "orange")
        
    @pyqtSlot(str)
    def _add_error(self, error: str):
        """Add error to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._add_log_entry(f"[{timestamp}] ERROR: {error}", "red")
        
    def _add_log_entry(self, text: str, color: str = "white"):
        """Add entry to log display"""
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Insert colored text
        html = f'<span style="color: {color};">{text}</span><br>'
        cursor.insertHtml(html)
        
        # Auto-scroll to bottom
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )
        
    def _toggle_monitoring(self, checked: bool):
        """Toggle monitoring on/off"""
        if checked:
            self.monitor.start_monitoring()
            self._add_log_entry("Monitoring enabled", "green")
        else:
            self.monitor.stop_monitoring()
            self._add_log_entry("Monitoring disabled", "yellow")
            
    def _clear_logs(self):
        """Clear log display"""
        self.log_display.clear()
        self._add_log_entry("Logs cleared", "gray")
        
    def add_debug_message(self, message: str):
        """Public method to add debug messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._add_log_entry(f"[{timestamp}] DEBUG: {message}", "cyan")