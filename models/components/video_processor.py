# models/components/video_processor.py
import cv2
import numpy as np
from typing import Optional, Tuple, Generator
import logging
from pathlib import Path

from ..entities import VideoInfo, ProcessingState


class VideoProcessor:
    """
    Component chịu trách nhiệm xử lý video (VP)
    Chỉ đọc/ghi video, không có logic AI
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_info: Optional[VideoInfo] = None
        self.state = ProcessingState.IDLE
        self.current_frame_id = 0
        
    def open_video(self, file_path: str) -> VideoInfo:
        """
        Mở video và trả về thông tin
        
        Args:
            file_path: Đường dẫn video
            
        Returns:
            VideoInfo object
            
        Raises:
            ValueError: Nếu không mở được video
        """
        self.logger.info(f"Opening video: {file_path}")
        
        # Validate file exists
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Video file not found: {file_path}")
        
        # Close previous video if any
        if self.cap is not None:
            self.close_video()
        
        # Open new video
        self.cap = cv2.VideoCapture(str(file_path))
        
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {file_path}")
        
        # Extract video info
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
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
        
        self.logger.info(f"Video opened successfully: {self.video_info.resolution} @ {fps}fps")
        
        return self.video_info
    
    def read_frame(self) -> Optional[Tuple[int, float, np.ndarray]]:
        """
        Đọc một frame từ video
        
        Returns:
            Tuple (frame_id, timestamp, frame) hoặc None nếu hết video
        """
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
    
    def read_frames(self, batch_size: int = 1) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """
        Generator để đọc frames theo batch
        
        Args:
            batch_size: Số frame mỗi batch
            
        Yields:
            Tuple (frame_id, timestamp, frame)
        """
        while True:
            result = self.read_frame()
            if result is None:
                break
            yield result
    
    def seek_frame(self, frame_number: int) -> bool:
        """
        Nhảy đến frame cụ thể
        
        Args:
            frame_number: Frame number to seek
            
        Returns:
            True nếu thành công
        """
        if self.cap is None:
            return False
        
        if 0 <= frame_number < self.video_info.frame_count:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.current_frame_id = frame_number
            return True
        
        return False
    
    def get_current_position(self) -> Tuple[int, float]:
        """
        Lấy vị trí hiện tại
        
        Returns:
            Tuple (frame_number, timestamp)
        """
        if self.cap is None or self.video_info is None:
            return 0, 0.0
        
        frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        timestamp = frame_pos / self.video_info.fps
        
        return frame_pos, timestamp
    
    def draw_on_frame(self, frame: np.ndarray, 
                     overlays: dict) -> np.ndarray:
        """
        Vẽ overlays lên frame (boxes, text, lines...)
        
        Args:
            frame: Original frame
            overlays: Dict chứa thông tin cần vẽ
            
        Returns:
            Frame với overlays
        """
        display_frame = frame.copy()
        
        # Draw bounding boxes
        if 'boxes' in overlays:
            for box in overlays['boxes']:
                x1, y1, x2, y2 = box['bbox']
                color = box.get('color', (0, 255, 0))
                thickness = box.get('thickness', 2)
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, thickness)
                
                # Draw label if exists
                if 'label' in box:
                    cv2.putText(display_frame, box['label'], 
                              (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                              0.5, color, 2)
        
        # Draw lines
        if 'lines' in overlays:
            for line in overlays['lines']:
                cv2.line(display_frame, line['p1'], line['p2'], 
                        line.get('color', (0, 255, 0)), 
                        line.get('thickness', 2))
        
        # Draw text
        if 'texts' in overlays:
            for text in overlays['texts']:
                cv2.putText(display_frame, text['content'],
                          text['position'], cv2.FONT_HERSHEY_SIMPLEX,
                          text.get('scale', 0.5),
                          text.get('color', (255, 255, 255)),
                          text.get('thickness', 1))
        
        return display_frame
    
    def save_frame(self, frame: np.ndarray, output_path: str) -> bool:
        """
        Lưu frame ra file
        
        Args:
            frame: Frame to save
            output_path: Output file path
            
        Returns:
            True nếu thành công
        """
        try:
            cv2.imwrite(output_path, frame)
            return True
        except Exception as e:
            self.logger.error(f"Error saving frame: {e}")
            return False
    
    def close_video(self):
        """Đóng video và giải phóng resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.video_info = None
        self.state = ProcessingState.IDLE
        self.current_frame_id = 0
        
        self.logger.info("Video closed")
    
    def __del__(self):
        """Destructor - đảm bảo release resources"""
        self.close_video()