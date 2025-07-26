# models/components/object_detector.py
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
import torch
from pathlib import Path

from ..entities import Detection


class ObjectDetector:
    """
    Component wrap YOLO model (OD)
    Supports YOLOv5 và YOLOv8
    """
    
    def __init__(self, model_path: Optional[str] = None, 
                 model_type: str = "yolov5",
                 confidence_threshold: float = 0.5):
        self.logger = logging.getLogger(__name__)
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.model = None
        
        # Class mapping cho traffic use case
        self.class_mapping = {
            # COCO classes to our classes
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
            if self.model_type == "yolov5":
                # Load YOLOv5
                self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                self.logger.info("Loaded default YOLOv5s model")
            elif self.model_type == "yolov8":
                # Load YOLOv8
                from ultralytics import YOLO
                self.model = YOLO('yolov8n.pt')
                self.logger.info("Loaded default YOLOv8n model")
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
                
        except Exception as e:
            self.logger.error(f"Error loading default model: {e}")
            raise
    
    def load_model(self, model_path: str):
        """Load custom model"""
        try:
            path = Path(model_path)
            if not path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            if self.model_type == "yolov5":
                self.model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                          path=model_path, force_reload=True)
            elif self.model_type == "yolov8":
                from ultralytics import YOLO
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
            # Run inference
            if self.model_type == "yolov5":
                results = self.model(frame)
                detections = self._process_yolov5_results(results)
            elif self.model_type == "yolov8":
                results = self.model(frame)
                detections = self._process_yolov8_results(results)
            else:
                detections = []
            
            # Filter by confidence
            detections = [d for d in detections if d.confidence >= self.confidence_threshold]
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Error during detection: {e}")
            return []
    
    def _process_yolov5_results(self, results) -> List[Detection]:
        """Process YOLOv5 results"""
        detections = []
        
        # results.pandas().xyxy[0] contains detections
        df = results.pandas().xyxy[0]
        
        for idx, row in df.iterrows():
            # Extract info
            x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
            confidence = float(row['confidence'])
            class_name = row['name']
            
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
    
    def _process_yolov8_results(self, results) -> List[Detection]:
        """Process YOLOv8 results"""
        detections = []
        
        if len(results) > 0:
            result = results[0]  # First result
            boxes = result.boxes
            
            if boxes is not None:
                for box in boxes:
                    # Extract info
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
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
    
    def set_confidence_threshold(self, threshold: float):
        """Update confidence threshold"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        self.logger.info(f"Confidence threshold set to {self.confidence_threshold}")
    
    def get_model_info(self) -> Dict:
        """Get model information"""
        return {
            "model_type": self.model_type,
            "confidence_threshold": self.confidence_threshold,
            "model_loaded": self.model is not None,
            "supported_classes": list(self.class_mapping.keys())
        }