import cv2
from picamera2 import Picamera2
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

class PiCameraTest(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_camera()

    def init_ui(self):
        self.setWindowTitle('Pi Camera Test')
        self.setGeometry(100, 100, 640, 480)
        
        layout = QVBoxLayout()
        self.image_label = QLabel()
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        # Timer for updating frame
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # ~30 FPS

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
            
            # Wait a moment for camera to warm up
            time.sleep(2)
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.picam = None

    def update_frame(self):
        if self.picam:
            try:
                # Capture frame
                frame = self.picam.capture_array()
                
                # Convert to RGB for Qt
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to QImage
                h, w, ch = frame_rgb.shape
                qt_image = QImage(frame_rgb.data, w, h, w * ch, QImage.Format_RGB888)
                
                # Display image
                self.image_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                    self.image_label.width(), 
                    self.image_label.height(),
                    Qt.KeepAspectRatio
                ))
                
            except Exception as e:
                print(f"Error capturing frame: {e}")

    def closeEvent(self, event):
        if self.picam:
            self.picam.stop()
        event.accept()

if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    test_window = PiCameraTest()
    test_window.show()
    sys.exit(app.exec_())
