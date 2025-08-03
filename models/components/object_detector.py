# models/components/object_detector.py
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

from ..entities import Detection


class ObjectDetector:
    """
    Component wrap YOLO model (OD)
    Supports YOLOv8 (using ultralytics)
    """
    
    def __init__(self, model_path: Optional[str] = None, 
                 model_type: str = "yolov8",
                 confidence_threshold: float = 0.5):
        self.logger = logging.getLogger(__name__)
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.model = None
        
        # Class mapping cho traffic use case
        # YOLOv8 COCO class names to our simplified names
        self.class_mapping = {
            "car": "car",
            "truck": "truck", 
            "bus": "bus",
            "motorcycle": "motorbike",
            "person": "person",
            "bicycle": "bicycle",
            "dog": "dog",
            "cat": "cat",
            # Add more mappings as needed
        }
        
        # Load model
        if model_path:
            self.load_model(model_path)
        else:
            self.load_default_model()
    
    def load_default_model(self):
        """Load default pretrained model"""
        try:
            from ultralytics import YOLO
            
            # Use YOLOv8n (nano) as default - fastest and smallest
            self.model = YOLO('yolov8n.pt')
            self.logger.info("Loaded default YOLOv8n model")
                
        except Exception as e:
            self.logger.error(f"Error loading default model: {e}")
            raise
    
    def load_model(self, model_path: str):
        """Load custom model"""
        try:
            from ultralytics import YOLO
            
            path = Path(model_path)
            if not path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            self.model = YOLO(model_path)
            self.logger.info(f"Loaded custom model from {model_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects trong frame
        
        Args:
            frame: Input frame (BGR format từ OpenCV)
            
        Returns:
            List of Detection objects
        """
        if self.model is None:
            self.logger.warning("No model loaded")
            return []
        
        try:
            # Run inference với YOLOv8
            results = self.model(frame, conf=self.confidence_threshold)
            
            # Process results
            detections = self._process_yolov8_results(results)
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Error during detection: {e}")
            return []
    
    def _process_yolov8_results(self, results) -> List[Detection]:
        """Process YOLOv8 results"""
        detections = []
        
        # results[0] contains the first (and only) image's results
        if len(results) == 0:
            return detections
            
        result = results[0]
        
        # Get boxes, classes, and confidences
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()  # Bounding boxes
            classes = result.boxes.cls.cpu().numpy()  # Class indices
            confidences = result.boxes.conf.cpu().numpy()  # Confidence scores
            
            # Get class names
            names = result.names  # Dictionary mapping class index to name
            
            for i in range(len(boxes)):
                # Extract info
                x1, y1, x2, y2 = boxes[i]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                confidence = float(confidences[i])
                class_idx = int(classes[i])
                class_name = names[class_idx]
                
                # Map to our classes
                mapped_class = self.class_mapping.get(class_name, class_name)
                
                # Create Detection
                detection = Detection(
                    id="",  # Will be assigned by tracker
                    class_name=mapped_class,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2)
                )
                
                detections.append(detection)
        
        return detections
    
    def get_supported_classes(self) -> List[str]:
        """Get list of supported object classes"""
        return list(self.class_mapping.values())
    
    def set_confidence_threshold(self, threshold: float):
        """Update confidence threshold"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        self.logger.info(f"Updated confidence threshold to {self.confidence_threshold}")