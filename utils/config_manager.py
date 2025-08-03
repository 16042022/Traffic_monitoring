# utils/config_manager.py
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """
    Quản lý configuration cho toàn bộ application
    Singleton pattern
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_path = None
        
    def load_config(self, config_path: str = "config.json") -> Dict[str, Any]:
        """
        Load configuration từ file
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        self.config_path = Path(config_path)
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                    self.logger.info(f"Loaded config from {config_path}")
            else:
                self.logger.warning(f"Config file not found: {config_path}")
                self._config = self.get_default_config()
                # Lưu default config
                self.save_config(self._config)
                
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self._config = self.get_default_config()
            
        return self._config
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            # Database settings
            "database": {
                "url": "sqlite:///traffic_monitoring.db",
                "echo": False,
                "pool_size": 5
            },
            
            # Video processing settings
            "video_processing": {
                "batch_size": 100,
                "save_interval": 30,  # frames
                "max_processing_threads": 2
            },
            
            # AI Model settings
            "ai_model": {
                "type": "yolov8",  # yolov5 or yolov8
                "model_path": None,  # Use default if None
                "confidence_threshold": 0.5,
                "nms_threshold": 0.4
            },
            
            # Virtual line configuration
            "virtual_line": {
                "p1_x": 100,
                "p1_y": 300,
                "p2_x": 800,
                "p2_y": 300,
                "counting_direction": "down"  # up, down, left, right
            },
            
            # Traffic monitoring settings
            "traffic_monitoring": {
                "stop_time_threshold": 20.0,  # seconds
                "congestion_thresholds": {
                    "low": 5,
                    "medium": 15,
                    "high": 25,
                    "very_high": 35
                }
            },
            
            # UI settings
            "ui": {
                "language": "vi",  # Vietnamese
                "theme": "light",
                "video_display_size": (800, 600),
                "fps_display": 30
            },
            
            # Paths
            "paths": {
                "video_storage": "./videos",
                "export_path": "./exports",
                "log_path": "./logs"
            }
        }
    
    def save_config(self, config: Optional[Dict[str, Any]] = None):
        """
        Save configuration to file
        
        Args:
            config: Configuration to save (uses current if None)
        """
        if config is None:
            config = self._config
            
        if config and self.config_path:
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                self.logger.info(f"Saved config to {self.config_path}")
            except Exception as e:
                self.logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports nested keys with dots)
        
        Args:
            key: Configuration key (e.g., "database.url")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        if self._config is None:
            self.load_config()
            
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value
        
        Args:
            key: Configuration key (supports dots)
            value: Value to set
        """
        if self._config is None:
            self.load_config()
            
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        self.logger.info(f"Updated config: {key} = {value}")
    
    def update(self, updates: Dict[str, Any]):
        """
        Update multiple configuration values
        
        Args:
            updates: Dictionary of updates
        """
        for key, value in updates.items():
            self.set(key, value)
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get full configuration"""
        if self._config is None:
            self.load_config()
        return self._config


# Global instance
config_manager = ConfigManager()