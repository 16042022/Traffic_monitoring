# utils/app_monitor.py
import logging
import psutil, sys
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import threading
from collections import deque


class PerformanceMetrics:
    """Container for performance metrics"""
    def __init__(self):
        self.timestamp = datetime.now()
        self.cpu_percent = 0.0
        self.memory_mb = 0.0
        self.memory_percent = 0.0
        self.fps = 0.0
        self.frame_processing_time = 0.0
        self.queue_size = 0
        self.thread_count = 0
        self.gpu_memory_mb = 0.0  # If available


class AppMonitor(QObject):
    """
    Application-wide monitoring for debugging and performance tracking
    """
    
    # Signals
    metrics_updated = pyqtSignal(PerformanceMetrics)
    warning_raised = pyqtSignal(str)
    error_detected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 measurements
        self.current_metrics = PerformanceMetrics()
        
        # Monitoring settings
        self.monitoring_enabled = True
        self.update_interval = 1000  # ms
        
        # Performance thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'frame_processing_time': 100.0,  # ms
            'queue_size': 50,
            'thread_count': 50
        }
        
        # Setup timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_metrics)
        
        # Process info
        self.process = psutil.Process()
        
        # Frame timing
        self.frame_times = deque(maxlen=30)  # For FPS calculation
        self.last_frame_time = None
        
    def start_monitoring(self):
        """Start monitoring system resources"""
        self.monitoring_enabled = True
        self.update_timer.start(self.update_interval)
        self.logger.info("Application monitoring started")
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_enabled = False
        self.update_timer.stop()
        self.logger.info("Application monitoring stopped")
        
    def _update_metrics(self):
        """Update all metrics"""
        try:
            metrics = PerformanceMetrics()
            
            # CPU usage
            metrics.cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # Memory usage
            memory_info = self.process.memory_info()
            metrics.memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            metrics.memory_percent = self.process.memory_percent()
            
            # Thread count
            metrics.thread_count = self.process.num_threads()
            
            # FPS calculation
            if self.frame_times:
                time_span = self.frame_times[-1] - self.frame_times[0]
                if time_span > 0:
                    metrics.fps = len(self.frame_times) / time_span
            
            # GPU memory (if available)
            # metrics.gpu_memory_mb = self._get_gpu_memory()
            
            # Store metrics
            self.current_metrics = metrics
            self.metrics_history.append(metrics)
            
            # Check thresholds
            self._check_thresholds(metrics)
            
            # Emit update
            self.metrics_updated.emit(metrics)
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
            
    def _check_thresholds(self, metrics: PerformanceMetrics):
        """Check if any metrics exceed thresholds"""
        warnings = []
        
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            warnings.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            
        if metrics.memory_percent > self.thresholds['memory_percent']:
            warnings.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            
        if metrics.thread_count > self.thresholds['thread_count']:
            warnings.append(f"High thread count: {metrics.thread_count}")
            
        if metrics.frame_processing_time > self.thresholds['frame_processing_time']:
            warnings.append(f"Slow frame processing: {metrics.frame_processing_time:.1f}ms")
            
        for warning in warnings:
            self.warning_raised.emit(warning)
            self.logger.warning(warning)
            
    '''
        def _get_gpu_memory(self) -> float:
        """Get GPU memory usage if available"""
        try:
            # Try to get NVIDIA GPU memory
            import nvidia_ml_py as nvml
            nvml.nvmlInit()
            device_count = nvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = nvml.nvmlDeviceGetHandleByIndex(0)
                info = nvml.nvmlDeviceGetMemoryInfo(handle)
                return info.used / 1024 / 1024  # MB
        except:
            pass
        return 0.0
    '''

    def record_frame_time(self):
        """Record frame processing time"""
        current_time = time.time()
        
        if self.last_frame_time is not None:
            processing_time = (current_time - self.last_frame_time) * 1000  # ms
            self.current_metrics.frame_processing_time = processing_time
            
        self.frame_times.append(current_time)
        self.last_frame_time = current_time
        
    def log_error(self, error: Exception, context: str = ""):
        """Log error with full traceback"""
        error_msg = f"Error in {context}: {str(error)}"
        traceback_str = traceback.format_exc()
        
        self.logger.error(f"{error_msg}\n{traceback_str}")
        self.error_detected.emit(error_msg)
        
        # Save to error log file
        self._save_error_log(error_msg, traceback_str)
        
    def _save_error_log(self, error_msg: str, traceback_str: str):
        """Save error to log file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"logs/error_{timestamp}.log"
            
            with open(log_file, 'w') as f:
                f.write(f"Error: {error_msg}\n")
                f.write(f"Time: {datetime.now()}\n")
                f.write(f"Process Info:\n")
                f.write(f"  CPU: {self.current_metrics.cpu_percent}%\n")
                f.write(f"  Memory: {self.current_metrics.memory_mb:.1f}MB\n")
                f.write(f"  Threads: {self.current_metrics.thread_count}\n")
                f.write(f"\nTraceback:\n{traceback_str}\n")
                
        except Exception as e:
            self.logger.error(f"Failed to save error log: {e}")
            
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        if not self.metrics_history:
            return {}
            
        # Calculate averages
        cpu_values = [m.cpu_percent for m in self.metrics_history]
        memory_values = [m.memory_mb for m in self.metrics_history]
        fps_values = [m.fps for m in self.metrics_history if m.fps > 0]
        
        return {
            'avg_cpu': sum(cpu_values) / len(cpu_values),
            'max_cpu': max(cpu_values),
            'avg_memory_mb': sum(memory_values) / len(memory_values),
            'max_memory_mb': max(memory_values),
            'avg_fps': sum(fps_values) / len(fps_values) if fps_values else 0,
            'min_fps': min(fps_values) if fps_values else 0,
            'sample_count': len(self.metrics_history)
        }
        
    def check_system_requirements(self) -> Dict[str, bool]:
        """Check if system meets requirements"""
        requirements = {
            'cpu_cores': psutil.cpu_count() >= 4,
            'memory_gb': psutil.virtual_memory().total / 1024**3 >= 8,
            'disk_space_gb': psutil.disk_usage('/').free / 1024**3 >= 10,
            'python_64bit': sys.maxsize > 2**32
        }
        
        return requirements


# Global monitor instance
_monitor_instance = None

def get_app_monitor() -> AppMonitor:
    """Get global monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AppMonitor()
    return _monitor_instance


# Decorator for monitoring function performance
def monitor_performance(func):
    """Decorator to monitor function performance"""
    def wrapper(*args, **kwargs):
        monitor = get_app_monitor()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # ms
            
            if execution_time > 100:  # Log slow functions
                monitor.logger.warning(
                    f"Slow function: {func.__name__} took {execution_time:.1f}ms"
                )
                
            return result
            
        except Exception as e:
            monitor.log_error(e, func.__name__)
            raise
            
    return wrapper