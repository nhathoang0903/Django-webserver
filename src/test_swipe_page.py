from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont

class TestSwipePage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.start_pos = QPoint()

    def init_ui(self):
        self.setWindowTitle('Swipe Test Page')
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
        
        layout = QVBoxLayout()
        self.label = QLabel("Swipe left or right")
        self.label.setFont(QFont("Arial", 24))
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.setLayout(layout)

    def mousePressEvent(self, event):
        """Ghi lại vị trí bắt đầu"""
        self.start_pos = event.pos()

    def mouseReleaseEvent(self, event):
        """Kiểm tra hướng vuốt"""
        dx = event.pos().x() - self.start_pos.x()
        
        if dx > 50:
            print("Swiped right")
        elif dx < -50:
            print("Swiped left")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    # Bật hỗ trợ cảm ứng cho PyQt5
    QApplication.setAttribute(Qt.AA_SynthesizeTouchForUnhandledMouseEvents, True)
    
    test_page = TestSwipePage()
    test_page.show()
    sys.exit(app.exec_())
