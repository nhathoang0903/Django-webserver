import torch
from ultralytics import YOLO
import json
import os
import time
import numpy as np
import cv2
# import onnxruntime
# import tflite_runtime.interpreter as tflite

class ProductDetector:
    _instance = None
    _is_initialized = False
    _last_result = None  # Cache kết quả cuối cùng
    _last_result_time = 0  # Thời gian của kết quả cuối cùng

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProductDetector, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_path="yolov8n.pt"):
        if not ProductDetector._is_initialized:
            self.model = YOLO(model_path)
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'json', 'products.json')
            self.products = self.load_products_from_json(json_path)
            self.frame_count = 0
            self.frames_to_skip = 5  
            self.fps = 0
            self.fps_counter = 0
            self.total_detection_time = 0
            self.total_frames = 0  # Tổng số frame đã xử lý cho tính FPS
            self.start_time = time.time()  # Thời gian bắt đầu để tính FPS
            self.last_detect_time = 0  # Thời gian lần cuối thực hiện detect
            ProductDetector._is_initialized = True
    
    @classmethod
    def preload_model(cls):
        """Call this method early in the application to start loading the model"""
        instance = cls()
        if instance.model is None:
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'model', 'yolov11vs30withdata35.onnx')
            instance.model = YOLO(model_path)
            print("Model preloaded successfully")
    
    def load_product_data(self):
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'products.json')
        with open(json_path, 'r', encoding='utf-8') as f: # Load product data
            self.products = json.load(f)
    
    def reset_frame_counter(self):
        """Reset bộ đếm frame về 0 để bắt đầu bỏ qua frame từ đầu."""
        self.frame_count = 0
        # Reset FPS counter khi bắt đầu phiên mới
        self.total_frames = 0
        self.start_time = time.time()
        self.fps_counter = 0
        self.total_detection_time = 0
        self.fps = 0
        self.last_detect_time = 0
        ProductDetector._last_result = None
        ProductDetector._last_result_time = 0
    
    def should_process_frame(self):
        """Kiểm tra xem có nên xử lý frame hiện tại hay không dựa trên các điều kiện tối ưu hóa"""
        self.frame_count += 1
        
        # Bỏ qua 5 frame đầu tiên
        if self.frame_count <= self.frames_to_skip:
            return False
            
        # Kiểm tra các điều kiện để tối ưu hiệu suất
        current_time = time.time()
        # Chỉ xử lý mỗi 8 frame một lần (số 8 được chọn để cân bằng giữa hiệu suất và độ nhạy)
        should_process = (
            self.frame_count % 8 == 0 and 
            current_time - self.last_detect_time > 0.3  # Ít nhất 0.3s giữa các lần phát hiện
        )
        
        return should_process
    
    def is_frame_stable(self, frame, threshold=80):
        """Kiểm tra xem frame có đủ ổn định để phát hiện sản phẩm không"""
        try:
            # Chuyển sang grayscale để phát hiện độ mờ
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Tính độ mờ sử dụng biến thiên Laplacian
            blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Tính độ sáng trung bình
            brightness = np.mean(gray)
            
            # In thông tin để debug
            print(f"Độ nét (Laplacian var): {blur_value:.2f}, Độ sáng: {brightness:.2f}")
            
            # Kiểm tra các tiêu chí chất lượng
            is_stable = (
                blur_value > threshold and  # Không quá mờ (đã giảm ngưỡng)
                brightness > 30 and         # Không quá tối
                brightness < 220            # Không quá sáng
            )
            
            if not is_stable:
                if blur_value <= threshold:
                    print(f"Hình quá mờ: {blur_value:.2f} <= {threshold}")
                elif brightness <= 30:
                    print("Hình quá tối")
                elif brightness >= 220:
                    print("Hình quá sáng")
            
            return is_stable
        except Exception as e:
            print(f"Lỗi khi kiểm tra độ ổn định của frame: {e}")
            return True  # Nếu xảy ra lỗi, vẫn giả định frame ổn định
    
    def detect_product(self, frame):
        """Phát hiện sản phẩm trong frame. Trả về thông tin sản phẩm nếu tìm thấy, None nếu không."""
        if self.model is None:
            self.preload_model()
        
        # Kiểm tra xem có nên xử lý frame hiện tại hay không
        if not self.should_process_frame():
            return None
        
        # Kiểm tra độ ổn định của frame
        if not self.is_frame_stable(frame):
            print("Frame không đủ ổn định để phát hiện sản phẩm")
            # XÓA cache khi gặp frame mờ
            ProductDetector._last_result = None
            ProductDetector._last_result_time = 0
            return None
        
        # Tăng tổng số frame đã xử lý
        self.total_frames += 1
        
        # Tối ưu: Giảm kích thước frame để tăng tốc độ xử lý
        frame_height, frame_width = frame.shape[:2]
        if frame_width > 640 or frame_height > 640:
            scale_factor = min(640 / frame_width, 640 / frame_height)
            new_width = int(frame_width * scale_factor)
            new_height = int(frame_height * scale_factor)
            frame = cv2.resize(frame, (new_width, new_height))
            print(f"Resized frame from {frame_width}x{frame_height} to {new_width}x{new_height}")
            
        # Bắt đầu đo thời gian xử lý
        start_time = time.time()
        
        # Tối ưu: Đặt các tham số cho model để tăng tốc độ
        results = self.model(frame, conf=0.6, iou=0.45, verbose=False)  # Tăng conf từ 0.55 lên 0.6
        
        # Kết thúc đo thời gian và tính FPS
        end_time = time.time()
        process_time = end_time - start_time
        
        # Tính toán và log FPS
        self.fps_counter += 1
        self.total_detection_time += process_time
        
        # Cập nhật FPS theo hai cách:
        # 1. Dựa trên thời gian xử lý model
        if self.fps_counter >= 5:  # Cập nhật FPS sau mỗi 5 frame
            self.fps = 5 / self.total_detection_time if self.total_detection_time > 0 else 0
            print(f"Model Detection FPS: {self.fps:.1f}, Thời gian xử lý: {(self.total_detection_time/5)*1000:.1f}ms")
            self.fps_counter = 0
            self.total_detection_time = 0
            
        # 2. Tính FPS tổng thể
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            overall_fps = self.total_frames / elapsed_time
            print(f"Overall FPS: {overall_fps:.1f} ({self.total_frames} frames in {elapsed_time:.1f}s)")
        
        # Không có kết quả
        if not results or len(results[0].boxes) == 0:
            return None
            
        # Get the first detected object
        box = results[0].boxes[0]
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        
        if confidence < 0.6:  # Ngưỡng confidence tối thiểu là 0.6
            return None

        # Cập nhật thời gian phát hiện cuối cùng
        self.last_detect_time = time.time()
            
        # Lấy tên sản phẩm từ kết quả detect
        detected_name = results[0].names[class_id]
        
        # Tìm sản phẩm trong json dựa vào tên chính xác
        for product in self.products:
            if product['name'] == detected_name:
                # Lưu kết quả vào cache
                ProductDetector._last_result = product
                ProductDetector._last_result_time = self.last_detect_time
                return product
                
        print(f"Warning: Detected {detected_name} but no matching product in JSON")
        return None
        
    def get_fps(self):
        """Trả về giá trị FPS hiện tại"""
        return self.fps