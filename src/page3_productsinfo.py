from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                           QGridLayout, QApplication, QFrame, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QEvent, QSize
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QMovie
import os
import json
import urllib.request
from urllib.error import URLError
import threading

class SimpleImageLoader:
    @staticmethod
    def load_image(url, size=(75, 75)):
        try:
            data = urllib.request.urlopen(url, timeout=2).read()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except (URLError, Exception):
            return None

class ProductCard(QFrame):
    def __init__(self, product):
        super().__init__()
        self.product = product
        self.setup_ui()
        self.load_image_async()

    def setup_ui(self):
        self.setFixedSize(160, 170)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                padding: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # Image placeholder
        self.image_label = QLabel()
        self.image_label.setFixedSize(75, 75)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("Loading...")
        self.image_label.setStyleSheet("color: #3D6F4A;")
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        # Name
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 9))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignHCenter)
        name_label.setFixedHeight(45)
        layout.addWidget(name_label)

        # Price
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 8, QFont.Bold))
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("color: #E72225;")
        layout.addWidget(price_label)

    def load_image_async(self):
        def load():
            pixmap = SimpleImageLoader.load_image(self.product['image_url'])
            if pixmap:
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("N/A")

        threading.Thread(target=load, daemon=True).start()

class LoadProductsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            # Read from local JSON file
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'products.json')
            with open(json_path, 'r', encoding='utf-8') as file:
                products = json.load(file)
            # Pre-fetch images
            for product in products[:8]:  # Load first 8 initially
                SimpleImageLoader.load_image(product['image_url'])
            self.finished.emit(products)
        except Exception as e:
            self.error.emit(str(e))

class ProductPage(QWidget):
    def __init__(self):
        super().__init__()
        self._fonts_loaded = False
        self.init_ui()
        self.setup_loading_indicator()
        self.start_loading_products()

    def load_fonts(self):
        if self._fonts_loaded:
            return
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        self._fonts_loaded = True

    def init_ui(self):
        self.setWindowTitle('Product Information - Smart Shopping Cart')
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
        self.setStyleSheet(f"background-color: #EEF5F0;")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 8, 30, 8)  # Reduced bottom margin
        main_layout.setSpacing(25)  # Increased spacing

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
        header_label.setFont(QFont("Inria Sans", 28))
        header_label.setStyleSheet("color: #3D6F4A;")
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(header_label)
        
        # Add stretch to push everything to the left
        top_layout.addStretch()

        main_layout.addLayout(top_layout)

        # Scroll Area for products
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(330)  
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                margin-right: -20px;  
            }
            QScrollBar:vertical {
                border: none;
                background: white;
                border-radius: 5px;
                width: 20px;
                margin: 0px;
                height: 290px;
            }
            QScrollBar::handle:vertical {
                background: #D9D9D9;
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
        self.grid_layout.setContentsMargins(0, 0, 15, 0)  # Add right margin to create space before scrollbar

        scroll_area.setWidget(self.container)
        main_layout.addWidget(scroll_area)

        # Create a horizontal layout for the button content
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # Space between icon and text
        button_layout.setAlignment(Qt.AlignCenter)
        
        # Create a container widget for the button
        button_container = QWidget()
        button_container.setCursor(Qt.PointingHandCursor)  # Add cursor
        button_container.setFixedSize(160, 40)
        button_container.setStyleSheet("""
            QWidget {
                background-color: #507849;
                border-radius: 20px;
            }
        """)
        
        # Add scan icon with both normal and hover states
        scan_icon = QLabel()
        scan_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'scanbutton.png')
        scan_hover_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'scanbutton_hover.png')
        self.normal_pixmap = QPixmap(scan_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.hover_pixmap = QPixmap(scan_hover_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scan_icon.setPixmap(self.normal_pixmap)
        scan_icon.setStyleSheet("padding-left: 20px;")
        
        # Add SCAN text
        scan_text = QLabel("SCAN")
        scan_text.setFont(QFont("Inter", 10, QFont.Bold))
        scan_text.setStyleSheet("""
            QLabel {
                color: white;
            }
        """)
        
        # Add widgets to button layout
        button_layout.addWidget(scan_icon)
        button_layout.addWidget(scan_text)
        button_layout.addStretch()  # Push content to the left
        button_container.setLayout(button_layout)
        
        # Create event filters for hover effect
        class HoverEventFilter(QObject):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.normal_pixmap = self.parent().normal_pixmap
                self.hover_pixmap = self.parent().hover_pixmap

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Enter:
                    scan_text.setStyleSheet("color: #FFFF00;")
                    scan_icon.setPixmap(self.hover_pixmap)
                    return True
                elif event.type() == QEvent.Leave:
                    scan_text.setStyleSheet("color: white;")
                    scan_icon.setPixmap(self.normal_pixmap)
                    return True
                elif event.type() == QEvent.MouseButtonPress:
                    from import_module import ImportModule
                    shopping_page = ImportModule.get_shopping_page()
                    shopping_page.show()
                    print("Switching to shopping page...")
                    obj.window().hide()
                    return True
                return False

        # Install event filter
        button_container.installEventFilter(HoverEventFilter(self))
        
        # Add spacer before button
        main_layout.addSpacing(5)
        main_layout.addWidget(button_container, alignment=Qt.AlignCenter)

    def setup_loading_indicator(self):
        self.loading_widget = QWidget(self)
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setSpacing(10)  # Thêm khoảng cách giữa các widget
        
        # Create loading text
        loading_text = QLabel("Loading products...")
        loading_text.setFont(QFont("Poppins", 11))
        loading_text.setStyleSheet("color: #3D6F4A;")
        loading_text.setAlignment(Qt.AlignCenter)
        
        # Create loading GIF
        loading_gif = QLabel()
        loading_gif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'loading_gif.gif')
        self.gif_movie = QMovie(loading_gif_path)
        self.gif_movie.setScaledSize(QSize(100, 100))  
        loading_gif.setMovie(self.gif_movie)
        self.gif_movie.start()
        
        loading_layout.addWidget(loading_text, alignment=Qt.AlignCenter)
        loading_layout.addWidget(loading_gif, alignment=Qt.AlignCenter)
        
        # Position the loading widget in the center of the page
        self.loading_widget.setGeometry(300, 150, 200, 200)
        self.loading_widget.show()

    def start_loading_products(self):
        self.loading_thread = LoadProductsThread()
        self.loading_thread.finished.connect(self.on_products_loaded)
        self.loading_thread.error.connect(self.on_loading_error)
        self.loading_thread.start()

    def on_products_loaded(self, products):
        # Stop the loading GIF
        self.gif_movie.stop()
        self.loading_widget.hide()
        
        # Load only first 16 products
        for i, product in enumerate(products[:16]):
            row = (i // 4) * 2
            col = i % 4
            self.grid_layout.addWidget(ProductCard(product), row, col)
            if (i + 1) % 4 == 0:
                QApplication.processEvents()

    def on_loading_error(self, error_message):
        self.loading_widget.hide()
        error_label = QLabel(f"Error loading products: {error_message}")
        error_label.setStyleSheet("color: red;")
        self.grid_layout.addWidget(error_label, 0, 0)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    product_page = ProductPage()
    product_page.show()
    sys.exit(app.exec_())