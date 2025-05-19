from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar, QApplication
from PyQt5.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, QRect, QTimer, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QFont

class PageTransitionOverlay(QWidget):
    def __init__(self, parent=None, show_loading_text=True):
        # Create as a top-level widget instead of child widget
        super().__init__(None)  # No parent - standalone window
        self.parent_widget = parent  # Store reference to parent
        self.setObjectName("transitionOverlay")
        
        # Set as frameless window that stays on top of everything
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Remove flags that might interfere with interaction
        # self.setAttribute(Qt.WA_NoSystemBackground)
        # self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Set overlay to cover the entire screen
        self.cover_full_screen()
        
        # Style the overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("""
            #transitionOverlay {
                background-color: #3D6F4A;
            }
            QLabel {
                color: white;
                font-family: 'Inria Sans';
            }
            QProgressBar {
                background-color: #3D6F4A;
                border: 2px solid white;
                border-radius: 15px;
                height: 30px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #FFFFFF;
                border-radius: 13px;
            }
        """)
        
        # Create layout before adding widgets
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Add progress bar for loading
        if show_loading_text:
            # Add progress bar
            self.progressBar = QProgressBar()
            self.progressBar.setFixedSize(500, 30)  # Larger, more visible progress bar
            self.progressBar.setMinimum(0)
            self.progressBar.setMaximum(100)
            self.progressBar.setValue(0)
            self.progressBar.setTextVisible(False)  # Hide percentage text
            self.layout.addWidget(self.progressBar)
            
            # Setup animation for progress bar
            self.progressAnim = QPropertyAnimation(self.progressBar, b"value")
            self.progressAnim.setDuration(1500)  # 1.5 seconds for one cycle
            self.progressAnim.setStartValue(0)
            self.progressAnim.setEndValue(100)
            self.progressAnim.setEasingCurve(QEasingCurve.InOutSine)  # Smooth animation
            
            # Connect animation finished to restart
            self.progressAnim.finished.connect(self.restart_progress_anim)
        else:
            self.progressBar = None
            self.progressAnim = None
        
        # Set up animation
        self.fadeAnimation = QPropertyAnimation(self, b"windowOpacity")
        self.fadeAnimation.setDuration(500)
        
        # Hidden by default
        self.hide()
        self._callbacks = []

    def cover_full_screen(self):
        """Cover the entire screen or screens"""
        desktop = QApplication.desktop()
        screen_rect = desktop.screenGeometry()
        self.setGeometry(screen_rect)
        
    def restart_progress_anim(self):
        """Restart the progress bar animation"""
        if hasattr(self, 'progressAnim') and self.progressAnim:
            self.progressBar.setValue(0)
            self.progressAnim.start()

    def fadeIn(self, callback=None):
        """Hiển thị overlay với hiệu ứng mờ dần"""
        # Đảm bảo overlay phủ toàn màn hình
        self.cover_full_screen()
        
        # Đảm bảo overlay nằm trên cùng
        self.show()
        self.raise_()
        
        # Cài đặt animation mờ dần
        self.fadeAnimation.setStartValue(0)
        self.fadeAnimation.setEndValue(1)
        
        # Khởi động animation progress bar nếu có
        if hasattr(self, 'progressAnim') and self.progressAnim:
            self.progressBar.setValue(0)
            self.progressAnim.start()
        
        if callback:
            self._callbacks.append(callback)
            
            # Xử lý khi fadeIn hoàn tất
            def on_fade_in_finished():
                # Ngắt kết nối để tránh gọi nhiều lần
                self.fadeAnimation.finished.disconnect(on_fade_in_finished)
                # Gọi callback ngay lập tức
                self._handleFadeInFinished()
                
            self.fadeAnimation.finished.connect(on_fade_in_finished)
            
        self.fadeAnimation.start()

    def _handleFadeInFinished(self):
        # Execute all callbacks then clear them
        for callback in self._callbacks:
            callback()
        self._callbacks.clear()

    def fadeOut(self, callback=None):
        """Ẩn overlay với hiệu ứng mờ dần"""
        # Đảm bảo overlay nằm trên cùng
        self.raise_()
        
        # Cài đặt animation mờ dần
        self.fadeAnimation.setStartValue(1)
        self.fadeAnimation.setEndValue(0)
        
        # Dừng animation progress bar
        if hasattr(self, 'progressAnim') and self.progressAnim:
            self.progressAnim.stop()
        
        if callback:
            self._callbacks.append(callback)
            
            def on_fade_out_finished():
                # Ngắt kết nối để tránh gọi nhiều lần
                self.fadeAnimation.finished.disconnect(on_fade_out_finished)
                # Gọi hàm cleanup ngay lập tức
                self._handleFadeOutFinished()
                
            self.fadeAnimation.finished.connect(on_fade_out_finished)
            
        self.fadeAnimation.start()

    def _handleFadeOutFinished(self):
        # Hide widget, execute callbacks, then cleanup
        self.hide()
        for callback in self._callbacks:
            callback()
        self._callbacks.clear()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw solid background without transparency
        painter.fillRect(self.rect(), QColor(61, 111, 74, 255))  # #3D6F4A
        super().paintEvent(event)
