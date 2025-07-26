# models/video_analysis_orchestrator.py
import logging
from typing import Optional, Dict, List, Callable
import json
from pathlib import Path
import time
from datetime import datetime

from .entities import VideoInfo, DetectionResult, ProcessingState
from .components.video_processor import VideoProcessor
from .components.object_detector import ObjectDetector
from .components.vehicle_tracker import VehicleTracker
from .components.traffic_monitor import TrafficMonitor
from .components.anomaly_detector import AnomalyDetector

# DAL imports
from dal import db_manager
from .repositories import (
    VideoRepository,
    DetectionEventRepository,
    TrafficDataRepository,
    AnomalyEventRepository
)


class VideoAnalysisOrchestrator:
    """
    Main orchestrator kết hợp tất cả components
    Updated với DAL integration
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.video_processor = VideoProcessor()
        self.object_detector = ObjectDetector(
            model_type=self.config.get("model_type", "yolov5"),
            confidence_threshold=self.config.get("confidence_threshold", 0.5)
        )
        self.vehicle_tracker = VehicleTracker()
        self.traffic_monitor = TrafficMonitor(
            self.config.get("virtual_line", {})
        )
        self.anomaly_detector = AnomalyDetector(
            self.config.get("stop_time_threshold", 20.0)
        )
        
        # Initialize repositories
        self.video_repo = VideoRepository()
        self.detection_repo = DetectionEventRepository()
        self.traffic_repo = TrafficDataRepository()
        self.anomaly_repo = AnomalyEventRepository()
        
        # Processing state
        self.current_video_info: Optional[VideoInfo] = None
        self.current_video_id: Optional[int] = None  # Database ID
        self.is_processing = False
        self.should_stop = False
        
        # Batch storage for performance
        self.detection_batch = []
        self.anomaly_batch = []
        self.batch_size = 100
        
        # Time aggregation for FR3.2.5
        self.minute_aggregations = {}
        self.current_minute = -1
        
        # Callbacks
        self.on_frame_processed: Optional[Callable] = None
        self.on_statistics_updated: Optional[Callable] = None
        self.on_anomaly_detected: Optional[Callable] = None
        self.on_processing_complete: Optional[Callable] = None
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Default configuration"""
        return {
            "virtual_line": {
                "p1_x": 100,
                "p1_y": 300,
                "p2_x": 800,
                "p2_y": 300,
                "counting_direction": "down"
            },
            "stop_time_threshold": 20.0,
            "confidence_threshold": 0.5,
            "model_type": "yolov5"
        }
    
    def load_video(self, file_path: str) -> VideoInfo:
        """
        Load video and create database record
        
        Args:
            file_path: Path to video file
            
        Returns:
            VideoInfo object
        """
        self.logger.info(f"Loading video: {file_path}")
        
        # Reset previous session
        self.reset()
        
        # Load video
        video_info = self.video_processor.open_video(file_path)
        self.current_video_info = video_info
        
        # Create database record
        with db_manager.session_scope() as session:
            db_video = self.video_repo.create(
                file_name=video_info.file_name,
                file_path=video_info.file_path,
                duration=video_info.duration,
                fps=video_info.fps,
                resolution=video_info.resolution,
                frame_count=video_info.frame_count,
                status='loaded'
            )
            self.current_video_id = db_video.id
            
        # Update traffic monitor
        self.traffic_monitor.traffic_data.video_id = self.current_video_id
        
        return video_info
    
    def process_video(self, save_to_db: bool = True):
        """
        Process loaded video with database storage
        
        Args:
            save_to_db: Whether to save results to database
        """
        if not self.current_video_info or not self.current_video_id:
            raise ValueError("No video loaded")
        
        self.is_processing = True
        self.should_stop = False
        
        # Update status to processing
        self.video_repo.update_status(self.current_video_id, 'processing')
        
        try:
            frame_count = 0
            start_time = time.time()
            
            for frame_id, timestamp, frame in self.video_processor.read_frames():
                if self.should_stop:
                    break
                
                # Process frame
                result = self._process_single_frame(frame_id, timestamp, frame)
                
                # Store to database batch
                if save_to_db:
                    self._add_to_batch(result)
                
                # Update minute aggregations (FR1.3.3)
                self._update_minute_aggregations(timestamp, result)
                
                # Draw results
                display_frame = self._draw_results(frame, result)
                
                # Callbacks
                if self.on_frame_processed:
                    self.on_frame_processed(display_frame, result)
                
                # Update statistics periodically
                if frame_count % 30 == 0:
                    if self.on_statistics_updated:
                        stats = self.get_current_statistics()
                        stats['current_timestamp'] = timestamp  # FR1.3.4
                        self.on_statistics_updated(stats)
                    
                    # Flush batches periodically
                    if save_to_db:
                        self._flush_batches()
                
                frame_count += 1
            
            # Processing complete
            processing_time = time.time() - start_time
            
            # Final flush
            if save_to_db:
                self._flush_batches()
                self._save_final_results(processing_time)
            
            # Update status
            self.video_repo.update_status(
                self.current_video_id, 
                'completed',
                processing_time
            )
            
            self.logger.info(f"Processing complete. Frames: {frame_count}, Time: {processing_time:.2f}s")
            
            # Callback
            if self.on_processing_complete:
                self.on_processing_complete(self.get_final_results())
                
        except Exception as e:
            self.logger.error(f"Error during processing: {e}")
            self.video_repo.update_status(self.current_video_id, 'failed')
            raise
        finally:
            self.is_processing = False
    
    def _process_single_frame(self, frame_id: int, timestamp: float, frame) -> DetectionResult:
        """Process single frame through all components"""
        
        # 1. Object Detection
        detections = self.object_detector.detect(frame)
        
        # 2. Vehicle Tracking
        detections = self.vehicle_tracker.update_tracks(detections, timestamp)
        
        # 3. Traffic Monitoring
        self.traffic_monitor.process_frame_detections(
            detections, self.vehicle_tracker, timestamp
        )
        
        # 4. Anomaly Detection
        anomalies = self.anomaly_detector.detect_anomalies(
            detections, self.vehicle_tracker, timestamp
        )
        
        # Create result
        result = DetectionResult(
            frame_id=frame_id,
            timestamp=timestamp
        )
        
        # Add detections
        for detection in detections:
            result.add_detection(detection)
        
        # Add alerts
        for anomaly in anomalies:
            result.add_alert(
                anomaly["type"],
                anomaly["message"],
                anomaly.get("object_id"),
                anomaly.get("position")
            )
            
            if self.on_anomaly_detected:
                self.on_anomaly_detected(anomaly)
        
        return result
    
    def _add_to_batch(self, result: DetectionResult):
        """Add results to batch for database storage"""
        
        # Add detection events (only crossed line events)
        for detection in result.detections:
            if detection.class_name in ["car", "motorbike", "truck", "bus"]:
                # Check if crossed line
                line_start, line_end, direction = self.traffic_monitor.virtual_line
                crossed = self.vehicle_tracker.check_line_crossing(
                    detection.id, line_start, line_end, direction
                )
                
                if crossed:
                    self.detection_batch.append({
                        "video_id": self.current_video_id,
                        "event_id": detection.id,
                        "frame_number": result.frame_id,
                        "timestamp_in_video": result.timestamp,
                        "object_type": detection.class_name,
                        "confidence_score": detection.confidence,
                        "bbox_x": detection.bbox[0],
                        "bbox_y": detection.bbox[1],
                        "bbox_width": detection.bbox[2] - detection.bbox[0],
                        "bbox_height": detection.bbox[3] - detection.bbox[1],
                        "crossed_line": True,
                        "crossing_direction": direction
                    })
        
        # Add anomaly events
        for alert in result.alerts:
            self.anomaly_batch.append({
                "video_id": self.current_video_id,
                "anomaly_type": alert["type"],
                "timestamp_in_video": result.timestamp,
                "object_id": alert.get("object_id"),
                "alert_message": alert["message"],
                "severity_level": "medium"  # Can be enhanced
            })
    
    def _flush_batches(self):
        """Flush batches to database"""
        if self.detection_batch:
            self.detection_repo.bulk_insert_detections(self.detection_batch)
            self.detection_batch = []
        
        if self.anomaly_batch:
            self.anomaly_repo.bulk_insert_anomalies(self.anomaly_batch)
            self.anomaly_batch = []
    
    def _update_minute_aggregations(self, timestamp: float, result: DetectionResult):
        """Update minute-based aggregations (FR1.3.3)"""
        minute = int(timestamp // 60)
        
        if minute not in self.minute_aggregations:
            self.minute_aggregations[minute] = {
                "car": 0, "motorbike": 0, "truck": 0, "bus": 0
            }
        
        # This is simplified - should track unique crossings
        for detection in result.detections:
            if detection.class_name in self.minute_aggregations[minute]:
                # Check if newly crossed
                if detection.id in self.vehicle_tracker.counted_ids:
                    if minute != self.current_minute:
                        self.minute_aggregations[minute][detection.class_name] += 1
        
        self.current_minute = minute
    
    def _save_final_results(self, processing_time: float):
        """Save final aggregated results to database"""
        
        # Save traffic data
        traffic_stats = self.traffic_monitor.get_statistics()
        
        self.traffic_repo.create_or_update(
            self.current_video_id,
            total_vehicles=traffic_stats["total_vehicles"],
            car_count=traffic_stats["vehicle_counts"]["car"],
            motorbike_count=traffic_stats["vehicle_counts"]["motorbike"],
            truck_count=traffic_stats["vehicle_counts"]["truck"],
            bus_count=traffic_stats["vehicle_counts"]["bus"],
            minute_aggregations=self.minute_aggregations,
            hour_aggregations=traffic_stats["hourly_counts"]
        )
    
    def _draw_results(self, frame, result: DetectionResult):
        """Draw results on frame"""
        overlays = {
            "boxes": [],
            "lines": [],
            "texts": []
        }
        
        # Add detection boxes
        for detection in result.detections:
            color = self._get_color_for_class(detection.class_name)
            overlays["boxes"].append({
                "bbox": detection.bbox,
                "label": f"{detection.class_name} ({detection.confidence:.2f})",
                "color": color,
                "thickness": 2
            })
        
        # Add virtual line
        line_start, line_end, _ = self.traffic_monitor.virtual_line
        overlays["lines"].append({
            "p1": line_start,
            "p2": line_end,
            "color": (0, 255, 0),
            "thickness": 2
        })
        
        # Add statistics
        stats = self.traffic_monitor.get_statistics()
        y_offset = 30
        
        # Total counts
        for vehicle_type, count in stats["vehicle_counts"].items():
            overlays["texts"].append({
                "content": f"{vehicle_type}: {count}",
                "position": (10, y_offset),
                "scale": 0.6,
                "color": (255, 255, 255),
                "thickness": 2
            })
            y_offset += 25
        
        # Current minute stats (FR1.3.3)
        current_minute = int(result.timestamp // 60)
        if current_minute in self.minute_aggregations:
            minute_total = sum(self.minute_aggregations[current_minute].values())
            overlays["texts"].append({
                "content": f"Phút {current_minute}: {minute_total} xe",
                "position": (10, y_offset + 10),
                "scale": 0.6,
                "color": (255, 255, 0),
                "thickness": 2
            })
        
        # Timestamp (FR1.3.4)
        time_str = f"Thời gian: {result.timestamp:.1f}s"
        overlays["texts"].append({
            "content": time_str,
            "position": (frame.shape[1] - 200, 30),
            "scale": 0.6,
            "color": (255, 255, 255),
            "thickness": 2
        })
        
        # Alerts
        if result.alerts:
            alert_y = frame.shape[0] - 100
            for i, alert in enumerate(result.alerts[:3]):
                overlays["texts"].append({
                    "content": alert["message"],
                    "position": (10, alert_y + i*25),
                    "scale": 0.6,
                    "color": (0, 0, 255),
                    "thickness": 2
                })
        
        return self.video_processor.draw_on_frame(frame, overlays)
    
    def _get_color_for_class(self, class_name: str) -> tuple:
        """Get color for object class"""
        colors = {
            "car": (255, 0, 0),      # Blue
            "motorbike": (0, 255, 0), # Green
            "truck": (0, 0, 255),     # Red
            "bus": (255, 255, 0),     # Cyan
            "person": (255, 0, 255),  # Magenta
            "animal": (128, 0, 128),  # Purple
            "obstacle": (0, 128, 255) # Orange
        }
        return colors.get(class_name, (128, 128, 128))
    
    def get_current_statistics(self) -> Dict:
        """Get current statistics with time info"""
        stats = {
            "traffic": self.traffic_monitor.get_statistics(),
            "anomalies": self.anomaly_detector.get_active_anomalies(),
            "tracker": {
                "active_tracks": len(self.vehicle_tracker.tracking_history),
                "total_counted": len(self.vehicle_tracker.counted_ids)
            },
            "minute_aggregations": self.minute_aggregations
        }
        return stats
    
    def get_final_results(self) -> Dict:
        """Get final processing results"""
        return {
            "video_info": self.current_video_info.__dict__ if self.current_video_info else {},
            "video_id": self.current_video_id,
            "traffic_data": self.traffic_monitor.traffic_data,
            "statistics": self.get_current_statistics(),
            "processing_time": self.traffic_monitor.traffic_data.processing_time
        }
    
    def pause(self):
        """Pause processing"""
        self.video_processor.state = ProcessingState.PAUSED
    
    def resume(self):
        """Resume processing"""
        self.video_processor.state = ProcessingState.PLAYING
    
    def stop(self):
        """Stop processing"""
        self.should_stop = True
    
    def reset(self):
        """Reset all components"""
        self.video_processor.close_video()
        self.vehicle_tracker.reset()
        self.traffic_monitor.reset()
        self.anomaly_detector.reset()
        self.current_video_info = None
        self.current_video_id = None
        self.is_processing = False
        self.should_stop = False
        self.detection_batch = []
        self.anomaly_batch = []
        self.minute_aggregations = {}
        self.current_minute = -1