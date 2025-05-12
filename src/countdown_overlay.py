from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsBlurEffect, QFrame
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt5.QtGui import QFont, QColor, QPainter
from utils.translation import _, get_current_language

class CountdownOverlay(QWidget):
    def __init__(self, parent=None, duration=5000):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create a frame that will be blurred
        self.blur_frame = QFrame(self)
        self.blur_effect = QGraphicsBlurEffect()
        self.blur_effect.setBlurRadius(0)
        self.blur_frame.setGraphicsEffect(self.blur_effect)
        
        # Match blur frame size to parent (camera view area)
        if parent:
            self.blur_frame.setFixedSize(parent.size())
            self.blur_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(240, 246, 241, 0.8);
                    border-radius: 9px;
                }
            """)
            self.setFixedSize(parent.size())
            
        # Setup count label
        self.count_label = QLabel(self)
        self.count_label.setFont(QFont("Inter", 72, QFont.Bold))
        self.count_label.setStyleSheet("""
            QLabel {
                color: black;
                background: transparent;
                border: none;
            }
        """)
        self.count_label.setAlignment(Qt.AlignCenter)
        
        # Position label in center
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.count_label)

        # Setup timer and animation
        self.duration = duration
        self.time_left = duration
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_count)
        self.timer.setInterval(1000)
        
        # Create blur animation
        self.blur_animation = QPropertyAnimation(self.blur_effect, b"blurRadius")
        self.blur_animation.setDuration(200)
        
    def start(self):
        self.time_left = self.duration
        # Start with blur animation
        self.blur_animation.setStartValue(0)
        self.blur_animation.setEndValue(10)
        self.blur_animation.start()
        self.update_count()
        self.timer.start()
        self.show()
        
    def stop(self):
        # Reverse blur animation
        self.blur_animation.setStartValue(10)
        self.blur_animation.setEndValue(0)
        self.blur_animation.start()
        self.timer.stop()
        self.hide()
        
    def update_count(self):
        seconds = max(0, int(self.time_left / 1000))
        if seconds > 0:
            self.count_label.setText(str(seconds))
            self.time_left -= 1000
        else:
            self.stop()