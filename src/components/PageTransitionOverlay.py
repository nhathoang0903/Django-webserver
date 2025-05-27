from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar, QApplication
from PyQt5.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, QRect, QTimer, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QFont
from utils.translation import _ # Added for translatable "Loading..."

class PageTransitionOverlay(QWidget):
    def __init__(self, parent=None, show_loading_text_for_default_mode=True, simple_mode=False):
        # Create as a top-level widget instead of child widget
        super().__init__(None)  # No parent - standalone window
        self.parent_widget = parent  # Store reference to parent
        self.setObjectName("transitionOverlay")
        self.simple_mode = simple_mode # Store simple_mode
        
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
        
        self._callbacks = [] # Initialize callbacks list

        if self.simple_mode:
            # Simple mode: Just text, no animations
            self.loading_label = QLabel(_("Loading...")) 
            self.loading_label.setFont(QFont("Inria Sans", 30, QFont.Bold))
            # The general QLabel style from the stylesheet should apply for color.
            # Explicit background-color: transparent for the label itself if necessary.
            self.loading_label.setStyleSheet("color: white; background-color: transparent;") 
            self.loading_label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(self.loading_label)
            
            self.progressBar = None
            self.progressAnim = None
            self.fadeAnimation = None # No fade animation in simple_mode
        else:
            # Default mode: Original behavior
            self.loading_label = None # No separate label in default mode
            if show_loading_text_for_default_mode: # Original parameter name was show_loading_text
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
            
            # Set up fade animation for default mode
            self.fadeAnimation = QPropertyAnimation(self, b"windowOpacity")
            self.fadeAnimation.setDuration(500)
        
        # Hidden by default
        self.hide()

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

        if self.simple_mode:
            self.setWindowOpacity(1.0) # Ensure fully opaque
            QApplication.processEvents() # Ensure it's drawn
            if callback:
                self._callbacks.append(callback)
            self._handleFadeInFinished() # Call handler immediately
        else:
            # Default mode fadeIn logic
            if self.fadeAnimation:
                self.fadeAnimation.setStartValue(0)
                self.fadeAnimation.setEndValue(1)
            
                # Khởi động animation progress bar nếu có
                if hasattr(self, 'progressAnim') and self.progressAnim:
                    self.progressBar.setValue(0)
                    self.progressAnim.start()
            
                # Disconnect any previous connections to finished specifically for _handleFadeInFinished
                # to prevent multiple executions from rapid calls.
                try:
                    self.fadeAnimation.finished.disconnect(self._handleFadeInFinished)
                except TypeError: # Catches error if not connected or connected to something else
                    pass

                if callback:
                    self._callbacks.append(callback)
                    # Xử lý khi fadeIn hoàn tất (connect for this call only)
                    self.fadeAnimation.finished.connect(self._handleFadeInFinished)
                
                self.fadeAnimation.start()
            else: # Should not happen if simple_mode is false, but as a fallback
                self.setWindowOpacity(1.0)
                QApplication.processEvents()
                if callback:
                    self._callbacks.append(callback)
                self._handleFadeInFinished()

    def _handleFadeInFinished(self):
        """Handle fade in animation completion with better error handling"""
        try:
            # Process events to ensure UI responsiveness
            QApplication.processEvents()
            
            # Execute all callbacks then clear them
            callbacks_to_execute = list(self._callbacks)
            self._callbacks.clear()
            
            # Execute callbacks after clearing to prevent duplicate execution
            for callback in callbacks_to_execute:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in fadeIn callback: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"Error handling fade in completion: {e}")
            self._callbacks.clear()  # Still clear callbacks to prevent hanging

    def fadeOut(self, callback=None):
        """Ẩn overlay với hiệu ứng mờ dần"""
        # Đảm bảo overlay nằm trên cùng
        self.raise_()

        if self.simple_mode:
            self.hide() # Just hide
            QApplication.processEvents() # Ensure it's hidden
            if callback:
                self._callbacks.append(callback)
            self._handleFadeOutFinished() # Call handler immediately
        else:
            # Default mode fadeOut logic
            # Dừng animation progress bar
            if hasattr(self, 'progressAnim') and self.progressAnim:
                self.progressAnim.stop()
            
            if self.fadeAnimation:
                self.fadeAnimation.setStartValue(1)
                self.fadeAnimation.setEndValue(0)

                try:
                    self.fadeAnimation.finished.disconnect(self._handleFadeOutFinished)
                except TypeError:
                    pass
                
                if callback:
                    self._callbacks.append(callback)
                    self.fadeAnimation.finished.connect(self._handleFadeOutFinished)
                
                self.fadeAnimation.start()
            else: # Fallback if no fadeAnimation in default mode
                self.hide()
                QApplication.processEvents()
                if callback:
                    self._callbacks.append(callback)
                self._handleFadeOutFinished()

    def _handleFadeOutFinished(self):
        """Handle fade out animation completion with better error handling"""
        try:
            # Hide widget first
            self.hide()
            
            # Process events to ensure UI responsiveness
            QApplication.processEvents()
            
            # Execute callbacks and clear list
            callbacks_to_execute = list(self._callbacks)
            self._callbacks.clear()
            
            # Execute callbacks after clearing to prevent duplicate execution
            for callback in callbacks_to_execute:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in fadeOut callback: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"Error handling fade out completion: {e}")
            self._callbacks.clear()  # Still clear callbacks to prevent hanging

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw solid background without transparency
        painter.fillRect(self.rect(), QColor(61, 111, 74, 255))  # #3D6F4A
        super().paintEvent(event)
