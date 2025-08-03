# models/components/video_processor.py
import cv2
import numpy as np
from typing import Optional, Tuple, Generator
import logging
from pathlib import Path
import threading
import queue
import time

from ..entities import VideoInfo, ProcessingState


class VideoProcessor:
    """
    Thread-safe Video Processor component
    Fixes crash issues with proper thread handling and memory management
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_info: Optional[VideoInfo] = None
        self.state = ProcessingState.IDLE
        self.current_frame_id = 0
        
        # Thread safety
        self._lock = threading.Lock()
        self._frame_queue = queue.Queue(maxsize=30)  # Buffer frames
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader = threading.Event()
        
    def open_video(self, file_path: str) -> VideoInfo:
        """
        Open video with proper error handling and thread safety
        """

        from utils import config_manager  # import trực tiếp để dùng config

        # Đọc thread_count từ config (mặc định = 1)
        thread_count = config_manager.get("video_processing.max_processing_threads", 1)
        self.logger.info(f"Opening video: {file_path}")
        
        # Validate file exists
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Video file not found: {file_path}")
        
        # Close previous video if any
        if self.cap is not None:
            self.close_video()
        
        # Thread-safe video opening
        with self._lock:
            # Use specific codec to avoid FFmpeg issues
            self.cap = cv2.VideoCapture(str(file_path), cv2.CAP_FFMPEG)

            # Giới hạn số thread decode
            if thread_count <= 0:
                thread_count = 1  # fallback
            
            # Set threading mode to avoid pthread issues
            # Set threading mode nếu hằng số có tồn tại
            if hasattr(cv2, "CAP_PROP_THREAD_COUNT"):
                self.cap.set(cv2.CAP_PROP_THREAD_COUNT, thread_count)
            else:
                self.logger.warning(
                    "CAP_PROP_THREAD_COUNT not supported; using global setNumThreads()"
                )
                cv2.setNumThreads(thread_count)
            
            # Reduce buffer size to avoid memory issues
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not self.cap.isOpened():
                raise ValueError(f"Cannot open video: {file_path}")
            
            # Extract video info safely
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or fps > 120:  # Sanity check
                fps = 30.0  # Default fallback
                
            frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Validate dimensions
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid video dimensions: {width}x{height}")
            
            duration = frame_count / fps if fps > 0 else 0
            
            self.video_info = VideoInfo(
                file_name=path.name,
                file_path=str(file_path),
                fps=fps,
                frame_count=frame_count,
                width=width,
                height=height,
                duration=duration
            )
            
            self.state = ProcessingState.IDLE
            self.current_frame_id = 0
            
        self.logger.info(f"Video opened: {width}x{height} @ {fps}fps, {frame_count} frames")
        
        return self.video_info
    
    def start_reader_thread(self):
        """Start background thread for reading frames"""
        if self._reader_thread is None or not self._reader_thread.is_alive():
            self._stop_reader.clear()
            self._reader_thread = threading.Thread(target=self._frame_reader_worker)
            self._reader_thread.daemon = True
            self._reader_thread.start()
            self.logger.debug("Frame reader thread started")
    
    def _frame_reader_worker(self):
        """Worker thread that reads frames in background"""
        while not self._stop_reader.is_set():
            try:
                # Don't read if queue is full
                if self._frame_queue.full():
                    time.sleep(0.01)
                    continue
                
                # Read frame with lock
                with self._lock:
                    if self.cap is None or not self.cap.isOpened():
                        break
                        
                    ret, frame = self.cap.read()
                    
                    if not ret:
                        self.state = ProcessingState.COMPLETED
                        break
                    
                    frame_id = self.current_frame_id
                    timestamp = frame_id / self.video_info.fps if self.video_info else 0
                    self.current_frame_id += 1
                
                # Put frame in queue (outside lock to avoid blocking)
                try:
                    self._frame_queue.put((frame_id, timestamp, frame), timeout=1.0)
                except queue.Full:
                    self.logger.warning("Frame queue full, dropping frame")
                    
            except Exception as e:
                self.logger.error(f"Error in frame reader: {e}")
                break
    
    def read_frame(self) -> Optional[Tuple[int, float, np.ndarray]]:
        """
        Read frame from queue (thread-safe)
        """
        # Check if video is open
        if self.cap is None or not self.cap.isOpened():
            return None
            
        # If state is PLAYING, use reader thread
        if self.state == ProcessingState.PLAYING and (self._reader_thread is None or not self._reader_thread.is_alive()):
            self.start_reader_thread()
        
        try:
            # Try to get frame from queue
            if not self._frame_queue.empty():
                return self._frame_queue.get(timeout=0.1)
            else:
                # Direct read if queue is empty
                with self._lock:
                    if self.cap is None or not self.cap.isOpened():
                        return None
                    
                    ret, frame = self.cap.read()
                    
                    if not ret:
                        self.state = ProcessingState.COMPLETED
                        return None
                    
                    frame_id = self.current_frame_id
                    timestamp = frame_id / self.video_info.fps if self.video_info else 0
                    self.current_frame_id += 1
                    
                    return frame_id, timestamp, frame
                    
        except queue.Empty:
            return None
        except Exception as e:
            self.logger.error(f"Error reading frame: {e}")
            return None
    
    def read_frames(self, batch_size: int = 1) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """
        Generator for reading frames in batches
        """
        count = 0
        while count < batch_size or batch_size <= 0:
            result = self.read_frame()
            if result is None:
                break
            yield result
            count += 1
    
    def seek_frame(self, frame_number: int) -> bool:
        """
        Seek to specific frame (thread-safe)
        """
        with self._lock:
            if self.cap is None:
                return False
            
            if 0 <= frame_number < self.video_info.frame_count:
                # Clear frame queue when seeking
                while not self._frame_queue.empty():
                    try:
                        self._frame_queue.get_nowait()
                    except queue.Empty:
                        break
                
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                self.current_frame_id = frame_number
                return True
            
            return False
    
    def get_current_position(self) -> Tuple[int, float]:
        """
        Get current position (thread-safe)
        """
        with self._lock:
            if self.cap is None or self.video_info is None:
                return 0, 0.0
            
            frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            timestamp = frame_pos / self.video_info.fps
            
            return frame_pos, timestamp
    
    def draw_on_frame(self, frame: np.ndarray, overlays: dict) -> np.ndarray:
        """
        Draw overlays on frame (detections, text, etc.)
        """
        if frame is None:
            return None
            
        # Make a copy to avoid modifying original
        display_frame = frame.copy()
        
        try:
            # Draw bounding boxes
            if 'boxes' in overlays:
                for box in overlays['boxes']:
                    x1, y1, x2, y2 = box['bbox']
                    color = box.get('color', (0, 255, 0))
                    thickness = box.get('thickness', 2)
                    
                    # Ensure coordinates are valid
                    x1, y1 = max(0, int(x1)), max(0, int(y1))
                    x2, y2 = min(frame.shape[1]-1, int(x2)), min(frame.shape[0]-1, int(y2))
                    
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, thickness)
                    
                    # Draw label if exists
                    if 'label' in box:
                        label = str(box['label'])
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.5
                        font_thickness = 1
                        
                        # Get text size
                        (text_width, text_height), _ = cv2.getTextSize(
                            label, font, font_scale, font_thickness
                        )
                        
                        # Draw background rectangle for text
                        cv2.rectangle(display_frame, 
                                    (x1, y1 - text_height - 4),
                                    (x1 + text_width + 4, y1),
                                    color, -1)
                        
                        # Draw text
                        cv2.putText(display_frame, label,
                                  (x1 + 2, y1 - 2),
                                  font, font_scale, (255, 255, 255), font_thickness)
            
            # Draw lines (e.g., virtual counting lines)
            if 'lines' in overlays:
                for line in overlays['lines']:
                    if 'pt1' in line and 'pt2' in line:
                        pt1 = tuple(map(int, line['pt1']))
                        pt2 = tuple(map(int, line['pt2']))
                        color = line.get('color', (255, 0, 0))
                        thickness = line.get('thickness', 2)
                        cv2.line(display_frame, pt1, pt2, color, thickness)
            
            # Draw text overlays
            if 'texts' in overlays:
                for text in overlays['texts']:
                    content = str(text['content'])
                    pos = tuple(map(int, text['position']))
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = text.get('scale', 0.7)
                    color = text.get('color', (255, 255, 255))
                    thickness = text.get('thickness', 2)
                    
                    # Draw with background for better visibility
                    if text.get('background', True):
                        (text_width, text_height), _ = cv2.getTextSize(
                            content, font, font_scale, thickness
                        )
                        cv2.rectangle(display_frame,
                                    (pos[0] - 2, pos[1] - text_height - 2),
                                    (pos[0] + text_width + 2, pos[1] + 2),
                                    (0, 0, 0), -1)
                    
                    cv2.putText(display_frame, content, pos,
                              font, font_scale, color, thickness)
            
        except Exception as e:
            self.logger.error(f"Error drawing overlays: {e}")
            return frame
        
        return display_frame
    
    def close_video(self):
        """
        Close video and clean up resources
        """
        self.logger.info("Closing video...")
        
        # Stop reader thread
        if self._reader_thread and self._reader_thread.is_alive():
            self._stop_reader.set()
            self._reader_thread.join(timeout=2.0)
        
        # Clear queue
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break
        
        # Close video capture
        with self._lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            self.video_info = None
            self.state = ProcessingState.IDLE
            self.current_frame_id = 0
        
        self.logger.info("Video closed successfully")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.close_video()
        except:
            pass