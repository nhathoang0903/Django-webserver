from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class TouchTestPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Touch Test Page')
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)

        layout = QVBoxLayout()
        self.label = QLabel("Touch anywhere on screen")
        self.label.setFont(QFont("Arial", 24))
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        """Bắt sự kiện nhấn chuột hoặc chạm màn hình"""
        pos = event.pos()
        print(f"Touched at: x={pos.x()}, y={pos.y()}")
        self.label.setText(f"Touched at: x={int(pos.x())}, y={int(pos.y())}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    test_page = TouchTestPage()
    test_page.show()
    sys.exit(app.exec_())
