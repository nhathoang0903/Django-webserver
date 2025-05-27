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
import subprocess
from page_timing import PageTiming
from cart_state import CartState
import requests
from config import CART_END_SESSION_API, DEVICE_ID, PRODUCTS_CHECK_NEW_API, PRODUCTS_CHECK_EDITS_API, PRODUCTS_CHECK_DELETIONS_API
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
    # Class-level cooldown flag for all ProductCard instances
    _add_to_cart_cooldown = False
    _cooldown_timer = None

    def __init__(self, product, cart_count_text=None):
        super().__init__()
        self.product = product
        self.cached_image = None  # Store cached image
        self.cart_count_text = cart_count_text  # Store reference to cart_count_text
        self.setup_ui()
        self.load_image_async()
        self.setCursor(Qt.PointingHandCursor)
        
        # Initialize cooldown timer if not already created
        if ProductCard._cooldown_timer is None:
            ProductCard._cooldown_timer = QTimer()
            ProductCard._cooldown_timer.setSingleShot(True)
            ProductCard._cooldown_timer.timeout.connect(ProductCard.reset_global_cooldown)
        
    @classmethod
    def reset_global_cooldown(cls):
        """Reset the global cooldown flag for all ProductCard instances"""
        cls._add_to_cart_cooldown = False
        print("[Page3] Global add-to-cart cooldown ended")
        
    def load_image_async(self):
        def load():
            pixmap = SimpleImageLoader.load_image(self.product['image_url'], size=(150, 150))  # Increased from 120x120
            if pixmap:
                self.cached_image = pixmap  # Cache the image
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("N/A")

        threading.Thread(target=load, daemon=True).start()

    def setup_ui(self):
        self.setFixedSize(270, 370)  # Tăng từ 350 lên 370 để thêm không gian cho các phần tử lớn hơn
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 20px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(3)
        layout.setSizeConstraint(QLayout.SetFixedSize)

        # Image placeholder
        self.image_label = QLabel()
        self.image_label.setFixedSize(150, 150)  
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("Loading...")
        self.image_label.setStyleSheet("color: #3D6F4A; font-size: 16px;")
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        # Name container with fixed size
        name_container = QWidget()
        name_container.setFixedSize(260, 65)  # Increased width from 230 to 260
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)
        
        # Name
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 20))  # Tăng từ 17 lên 19
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        name_label.setFixedWidth(245)  # Increased from 220 to 245
        name_label.setStyleSheet("""
            QLabel {
                color: black;
                padding: 0px 5px;
            }
        """)
        name_layout.addWidget(name_label)
        layout.addWidget(name_container)
        self.name_label_ref = name_label # Store reference

        # Price - MADE LARGER
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 24, QFont.Bold))  # Tăng từ 18 lên 24 và thêm Bold
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("color: #E72225; margin-top: 5px;")
        layout.addWidget(price_label)
        self.price_label_ref = price_label # Store reference

        # Add to Cart button - MADE LARGER
        self.add_to_cart_btn = QPushButton(_("productPage.addToCart"))
        self.add_to_cart_btn.setFont(QFont("Josefin Sans", 22, QFont.Bold))  # Tăng từ 18 lên 22 và thêm Bold
        self.add_to_cart_btn.setCursor(Qt.PointingHandCursor)
        self.add_to_cart_btn.setFixedWidth(250)  # Giữ nguyên width 250
        self.add_to_cart_btn.setFixedHeight(70)  # Tăng từ 50 lên 60
        self.add_to_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border: none;
                border-radius: 18px;
                padding: 8px 12px;
                margin: 5px 10px;
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
        
        # Check if product is already in cart and update button accordingly
        self.update_button_state()
        
    def refresh_ui(self):
        """Refresh the UI elements of the card with current product data."""
        # Update name
        name = self.product['name'].replace('_', ' ')
        if hasattr(self, 'name_label_ref'): 
             self.name_label_ref.setText(name)
        else:
            print(f"[Page3] Warning: name_label_ref not found for {self.product['name']}")

        # Update price
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        if hasattr(self, 'price_label_ref'): 
            self.price_label_ref.setText(f"{price} vnd")
        else:
            print(f"[Page3] Warning: price_label_ref not found for {self.product['name']}")
        
        # Reload image if URL changed
        # Assuming the image_url might change, otherwise this might be redundant if only other fields change
        # For now, always reload to be safe, can be optimized later if image_url is static for a product_id
        self.load_image_async()
        
        # Update button state (e.g. if product was removed from cart elsewhere)
        # This will be handled by the page level now, but we can call the visual update part.
        # We need to know if it's in cart - for now, assume it's not unless set by page.
        self.set_visual_state(is_in_cart=False) # Default to not in cart on refresh, page will correct.
        print(f"[Page3] Refreshed UI for ProductCard: {self.product['name']}")

    def set_visual_state(self, is_in_cart: bool):
        """Sets the visual state of the 'Add to Cart' button based on cart status."""
        if is_in_cart:
            self.add_to_cart_btn.setText(_("productPage.added"))
            self.add_to_cart_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3D6F4A;
                    color: #FFFF00;
                    border: none;
                    border-radius: 18px;
                    padding: 8px 12px;
                    margin: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #3D6F4A;
                }
                QPushButton:pressed {
                    background-color: #3D6F4A;
                }
            """)
        else:
            self.add_to_cart_btn.setText(_("productPage.addToCart"))
            self.add_to_cart_btn.setStyleSheet("""
                QPushButton {
                    background-color: #507849;
                    color: white;
                    border: none;
                    border-radius: 18px;
                    padding: 8px 12px;
                    margin: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #3D6F4A;
                }
                QPushButton:pressed {
                    background-color: #2C513A;
                }
            """)
        
    def update_button_state(self):
        """Kiểm tra sản phẩm đã có trong giỏ hàng chưa và cập nhật trạng thái button.
        DEPRECATED: This method should no longer read files.
        The ProductPage will now manage this and call set_visual_state directly.
        For now, it will try to get state from CartManager only.
        """
        try:
            cart_manager = CartManager()
            if not isinstance(self.product, dict) or 'name' not in self.product:
                print(f"[Page3] Product is not valid dict or missing name: {type(self.product)}")
                self.set_visual_state(False) # Default to not in cart
                return
                
            product_name = self.product['name']
            is_in_cart = False
            cart_items = cart_manager.get_cart_items()
            
            for item in cart_items:
                if isinstance(item, dict) and 'product' in item and isinstance(item['product'], dict) and 'name' in item['product']:
                    if item['product']['name'] == product_name:
                        is_in_cart = True
                        break
                elif isinstance(item, dict) and 'product_name' in item:
                    if item['product_name'] == product_name:
                        is_in_cart = True
                        break
                elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], dict) and 'name' in item[0]:
                    if item[0]['name'] == product_name:
                        is_in_cart = True
                        break
            
            self.set_visual_state(is_in_cart)
            if is_in_cart:
                 print(f"[Page3-deprecated_update_button_state] Product {product_name} is in cart (CartManager only), updated button state")

        except Exception as e:
            print(f"[Page3] Error in deprecated update_button_state: {e}")
            self.set_visual_state(False) # Default on error
    
    def add_to_cart(self):
        try:
            # Check for global cooldown
            if ProductCard._add_to_cart_cooldown:
                print("[Page3] Add to cart ignored - global cooldown active")
                return
                
            cart_manager = CartManager()
            
            if not isinstance(self.product, dict) or 'name' not in self.product:
                print(f"[Page3] Product is not valid dict or missing name: {type(self.product)}")
                return
                
            product_name = self.product['name']
            
            is_existing = False
            cart_items = cart_manager.get_cart_items()
            
            for item in cart_items:
                if isinstance(item, dict) and 'product' in item and isinstance(item['product'], dict) and 'name' in item['product']:
                    if item['product']['name'] == product_name:
                        is_existing = True
                        break
                elif isinstance(item, dict) and 'product_name' in item:
                    if item['product_name'] == product_name:
                        is_existing = True
                        break
                elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], dict) and 'name' in item[0]:
                    if item[0]['name'] == product_name:
                        is_existing = True
                        break
                    
            if is_existing:
                print(f"[Page3] Product already in cart: {product_name}")
                self.set_visual_state(True) # Update visual state
                return
                
            ProductCard._add_to_cart_cooldown = True
                
            cart_manager.add_item(self.product, 1)
            print(f"[Page3] Added product to cart: {product_name}")
            
            cart_count = cart_manager.get_cart_count()
            print(f"[Page3] New cart count: {cart_count}")
            
            if self.cart_count_text:
                self.cart_count_text.setText(f"({cart_count})")
                self.cart_count_text.show()
                print(f"[Page3] Updated cart_count_text: ({cart_count})")
            
            self.set_visual_state(True) # Update visual state
            print(f"[Page3] Updated button state for {product_name} to ADDED")
            
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, ProductPage):
                    widget.update_cart_count()
                    break
            
            ProductCard._cooldown_timer.start(500)
            print("[Page3] Started global add-to-cart cooldown for 0.5s")
            
        except Exception as e:
            print(f"[Page3] Error adding to cart: {e}")
            ProductCard._add_to_cart_cooldown = False

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
        self.setFixedSize(280, 70)
        self.current_category = "All Categories"  # Lưu category tiếng Anh hiện tại
        self.setText(_("productPage.categories.All Categories"))
        self.setFont(QFont("Josefin Sans", 22))  
        self.setCursor(Qt.PointingHandCursor)
        
        # Style for main button
        self.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 3px solid #3D6F4A;
                border-radius: 15px;
                padding: 10px 25px;
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
                border: 3px solid #3D6F4A;
                border-radius: 15px;
                padding: 10px;
                min-width: 280px;
            }
            QMenu::item {
                padding: 15px 25px;
                border-radius: 8px;
                color: #3D6F4A;
                font-family: 'Josefin Sans';
                font-size: 24pt;  /* Increased from 18pt to 24pt */
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
            
            # Sử dụng CartManager để truy cập CartState
            cart_manager = CartManager()
            print(f"[Page3] Initializing ProductPage")
            print(f"[Page3] Initial cart count: {cart_manager.get_cart_count()}")
            print(f"[Page3] Initial cart items: {cart_manager.get_cart_items()}")
            # Đăng ký callback với CartState thông qua CartManager
            cart_manager.cart_state.register_change_callback(self.update_cart_count)
            
            # Check for new products before initializing UI
            self.check_for_new_products()
            
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
            
            # Setup timer for frequent product updates (check every 5 seconds)
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.check_for_new_products)
            self.update_timer.start(5000)  # 5000 ms = 5 seconds
            print("[Page3] Started product update timer (5-second interval)")
        
        # Always update translations when the page is initialized or shown again
        self.update_translations()
        
        # Update cart count when initializing or shown againor
        self.update_cart_count()

    def check_for_new_products(self):
        """Check for new products directly from the API and update the display if found - optimized for speed"""
        try:
            # Get current products from cache to be faster
            if not ProductPage._products_cache:
                # If cache is empty, we're already loading products elsewhere
                return
                
            current_products = ProductPage._products_cache
            existing_product_ids = {product["product_id"] for product in current_products}
            something_changed = False

            # 1. Check for new products
            try:
                response = requests.get(PRODUCTS_CHECK_NEW_API, timeout=2)
                if response.status_code == 200:
                    api_data = response.json()
                    new_products_data = api_data.get("products", [])
                    new_products_found = []
                    for product in new_products_data:
                        product_id = product.get("product_id")
                        if product_id and product_id not in existing_product_ids:
                            if "low_stock_threshold" in product:
                                del product["low_stock_threshold"]
                            new_products_found.append(product)
                            existing_product_ids.add(product_id)
                    
                    if new_products_found:
                        print(f"[Page3] Adding {len(new_products_found)} new products to display")
                        current_products.extend(new_products_found)
                        ProductPage._products_cache = current_products
                        self.add_new_product_cards(new_products_found)
                        something_changed = True
            except requests.exceptions.Timeout:
                pass # Skip silently
            except Exception as e:
                print(f"[Page3] Error fetching or processing new products: {e}")

            # 2. Check for edited products
            try:
                response = requests.get(PRODUCTS_CHECK_EDITS_API, timeout=2)
                if response.status_code == 200:
                    api_data = response.json()
                    edited_products_data = api_data.get("edits", [])
                    if edited_products_data:
                        print(f"[Page3] Processing {len(edited_products_data)} product edits.")
                        for edit in edited_products_data:
                            product_id_to_edit = edit.get("product_id")
                            field_to_change = edit.get("field_changed")
                            new_value = edit.get("new_value")

                            if product_id_to_edit is not None and field_to_change and new_value is not None:
                                # Update in _products_cache
                                product_updated_in_cache = False
                                for p_idx, p_cache in enumerate(ProductPage._products_cache):
                                    if p_cache.get("product_id") == product_id_to_edit:
                                        if p_cache.get(field_to_change) != new_value:
                                            print(f"[Page3] Updating product ID {product_id_to_edit} in _products_cache: field '{field_to_change}' to '{new_value}'")
                                            ProductPage._products_cache[p_idx][field_to_change] = new_value
                                            product_updated_in_cache = True
                                            something_changed = True
                                        break
                                
                                # Update ProductCard in _cards_cache
                                if product_updated_in_cache: # Only update card if product cache was changed
                                    for card in ProductPage._cards_cache:
                                        if card.product.get("product_id") == product_id_to_edit:
                                            # The card.product is a reference to the item in _products_cache, so it's already updated.
                                            # We just need to tell the card to refresh its display.
                                            card.refresh_ui()
                                            print(f"[Page3] Refreshed UI for edited product ID {product_id_to_edit}")
                                            break
            except requests.exceptions.Timeout:
                pass # Skip silently
            except Exception as e:
                print(f"[Page3] Error fetching or processing product edits: {e}")

            # 3. Check for deleted products
            try:
                response = requests.get(PRODUCTS_CHECK_DELETIONS_API, timeout=2)
                if response.status_code == 200:
                    api_data = response.json()
                    deleted_products_data = api_data.get("deletions", [])
                    product_ids_to_delete = {d.get("product_id") for d in deleted_products_data if d.get("product_id") is not None}

                    if product_ids_to_delete:
                        print(f"[Page3] Processing deletion for product IDs: {product_ids_to_delete}")
                        # Remove from _products_cache
                        original_product_count = len(ProductPage._products_cache)
                        ProductPage._products_cache = [p for p in ProductPage._products_cache if p.get("product_id") not in product_ids_to_delete]
                        if len(ProductPage._products_cache) != original_product_count:
                            something_changed = True

                        # Remove from _cards_cache and grid_layout
                        cards_to_remove = [card for card in ProductPage._cards_cache if card.product.get("product_id") in product_ids_to_delete]
                        if cards_to_remove:
                            for card_to_remove in cards_to_remove: # renamed card to card_to_remove to avoid conflict
                                print(f"[Page3] Removing card for product ID {card_to_remove.product.get('product_id')} from UI and cache.")
                                card_to_remove.hide()
                                self.grid_layout.removeWidget(card_to_remove)
                                card_to_remove.deleteLater() # Important for cleanup
                                ProductPage._cards_cache.remove(card_to_remove)
                            something_changed = True # Ensure refresh if cards were removed
            except requests.exceptions.Timeout:
                pass # Skip silently
            except Exception as e:
                print(f"[Page3] Error fetching or processing product deletions: {e}")

            # If anything changed, save to JSON and update display
            if something_changed:
                print("[Page3] Product data changed, saving and refreshing display.")
                threading.Thread(target=self._save_product_json, 
                               args=(ProductPage._products_cache,), 
                               daemon=True).start()
                
                # Reapply the current category filter to update the view
                if hasattr(self, 'category_dropdown') and hasattr(self.category_dropdown, 'current_category'):
                    current_category = self.category_dropdown.current_category
                    self.filter_products(current_category) # This will re-populate the grid
                else:
                    self.filter_products("All Categories") # Default if no category selected
                
        except Exception as e:
            print(f"[Page3] Error in check_for_new_products: {e}")

    def _save_product_json(self, products):
        """Save products to JSON file in a separate thread to not block UI"""
        try:
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'json', 'products.json')
            with open(json_path, 'w', encoding='utf-8') as file:
                json.dump(products, file, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Page3] Error saving products.json: {e}")

    def add_new_product_cards(self, new_products):
        """Create product cards for new products and add them to the cache"""
        if not new_products:
            return
            
        try:
            print(f"[Page3] Creating cards for {len(new_products)} new products")
            
            # Calculate starting position for new cards
            start_index = len(ProductPage._cards_cache)
            
            # Create new cards
            for i, product in enumerate(new_products):
                card = ProductCard(product, self.cart_count_text)
                
                # Calculate grid position
                idx = start_index + i
                row = (idx // 5) * 2  # 5 products per row
                col = idx % 5
                
                # Store position in card
                card.grid_pos = (row, col)
                
                # Add to cache
                ProductPage._cards_cache.append(card)
                print(f"[Page3] Created card for {product['name']} at position ({row}, {col})")
                
            print(f"[Page3] Added {len(new_products)} cards to cache. Total cards: {len(ProductPage._cards_cache)}")
            
        except Exception as e:
            print(f"[Page3] Error adding new product cards: {e}")

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
                row = (i // 5) * 2  # Changed from 4 to 5 products per row
                col = i % 5  # Changed from 4 to 5 columns
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
            row = (i // 5) * 2  # Changed from 4 to 5 products per row
            col = i % 5  # Changed from 4 to 5 columns
            card = ProductCard(product, self.cart_count_text)  # Pass cart_count_text reference
            card.font_family = font_family
            # Store original position
            card.grid_pos = (row, col)
            self.grid_layout.addWidget(card, row, col)
            ProductPage._cards_cache.append(card)
            # Process events more frequently for better responsiveness during initial load
            QApplication.processEvents() # Was: if (i + 1) % 5 == 0:

    def closeEvent(self, event):
        """Clean up when closing"""
        try:
            # Stop the update timer if it exists
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
                print("[Page3] Stopped product update timer")
                
            # Unregister callback
            cart_manager = CartManager()
            cart_manager.cart_state.unregister_change_callback(self.update_cart_count)
            
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
        main_layout.setContentsMargins(80, 0, 80, 20)  # Giảm top margin xuống 0
        main_layout.setSpacing(0)  # Giảm spacing xuống 0 để các phần tử sát nhau hơn

        # Top section with logo and header
        top_layout = QHBoxLayout()
        top_layout.setSpacing(40)
        top_layout.setContentsMargins(0, 0, 0, 0)  # Giảm margin xuống 0
        
        # Logo - use exact same size as page1 (350x146)
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(350, 146, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Matched with page1
        logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(logo_label)

        # Header - use translation with larger font
        self.header_label = QLabel(_("productPage.title"))  # Store reference to header label
        self.header_label.setFont(QFont("Inria Sans", 64))  # Increased from 40 to 64 to match page1
        self.header_label.setStyleSheet("color: #3D6F4A;")
        self.header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(self.header_label)
        
        # Add spacing to push category dropdown and home button to the right
        top_layout.addStretch(1)
        
        # Category dropdown - larger size
        self.category_dropdown = CategoryDropdown(self)
        top_layout.addWidget(self.category_dropdown)
        
        # Add home button - larger size
        home_button = QPushButton()
        home_button.setFixedSize(80, 80)  # Increased from 60x60 to 80x80 to match page1
        home_button.setCursor(Qt.PointingHandCursor)
        home_button.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                border: none;
                border-radius: 40px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3e5c38;
            }
        """)
        
        # Add home icon - larger
        home_icon = QLabel()
        home_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'home.png')
        home_pixmap = QPixmap(home_icon_path)
        if not home_pixmap.isNull():
            home_icon.setPixmap(home_pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Increased from 50x50
        home_icon.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        # Create container for icon
        icon_container = QWidget()
        icon_container.setFixedSize(60, 60)  # Increased from 50x50
        icon_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
                border-radius: 30px; 
            }
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(home_icon, alignment=Qt.AlignCenter)
        home_button.setLayout(icon_layout)
        
        # Connect home button to return to page1
        home_button.clicked.connect(self.return_to_welcome)
        top_layout.addWidget(home_button)

        main_layout.addLayout(top_layout)
        
        # Scroll Area for products - larger height
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(820)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                margin-right: 0px;
                margin-top: 0px;
                margin-bottom: 10px;
            }
            QScrollBar:vertical {
                border: none;
                background: white;
                border-radius: 15px;
                width: 40px;
                margin: 12px 0px 12px 0px;
                height: 696px;
                subcontrol-origin: margin;
                subcontrol-position: top;
            }
            QScrollBar::handle:vertical {
                background: #D9D9D9;
                border-radius: 15px;
                min-height: 50px;
                margin: 3px;
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
                /* Removed unsupported property: display: none; */
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
                        scroll_amount = dy * 2.5# Adjust sensitivity
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

        # Container widget for the grid - wider
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container.setFixedWidth(1800) 
        self.container.setMinimumHeight(720) 
        
        # Grid layout for products - adjust spacing
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(30)  # Giảm spacing xuống để các card gần nhau hơn
        self.grid_layout.setContentsMargins(20, 0, 150, 30)
        self.grid_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)

        scroll_area.setWidget(self.container)
        
        # Create a wrapper layout to properly align the scroll area
        scroll_wrapper = QHBoxLayout()
        scroll_wrapper.setContentsMargins(0, 0, 0, 0)
        scroll_wrapper.addWidget(scroll_area)
        
        main_layout.addLayout(scroll_wrapper)

        main_layout.addSpacing(20) 

        # Create a horizontal layout for the bottom section
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create container for the entire bottom section with fixed height 
        bottom_container = QWidget()
        bottom_container.setFixedHeight(80)  # Increased from 45 to 80
        bottom_container_layout = QHBoxLayout(bottom_container)
        bottom_container_layout.setContentsMargins(40, 0, 40, 0)  # Increased left/right margins
        
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
        button_container.setFixedSize(375, 80)  
        button_container.setStyleSheet("""
            QWidget {
                background-color: #507849;
                border-radius: 35px;
            }
        """)
        
        # Create button content layout
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(40, 0, 30, 0) 
        button_layout.setSpacing(15) 

        cart_icon = QLabel()
        cart_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'yourcarticon.png')
        self.normal_pixmap = QPixmap(cart_icon_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Tăng từ 36x36 lên 42x42
        self.hover_pixmap = QPixmap(cart_icon_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Tăng từ 36x36 lên 42x42
        cart_icon.setPixmap(self.normal_pixmap)
        
        # Add cart text and count - larger font
        self.cart_text = QLabel(_("productPage.yourCart") + " ")  
        self.cart_text.setFont(QFont("Inter", 22, QFont.Bold)) 
        self.cart_text.setStyleSheet("color: white;")
        
        # Add cart count with red color - larger font
        self.cart_count_text = QLabel("(0)")
        self.cart_count_text.setFont(QFont("Inter", 22, QFont.Bold))  # Tăng từ 18 lên 22 để khớp với cart_text
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
        cart_manager = CartManager()
        cart_count = cart_manager.get_cart_count()
        if cart_count > 0:
            self.cart_count_text.setText(f"({cart_count})")
            self.cart_count_text.show()
        else:
            self.cart_count_text.hide()

        # Add bottom container to main layout
        main_layout.addWidget(bottom_container)

    def setup_loading_indicator(self):
        self.loading_widget = QWidget(self)
        self.loading_widget.setGeometry(0, 0, self.width(), self.height())
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setSpacing(20)  # Increased spacing
        loading_layout.setAlignment(Qt.AlignCenter)  # Center alignment
        
        # Create loading text
        loading_text = QLabel("Loading products...")
        loading_text.setFont(QFont("Poppins", 18))  # Increased from 11 to 18
        loading_text.setStyleSheet("color: #3D6F4A;")
        loading_text.setAlignment(Qt.AlignCenter)
        
        # Create loading GIF
        loading_gif = QLabel()
        loading_gif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'loading_gif.gif')
        self.gif_movie = QMovie(loading_gif_path)
        self.gif_movie.setScaledSize(QSize(200, 200))  # Increased from 100x100 to 200x200
        loading_gif.setMovie(self.gif_movie)
        self.gif_movie.start()
        
        loading_layout.addWidget(loading_text, alignment=Qt.AlignCenter)
        loading_layout.addWidget(loading_gif, alignment=Qt.AlignCenter)
        
        # Position the loading widget in the center
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
        """Cải tiến chuyển đổi sang trang shopping"""
        if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
            self.transition_in_progress = True
            
            # Xử lý các sự kiện đang chờ trước
            QApplication.processEvents()
            
            # Bắt đầu tính thời gian
            start_time = PageTiming.start_timing()

            # Tạo transition overlay ở simple_mode
            from components.PageTransitionOverlay import PageTransitionOverlay
            # Use simple_mode and disable the original loading text/progress bar for default mode
            loading_overlay = PageTransitionOverlay(self, show_loading_text_for_default_mode=False, simple_mode=True)
            
            def proceed_with_page_switch():
                # Tạo trang ShoppingPage
                from page4_shopping import ShoppingPage
                self.shopping_page = ShoppingPage()
                
                # Hiển thị trang shopping
                self.shopping_page.show()

                # Ẩn trang hiện tại (ProductPage)
                self.hide()
                
                # Ẩn overlay (ngay lập tức trong simple_mode)
                loading_overlay.fadeOut(None) 
                
                # Ghi nhận thời gian và reset cờ
                PageTiming.end_timing(start_time, "ProductPage", "ShoppingPage")
                self.transition_in_progress = False
            
            # Hiện overlay. Trong simple_mode, fadeIn là ngay lập tức và sau đó gọi callback.
            loading_overlay.fadeIn(proceed_with_page_switch)

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
            
            # Sắp xếp lại các sản phẩm - display 5 per row
            for i, card in enumerate(sorted_cards):
                row = (i // 5) * 2  # Changed from 4 to 5 products per row
                col = i % 5  # Changed from 4 to 5 columns
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
            
            # Thêm sản phẩm đã lọc và sắp xếp vào vị trí mới - display 5 per row
            for i, card in enumerate(sorted_filtered_cards):
                row = (i // 5) * 2  # Changed from 4 to 5 products per row
                col = i % 5  # Changed from 4 to 5 columns
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

    def update_cart_count(self, data=None):
        """Cập nhật hiển thị số lượng giỏ hàng"""
        try:
            cart_manager = CartManager()
            cart_count = cart_manager.get_cart_count()
            print(f"[Page3] Updating cart count: {cart_count}")
            
            # Cập nhật cart_count_text nếu có
            if hasattr(self, 'cart_count_text'):
                if cart_count > 0:
                    self.cart_count_text.setText(f"({cart_count})")
                    self.cart_count_text.show()
                    print(f"[Page3] Updated cart_count_text: ({cart_count})")
                else:
                    self.cart_count_text.setText("")
                    self.cart_count_text.hide()
                    print("[Page3] Cart is empty, hiding count display")
            
            # Cập nhật cart_btn nếu có
            if hasattr(self, 'cart_btn'):
                self.cart_btn.update_count(cart_count)
                print(f"[Page3] Updated cart_btn counter")
                
        except Exception as e:
            print(f"[Page3] Error updating cart count: {e}")

    def showEvent(self, event):
        """Xử lý sự kiện khi trang được hiển thị"""
        super().showEvent(event)
        
        # Đảm bảo trang hiển thị đầy đủ
        self.setWindowOpacity(1.0)
        
        # Check for new products when the page is shown
        self.check_for_new_products()
        
        # Check if we're transitioning from page1
        coming_from_page1 = (hasattr(self, 'from_page') and self.from_page == "page1") or (hasattr(self, 'from_page1') and self.from_page1)
        print(f"[Page3] showEvent - coming_from_page1: {coming_from_page1}")
        
        # Reset cart state if coming from page1
        if coming_from_page1:
            print("[Page3] Coming from page1, clearing cart state")
            cart_manager = CartManager()
            cart_manager.clear_cart()
            
            # Reset button states for all product cards
            if hasattr(self, '_cards_cache') and self._cards_cache:
                print(f"[Page3] Resetting {len(self._cards_cache)} product cards")
                for card in self._cards_cache:
                    card.add_to_cart_btn.setText(_("productPage.addToCart"))
                    card.add_to_cart_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #507849;
                            color: white;
                            border: none;
                            border-radius: 18px;
                            padding: 8px 12px;
                            margin: 5px 10px;
                        }
                        QPushButton:hover {
                            background-color: #3D6F4A;
                        }
                        QPushButton:pressed {
                            background-color: #2C513A;
                        }
                    """)
        else:
            # Nếu đến từ trang khác (không phải page1), cập nhật trạng thái các button
            print("[Page3] Coming back from other page, updating button states")
            self.force_update_all_button_states()
        
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
        cart_manager = CartManager()
        cart_count = cart_manager.get_cart_count()
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
            
        # Luôn cập nhật lại trạng thái của tất cả buttons, bất kể đến từ đâu
        # Điều này đảm bảo các thay đổi từ page4 được cập nhật chính xác
        self.force_update_all_button_states()
        
        # Reset vị trí cuộn nếu đến từ page1
        if coming_from_page1:
            print(f"[Page3] Resetting scroll position, coming from page1")
            scroll = self.findChild(QScrollArea)
            if scroll:
                scroll.verticalScrollBar().setValue(0)

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
            
    def update_all_cards(self):
        """Cập nhật trạng thái của tất cả các thẻ sản phẩm"""
        try:
            # Chỉ thực hiện nếu có cards trong cache
            if ProductPage._cards_cache:
                print(f"[Page3] Updating all product cards, total: {len(ProductPage._cards_cache)}")
                for card in ProductPage._cards_cache:
                    try:
                        if hasattr(card, 'update_button_state'): # This will now call the deprecated version
                            card.update_button_state()          # which internally calls set_visual_state
                    except Exception as e:
                        print(f"[Page3] Error updating card: {e}")
        except Exception as e:
            print(f"[Page3] Error updating all cards: {e}")

    def force_update_all_button_states(self):
        """Bắt buộc cập nhật trạng thái của tất cả các button dựa trên giỏ hàng hiện tại.
        Optimized to read JSON file only once and use a set for efficient lookup.
        """
        try:
            cart_manager = CartManager()
            print(f"[Page3] Forcing update all button states. CartManager has {len(cart_manager.get_cart_items())} items")
            
            # 1. Get product names from CartManager
            product_names_in_cart_manager = set()
            cart_manager_items = cart_manager.get_cart_items()
            for item in cart_manager_items:
                if isinstance(item, dict) and 'product' in item and isinstance(item['product'], dict) and 'name' in item['product']:
                    product_names_in_cart_manager.add(item['product']['name'])
                elif isinstance(item, dict) and 'product_name' in item:
                    product_names_in_cart_manager.add(item['product_name'])
                elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], dict) and 'name' in item[0]:
                    product_names_in_cart_manager.add(item[0]['name'])
            
            # 2. Get product names from shopping_process.json (read only once)
            product_names_from_json = set()
            try:
                json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'shopping_process.json')
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        json_data = json.load(f)
                        for product_info in json_data.get('detected_products', []):
                            if 'product_name' in product_info:
                                product_names_from_json.add(product_info['product_name'])
            except Exception as e:
                print(f"[Page3] Error reading shopping_process.json in force_update: {e}")

            # 3. Combine product names into a single set for efficient lookup
            all_product_names_in_cart = product_names_in_cart_manager.union(product_names_from_json)
            print(f"[Page3] Combined product names in cart: {all_product_names_in_cart}")
            
            # 4. Update visual state of all cards
            if ProductPage._cards_cache:
                print(f"[Page3] Updating visual state for {len(ProductPage._cards_cache)} product cards")
                for card in ProductPage._cards_cache:
                    try:
                        if not hasattr(card, 'product') or not isinstance(card.product, dict) or 'name' not in card.product:
                            print(f"[Page3] Card has invalid product: {getattr(card, 'product', None)}")
                            if hasattr(card, 'set_visual_state'): card.set_visual_state(False) # Default for invalid cards
                            continue
                            
                        product_name = card.product['name']
                        is_in_cart = product_name in all_product_names_in_cart
                        
                        if hasattr(card, 'set_visual_state'):
                            card.set_visual_state(is_in_cart)
                            # Optional: print specific state change
                            # print(f"[Page3] Set {product_name} button to {'ADDED' if is_in_cart else 'ADD'} state") 
                        else:
                             print(f"[Page3] Card for {product_name} is missing set_visual_state method.")

                    except Exception as e:
                        print(f"[Page3] Error updating card visual state for {getattr(card.product, 'name', 'UNKNOWN')}: {e}")
        except Exception as e:
            print(f"[Page3] Error in force_update_all_button_states: {e}")

class ProductCardDialog(QDialog):
    def __init__(self, product, image, parent=None):
        super().__init__(parent)
        self.product = product
        self.image = image
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedSize(600, 750)  # Increased from 400x500 to 600x750
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 20px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)  # Increased margins
        layout.setSpacing(25)  # Increased spacing
        
        # Image - larger
        image_label = QLabel()
        if self.image:
            image_label.setPixmap(self.image.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Increased from 200x200
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # Name - larger font
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 22, QFont.Bold))  # Increased from 14 to 22
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        # Price - larger font
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 18))  # Increased from 12 to 18
        price_label.setStyleSheet("color: #E72225;")
        price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(price_label)
        
        # Description - larger font
        desc_label = QLabel(self.product.get('description', 'No description available'))
        desc_label.setFont(QFont("Josefin Sans", 16))  # Increased from 10 to 16
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add to Cart button - larger
        add_to_cart_btn = QPushButton(_("productPage.addToCart"))
        add_to_cart_btn.setFont(QFont("Josefin Sans", 18))  # Increased from 12 to 18
        add_to_cart_btn.setCursor(Qt.PointingHandCursor)
        add_to_cart_btn.setFixedHeight(50)  # Increased from 30 to 50
        add_to_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 15px;
                margin: 15px 30px;
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
        
        # Close button - larger
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont("Josefin Sans", 18))  # Increased from 12 to 18
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedHeight(50)  # Increased from 30 to 50
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E72225;
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 15px;
                margin: 15px 30px;
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