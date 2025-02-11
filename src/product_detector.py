import torch
from ultralytics import YOLO
import json
import os

class ProductDetector:
    def __init__(self):
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'model', 'model25n.pt')
        self.model = YOLO(model_path)
        self.load_product_data()
    
    def load_product_data(self):
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'products.json')
        with open(json_path, 'r', encoding='utf-8') as f: # Load product data
            self.products = json.load(f)
    
    def detect_product(self, frame):
        results = self.model(frame)
        
        if not results or len(results[0].boxes) == 0:
            return None
            
        # Get the first detected object
        box = results[0].boxes[0]
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        
        if confidence < 0.5:  # Minimum confidence threshold
            return None
            
        # Match with product data
        for product in self.products:
            if product['product_id'] == class_id:
                return product
                
        return None