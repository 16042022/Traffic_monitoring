# Tài liệu Kỹ thuật - Hệ thống Giám sát Giao thông Thông minh

## Mục lục
1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc-architectural-overview)
2. [Mô tả các Modules/Components chính](#2-mô-tả-các-modulescomponents-chính)
3. [Chi tiết các Class/Method quan trọng](#3-chi-tiết-các-classmethod-quan-trọng)
4. [Thiết kế cơ sở dữ liệu](#4-thiết-kế-cơ-sở-dữ-liệu-database-schema)
5. [Hướng dẫn cài đặt và chạy](#5-hướng-dẫn-cài-đặt-và-chạy)

---

## 1. Tổng quan kiến trúc (Architectural Overview)

### 1.1 Mô hình MVC với DAL và Repository Pattern

Hệ thống tuân thủ nghiêm ngặt mô hình **Model-View-Controller (MVC)** kết hợp với **Data Access Layer (DAL)** và **Repository Pattern** để đảm bảo tính modular, khả năng testing và bảo trì.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│      VIEW       │◄──►│   CONTROLLER    │◄──►│     MODEL       │
│   (GUI Layer)   │    │ (Input Handler) │    │(Business Logic) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   REPOSITORY    │
                                              │ (Data Interface)│
                                              └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │      DAL        │
                                              │ (DB Interaction)│
                                              └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │    DATABASE     │
                                              │    (SQLite)     │
                                              └─────────────────┘
```

### 1.2 Các tầng kiến trúc

#### **View Layer (Tầng Hiển thị)**
- **Công nghệ**: PyQt5 cho desktop GUI
- **Chức năng**: Hiển thị video, thống kê, cảnh báo và nhận tương tác người dùng
- **Thành phần**: MainWindow, VideoPlayerWidget, AnalysisPanel, HistoryWidget

#### **Controller Layer (Tầng Điều khiển)**
- **Chức năng**: Xử lý sự kiện từ View, điều phối các action với Model
- **Thành phần**: MainController, VideoController, AnalysisController, HistoryController

#### **Model Layer (Tầng Logic nghiệp vụ)**
- **Chức năng**: Chứa toàn bộ logic xử lý video, AI detection, tracking
- **Thành phần**: VideoProcessor, ObjectDetector, VehicleTracker, TrafficMonitor, AnomalyDetector

#### **Repository Layer (Tầng Repository)**
- **Chức năng**: Abstraction layer cho database operations
- **Thành phần**: VideoRepository, DetectionEventRepository, TrafficDataRepository, AnomalyEventRepository

#### **DAL (Data Access Layer)**
- **Chức năng**: Direct database connection và ORM management
- **Công nghệ**: SQLAlchemy ORM với SQLite

---

## 2. Mô tả các Modules/Components chính

### 2.1 Model Components

#### **VideoProcessor (VP)**
- **Vai trò**: Xử lý file video, đọc frame, overlay kết quả
- **Chức năng chính**:
  - Mở và đọc file video (MP4, AVI)
  - Iterate qua từng frame
  - Overlay detection results, statistics, alerts
  - Đảm bảo real-time update cho hiển thị

#### **ObjectDetector (OD)**
- **Vai trò**: Áp dụng AI model (YOLO) để phát hiện object
- **Chức năng chính**:
  - Load YOLO model (YOLOv5/YOLOv8)
  - Inference trên từng frame
  - Trả về detection results với bounding boxes

#### **VehicleTracker (VT)**
- **Vai trò**: Tracking objects qua các frame, gán ID duy nhất
- **Chức năng chính**:
  - Gán unique ID cho mỗi detected object
  - Maintain tracking history
  - Calculate movement info (speed, distance, stopped status)
  - Detect virtual line crossing

#### **TrafficMonitor (TMD)**
- **Vai trò**: Tính toán thống kê giao thông
- **Chức năng chính**:
  - Đếm lưu lượng theo virtual line
  - Phân loại theo vehicle type
  - Tính toán traffic density levels
  - Hourly statistics aggregation

#### **AnomalyDetector (OAD)**
- **Vai trò**: Phát hiện các bất thường
- **Chức năng chính**:
  - Detect pedestrians, animals, obstacles
  - Monitor stopped vehicles (20-second threshold)
  - Generate alerts với severity levels
  - Track anomaly duration và resolution

### 2.2 Repository Components

#### **VideoRepository**
- **CRUD operations** cho Video entities
- **Advanced queries**: by status, recent videos, search
- **Statistics**: processing duration, success rates

#### **DetectionEventRepository**
- **Store individual** vehicle crossing events
- **Time-based queries** cho aggregation
- **Support** lane-specific và direction filtering

#### **TrafficDataRepository**
- **Aggregated statistics** storage
- **Time-interval** summaries (minute/hour)
- **Traffic density** calculations

#### **AnomalyEventRepository**
- **Anomaly tracking** với lifecycle management
- **Severity filtering** và alert status
- **Timeline generation** cho historical analysis

### 2.3 View Components

#### **MainWindow**
- **Central hub** cho application
- **Menu system** và toolbar
- **Layout management** với splitters

#### **VideoPlayerWidget**
- **Video playback** controls
- **Real-time overlay** của detection results
- **Progress tracking** và frame navigation

#### **AnalysisPanel**
- **Real-time statistics** display
- **Alert notifications** panel
- **Configuration controls**

#### **HistoryWidget**
- **Browse processed** videos
- **View historical** results
- **Time-based summaries** display

---

## 3. Chi tiết các Class/Method quan trọng

### 3.1 VehicleTracker Class

```python
class VehicleTracker:
    def __init__(self, max_disappeared: int = 30):
        """
        Initialize vehicle tracker
        
        Args:
            max_disappeared: Max frames before removing inactive object
        """
        
    def update(self, detections: List[Detection]) -> Dict[str, TrackingInfo]:
        """
        Update tracking với new detections
        
        Args:
            detections: List of Detection objects from current frame
            
        Returns:
            Dict mapping object_id to TrackingInfo
        """
        
    def assign_ids(self, detections: List[Detection]) -> List[Detection]:
        """
        Assign unique IDs to detections
        
        Args:
            detections: Raw detections from object detector
            
        Returns:
            Detections with assigned unique IDs
        """
```

### 3.2 TrafficMonitor Class

```python
class TrafficMonitor:
    def __init__(self, virtual_line_config: Dict):
        """
        Initialize traffic monitor
        
        Args:
            virtual_line_config: Configuration for counting line
        """
        
    def count_vehicle_crossing(self, tracking_info: Dict[str, TrackingInfo]) -> Dict:
        """
        Count vehicles crossing virtual line
        
        Args:
            tracking_info: Current tracking information
            
        Returns:
            Updated count statistics
        """
        
    def get_statistics(self) -> Dict:
        """
        Get current traffic statistics
        
        Returns:
            Dict with total counts, counts by type, density level
        """
```

### 3.3 AnomalyDetector Class

```python
class AnomalyDetector:
    def __init__(self, stop_time_threshold: float = 20.0):
        """
        Initialize anomaly detector
        
        Args:
            stop_time_threshold: Seconds before flagging stopped vehicle
        """
        
    def detect_anomalies(self, detections: List[Detection], 
                        tracker: VehicleTracker,
                        timestamp: float) -> List[Dict]:
        """
        Detect anomalies in current frame
        
        Args:
            detections: Current frame detections
            tracker: VehicleTracker instance
            timestamp: Current video timestamp
            
        Returns:
            List of detected anomalies with type, severity, location
        """
```

### 3.4 VideoRepository Class

```python
class VideoRepository:
    def create(self, video_info: Dict) -> Video:
        """
        Create new video record
        
        Args:
            video_info: Dict với file_name, duration, fps, etc.
            
        Returns:
            Created Video entity
        """
        
    def get_by_status(self, status: str) -> List[Video]:
        """
        Get videos by processing status
        
        Args:
            status: 'pending', 'processing', 'completed', 'failed'
            
        Returns:
            List of Video entities matching status
        """
        
    def update_processing_status(self, video_id: int, 
                               status: str, 
                               duration: float = None) -> bool:
        """
        Update video processing status
        
        Args:
            video_id: Video ID
            status: New status
            duration: Processing duration in seconds
            
        Returns:
            Success boolean
        """
```

---

## 4. Thiết kế cơ sở dữ liệu (Database Schema)

### 4.1 Sơ đồ Entity-Relationship

```
┌─────────────────┐       ┌─────────────────┐
│     Videos      │ 1   N │ Detection_Events│
│                 ├───────┤                 │
│ - id (PK)       │       │ - id (PK)       │
│ - file_name     │       │ - video_id (FK) │
│ - upload_time   │       │ - frame_number  │
│ - duration      │       │ - object_type   │
│ - status        │       │ - bbox_coords   │
└─────────────────┘       └─────────────────┘
         │                          │
         │ 1                        │
         │                          │
         │ 1                        │
         │                          │
┌─────────────────┐       ┌─────────────────┐
│  Traffic_Data   │       │ Anomaly_Events  │
│                 │       │                 │
│ - id (PK)       │       │ - id (PK)       │
│ - video_id (FK) │       │ - video_id (FK) │
│ - total_vehicles│       │ - anomaly_type  │
│ - car_count     │       │ - severity      │
│ - minute_aggs   │       │ - timestamp     │
└─────────────────┘       └─────────────────┘
```

### 4.2 Chi tiết các bảng

#### **Bảng Videos**
```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    duration REAL NOT NULL,                    -- Duration in seconds
    fps REAL NOT NULL,                         -- Frames per second  
    resolution VARCHAR(20),                    -- e.g., "1920x1080"
    frame_count INTEGER,
    processing_timestamp DATETIME,
    processing_duration REAL,                 -- Processing time in seconds
    status VARCHAR(20) DEFAULT 'pending',     -- pending/processing/completed/failed
    storage_path VARCHAR(500)
);
```

#### **Bảng Detection_Events**
```sql
CREATE TABLE detection_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    event_id VARCHAR(50),                     -- Tracking ID (e.g., "obj_123")
    frame_number INTEGER NOT NULL,
    timestamp_in_video REAL NOT NULL,         -- Seconds from video start
    object_type VARCHAR(50) NOT NULL,         -- car, motorbike, truck, bus, person
    confidence_score REAL,
    bbox_x INTEGER,
    bbox_y INTEGER, 
    bbox_width INTEGER,
    bbox_height INTEGER,
    crossed_line BOOLEAN DEFAULT FALSE,       -- Whether crossed virtual line
    crossing_direction VARCHAR(20),           -- up, down, left, right
    lane_id INTEGER,                          -- If multiple lanes
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

-- Indexes cho performance
CREATE INDEX idx_video_frame ON detection_events(video_id, frame_number);
CREATE INDEX idx_video_time ON detection_events(video_id, timestamp_in_video);
CREATE INDEX idx_video_object ON detection_events(video_id, object_type);
CREATE INDEX idx_video_crossed ON detection_events(video_id, crossed_line);
```

#### **Bảng Traffic_Data**
```sql
CREATE TABLE traffic_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL UNIQUE,
    total_vehicles INTEGER DEFAULT 0,
    car_count INTEGER DEFAULT 0,
    motorbike_count INTEGER DEFAULT 0,
    truck_count INTEGER DEFAULT 0,
    bus_count INTEGER DEFAULT 0,
    avg_vehicles_per_minute REAL,
    peak_vehicles_per_minute INTEGER,
    peak_minute_timestamp REAL,              -- Timestamp of peak traffic
    minute_aggregations TEXT,                -- JSON: {"0": {"car": 5}, "1": {...}}
    hour_aggregations TEXT,                  -- JSON: {"0": {"car": 50}, ...}
    lane_data TEXT,                          -- JSON: {"lane_1": {"car": 10}}
    avg_speed REAL,                          -- If speed detection implemented
    congestion_level VARCHAR(20),            -- low, medium, high, very_high
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

#### **Bảng Anomaly_Events**
```sql
CREATE TABLE anomaly_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,        -- pedestrian, animal, obstacle, stopped_vehicle
    severity_level VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    timestamp_in_video REAL NOT NULL,        -- Seconds from video start
    duration REAL,                           -- Duration of anomaly (for stopped vehicles)
    detection_area VARCHAR(50),              -- e.g., "lane_1", "intersection" 
    bbox_x INTEGER,
    bbox_y INTEGER,
    bbox_width INTEGER,
    bbox_height INTEGER,
    object_id VARCHAR(50),                   -- Tracking ID if available
    object_class VARCHAR(50),                -- Specific class (e.g., "person", "dog")
    confidence_score REAL,
    alert_status VARCHAR(20) DEFAULT 'active', -- active, acknowledged, resolved
    alert_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

-- Indexes cho performance  
CREATE INDEX idx_video_anomaly_type ON anomaly_events(video_id, anomaly_type);
CREATE INDEX idx_video_anomaly_time ON anomaly_events(video_id, timestamp_in_video);
CREATE INDEX idx_anomaly_severity ON anomaly_events(video_id, severity_level);
CREATE INDEX idx_alert_status ON anomaly_events(alert_status);
```

### 4.3 Mối quan hệ và ràng buộc

- **Videos ↔ Detection_Events**: One-to-Many (một video có nhiều detection events)
- **Videos ↔ Traffic_Data**: One-to-One (một video có một bản ghi traffic data)  
- **Videos ↔ Anomaly_Events**: One-to-Many (một video có nhiều anomaly events)
- **Foreign Key Constraints**: Đảm bảo data integrity với CASCADE DELETE
- **Indexes**: Tối ưu truy vấn theo video_id, timestamp, object_type

---

## 5. Hướng dẫn cài đặt và chạy

### 5.1 Yêu cầu hệ thống

#### **Hardware Requirements**
- RAM: Tối thiểu 8GB (khuyến nghị 16GB)
- GPU: NVIDIA GPU với CUDA support (optional, cho tăng tốc AI inference)
- Storage: Tối thiểu 10GB free space

#### **Software Requirements**
- Python 3.8+
- CUDA 11.0+ (nếu sử dụng GPU)
- Webcam hoặc video files để test

### 5.2 Cài đặt Dependencies

#### **Step 1: Clone repository**
```bash
git clone <repository-url>
cd traffic-monitoring-system
```

#### **Step 2: Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows
```

#### **Step 3: Install requirements**
```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
# Core dependencies
opencv-python>=4.8.0
PyQt5>=5.15.0
numpy>=1.21.0
sqlalchemy>=1.4.0
ultralytics>=8.0.0
torch>=1.13.0
torchvision>=0.14.0

# Additional utilities  
Pillow>=9.0.0
matplotlib>=3.5.0
scipy>=1.9.0
```

### 5.3 Cấu hình ban đầu

#### **Step 1: Initialize database**
```bash
python dal/migrations/init_db.py
```

#### **Step 2: Configure settings**
Tạo file `config.json`:
```json
{
    "model_type": "yolov8n",
    "confidence_threshold": 0.5,
    "stop_time_threshold": 20.0,
    "virtual_line": {
        "start_point": [100, 300],
        "end_point": [500, 300],
        "direction": "horizontal"
    },
    "paths": {
        "model_path": "./models/yolov8n.pt",
        "log_path": "./logs/",
        "database_url": "sqlite:///traffic_monitoring.db"
    }
}
```

### 5.4 Chạy ứng dụng

#### **Development mode**
```bash
python main_application.py
```

#### **Production mode**
```bash
python main_application.py --production
```

#### **Run tests**
```bash
# Run all tests
python -m unittest discover tests/

# Run specific test category
python tests/run_tests.py --components
python tests/run_tests.py --repositories
```

### 5.5 Sử dụng cơ bản

1. **Mở video**: Click "Mở Video" hoặc drag & drop file video
2. **Bắt đầu phân tích**: Click "Bắt đầu" để start processing
3. **Xem kết quả real-time**: Statistics và alerts hiển thị trong Analysis Panel
4. **Lịch sử**: Switch sang History tab để xem processed videos
5. **Cấu hình**: Menu Settings để adjust thresholds và parameters

### 5.6 Troubleshooting

#### **Common Issues**

**1. YOLO model không load được:**
```bash
# Download model manually
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

**2. Database connection errors:**
```bash
# Recreate database
python dal/migrations/init_db.py --drop-existing
```

**3. GUI không hiển thị:**
```bash
# Check PyQt5 installation
python -c "from PyQt5.QtWidgets import QApplication"
```

#### **Performance Tuning**

**1. GPU acceleration:**
- Install CUDA-compatible PyTorch
- Verify GPU được detect: `torch.cuda.is_available()`

**2. Model optimization:**
- Sử dụng lighter model (yolov8n vs yolov8x)
- Reduce input resolution trong config

**3. Database optimization:**
- Regularly vacuum SQLite: `VACUUM;`
- Monitor database size và consider archiving

---

## Kết luận

Hệ thống Traffic Monitoring được thiết kế với kiến trúc modular, scalable và maintainable. Việc áp dụng MVC pattern kết hợp với Repository pattern và DAL đảm bảo separation of concerns và khả năng testing tốt. Database schema được tối ưu cho performance với các indexes phù hợp, hỗ trợ các truy vấn phức tạp cho time-based analysis và historical reporting.

Hệ thống có thể dễ dàng mở rộng để hỗ trợ thêm các loại anomaly detection, multiple camera streams, hoặc real-time streaming từ IP cameras. Architecture linh hoạt cho phép thay đổi database backend từ SQLite sang PostgreSQL/MySQL khi cần scale up.
