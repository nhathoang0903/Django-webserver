from base_page import BasePage  
from components.PageTransitionOverlay import PageTransitionOverlay
from components.ProductCardDialog import ProductCardDialog 
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                           QGridLayout, QApplication, QFrame, QHBoxLayout, QScroller, QComboBox, QPushButton, QMenu, QDialog, QGraphicsBlurEffect, QLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QEvent, QSize, QPropertyAnimation, QEasingCurve, QTimer, QFileSystemWatcher
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QMovie, QIcon
import os
import json
import urllib.request
from urllib.error import URLError
import threading
from page_timing import PageTiming
from cart_state import CartState
import requests
from config import CART_END_SESSION_API, DEVICE_ID
import importlib
import sys
from utils.translation import _, get_current_language

class CartManager:
    """Class quản lý giỏ hàng, giúp đơn giản hóa việc truy cập CartState từ nhiều nơi"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CartManager, cls).__new__(cls)
            cls._instance.cart_state = CartState()
        return cls._instance
    
    def get_cart_count(self):
        """Trả về số lượng sản phẩm trong giỏ hàng"""
        return len(self.cart_state.cart_items)
        
    def get_cart_items(self):
        """Trả về danh sách sản phẩm trong giỏ hàng"""
        return self.cart_state.cart_items
        
    def add_item(self, product, quantity=1):
        """Thêm sản phẩm vào giỏ hàng"""
        return self.cart_state.add_item(product, quantity)
        
    def clear_cart(self):
        """Xóa toàn bộ giỏ hàng"""
        self.cart_state.clear_cart()
        self.cart_state.save_to_json()

class SimpleImageLoader:
    _cache = {}  # Add image cache

    @staticmethod
    def load_image(url, size=(75, 75)):
        # Check cache first
        cache_key = f"{url}_{size[0]}x{size[1]}"
        if cache_key in SimpleImageLoader._cache:
            return SimpleImageLoader._cache[cache_key]

        try:
            # Convert URL to use images.weserv.nl proxy
            if not url.startswith('https://images.weserv.nl'):
                proxy_url = f"https://images.weserv.nl/?url={url}"
            else:
                proxy_url = url

            # Add timeout to prevent hanging
            request = urllib.request.Request(
                proxy_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            data = urllib.request.urlopen(request, timeout=5).read()  # Increased timeout
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            # Scale image before caching
            scaled = pixmap.scaled(size[0], size[1], 
                                 Qt.KeepAspectRatio, 
                                 Qt.SmoothTransformation)
            
            # Cache the scaled image
            SimpleImageLoader._cache[cache_key] = scaled
            return scaled

        except Exception as e:
            print(f"Error loading image {url}: {e}")
            # Load and cache default image
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'assets', 
                'default-product.png'
            )
            default_pixmap = QPixmap(default_path)
            scaled = default_pixmap.scaled(size[0], size[1],
                                         Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation)
            SimpleImageLoader._cache[cache_key] = scaled
            return scaled

class ProductCard(QFrame):
    def __init__(self, product, cart_count_text=None):
        super().__init__()
        self.product = product
        self.cached_image = None  # Store cached image
        self.cart_state = CartState()  # Add CartState instance
        self.cart_count_text = cart_count_text  # Store reference to cart_count_text
        self.setup_ui()
        self.load_image_async()
        self.setCursor(Qt.PointingHandCursor)
        
    def load_image_async(self):
        def load():
            pixmap = SimpleImageLoader.load_image(self.product['image_url'])
            if pixmap:
                self.cached_image = pixmap  # Cache the image
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("N/A")

        threading.Thread(target=load, daemon=True).start()

    def setup_ui(self):
        self.setFixedSize(140, 180)  # Reduced card width from 160 to 140
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                padding: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(1)
        layout.setSizeConstraint(QLayout.SetFixedSize)

        # Image placeholder
        self.image_label = QLabel()
        self.image_label.setFixedSize(65, 65)  # Reduced image size from 75 to 65
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("Loading...")
        self.image_label.setStyleSheet("color: #3D6F4A;")
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        # Name container with fixed size
        name_container = QWidget()
        name_container.setFixedSize(130, 40)  # Reduced width from 150 to 130
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)
        
        # Name
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 10))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        name_label.setFixedWidth(120)  # Reduced width from 140 to 120
        name_label.setStyleSheet("""
            QLabel {
                color: black;
                padding: 0px 5px;
            }
        """)
        name_layout.addWidget(name_label)
        layout.addWidget(name_container)

        # Price
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 8))
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("color: #E72225;")
        layout.addWidget(price_label)

        # Add to Cart button - use translation
        self.add_to_cart_btn = QPushButton(_("productPage.addToCart"))
        self.add_to_cart_btn.setFont(QFont("Josefin Sans", 10))
        self.add_to_cart_btn.setCursor(Qt.PointingHandCursor)
        self.add_to_cart_btn.setFixedWidth(132)
        self.add_to_cart_btn.setFixedHeight(32)
        self.add_to_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 3px 8px;
                margin: 1px 10px;
            }
            QPushButton:hover {
                background-color: #3D6F4A;
            }
            QPushButton:pressed {
                background-color: #2C513A;
            }
        """)
        self.add_to_cart_btn.clicked.connect(self.add_to_cart)
        layout.addWidget(self.add_to_cart_btn)
        
    def add_to_cart(self):
        try:
            # Add 1 item by default from product page
            is_existing = self.cart_state.add_item(self.product, 1)
            print(f"[Page3] Added product to cart: {self.product['name']}")
            print(f"[Page3] Is existing item: {is_existing}")

            # Update the cart count to reflect the total number of items in cart_items
            cart_count = len(self.cart_state.cart_items)
            print(f"[Page3] New cart count after adding: {cart_count}")
            
            # Cập nhật cart_count_text nếu đã được truyền vào
            if self.cart_count_text:
                self.cart_count_text.setText(f"({cart_count})")
                self.cart_count_text.show()
                print(f"[Page3] Updated cart_count_text directly: ({cart_count})")
            
            # Find ProductPage instance and update cart count
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, ProductPage):
                    widget.update_cart_count()
                    break
            
            # Show success message or animation if needed
            self.add_to_cart_btn.setText(_("productPage.added"))
            QTimer.singleShot(1000, lambda: self.add_to_cart_btn.setText(_("productPage.addToCart")))
            
        except Exception as e:
            print(f"[Page3] Error adding to cart: {e}")

class LoadProductsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'json', 'products.json')
            with open(json_path, 'r', encoding='utf-8') as file:
                products = json.load(file)

            # Pre-load images in batches to avoid overwhelming network
            batch_size = 4
            for i in range(0, min(16, len(products)), batch_size):
                batch = products[i:i+batch_size]
                threads = []
                for product in batch:
                    thread = threading.Thread(
                        target=SimpleImageLoader.load_image,
                        args=(product['image_url'],),
                        daemon=True
                    )
                    threads.append(thread)
                    thread.start()
                
                # Wait for batch to complete
                for thread in threads:
                    thread.join(timeout=3)  # Timeout after 3 seconds

            self.finished.emit(products)
            
        except Exception as e:
            self.error.emit(str(e))

class CategoryDropdown(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 40)
        self.current_category = "All Categories"  # Lưu category tiếng Anh hiện tại
        self.setText(_("productPage.categories.All Categories"))
        self.setFont(QFont("Josefin Sans", 11))
        self.setCursor(Qt.PointingHandCursor)
        
        # Style for main button
        self.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #3D6F4A;
                border-radius: 8px;
                padding: 5px 15px;
                color: #3D6F4A;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        
        # Create custom dropdown menu
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 2px solid #3D6F4A;
                border-radius: 8px;
                padding: 5px;
                min-width: 140px;
            }
            QMenu::item {
                padding: 8px 15px;
                border-radius: 4px;
                color: #3D6F4A;
                font-family: 'Josefin Sans';
                font-size: 11pt;
            }
            QMenu::item:selected {
                background-color: #EEF5F0;
            }
            QMenu::item:pressed {
                background-color: #3D6F4A;
                color: white;
            }
        """)
        
        # Add categories - keep English names for sorting but display translated text
        categories = ["All Categories", "Beverage", "Food", "Snack"]
        for category in categories:
            # Create action with translated text
            translated_category = _("productPage.categories." + category)
            action = self.menu.addAction(translated_category)
            # Pass the original English category name for filtering, but store translated text too
            action.triggered.connect(lambda checked, c=category, tc=translated_category: self.on_category_selected(c, tc))
        
        # Show dropdown on click
        self.clicked.connect(self.show_menu)
        
    def show_menu(self):
        # Calculate position for dropdown to appear below button
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.menu.popup(pos)
        
    def on_category_selected(self, category, translated_category):
        # Lưu category tiếng Anh hiện tại
        self.current_category = category
        # Set button text to translated category
        self.setText(translated_category)
        # Use original English category name for filtering
        self.parent().filter_products(category)
        
    def update_translation(self):
        """Cập nhật text hiển thị của button theo ngôn ngữ hiện tại"""
        self.setText(_("productPage.categories." + self.current_category))

class ProductPage(BasePage):  # Changed from QWidget to BasePage
    _instance = None
    _products_cache = None
    _cards_cache = []
    _watcher = None  # Add file watcher
    _last_language = None  # Add tracking for language changes
    _preserve_cache = True  # Thêm biến để theo dõi việc bảo vệ cache

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProductPage, cls).__new__(cls)
            cls._instance._needs_init = True
            # Initialize language tracking
            cls._last_language = get_current_language()
        return cls._instance

    def __init__(self):
        if hasattr(self, '_needs_init') and self._needs_init:
            super().__init__()  # Call BasePage init
            self.setObjectName("ProductPage")  # Add this line
            self.installEventFilter(self)  # Register event filter
            self._needs_init = False  
            self._fonts_loaded = False
            self.cart_state = CartState()  # Initialize cart_state
            print(f"[Page3] Initializing ProductPage")
            print(f"[Page3] Initial cart count: {len(self.cart_state.cart_items)}")
            print(f"[Page3] Initial cart items: {self.cart_state.cart_items}")
            self.cart_state.register_change_callback(self.update_cart_count)  # Register callback
            self.init_ui()
            
            # Initialize transition overlay
            self.transition_overlay = PageTransitionOverlay(self)
            
            if not ProductPage._products_cache:
                self.setup_loading_indicator()
                self.start_loading_products()
            else:
                self.display_cached_products()
                
            # Set application icon
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
            self.setWindowIcon(QIcon(icon_path))
        
        # Always update translations when the page is initialized or shown again
        self.update_translations()
        
        # Update cart count when initializing or shown again
        self.update_cart_count()

    def reload_current_page(self):
        """Reload the current page"""
        try:
            # Store current state
            current_products = ProductPage._products_cache
            current_cards = ProductPage._cards_cache
            
            # Clear cache
            ProductPage._products_cache = None
            ProductPage._cards_cache = []
            
            # Reinitialize the page
            self._needs_init = True
            self.__init__()
            
            # Restore state
            ProductPage._products_cache = current_products
            ProductPage._cards_cache = current_cards
            
            # Redisplay products
            self.display_cached_products()
            
        except Exception as e:
            print(f"Error reloading current page: {str(e)}")

    def ensure_cards_have_grid_pos(self):
        """Đảm bảo tất cả cards đều có thuộc tính grid_pos"""
        for i, card in enumerate(ProductPage._cards_cache):
            if not hasattr(card, 'grid_pos'):
                row = (i // 4) * 2
                col = i % 4
                card.grid_pos = (row, col)
                print(f"[Page3] Added missing grid_pos ({row}, {col}) to card {i}")

    def display_cached_products(self):
        """Hiển thị sản phẩm từ cache nếu cache không trống"""
        print("[Page3] Displaying products from cache")
        self.debug_cache()
        
        if not ProductPage._products_cache or not ProductPage._cards_cache:
            print("[Page3] No cached products found, loading from server")
            self.setup_loading_indicator()
            self.start_loading_products()
            return False
            
        # Đảm bảo tất cả card đều có grid_pos
        self.ensure_cards_have_grid_pos()
        
        # Hiển thị danh sách sản phẩm đã được lọc theo danh mục hiện tại
        current_category = "All Categories"
        if hasattr(self, 'category_dropdown') and hasattr(self.category_dropdown, 'current_category'):
            current_category = self.category_dropdown.current_category
            
        print(f"[Page3] Applying current category filter: {current_category}")
        self.filter_products(current_category)
        
        # Xóa loading indicator nếu có
        if hasattr(self, 'loading_label') and self.loading_label:
            self.loading_label.hide()
            self.layout.removeWidget(self.loading_label)
            
        return True

    def on_products_loaded(self, products):
        """Modified to show all products without limit"""
        self.gif_movie.stop()
        self.loading_widget.hide()
        
        ProductPage._products_cache = products
        font_family = self.load_fonts()
        
        # Create and cache all product cards with fixed positions
        ProductPage._cards_cache = []
        for i, product in enumerate(products):
            row = (i // 4) * 2
            col = i % 4
            card = ProductCard(product, self.cart_count_text)  # Pass cart_count_text reference
            card.font_family = font_family
            # Store original position
            card.grid_pos = (row, col)
            self.grid_layout.addWidget(card, row, col)
            ProductPage._cards_cache.append(card)
            if (i + 1) % 4 == 0:
                QApplication.processEvents()

    def closeEvent(self, event):
        """Clean up when closing"""
        try:
            # Unregister callback
            self.cart_state.unregister_change_callback(self.update_cart_count)
            
            # Chỉ xóa cache khi không được đánh dấu bảo vệ
            if not ProductPage._preserve_cache:
                print(f"[Page3] closeEvent: Clearing cache due to _preserve_cache={ProductPage._preserve_cache}")
                ProductPage._products_cache = None
                ProductPage._cards_cache = []
            else:
                print(f"[Page3] closeEvent: Preserving cache due to _preserve_cache={ProductPage._preserve_cache}")
                
        except Exception as e:
            print(f"[Page3] Error in closeEvent: {e}")
            
        # Reset _preserve_cache to default value (True) sau khi đã xử lý
        ProductPage._preserve_cache = True
        super().closeEvent(event)

    @classmethod
    def clear_cache(cls):
        """Method to manually clear cache if needed"""
        cls._products_cache = None
        cls._cards_cache = []
        if cls._instance:
            cls._instance = None

    def load_fonts(self):
        # Load fonts needed for this page
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        self.setWindowTitle(_("productPage.title"))  # Use translation
        # Remove setGeometry and setFixedSize since handled by BasePage
        self.setStyleSheet(f"background-color: #EEF5F0;")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 0, 30, 8)  # Reduced top margin to 0
        main_layout.setSpacing(0)  # Remove all spacing between elements

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

        # Header - use translation
        self.header_label = QLabel(_("productPage.title"))  # Store reference to header label
        self.header_label.setFont(QFont("Inria Sans", 28))
        self.header_label.setStyleSheet("color: #3D6F4A;")
        self.header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(self.header_label)
        
        # Category dropdown
        self.category_dropdown = CategoryDropdown(self)
        top_layout.addWidget(self.category_dropdown)
        
        # Add home button
        home_button = QPushButton()
        home_button.setFixedSize(40, 40)  
        home_button.setCursor(Qt.PointingHandCursor)
        home_button.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                border: none;
                border-radius: 20px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3e5c38;
            }
        """)
        
        # Add home icon
        home_icon = QLabel()
        home_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'home.png')
        home_pixmap = QPixmap(home_icon_path)
        if not home_pixmap.isNull():
            home_icon.setPixmap(home_pixmap.scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        home_icon.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        # Create container for icon
        icon_container = QWidget()
        icon_container.setFixedSize(30, 30) 
        icon_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
                border-radius: 15px; 
            }
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(home_icon, alignment=Qt.AlignCenter)
        home_button.setLayout(icon_layout)
        
        # Connect home button to return to page1
        home_button.clicked.connect(self.return_to_welcome)
        top_layout.addWidget(home_button)
        
        # Add stretch to push everything to the left
        top_layout.addStretch()

        main_layout.addLayout(top_layout)
        
        # Add minimal spacing between top layout and scroll area
        main_layout.addSpacing(-12)  

        # Scroll Area for products
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(390)  # Increased from 380 to 390
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                margin-right: 0px;
                margin-top: -12px;
                margin-bottom: 5px;  
            }
            QScrollBar:vertical {
                border: none;
                background: white;
                border-radius: 10px;
                width: 30px;
                margin: 8px 0px 8px 0px;  /* Increased from 5px to 8px */
                height: 364px;  /* Adjusted to accommodate increased margins */
                subcontrol-origin: margin;
                subcontrol-position: top;
            }
            QScrollBar::handle:vertical {
                background: #D9D9D9;
                border-radius: 10px;
                min-height: 30px;
                margin: 2px;  /* Added margin all around handle */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
            }
            QScrollBar:horizontal {
                height: 0px;
                background: transparent;
                border: none;
                display: none;
            }
        """)

        # Custom gesture handling
        class GestureFilter(QObject):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.start_pos = None
                self.min_distance = 10  # Minimum distance for swipe

            def eventFilter(self, obj, event):
                if event.type() == QEvent.MouseButtonPress:
                    self.start_pos = event.pos()
                    return True
                elif event.type() == QEvent.MouseMove and self.start_pos:
                    current_pos = event.pos()
                    dx = current_pos.x() - self.start_pos.x()
                    dy = current_pos.y() - self.start_pos.y()
                    
                    # Only process vertical movement
                    if abs(dy) > self.min_distance:
                        # Calculate scroll amount based on vertical movement
                        scroll_amount = dy * 0.5  # Adjust sensitivity
                        scroll_area.verticalScrollBar().setValue(
                            scroll_area.verticalScrollBar().value() - int(scroll_amount)
                        )
                        self.start_pos = current_pos
                    return True
                elif event.type() == QEvent.MouseButtonRelease:
                    self.start_pos = None
                    return True
                return False

        # Install gesture filter
        gesture_filter = GestureFilter(scroll_area)
        scroll_area.viewport().installEventFilter(gesture_filter)

        # Container widget for the grid
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container.setFixedWidth(600)
        self.container.setMinimumHeight(380)  # Increased from 360 to 380
        
        # Grid layout for products
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(25)  
        self.grid_layout.setContentsMargins(10, 10, 60, 20)  # Increased bottom margin from 10 to 20
        self.grid_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)

        scroll_area.setWidget(self.container)
        main_layout.addWidget(scroll_area)

        # Create a horizontal layout for the bottom section
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create container for the entire bottom section with fixed height 
        bottom_container = QWidget()
        bottom_container.setFixedHeight(45)  # Reduced from 50 to 45
        bottom_container_layout = QHBoxLayout(bottom_container)
        bottom_container_layout.setContentsMargins(20, 0, 20, 0)
        
        # Create 3 equal width sections
        left_widget = QWidget()  # Empty left widget for spacing
        
        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        
        right_widget = QWidget()  # Empty right widget for spacing
        
        # Add all sections with equal width
        bottom_container_layout.addWidget(left_widget, 1)  # Stretch factor 1
        bottom_container_layout.addWidget(middle_widget, 1)  # Stretch factor 1
        bottom_container_layout.addWidget(right_widget, 1)  # Stretch factor 1
        
        # Create SCAN button
        button_container = QWidget()
        button_container.setCursor(Qt.PointingHandCursor)
        button_container.setFixedSize(200, 40)  # Increased width from 160 to 200
        button_container.setStyleSheet("""
            QWidget {
                background-color: #507849;
                border-radius: 20px;
            }
        """)
        
        # Create button content layout
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 10, 0)
        button_layout.setSpacing(10)
        
        # Add cart icon with both normal and hover states
        cart_icon = QLabel()
        cart_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'yourcarticon.png')
        self.normal_pixmap = QPixmap(cart_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.hover_pixmap = QPixmap(cart_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        cart_icon.setPixmap(self.normal_pixmap)
        
        # Add cart text and count
        self.cart_text = QLabel(_("productPage.yourCart") + " ")  # Store reference to cart text
        self.cart_text.setFont(QFont("Inter", 12, QFont.Bold))
        self.cart_text.setStyleSheet("color: white;")
        
        # Add cart count with red color
        self.cart_count_text = QLabel("(0)")
        self.cart_count_text.setFont(QFont("Inter", 12, QFont.Bold))
        self.cart_count_text.setStyleSheet("color: #FFFF00;")
        
        # Create a container for cart text and count
        cart_text_container = QWidget()
        cart_text_layout = QHBoxLayout(cart_text_container)
        cart_text_layout.setContentsMargins(0, 0, 0, 0)
        cart_text_layout.setSpacing(2)
        cart_text_layout.addWidget(self.cart_text)
        cart_text_layout.addWidget(self.cart_count_text)
        
        # Add widgets to button layout
        button_layout.addWidget(cart_icon)
        button_layout.addWidget(cart_text_container)
        button_layout.addStretch()

        # Add button to center widget
        middle_layout.addWidget(button_container, 0, Qt.AlignCenter)

        # Create event filters for hover effect
        class HoverEventFilter(QObject):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.normal_pixmap = self.parent().normal_pixmap
                self.hover_pixmap = self.parent().hover_pixmap
                # Lưu tham chiếu đến cart_text trực tiếp từ parent
                self.parent_cart_text = self.parent().cart_text
                
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Enter:
                    # Sử dụng tham chiếu đã lưu thay vì self.cart_text
                    self.parent_cart_text.setStyleSheet("color: #FFFF00;")
                    cart_icon.setPixmap(self.hover_pixmap)
                    return True
                elif event.type() == QEvent.Leave:
                    # Sử dụng tham chiếu đã lưu thay vì self.cart_text
                    self.parent_cart_text.setStyleSheet("color: white;")
                    cart_icon.setPixmap(self.normal_pixmap)
                    return True
                elif event.type() == QEvent.MouseButtonPress:
                    self.parent().show_shopping_page()
                    return True
                return False

        # Install event filter
        button_container.installEventFilter(HoverEventFilter(self))

        # Initialize cart count visibility based on current cart state
        cart_count = len(self.cart_state.cart_items)
        if cart_count > 0:
            self.cart_count_text.setText(f"({cart_count})")
            self.cart_count_text.show()
        else:
            self.cart_count_text.hide()

        # Add bottom container to main layout
        main_layout.addWidget(bottom_container)

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

    def on_loading_error(self, error_message):
        self.loading_widget.hide()
        error_label = QLabel(f"Error loading products: {error_message}")
        error_label.setStyleSheet("color: red;")
        self.grid_layout.addWidget(error_label, 0, 0)

    def show_shopping_page(self):
        """Enhanced transition to shopping page"""
        def switch_page():
            start_time = PageTiming.start_timing()
            from page4_shopping import ShoppingPage
            self.shopping_page = ShoppingPage()
            
            def show_new_page():
                self.shopping_page.show()
                self.transition_overlay.fadeOut(lambda: self.hide())
                PageTiming.end_timing(start_time, "ProductPage", "ShoppingPage")
                
            self.transition_overlay.fadeIn(show_new_page)
            
        switch_page()

    @staticmethod
    def debug_cache():
        """In thông tin debug về cache hiện tại"""
        print(f"[Page3] DEBUG CACHE STATUS:")
        print(f"[Page3] - Products cache: {ProductPage._products_cache is not None}")
        if ProductPage._products_cache:
            print(f"[Page3] - Number of cached products: {len(ProductPage._products_cache)}")
        print(f"[Page3] - Cards cache: {ProductPage._cards_cache is not None}")
        if ProductPage._cards_cache:
            print(f"[Page3] - Number of cached cards: {len(ProductPage._cards_cache)}")
            print(f"[Page3] - First few cards: {ProductPage._cards_cache[:3]}")
            
    def filter_products(self, category):
        """
        Lọc sản phẩm theo danh mục.
        Tham số category luôn là tên tiếng Anh, bất kể ngôn ngữ hiển thị
        """
        print(f"[Page3] Filtering products by category: {category}")
        self.debug_cache()
        
        # Kiểm tra nếu không có cards nào hoặc cache trống, tải lại
        if not ProductPage._products_cache or not ProductPage._cards_cache:
            print(f"[Page3] Cache is empty, reloading products")
            self.setup_loading_indicator()
            self.start_loading_products()
            return
        
        print(f"[Page3] Current cards in cache: {len(ProductPage._cards_cache)}")
        
        # Hide all cards and remove from layout
        for card in ProductPage._cards_cache:
            card.hide()
            self.grid_layout.removeWidget(card)

        # Đếm số card được hiển thị
        displayed_count = 0
        
        # Kiểm tra tính hợp lệ của mỗi card trước khi hiển thị
        valid_cards = []
        for card in ProductPage._cards_cache:
            try:
                # Thử truy cập thuộc tính để đảm bảo card vẫn hợp lệ
                _ = card.product['name']
                valid_cards.append(card)
            except Exception as e:
                print(f"[Page3] Found invalid card, error: {e}")
        
        # Cập nhật lại cache nếu có card không hợp lệ
        if len(valid_cards) != len(ProductPage._cards_cache):
            print(f"[Page3] Updating cache - found {len(ProductPage._cards_cache) - len(valid_cards)} invalid cards")
            ProductPage._cards_cache = valid_cards
        
        if (category == "All Categories"):
            # Sắp xếp theo bảng chữ cái dựa trên sản phẩm gốc
            sorted_cards = sorted(valid_cards, 
                                key=lambda card: card.product['name'].replace('_', ' '))
            
            # Sắp xếp lại các sản phẩm
            for i, card in enumerate(sorted_cards):
                row = (i // 4) * 2
                col = i % 4
                self.grid_layout.addWidget(card, row, col)
                card.show()
                displayed_count += 1
        else:
            # Lọc sản phẩm theo danh mục, dựa trên tên danh mục tiếng Anh
            filtered_cards = [card for card in valid_cards 
                            if card.product['category'] == category]
            
            # Sắp xếp theo bảng chữ cái
            sorted_filtered_cards = sorted(filtered_cards, 
                                         key=lambda card: card.product['name'].replace('_', ' '))
            
            # Thêm sản phẩm đã lọc và sắp xếp vào vị trí mới
            for i, card in enumerate(sorted_filtered_cards):
                row = (i // 4) * 2
                col = i % 4
                self.grid_layout.addWidget(card, row, col)
                card.show()
                displayed_count += 1

        # Cập nhật layout
        self.container.update()
        print(f"[Page3] Filtered products displayed: {displayed_count} cards shown")
        
        # Lưu lại danh mục hiện tại (tiếng Anh) để dùng khi đổi ngôn ngữ
        if hasattr(self, 'category_dropdown'):
            self.category_dropdown.current_category = category

    def return_to_welcome(self):
        """Return to welcome page using CART_END_SESSION_API"""
        try:
            # Đảm bảo cache vẫn được bảo vệ
            ProductPage._preserve_cache = True
            print(f"[Page3] Setting _preserve_cache to True before returning to welcome")
            
            # Call end session API
            response = requests.post(f"{CART_END_SESSION_API}{DEVICE_ID}/")
            if response.status_code == 200:
                # Clear phone number in JSON file
                try:
                    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'config', 'phone_number.json')
                    with open(file_path, 'w') as f:
                        json.dump({"phone_number": ""}, f)
                    print("Successfully cleared phone number")
                except Exception as e:
                    print(f"Error clearing phone number: {e}")
                    
                # Lưu lại trạng thái cache hiện tại
                current_products = ProductPage._products_cache
                current_cards = ProductPage._cards_cache.copy()  # Tạo bản sao để tránh mất reference
                
                # Return to page1
                from page1_welcome import WelcomePage
                self.welcome_page = WelcomePage()
                self.welcome_page.show()
                
                # Ẩn trang hiện tại thay vì đóng để tránh mất cache
                self.hide()
            else:
                print(f"Error ending session: {response.text}")
        except Exception as e:
            print(f"Error returning to welcome page: {e}")

    def update_cart_count(self):
        """Update the cart count display"""
        try:
            cart_count = CartManager().get_cart_count()
            print(f"[Page3] Updating cart count: {cart_count}")
            
            # Cập nhật cart_count_text trước tiên nếu có
            if hasattr(self, 'cart_count_text'):
                if cart_count > 0:
                    self.cart_count_text.setText(f"({cart_count})")
                    self.cart_count_text.show()
                    print(f"[Page3] Updated cart_count_text: ({cart_count})")
                else:
                    self.cart_count_text.setText("")
                    self.cart_count_text.hide()
                    print("[Page3] Cart is empty, hiding count display")
            
            # Tiếp tục cập nhật cart_btn nếu có
            if hasattr(self, 'cart_btn'):
                self.cart_btn.update_count(cart_count)
                print(f"[Page3] Updated cart_btn counter")
                
        except Exception as e:
            print(f"[Page3] Error updating cart count: {e}")

    def showEvent(self, event):
        """Xử lý sự kiện khi trang được hiển thị"""
        super().showEvent(event)
        
        # In thông tin debug về cache hiện tại
        self.debug_cache()
            
        # Đếm số lượng item trong grid
        grid_items = 0
        for row in range(self.grid_layout.rowCount()):
            for col in range(self.grid_layout.columnCount()):
                item = self.grid_layout.itemAtPosition(row, col)
                if item is not None and item.widget() is not None:
                    grid_items += 1
                    
        print(f"[Page3] Grid layout currently has {grid_items} items")
        
        # Kiểm tra ngôn ngữ hiện tại
        current_language = get_current_language()
        print(f"[Page3] Current language: {current_language}, Last language: {ProductPage._last_language}")
        
        # Nếu ngôn ngữ đã thay đổi, cập nhật lại trang
        if current_language != ProductPage._last_language:
            print(f"[Page3] Language changed from {ProductPage._last_language} to {current_language}, reinitializing")
            ProductPage._last_language = current_language
            ProductPage._needs_init = True
            
            # Gọi __init__ lại để cập nhật toàn bộ
            self.__init__()
            
            # Sau khi khởi tạo lại, áp dụng bộ lọc danh mục hiện tại nếu có
            if hasattr(self, 'category_dropdown') and hasattr(self.category_dropdown, 'current_category'):
                print(f"[Page3] Reapplying category filter: {self.category_dropdown.current_category}")
                self.filter_products(self.category_dropdown.current_category)
        
        # Nếu grid trống nhưng có products trong cache, hiển thị lại từ cache
        if grid_items == 0 and ProductPage._cards_cache and len(ProductPage._cards_cache) > 0:
            print(f"[Page3] Grid is empty but we have {len(ProductPage._cards_cache)} cards in cache, redisplaying")
            
            # Xác định category hiện tại nếu có
            current_category = "All Categories"
            if hasattr(self, 'category_dropdown') and hasattr(self.category_dropdown, 'current_category'):
                current_category = self.category_dropdown.current_category
                
            # Gọi filter_products để hiển thị lại sản phẩm
            self.filter_products(current_category)
            
            # Đảm bảo cập nhật layout sau khi thêm lại các widget
            QApplication.processEvents()
            self.container.update()
        
        # Cập nhật số lượng hàng trong giỏ
        cart_count = CartManager().get_cart_count()
        print(f"[Page3] Updating cart count: {cart_count}")
        
        # Kiểm tra sự tồn tại của cart_btn trước khi sử dụng
        if hasattr(self, 'cart_btn'):
            self.cart_btn.update_count(cart_count)
        else:
            # Sử dụng cart_count_text thay thế nếu có
            if hasattr(self, 'cart_count_text'):
                if cart_count > 0:
                    self.cart_count_text.setText(f"({cart_count})")
                    self.cart_count_text.show()
                else:
                    self.cart_count_text.setText("")
                    self.cart_count_text.hide()
            print(f"[Page3] Warning: 'cart_btn' attribute not found, using fallback method")
        
        # Reset vị trí cuộn nếu đến từ page1
        # Kiểm tra cả from_page và from_page1 để đảm bảo tương thích
        if (hasattr(self, 'from_page') and self.from_page == "page1") or (hasattr(self, 'from_page1') and self.from_page1):
            print(f"[Page3] Resetting scroll position, coming from page1")
            scroll = self.findChild(QScrollArea)
            if scroll:
                scroll.verticalScrollBar().setValue(0)

    def show_product_page(self):
        """Navigate to the product information page"""
        # Stop camera and session monitor before switching page
        if self.camera_active:
            self.stop_camera()
            
        if hasattr(self, 'session_monitor'):
            self.session_monitor.stop() 
            self.session_monitor.wait()
            print("Stopped session monitor before product page")
            
        if hasattr(self, 'payment_monitor'):
            self.payment_monitor.stop()
            self.payment_monitor.wait()
            print("Stopped payment monitor before product page")
            
        # Import ProductPage dynamically to avoid circular imports
        from page3_productsinfo import ProductPage
        product_page = ProductPage()
        product_page.from_page1 = False  # Set flag to indicate not coming from page1
        
        # Show the product page and hide current page
        product_page.show()
        self.hide()

    def update_translations(self):
        """Update all UI elements with current language translations"""
        print(f"[Page3] Updating translations to: {get_current_language()}")
        
        # Update window title
        self.setWindowTitle(_("productPage.title"))
        
        # Update header label
        if hasattr(self, 'header_label'):
            self.header_label.setText(_("productPage.title"))
            
        # Update category dropdown
        if hasattr(self, 'category_dropdown'):
            # Sử dụng phương thức mới của CategoryDropdown
            self.category_dropdown.update_translation()
            
            # Recreate menu with updated translations
            if hasattr(self.category_dropdown, 'menu'):
                self.category_dropdown.menu.clear()
                categories = ["All Categories", "Beverage", "Food", "Snack"]
                for category in categories:
                    translated_category = _("productPage.categories." + category)
                    action = self.category_dropdown.menu.addAction(translated_category)
                    action.triggered.connect(
                        lambda checked, c=category, tc=translated_category: 
                        self.category_dropdown.on_category_selected(c, tc)
                    )
        
        # Update product cards
        if hasattr(self, '_cards_cache') and self._cards_cache:
            for card in self._cards_cache:
                if hasattr(card, 'add_to_cart_btn'):
                    card.add_to_cart_btn.setText(_("productPage.addToCart"))
        
        # Update cart text
        if hasattr(self, 'cart_text'):
            self.cart_text.setText(_("productPage.yourCart") + " ")

    def force_redisplay_products(self):
        """Force the redisplay of all products from cache"""
        print(f"[Page3] Forcing redisplay of {len(ProductPage._cards_cache)} products")
        
        # Đảm bảo cached cards có đủ thông tin vị trí
        self.ensure_cards_have_grid_pos()
        
        # Lấy thông tin danh mục hiện tại nếu có
        current_category = "All Categories"
        if hasattr(self, 'category_dropdown') and hasattr(self.category_dropdown, 'current_category'):
            current_category = self.category_dropdown.current_category
            
        # Hiển thị lại sản phẩm theo danh mục hiện tại
        self.filter_products(current_category)
        
    def reset_scroll_position(self):
        """Reset scroll position to top of the page"""
        try:
            # Find the scroll area in the page
            for widget in self.findChildren(QScrollArea):
                if isinstance(widget, QScrollArea):
                    widget.verticalScrollBar().setValue(0)
                    print("[Page3] Reset scroll position to top")
                    break
        except Exception as e:
            print(f"[Page3] Error resetting scroll position: {e}")
            
    def update_cart_count(self):
        """Update the cart count display"""
        try:
            cart_count = CartManager().get_cart_count()
            print(f"[Page3] Updating cart count: {cart_count}")
            if hasattr(self, 'cart_btn'):
                self.cart_btn.update_count(cart_count)
        except Exception as e:
            print(f"[Page3] Error updating cart count: {e}")

class ProductCardDialog(QDialog):
    def __init__(self, product, image, parent=None):
        super().__init__(parent)
        self.product = product
        self.image = image
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedSize(400, 500)  # Increased dialog size
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 15px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Image
        image_label = QLabel()
        if self.image:
            image_label.setPixmap(self.image.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # Name
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 14, QFont.Bold))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        # Price
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 12))
        price_label.setStyleSheet("color: #E72225;")
        price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(price_label)
        
        # Description
        desc_label = QLabel(self.product.get('description', 'No description available'))
        desc_label.setFont(QFont("Josefin Sans", 10))
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add to Cart button - use translation
        add_to_cart_btn = QPushButton(_("productPage.addToCart"))
        add_to_cart_btn.setFont(QFont("Josefin Sans", 12))
        add_to_cart_btn.setCursor(Qt.PointingHandCursor)
        add_to_cart_btn.setFixedHeight(30)
        add_to_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 5px 10px;
                margin: 10px 20px;
            }
            QPushButton:hover {
                background-color: #3D6F4A;
            }
            QPushButton:pressed {
                background-color: #2C513A;
            }
        """)
        add_to_cart_btn.clicked.connect(lambda: self.parent().add_to_cart(self.product))
        layout.addWidget(add_to_cart_btn)
        
        # Close button - use "Close" as it's common across UIs
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont("Josefin Sans", 12))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E72225;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 5px 10px;
                margin: 10px 20px;
            }
            QPushButton:hover {
                background-color: #C41E3A;
            }
            QPushButton:pressed {
                background-color: #A31A32;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    from count_item import add_cart_count_label, update_cart_count
    app = QApplication(sys.argv)
    product_page = ProductPage()
    add_cart_count_label(product_page)  # Thêm widget "Your Cart"
    product_page.show()
    sys.exit(app.exec_())