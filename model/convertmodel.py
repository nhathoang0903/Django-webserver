
from ultralytics import YOLO

def convert_to_openvino():
    # Load the model
    model = YOLO('model25nv2.pt')
    
    # Export the model to OpenVINO format
    model.export(format='openvino', 
                imgsz=[640, 640],
                half=True)  # half precision for faster inference
    
    print("Model converted successfully to OpenVINO format")

if __name__ == "__main__":
    convert_to_openvino()