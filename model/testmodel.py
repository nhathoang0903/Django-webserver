from ultralytics import YOLO
import cv2
import numpy as np
import os

def test_openvino_model():
    # Load the converted model
    model = YOLO('model25nv2_openvino_model/')
    
    # Load test image
    img = cv2.imread('test1.jpeg')  
    if img is None:
        print("Error: Could not load image")
        return
    
    # Perform inference
    results = model(img)
    
    # Process results
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Get confidence and class
            conf = float(box.conf)
            cls = int(box.cls)
            
            # Draw bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, f'Class: {cls} Conf: {conf:.2f}', 
                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (0, 255, 0), 2)
    
    # Create output directory if it doesn't exist
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Save the result image
    output_path = os.path.join(output_dir, 'result.jpg')
    cv2.imwrite(output_path, img)
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    test_openvino_model()