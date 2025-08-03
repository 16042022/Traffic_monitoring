"""
Video Analysis Orchestrator - Điều phối phân tích TỰ ĐỘNG toàn bộ video
Thay đổi chính: Xử lý TOÀN BỘ video từ đầu đến cuối khi nhấn Start
"""

import cv2
import numpy as np
from datetime import datetime, timedelta
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
import logging
from dataclasses import dataclass
from threading import Thread, Event
import queue

from models.components.video_processor import VideoProcessor
from models.components.object_detector import ObjectDetector
from models.components.vehicle_tracker import VehicleTracker
from models.components.traffic_monitor import TrafficMonitor
from models.components.anomaly_detector import AnomalyDetector
from models.repositories.video_repository import VideoRepository
from models.repositories.detection_event_repository import DetectionEventRepository
from models.repositories.traffic_data_repository import TrafficDataRepository
from models.repositories.anomaly_event_repository import AnomalyEventRepository
from utils.config_manager import config_manager
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class AnalysisProgress:
    """Thông tin tiến trình phân tích"""
    current_frame: int
    total_frames: int
    current_time: float  # Timestamp trong video (seconds)
    total_duration: float  # Tổng thời lượng video (seconds)
    percent_complete: float
    fps: float
    status: str  # 'analyzing', 'paused', 'completed', 'error'
    
@dataclass
class RealTimeStats:
    """Thống kê thời gian thực"""
    total_vehicles: int
    vehicles_by_type: Dict[str, int]
    current_minute_count: int
    anomalies_detected: int
    processing_fps: float
    video_timestamp: str  # HH:MM:SS format

class VideoAnalysisOrchestrator:
    """
    Điều phối toàn bộ quá trình phân tích video TỰ ĐỘNG
    """
    
    # Trong phần __init__, thêm reset() để đảm bảo state clean
    def __init__(self):
        """Initialize orchestrator với tất cả components"""
        logger.info("Initializing VideoAnalysisOrchestrator...")
        
        # Load config using global config_manager instance
        self.config = config_manager.config
        
        # Initialize components
        self.video_processor = VideoProcessor()
        self.object_detector = ObjectDetector()
        self.vehicle_tracker = VehicleTracker()
        self.traffic_monitor = TrafficMonitor(self.config.get('virtual_line'))
        self.anomaly_detector = AnomalyDetector()
        
        # Initialize repositories
        self.video_repo = VideoRepository()
        self.detection_event_repo = DetectionEventRepository()
        self.traffic_data_repo = TrafficDataRepository()
        self.anomaly_event_repo = AnomalyEventRepository()
        
        # Analysis state
        self.current_video_id: Optional[int] = None
        self.is_analyzing = False
        self.is_paused = False
        self.should_stop = False
        self.analysis_thread: Optional[Thread] = None
        
        # Progress tracking
        self.progress_queue = queue.Queue()
        self.stats_queue = queue.Queue()
        self.frame_queue = queue.Queue(maxsize=5)  # Buffer frames
        
        # Callbacks
        self.progress_callback: Optional[Callable] = None
        self.stats_callback: Optional[Callable] = None
        self.frame_callback: Optional[Callable] = None
        
        # Initialize counted IDs set
        self._counted_ids = set()
        
        logger.info("VideoAnalysisOrchestrator initialized successfully")
    
    def set_callbacks(self, 
                     progress_callback: Optional[Callable] = None,
                     stats_callback: Optional[Callable] = None,
                     frame_callback: Optional[Callable] = None):
        """Set callback functions để update UI"""
        self.progress_callback = progress_callback
        self.stats_callback = stats_callback
        self.frame_callback = frame_callback
    
    # Trong start_full_video_analysis, đảm bảo reset state trước
    def start_full_video_analysis(self, video_path: str) -> int:
        """
        BẮT ĐẦU PHÂN TÍCH TỰ ĐỘNG TOÀN BỘ VIDEO
        
        Args:
            video_path: Đường dẫn tới file video
            
        Returns:
            video_id: ID của video trong database
        """
        if self.is_analyzing:
            logger.warning("Analysis already in progress")
            return -1
        
        try:
            # Reset state trước khi bắt đầu phân tích mới
            self.reset()
            
            # Open video to get metadata
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video: {video_path}")
                return -1
            
            # Get video metadata
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0.0
            resolution = f"{width}x{height}"
            
            cap.release()
            
            # Create video record in database with all required fields
            video = self.video_repo.create(
                file_name=Path(video_path).name,
                file_path=video_path,
                upload_timestamp=datetime.now(),
                duration=duration,
                fps=fps,
                resolution=resolution,
                frame_count=frame_count,
                status='processing'
            )
            
            # QUAN TRỌNG: Lưu video ID đúng cách
            if video and hasattr(video, 'id'):
                self.current_video_id = video.id
                logger.info(f"Created video record with ID: {self.current_video_id}")
                logger.info(f"Type of video_id: {type(self.current_video_id)}")
            else:
                logger.error("Failed to create video record or get video ID")
                return -1
                
            # Reset state
            self.is_analyzing = True
            self.is_paused = False
            self.should_stop = False
            
            # Clear queues
            while not self.progress_queue.empty():
                self.progress_queue.get()
            while not self.stats_queue.empty():
                self.stats_queue.get()
            while not self.frame_queue.empty():
                self.frame_queue.get()
            
            # Start analysis thread 
            self.analysis_thread = Thread(
                target=self._analyze_video_worker,
                args=(video_path, ), 
                daemon=True
            )
            self.analysis_thread.start()
            
            logger.info(f"Started automatic analysis for video: {video_path}, video_id: {self.current_video_id}")
            return self.current_video_id
            
        except Exception as e:
            logger.error(f"Error starting video analysis: {e}")
            self.is_analyzing = False
            return -1
    
    def _analyze_video_worker(self, video_path: str):
        """
        Worker thread - XỬ LÝ TOÀN BỘ VIDEO TỪ ĐẦU ĐẾN CUỐI
        """
        try:
            # Open video
            try:
                video_info = self.video_processor.open_video(video_path)
                if not video_info:
                    raise Exception("Failed to load video")
            except Exception as e:
                logger.error(f"Error opening video: {e}")
                raise Exception(f"Failed to load video: {str(e)}")
            
            # Get video info from video processor
            video_info = self.video_processor.video_info
            if not video_info:
                raise Exception("Video info not available")
                
            total_frames = video_info.frame_count
            fps = video_info.fps
            total_duration = video_info.duration
            
            # Initialize tracking
            frame_count = 0
            self._start_time = time.time()
            start_time = time.time()
            last_minute = 0
            minute_counts = {}  # Đếm xe theo từng phút
            
            # Process each frame của video
            while not self.should_stop:
                # Check if paused
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)
                
                # Read next frame
                frame_data = self.video_processor.read_frame()
                if frame_data is None:  # End of video
                    break
                
                frame_id, timestamp, frame = frame_data
                frame_count = frame_id + 1
                current_time = timestamp
                current_minute = int(current_time / 60)
                
                # 1. OBJECT DETECTION
                detections = self.object_detector.detect(frame)
                
                # 2. VEHICLE TRACKING
                tracked_objects = self.vehicle_tracker.update_tracks(detections, current_time)
                
                # 3. TRAFFIC MONITORING - Đếm xe qua đường ảo
                crossing_events = []
                
                # Check which vehicles crossed in this frame
                for detection in tracked_objects:
                    # Check if vehicle crossed the line
                    if detection.id and detection.id not in self._counted_ids:
                        if self.vehicle_tracker.check_line_crossing(
                            detection.id,
                            self.traffic_monitor.virtual_line[0],  # line start
                            self.traffic_monitor.virtual_line[1],  # line end  
                            self.traffic_monitor.virtual_line[2]   # direction
                        ):
                            crossing_events.append({
                                'vehicle_type': detection.class_name,
                                'bbox': detection.bbox,
                                'track_id': detection.id,
                                'confidence': detection.confidence,
                                'direction': self.traffic_monitor.virtual_line[2]
                            })
                            self._counted_ids.add(detection.id)
                
                # Lưu các sự kiện đếm xe vào database
                for event in crossing_events:
                    # LOG để debug
                    if frame_count % 100 == 0:  # Log mỗi 100 frames
                        logger.debug(f"Creating detection event with video_id: {self.current_video_id}")
                        
                    detection_event = self.detection_event_repo.create(
                        video_id=self.current_video_id,
                        event_id=event.get('track_id', f"evt_{frame_count}"),  # Dùng event_id
                        frame_number=frame_count,
                        timestamp_in_video=current_time,
                        object_type=event['vehicle_type'],
                        bbox_x=int(event['bbox'][0]),
                        bbox_y=int(event['bbox'][1]),
                        bbox_width=int(event['bbox'][2]),
                        bbox_height=int(event['bbox'][3]),
                        confidence_score=event.get('confidence', 0.9),
                        crossed_line=True,
                        crossing_direction=event.get('direction', 'unknown'),
                        lane_id=event.get('lane_id', 'main')
                    )
                
                # 4. ANOMALY DETECTION
                anomalies = self.anomaly_detector.detect_anomalies(
                    tracked_objects,
                    self.vehicle_tracker,
                    current_time
                )
                
                # Lưu anomaly events
                for anomaly in anomalies:
                    # Kiểm tra video_id trước khi tạo anomaly event
                    if not self.current_video_id:
                        logger.error(f"current_video_id is None when creating anomaly event!")
                        logger.error(f"Frame: {frame_count}, Time: {current_time}")
                        logger.error(f"Anomaly: {anomaly}")
                        continue
                        
                    try:
                        # LOG chi tiết để debug
                        logger.debug(f"Creating anomaly event with video_id: {self.current_video_id} for anomaly: {anomaly['type']}")
                        
                        self.anomaly_event_repo.create(
                            video_id=self.current_video_id,
                            anomaly_type=anomaly['type'],
                            severity_level=anomaly.get('severity', 'medium'),
                            timestamp_in_video=anomaly.get('timestamp', current_time),
                            duration=anomaly.get('duration', 0.0),
                            detection_area=anomaly.get('area', 'main'),
                            bbox_x=int(anomaly['bbox'][0]) if 'bbox' in anomaly else None,
                            bbox_y=int(anomaly['bbox'][1]) if 'bbox' in anomaly else None,
                            bbox_width=int(anomaly['bbox'][2]) if 'bbox' in anomaly else None,
                            bbox_height=int(anomaly['bbox'][3]) if 'bbox' in anomaly else None,
                            object_id=str(anomaly.get('object_id', '')),
                            object_class=anomaly.get('object_class', 'unknown'),
                            confidence_score=anomaly.get('confidence', 0.9),
                            alert_status='active',
                            alert_message=anomaly.get('message', f"Detected {anomaly['type']} anomaly")
                        )
                    except Exception as e:
                        logger.error(f"Failed to create anomaly event: {e}")
                        logger.error(f"video_id: {self.current_video_id}, anomaly: {anomaly}")
                
                # 5. OVERLAY RESULTS on frame
                annotated_frame = self._overlay_results(
                    frame, 
                    tracked_objects, 
                    anomalies
                )
                
                # 6. UPDATE STATISTICS
                stats = self.traffic_monitor.get_statistics()
                
                # Tính thống kê theo phút
                if current_minute > last_minute:
                    minute_counts[last_minute] = stats['total_vehicles']
                    last_minute = current_minute
                
                # Calculate processing FPS
                elapsed = time.time() - start_time
                processing_fps = frame_count / elapsed if elapsed > 0 else 0
                
                # 7. SEND UPDATES to UI
                # Progress update
                progress = AnalysisProgress(
                    current_frame=frame_count,
                    total_frames=total_frames,
                    current_time=current_time,
                    total_duration=total_duration,
                    percent_complete=(frame_count / total_frames * 100) if total_frames > 0 else 0,
                    fps=processing_fps,
                    status='analyzing'
                )
                self.progress_queue.put(progress)
                
                # Stats update
                vehicle_counts = stats.get('vehicle_counts', {})
                real_time_stats = RealTimeStats(
                    total_vehicles=stats['total_vehicles'],
                    vehicles_by_type=vehicle_counts,
                    current_minute_count=len([e for e in crossing_events]),
                    anomalies_detected=len(anomalies),
                    processing_fps=processing_fps,
                    video_timestamp=str(timedelta(seconds=int(current_time)))
                )
                self.stats_queue.put(real_time_stats)
                
                # Frame update (skip some frames to not overwhelm UI)
                if frame_count % 3 == 0:  # Show every 3rd frame
                    try:
                        self.frame_queue.put_nowait(annotated_frame)
                    except queue.Full:
                        pass  # Skip if queue is full
                
                # Notify callbacks
                if self.progress_callback:
                    self.progress_callback(progress)
                if self.stats_callback:
                    self.stats_callback(real_time_stats)
                if self.frame_callback and frame_count % 3 == 0:
                    self.frame_callback(annotated_frame)
            
            # ANALYSIS COMPLETED - Tổng hợp kết quả cuối cùng
            self._finalize_analysis()
            
        except Exception as e:
            logger.error(f"Error in video analysis worker: {e}")
            self._handle_analysis_error(str(e))
        finally:
            self.is_analyzing = False
            self.video_processor.close_video()
    
    def _overlay_results(self, frame: np.ndarray, 
                            tracked_objects: List[Any],  # List of Detection objects
                            anomalies: List[Dict]) -> np.ndarray:
        """Vẽ kết quả detection lên frame"""
        annotated = frame.copy()
        
        # Draw tracked vehicles
        for obj in tracked_objects:
            # obj is a Detection object, not a dict
            bbox = obj.bbox
            track_id = obj.id
            obj_type = obj.class_name
            
            # Color based on type and anomaly status
            color = (0, 255, 0)  # Green for normal vehicles
            
            # Check if this object has any anomaly
            # Anomaly có thể có object_id thay vì track_id
            if any(a.get('object_id') == track_id or a.get('track_id') == track_id 
                for a in anomalies):
                color = (0, 0, 255)  # Red for anomalies
            
            # Draw bbox
            cv2.rectangle(annotated, 
                        (int(bbox[0]), int(bbox[1])),
                        (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])),
                        color, 2)
            
            # Draw label
            label = f"{obj_type}"
            if track_id:
                label += f" #{track_id}"
            cv2.putText(annotated, label,
                    (int(bbox[0]), int(bbox[1] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw virtual line
        line_config = config_manager.get('virtual_line')
        if line_config:
            cv2.line(annotated,
                    (line_config['p1_x'], line_config['p1_y']),
                    (line_config['p2_x'], line_config['p2_y']),
                    (255, 255, 0), 2)
        
        # Draw anomaly alerts
        y_offset = 30
        for anomaly in anomalies:
            alert_text = f"CẢNH BÁO: {anomaly['type']} - {anomaly.get('severity', 'medium')}"
            cv2.putText(annotated, alert_text,
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_offset += 30
        
        return annotated
    
    def _finalize_analysis(self):
        """Hoàn tất phân tích và lưu kết quả tổng hợp"""
        try:
            # Log current video ID để debug
            logger.info(f"Finalizing analysis for video_id: {self.current_video_id}")
            
            # Get final statistics
            final_stats = self.traffic_monitor.get_statistics()
            
            # Update video record - cần đảm bảo video_id đúng
            if self.current_video_id:
                self.video_repo.update(
                    self.current_video_id,  # Đã là integer ID
                    status='completed',
                    processing_timestamp=datetime.now(),
                    processing_duration=time.time() - self._start_time if hasattr(self, '_start_time') else 0
                )
                
                # Save aggregated traffic data
                stats = final_stats.get('vehicle_counts', {})
                self.traffic_data_repo.create_or_update(
                    self.current_video_id,
                    total_vehicles=final_stats.get('total_vehicles', 0),
                    car_count=stats.get('car', 0),
                    motorbike_count=stats.get('motorbike', 0),
                    truck_count=stats.get('truck', 0),
                    bus_count=stats.get('bus', 0),
                    avg_speed=0.0,  # Not implemented yet
                    congestion_level='low'  # Simplified
                )
            else:
                logger.error("No current_video_id when finalizing analysis!")
            
            # Get current position from video processor
            current_pos, current_timestamp = self.video_processor.get_current_position()
            
            # Send completion notification
            progress = AnalysisProgress(
                current_frame=current_pos,
                total_frames=self.video_processor.video_info.frame_count if self.video_processor.video_info else 0,
                current_time=current_timestamp,
                total_duration=self.video_processor.video_info.duration if self.video_processor.video_info else 0,
                percent_complete=100,
                fps=0,
                status='completed'
            )
            
            if self.progress_callback:
                self.progress_callback(progress)
            
            logger.info(f"Video analysis completed. Total vehicles: {final_stats.get('total_vehicles', 0)}")
            
        except Exception as e:
            logger.error(f"Error finalizing analysis: {e}")
    
    def _handle_analysis_error(self, error_msg: str):
        """Xử lý lỗi trong quá trình phân tích"""
        try:
            # Update video status
            if self.current_video_id:
                self.video_repo.update(
                    self.current_video_id,
                    status='error',
                    error_message=error_msg
                )
            
            # Send error notification
            progress = AnalysisProgress(
                current_frame=0,
                total_frames=0,
                current_time=0,
                total_duration=0,
                percent_complete=0,
                fps=0,
                status='error'
            )
            
            if self.progress_callback:
                self.progress_callback(progress)
                
        except Exception as e:
            logger.error(f"Error handling analysis error: {e}")
    
    def pause_analysis(self):
        """Tạm dừng phân tích"""
        if self.is_analyzing and not self.is_paused:
            self.is_paused = True
            logger.info("Analysis paused")
    
    def resume_analysis(self):
        """Tiếp tục phân tích"""
        if self.is_analyzing and self.is_paused:
            self.is_paused = False
            logger.info("Analysis resumed")
    
    def stop_analysis(self):
        """Dừng phân tích hoàn toàn"""
        if self.is_analyzing:
            self.should_stop = True
            self.is_paused = False
            if self.analysis_thread:
                self.analysis_thread.join(timeout=5)
            self.is_analyzing = False
            logger.info("Analysis stopped")
    
    def get_current_progress(self) -> Optional[AnalysisProgress]:
        """Lấy tiến trình hiện tại"""
        try:
            return self.progress_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_current_stats(self) -> Optional[RealTimeStats]:
        """Lấy thống kê hiện tại"""
        try:
            return self.stats_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Lấy frame hiện tại đã annotated"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def is_processing(self) -> bool:
        """Check if currently processing"""
        return self.is_analyzing
    
    def get_analysis_results(self, video_id: int) -> Dict[str, Any]:
        """Lấy kết quả phân tích đã lưu"""
        try:
            # Get video info
            video = self.video_repo.get_by_id(video_id)
            if not video:
                return {}
            
            # Get traffic statistics
            traffic_stats = self.traffic_data_repo.get_by_video_id(video_id)
            
            # Get anomaly summary  
            anomaly_summary = self.anomaly_event_repo.get_summary_by_video(video_id)
            
            # Get time-based statistics
            time_stats = self.detection_event_repo.get_time_based_statistics(
                video_id, 
                interval_minutes=1
            )
            
            # Format traffic statistics
            traffic_statistics = {}
            if traffic_stats:
                traffic_statistics = {
                    'total_vehicles': traffic_stats.total_vehicles,
                    'car_count': traffic_stats.car_count,
                    'motorbike_count': traffic_stats.motorbike_count,
                    'truck_count': traffic_stats.truck_count,
                    'bus_count': traffic_stats.bus_count,
                    'avg_speed': traffic_stats.avg_speed,
                    'congestion_level': traffic_stats.congestion_level
                }
            
            return {
                'video_info': video,
                'traffic_statistics': traffic_statistics,
                'anomaly_summary': anomaly_summary,
                'time_based_stats': time_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting analysis results: {e}")
            return {}
        
    # Thêm method này vào class VideoAnalysisOrchestrator
    def reset(self):
        """Reset all tracking variables và state"""
        logger.info("Resetting VideoAnalysisOrchestrator state")
        
        # Reset video ID và tracking
        self.current_video_id = None
        self.is_analyzing = False
        self.is_paused = False
        self.should_stop = False
        
        # Reset counted IDs cho traffic monitor
        if hasattr(self, '_counted_ids'):
            self._counted_ids.clear()
        else:
            self._counted_ids = set()
        
        # Reset components
        self.vehicle_tracker.reset()
        self.traffic_monitor.reset()
        self.anomaly_detector.reset()
        
        # Clear queues
        while not self.progress_queue.empty():
            self.progress_queue.get()
        while not self.stats_queue.empty():
            self.stats_queue.get()
        while not self.frame_queue.empty():
            self.frame_queue.get()
            
        logger.info("Reset completed")