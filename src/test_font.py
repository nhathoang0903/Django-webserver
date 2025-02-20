
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import Qt
import os

class FontTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Font Test')
        self.setGeometry(100, 100, 600, 400)

        # Create central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Load fonts
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        josefin_path = os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf')
        
        # Add font and get font ID
        font_id = QFontDatabase.addApplicationFont(josefin_path)
        
        # Display font loading result
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            font_family = families[0]
            status = f"Font loaded successfully. Family name: {font_family}"
            print(f"Font loaded successfully. Family name: {font_family}")
        else:
            status = f"Failed to load font from: {josefin_path}"
            font_family = "Arial"

        # Add status label
        status_label = QLabel(status)
        layout.addWidget(status_label)

        # Test text with loaded font
        test_label = QLabel("Test text with loaded font")
        test_label.setFont(QFont(font_family, 14))
        layout.addWidget(test_label)

        # List all available fonts
        layout.addWidget(QLabel("\nAll Available Fonts:"))
        all_fonts = QFontDatabase().families()
        fonts_label = QLabel("\n".join(all_fonts[:20]))  # Show first 20 fonts
        layout.addWidget(fonts_label)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = FontTestWindow()
    window.show()
    sys.exit(app.exec_())