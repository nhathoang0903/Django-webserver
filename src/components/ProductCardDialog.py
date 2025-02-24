from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QGraphicsBlurEffect, QWidget)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QFontDatabase
import os

class OverlayWidget(QWidget):
    def __init__(self, dialog, parent=None):
        super().__init__(parent)
        self.dialog = dialog
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        # Đảm bảo overlay luôn ở trên cùng
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.raise_()
        print("Overlay created")
        
    def showEvent(self, event):
        # Đảm bảo overlay luôn ở trên dialog
        self.raise_()
        super().showEvent(event)

    def mousePressEvent(self, event):
        pos = event.pos()
        print(f"Mouse pressed at: ({pos.x()}, {pos.y()})")
        
        # Chuyển đổi tọa độ chuột từ overlay sang tọa độ màn hình
        global_pos = self.mapToGlobal(pos)
        dialog_rect = self.dialog.geometry()
        
        print(f"Dialog rect: {dialog_rect}")
        print(f"Global pos: {global_pos}")
        
        # Kiểm tra xem click có nằm trong dialog không
        if not dialog_rect.contains(global_pos):
            print("Click outside dialog - closing")
            self.dialog.close_dialog()
        else:
            print("Click inside dialog - ignoring")

class ProductCardDialog(QDialog):
    def __init__(self, product, cached_image, parent=None):
        super().__init__(None)  # No parent for dialog
        self.product = product
        self.cached_image = cached_image
        self.main_page = self.get_main_page(parent)
        self.setup_ui()
        
        # Setup overlay và hiển thị sau khi setup UI
        if self.main_page:
            self.overlay = OverlayWidget(self, self.main_page)
            self.overlay.setGeometry(self.main_page.rect())
            # Hiển thị overlay sau dialog
            self.show()
            self.overlay.show()
            self.overlay.raise_()  # Đảm bảo overlay ở trên cùng
            
            # Đặt vị trí dialog ngay lập tức
            geometry = self.main_page.geometry()
            x = geometry.x() + (geometry.width() - self.width()) // 2
            y = geometry.y() + (geometry.height() - self.height()) // 2
            self.move(x, y)
            print(f"Dialog moved to: ({x}, {y})")
            
        self.apply_blur_effect()
        
    def setup_overlay(self):
        pass  # Đã được xử lý trong __init__
        
    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))
        
    def get_main_page(self, widget):
        """Get the main page widget by traversing up the parent hierarchy"""
        while widget is not None:
            if widget.objectName() == "ProductPage":
                return widget
            widget = widget.parent()
        return None
        
    def setup_ui(self):
        self.setWindowTitle('Product Details')
        self.setFixedSize(200, 280)  # Fixed size matching product card size
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #CCCCCC;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E72225;
            }
        """)
        close_btn.clicked.connect(self.close_dialog)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        # Image - fixed size
        image_label = QLabel()
        image_label.setFixedSize(100, 100)
        image_label.setAlignment(Qt.AlignCenter)
        if self.cached_image:
            # Force resize to fixed dimensions
            pixmap = self.cached_image.scaled(
                100, 100,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            image_label.setPixmap(pixmap)
        layout.addWidget(image_label, alignment=Qt.AlignCenter)
        
        # Name
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 11))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFixedHeight(40)
        layout.addWidget(name_label)
        
        # Price
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 10))
        price_label.setStyleSheet("color: #E72225;")
        price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(price_label)
        
        # Description if available
        if 'description' in self.product:
            desc_label = QLabel(self.product['description'])
            desc_label.setFont(QFont("Poppins", 9))
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignJustify)
            desc_label.setStyleSheet("color: #666666;")
            desc_label.setFixedHeight(60)
            layout.addWidget(desc_label)
            
        layout.addStretch()

    def apply_blur_effect(self):
        # Apply blur to main page instead of just the card
        if self.main_page:
            self.blur_effect = QGraphicsBlurEffect()
            self.blur_effect.setBlurRadius(5)
            self.main_page.setGraphicsEffect(self.blur_effect)

    def close_dialog(self):
        print(">>> Closing dialog")
        if self.main_page:
            self.main_page.setGraphicsEffect(None)
        if hasattr(self, 'overlay'):
            print(">>> Removing overlay")
            self.overlay.deleteLater()
        self.close()

    def showEvent(self, event):
        # Đảm bảo dialog luôn ở trên overlay
        self.raise_()
        self.activateWindow()
        super().showEvent(event)
        print("Dialog shown and raised")

    def closeEvent(self, event):
        if self.main_page:
            self.main_page.setGraphicsEffect(None)
        if hasattr(self, 'overlay'):
            self.overlay.deleteLater()
        super().closeEvent(event)

    def exec_(self):
        # Override exec_ để đảm bảo thứ tự hiển thị đúng
        result = super().exec_()
        return result
