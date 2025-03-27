import cv2
from picamera2 import Picamera2
import time
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from product_detector import ProductDetector

class PiCameraDetectorTest(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_camera()
        self.init_detector()
        self.frame_count = 0
        self.last_detect_time = 0

    def init_ui(self):
        self.setWindowTitle('Pi Camera Detector Test')
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        
        # Camera feed label
        self.image_label = QLabel()
        self.image_label.setFixedSize(640, 480)
        layout.addWidget(self.image_label)
        
        # Result label
        self.result_label = QLabel("No product detected")
        self.result_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #333;
                padding: 10px;
                background: #f0f0f0;
                border-radius: 5px;
            }
        """)
        self.result_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result_label)
        
        self.setLayout(layout)

    def init_camera(self):
        try:
            self.picam = Picamera2()
            
            # Configure camera
            config = self.picam.create_preview_configuration(
                main={"size": (640, 480)},
                lores={"size": (320, 240)},
                display="lores"
            )
            self.picam.configure(config)
            
            # Start camera
            self.picam.start()
            print("Camera initialized successfully")
            
            # Wait for camera to warm up
            time.sleep(2)
            
            # Start frame timer
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(33)  # ~30 FPS
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.picam = None
            
    def init_detector(self):
        """Initialize product detector"""
        self.detector = ProductDetector()
        # Preload model if available
        if hasattr(ProductDetector, 'preload_model'):
            ProductDetector.preload_model()

    def update_frame(self):
        if not self.picam:
            return
            
        try:
            # Capture frame
            frame = self.picam.capture_array()
            
            # Convert to RGB for Qt display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Run detection every 10 frames
            current_time = time.time()
            if self.frame_count % 10 == 0 and current_time - self.last_detect_time > 0.5:
                if self.is_frame_stable(frame):
                    # Process frame for detection
                    detect_frame = frame.copy()
                    product = self.detector.detect_product(detect_frame)
                    
                    if product:
                        self.last_detect_time = current_time
                        self.result_label.setText(
                            f"Detected: {product['name']}\n"
                            f"Price: {product['price']} VND"
                        )
                        self.result_label.setStyleSheet("""
                            QLabel {
                                font-size: 16px;
                                color: white;
                                padding: 10px;
                                background: #4CAF50;
                                border-radius: 5px;
                            }
                        """)
                    
                    del detect_frame
            
            # Convert to QImage for display
            h, w, ch = frame_rgb.shape
            qt_image = QImage(frame_rgb.data, w, h, w * ch, QImage.Format_RGB888)
            
            # Display image
            self.image_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio
            ))
            
            self.frame_count += 1
            
        except Exception as e:
            print(f"Error capturing frame: {e}")

    def is_frame_stable(self, frame, threshold=100):
        """Check if frame is stable enough for detection"""
        # Convert to grayscale for blur detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate Laplacian variance (blur detection)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Calculate frame brightness
        brightness = np.mean(gray)
        
        # Check if frame meets quality criteria
        is_stable = (blur_value > threshold and  # Not too blurry
                    brightness > 30 and          # Not too dark
                    brightness < 220)            # Not too bright
                    
        return is_stable

    def closeEvent(self, event):
        if self.picam:
            self.picam.stop()
        event.accept()

if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    test_window = PiCameraDetectorTest()
    test_window.show()
    sys.exit(app.exec_())
