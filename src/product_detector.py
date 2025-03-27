import torch
from ultralytics import YOLO
import json
import os
# import onnxruntime
# import tflite_runtime.interpreter as tflite

class ProductDetector:
    _instance = None
    _is_initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProductDetector, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not ProductDetector._is_initialized:
            self.model = None
            self.products = None
            self.load_product_data()
            ProductDetector._is_initialized = True
    
    @classmethod
    def preload_model(cls):
        """Call this method early in the application to start loading the model"""
        instance = cls()
        if instance.model is None:
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'model', 'yolov11n20.onnx')
            instance.model = YOLO(model_path)
    
    def load_product_data(self):
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'products.json')
        with open(json_path, 'r', encoding='utf-8') as f: # Load product data
            self.products = json.load(f)
    
    def detect_product(self, frame):
        if self.model is None:
            self.preload_model()
        
        results = self.model(frame)
        
        if not results or len(results[0].boxes) == 0:
            return None
            
        # Get the first detected object
        box = results[0].boxes[0]
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        
        if confidence < 0.5:  # Minimum confidence threshold
            return None

        # Lấy tên sản phẩm từ kết quả detect
        detected_name = results[0].names[class_id]
        
        # Tìm sản phẩm trong json dựa vào tên chính xác
        for product in self.products:
            if product['name'] == detected_name:
                return product
                
        print(f"Warning: Detected {detected_name} but no matching product in JSON")
        return None