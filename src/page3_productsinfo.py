from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                           QGridLayout, QApplication, QFrame, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QMovie
import os
import requests
from urllib.request import urlopen
import json

class LoadProductsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            response = requests.get('http://127.0.0.1:8000/products')
            products = response.json()
            self.finished.emit(products)
        except Exception as e:
            self.error.emit(str(e))

class ProductPage(QWidget):
    def __init__(self):
        super().__init__()
        self.load_fonts()
        self.init_ui()
        self.setup_loading_indicator()
        self.start_loading_products()

    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))

    def init_ui(self):
        self.setWindowTitle('Product Information - Smart Shopping Cart')
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
        self.setStyleSheet(f"background-color: #EEF5F0;")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 8, 30, 20)
        main_layout.setSpacing(10)

        # Top section with logo and header
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(logo_label)

        # Header
        header_label = QLabel("Product Information")
        header_label.setFont(QFont("Inria Sans", 24, QFont.Bold))
        header_label.setStyleSheet("color: #3D6F4A;")
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(header_label)
        
        # Add stretch to push everything to the left
        top_layout.addStretch()

        main_layout.addLayout(top_layout)

        # Scroll Area for products
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #EEF5F0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #507849;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Container widget for the grid
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        
        # Grid layout for products
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(self.container)
        main_layout.addWidget(scroll_area)

    def setup_loading_indicator(self):
        self.loading_widget = QWidget(self)
        loading_layout = QVBoxLayout(self.loading_widget)
        
        # Create loading spinner
        self.loading_label = QLabel()
        loading_gif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'loading.gif')
        self.movie = QMovie(loading_gif_path)
        self.loading_label.setMovie(self.movie)
        self.movie.start()
        
        # Create loading text
        loading_text = QLabel("Loading products...")
        loading_text.setFont(QFont("Poppins", 12))
        loading_text.setStyleSheet("color: #3D6F4A;")
        loading_text.setAlignment(Qt.AlignCenter)
        
        loading_layout.addWidget(self.loading_label, alignment=Qt.AlignCenter)
        loading_layout.addWidget(loading_text, alignment=Qt.AlignCenter)
        
        # Position the loading widget in the center of the page
        self.loading_widget.setGeometry(300, 150, 200, 200)
        self.loading_widget.show()

    def start_loading_products(self):
        self.loading_thread = LoadProductsThread()
        self.loading_thread.finished.connect(self.on_products_loaded)
        self.loading_thread.error.connect(self.on_loading_error)
        self.loading_thread.start()

    def on_products_loaded(self, products):
        # Hide loading indicator
        self.loading_widget.hide()
        
        # Add products to grid, 4 per row
        for i, product in enumerate(products):
            row = (i // 4) * 2
            col = i % 4
            self.grid_layout.addWidget(self.create_product_card(product), row, col)

    def on_loading_error(self, error_message):
        self.loading_widget.hide()
        error_label = QLabel(f"Error loading products: {error_message}")
        error_label.setStyleSheet("color: red;")
        self.grid_layout.addWidget(error_label, 0, 0)

    def create_product_card(self, product):
        # Create product card frame
        card = QFrame()
        card.setFixedSize(160, 200)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        # Card layout
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(5)

        # Product image
        image_label = QLabel()
        try:
            image_data = urlopen(product['image_url']).read()
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            image_label.setPixmap(pixmap.scaled(120, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except:
            # Use placeholder if image loading fails
            image_label.setText("Image Not Available")
        image_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(image_label)

        # Product name
        name_label = QLabel(product['name'])
        name_label.setFont(QFont("Poppins", 10))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #3D6F4A;")
        card_layout.addWidget(name_label)

        # Product price
        price_label = QLabel(f"{float(product['price']):,.0f} vnd")
        price_label.setFont(QFont("Poppins", 10, QFont.Bold))
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("color: #E72225;")
        card_layout.addWidget(price_label)

        return card

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    product_page = ProductPage()
    product_page.show()
    sys.exit(app.exec_())