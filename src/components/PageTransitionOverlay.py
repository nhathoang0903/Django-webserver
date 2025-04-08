from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup
from PyQt5.QtGui import QPainter, QColor

class PageTransitionOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transitionOverlay")
        
        # Set overlay to top and full screen
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("""
            #transitionOverlay {
                background-color: rgba(0, 0, 0, 70%);
            }
            QLabel {
                color: white;
                font-family: 'Inria Sans';
                font-size: 16px;
            }
        """)
        
        # Create layout before adding widgets
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setAlignment(Qt.AlignCenter)
        
        # Loading indicator
        self.loadingLabel = QLabel("Loading...")
        self.layout.addWidget(self.loadingLabel)
        
        # Set up animation
        self.fadeAnimation = QPropertyAnimation(self, b"windowOpacity")
        self.fadeAnimation.setDuration(500)
        
        # Hidden by default
        self.hide()
        self._callbacks = []

    def fadeIn(self, callback=None):
        # Enhanced fade in with callback cleanup
        if self.parent():
            self.setFixedSize(self.parent().size())  # Ensure it covers the entire parent window
        self.show()
        self.fadeAnimation.setStartValue(0)
        self.fadeAnimation.setEndValue(1)
        
        if callback:
            self._callbacks.append(callback)
            self.fadeAnimation.finished.connect(self._handleFadeInFinished)
            
        self.fadeAnimation.start()

    def _handleFadeInFinished(self):
        # Execute all callbacks then clear them
        for callback in self._callbacks:
            callback()
        self._callbacks.clear()
        self.fadeAnimation.finished.disconnect(self._handleFadeInFinished)

    def fadeOut(self, callback=None):
        # Enhanced fade out with callback cleanup
        self.fadeAnimation.setStartValue(1)
        self.fadeAnimation.setEndValue(0)
        
        if callback:
            self._callbacks.append(callback)
            self.fadeAnimation.finished.connect(self._handleFadeOutFinished)
            
        self.fadeAnimation.start()

    def _handleFadeOutFinished(self):
        # Hide widget, execute callbacks, then cleanup
        self.hide()
        for callback in self._callbacks:
            callback()
        self._callbacks.clear()
        self.fadeAnimation.finished.disconnect(self._handleFadeOutFinished)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background with transparency
        painter.fillRect(self.rect(), QColor(0, 0, 0, 127))
        super().paintEvent(event)
