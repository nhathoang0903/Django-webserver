import json
import weakref
from functools import lru_cache
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QPushButton, QApplication, QFrame, QGridLayout, QScrollArea, QDialog, QGraphicsBlurEffect, QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QObject, QEvent, QTimer, QPropertyAnimation, QRect, QParallelAnimationGroup, QPoint, QEasingCurve
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon, QImage, QCursor
from PyQt5.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt5.QtCore import QUrl
import os
import cv2
import numpy as np
import time
from product_detector import ProductDetector
from product_modal import ProductModal
from cart_item_widget import CartItemWidget
from cart_state import CartState
from cancelshopping_modal import CancelShoppingModal
from PyQt5 import sip
from countdown_overlay import CountdownOverlay
from page_timing import PageTiming
from components.PageTransitionOverlay import PageTransitionOverlay
from base_page import BasePage  
import requests
from PyQt5.QtCore import QThread, pyqtSignal
import time
from config import CART_END_SESSION_STATUS_API, DEVICE_ID, CART_CHECK_PAYMENT_SIGNAL, CART_END_SESSION_API
from threading import Thread

class SessionMonitor(QThread):
    """Thread to monitor cart session status"""
    session_ended = pyqtSignal()  # Signal when session ends

    def __init__(self, page_name="page4"):
        super().__init__()
        self.is_running = True
        self.page_name = page_name  

    def run(self):
        if self.page_name != "page4":  # Ensure this thread only runs in page4
            print(f"SessionMonitor is disabled for {self.page_name}")
            return
            
        while self.is_running:
            try:
                # Get session status
                url = f"{CART_END_SESSION_STATUS_API}{DEVICE_ID}/status/"
                # print(f"Checking session status: {url}")
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    # print(f"Session status response: {data}")
                    
                    if data.get("device_status") == "available":
                        print(f"Session ended at: {data.get('last_session_end')}")
                        self.session_ended.emit()
                        break  # Exit thread when session ends
                        
            except Exception as e:
                print(f"Error checking session status: {e}")
                
            time.sleep(0.5)  # Poll every 500ms

    def stop(self):
        self.is_running = False

class PaymentSignalMonitor(QThread):
    """Thread to monitor payment signals"""
    payment_signal_received = pyqtSignal()  # Signal when payment is requested

    def __init__(self, page_name="page4"):
        super().__init__()
        self.is_running = True
        self.page_name = page_name  # Add page name to restrict execution

    def run(self):
        if self.page_name != "page4":  # Ensure this thread only runs in page4
            print(f"PaymentSignalMonitor is disabled for {self.page_name}")
            return

        while self.is_running:
            try:
                # Get payment signal status
                url = f"{CART_CHECK_PAYMENT_SIGNAL}{DEVICE_ID}/"
                # print(f"Checking payment signal: {url}")
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    # print(f"Payment signal response: {data}")
                    
                    if "signal_type" in data and data["signal_type"] == "payment":
                        print("Payment signal received, switching to QR page")
                        self.payment_signal_received.emit()
                        break  # Exit thread when signal received
                        
            except Exception as e:
                print(f"Error checking payment signal: {e}")
                
            time.sleep(0.5)  # Poll every 500ms

    def stop(self):
        self.is_running = False

class CartItemsScrollArea(QScrollArea):
    """Custom scroll area with touch scrolling support for cart items"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: white;
                width: 15px;
                margin: 0px;
                margin-left: 5px;
            }
            QScrollBar::handle:vertical {
                background: #D9D9D9;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                height: 0px;
                background: transparent;
            }
        """)
        
        # Variables for mouse tracking
        self.mouse_pressed = False
        self.last_mouse_pos = QPoint()
        self.velocity = 0
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.decelerate_scroll)
        self.scroll_timer.setInterval(16)  # ~60fps
        
        # Variables for bounce effect
        self.bounce_animation = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self.bounce_animation.setDuration(300)
        self.bounce_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.is_bouncing = False
        
        # Enable viewport mouse tracking
        self.viewport().setMouseTracking(True)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            self.last_mouse_pos = event.pos()
            self.velocity = 0
            self.scroll_timer.stop()
            if self.bounce_animation.state() == QPropertyAnimation.Running:
                self.bounce_animation.stop()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.mouse_pressed:
            delta = event.pos().y() - self.last_mouse_pos.y()
            
            # Get current scroll value and bounds
            scrollbar = self.verticalScrollBar()
            current_value = scrollbar.value()
            min_value = scrollbar.minimum()
            max_value = scrollbar.maximum()
            
            # Check if we're at the top or bottom boundary
            at_top = current_value == min_value and delta > 0
            at_bottom = current_value == max_value and delta < 0
            
            if at_top or at_bottom:
                # Apply resistance when pulling beyond limits
                delta = delta * 0.3  # Reduce scroll effect to create resistance
                
            # Apply scroll - convert to int
            scrollbar.setValue(int(current_value - delta))
            
            # Update velocity
            self.velocity = delta
            self.last_mouse_pos = event.pos()
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.mouse_pressed:
            self.mouse_pressed = False
            
            # Get current scroll value and bounds
            scrollbar = self.verticalScrollBar()
            current_value = scrollbar.value()
            min_value = scrollbar.minimum()
            max_value = scrollbar.maximum()
            
            # Check if we need to apply bounce animation
            if current_value <= min_value and self.velocity > 0:
                # Bounce from top
                self.apply_bounce_animation(min_value)
            elif current_value >= max_value and self.velocity < 0:
                # Bounce from bottom
                self.apply_bounce_animation(max_value)
            # Otherwise start deceleration
            elif abs(self.velocity) > 5:
                self.scroll_timer.start()
                
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def apply_bounce_animation(self, target_value):
        """Apply bounce animation when reaching the end of scrollable area"""
        self.is_bouncing = True
        self.bounce_animation.setStartValue(self.verticalScrollBar().value())
        self.bounce_animation.setEndValue(target_value)
        self.bounce_animation.start()
    
    def wheelEvent(self, event):
        """Enhanced wheel event for smoother scrolling"""
        # Get the delta value from the wheel event
        delta = event.angleDelta().y()
        
        # Calculate scroll amount (faster for larger deltas)
        scroll_amount = delta / 2
        
        # Get current scroll value and bounds
        scrollbar = self.verticalScrollBar()
        current_value = scrollbar.value()
        min_value = scrollbar.minimum()
        max_value = scrollbar.maximum()
        
        # Check if we're at boundaries
        at_top = current_value == min_value and scroll_amount > 0
        at_bottom = current_value == max_value and scroll_amount < 0
        
        if at_top or at_bottom:
            # Apply resistance when at boundaries
            scroll_amount = scroll_amount * 0.3
        
        # Apply scroll - convert to int
        scrollbar.setValue(int(current_value - scroll_amount))
        
        # Start inertial scrolling with the wheel velocity
        self.velocity = delta / 12
        if not self.scroll_timer.isActive() and abs(self.velocity) > 5:
            self.scroll_timer.start()
        
        event.accept()
    
    def decelerate_scroll(self):
        # Apply deceleration
        self.velocity *= 0.9
        
        # Stop when velocity is very low
        if abs(self.velocity) < 0.5:
            self.scroll_timer.stop()
            return
            
        # Get current scroll value and bounds
        scrollbar = self.verticalScrollBar()
        current_value = scrollbar.value()
        min_value = scrollbar.minimum()
        max_value = scrollbar.maximum()
        
        # Check if we've hit boundaries
        if (current_value <= min_value and self.velocity > 0) or (current_value >= max_value and self.velocity < 0):
            self.scroll_timer.stop()
            # Apply bounce animation
            self.apply_bounce_animation(min_value if current_value <= min_value else max_value)
            return
            
        # Continue scrolling with decelerating velocity - convert to int
        scrollbar.setValue(int(current_value - self.velocity))

class ShoppingPage(BasePage):  # Changed from QWidget to BasePage
    # Class level attributes for critical components
    _current_frame = None
    _processing = False
    _widgets_cache = None
    _image_cache = None
    _cleanup_tasks = None
    _detector = None
    _product_modal = None
    _cancel_modal = None

    def __init__(self):
        super().__init__()  # Call BasePage init
        self.installEventFilter(self)  # Register event filter
        
        # Initialize memory management attributes first
        ShoppingPage._current_frame = None  # Ensure class attribute is initialized
        self._processing = False
        self._widgets_cache = weakref.WeakValueDictionary()
        self._image_cache = {}
        self._cleanup_tasks = []
        self.frame_count = 0
        self.detection_start_time = None  # Add this line
        self.temp_image_counter = 0  # Counter for temp images
        self.setup_temp_folder()
        self.frame_buffer = []  # Buffer to store frames for quality check
        self.last_detect_time = 0  # Track last detection time
        self.add_cart_start_time = None  # Add new timing variable
        
        # Initialize camera related attributes
        self.camera = None
        self.camera_active = False
        self.product_detected = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Initialize other components
        self.home_page = None
        self.cart_state = CartState()
        self.cart_state.save_to_json()
        self.cart_items = []
        self.right_section = None
        self.blur_effect = None
        self.opacity_effect = None
        self.warning_animation = None

        # Initialize UI 
        self.load_fonts()
        self.init_ui()
        
        # Initialize modals
        camera_height = 299
        self.product_modal = self.get_product_modal()
        self.cancel_modal = CancelShoppingModal(self)
        self.cancel_modal.cancelled.connect(self.go_home)
        self.cancel_modal.hide()
        
        # Add toast notification attribute
        self.toast_label = None
        
        # Thêm flag để theo dõi trạng thái thanh toán
        self.payment_completed = False 
        self.countdown_overlay = None
        self.transition_overlay = PageTransitionOverlay(self)
        self.transition_in_progress = False  # Add this line

        # Initialize session monitor
        self.session_monitor = SessionMonitor(page_name="page4")
        self.payment_monitor = PaymentSignalMonitor(page_name="page4")  # Pass page name here
        
        # Connect signals
        self.session_monitor.session_ended.connect(self.handle_remote_session_end)
        self.payment_monitor.payment_signal_received.connect(self.handle_payment_signal)
        
        # Start both monitors with offset
        self.session_monitor.start()
        QTimer.singleShot(250, self.payment_monitor.start)  # Start with 250ms offset
        self.payment_page = None  # Add reference to payment page
        self.preload_images()  # Preload images for faster loading

    @lru_cache(maxsize=32)
    def load_cached_image(self, path):
        """Cache image loading to reduce memory usage"""
        if (path not in self._image_cache):
            self._image_cache[path] = QPixmap(path)
        return self._image_cache[path]
        
    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        self.setWindowTitle('Shopping - Smart Shopping Cart')
        # Remove setGeometry and setFixedSize since handled by BasePage
        
        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Section
        left_section = QWidget()
        left_section.setFixedWidth(400)
        left_section.setStyleSheet("background-color: #F0F6F1;")
        
        # Change to QGridLayout with adjusted spacing
        left_layout = QGridLayout(left_section)
        left_layout.setContentsMargins(20, 10, 20, 20)  # Reduced top margin from 20 to 10
        left_layout.setSpacing(0)

        # Top section with logo - Row 0
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = self.load_cached_image(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setContentsMargins(0, 0, 0, 15)  # Add bottom margin to logo
        left_layout.addWidget(logo_label, 0, 0, 1, 2)  # row 0, col 0, rowspan 1, colspan 2

        # Buttons Container - Row 1 with adjusted margins
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 15)  # Reduce top margin to 0, keep bottom margin

        # Scan Button
        scan_button = self.create_button("SCAN", icon_path="camera.png")
        scan_button.clicked.connect(self.toggle_camera)
        buttons_layout.addWidget(scan_button)

        # Product Info Button
        product_info_button = self.create_button("PRODUCT INFO", icon_path="info.png")
        product_info_button.clicked.connect(self.show_product_page)
        # print("Open product info page")
        buttons_layout.addWidget(product_info_button)

        left_layout.addWidget(buttons_container, 1, 0, 1, 2)  # row 1, col 0, rowspan 1, colspan 2

        # Camera View Area - Row 2
        self.camera_frame = QFrame()
        self.camera_frame.setStyleSheet("""
            QFrame {
                background-color: #F0F6F1;
                border: 1.5px dashed #000000;
                border-radius: 9px;
            }
        """)
        self.camera_frame.setFixedSize(336, 318)  

        # Create a label for camera feed
        self.camera_label = QLabel(self.camera_frame)
        self.camera_label.setFixedSize(self.camera_frame.size())
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            QLabel {
                background-color: #F0F6F1;  
                border: 1.5px dashed #000000;
                border-radius: 9px;
            }
        """)

        # Create inner frame for scan area
        self.scan_area = QFrame(self.camera_frame)
        self.scan_area.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        # Make scan area fixed size and center it in camera frame
        self.scan_area.setFixedSize(245, 247)  # Make it square
        self.scan_area.move(
            (self.camera_frame.width() - self.scan_area.width()) // 2,
            (self.camera_frame.height() - self.scan_area.height()) // 2
        )

        # Add scan area icon (keep existing icon setup)
        self.camera_icon = QLabel(self.scan_area)
        scan_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    'assets', 'scanarea.png')
        self.camera_icon.setPixmap(QPixmap(scan_icon_path)
                            .scaled(97, 97, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.camera_icon.setAlignment(Qt.AlignCenter)
        
        # Center the icon in scan_area
        self.camera_icon.setGeometry(
            (self.scan_area.width() - 97) // 2,
            (self.scan_area.height() - 97) // 2,
            97, 97
        )

        left_layout.addWidget(self.camera_frame, 2, 0, 1, 2, Qt.AlignCenter)

        # Set vertical spacing between rows
        left_layout.setVerticalSpacing(5)  # Reduce space between rows

        # Add vertical stretch at the bottom if needed
        left_layout.setRowStretch(3, 1)  # Make row 3 (empty row) stretch

        # Right Section (Cart)
        self.right_section = QWidget()
        self.right_section.setFixedWidth(400)
        self.right_section.setStyleSheet("background-color: white;")

        # Main right layout
        self.right_layout = QVBoxLayout(self.right_section)
        self.right_layout.setContentsMargins(20, 35, 20, 20)
        self.right_layout.setSpacing(0)

        # Fixed header container with horizontal layout
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(60)
        self.header_widget.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Cart Header (left aligned)
        self.cart_header = QLabel("Your Cart")
        self.cart_header.setFont(QFont("Baloo", 24))
        self.cart_header.setStyleSheet("color: black; padding-top: 10px;")
        header_layout.addWidget(self.cart_header)

        # Cancel Shopping button (right aligned)
        self.cancel_shopping_btn = QPushButton("Cancel shopping")
        self.cancel_shopping_btn.setFixedSize(120, 35)
        self.cancel_shopping_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F3F3;
                border: 1px solid #D30E11;
                border-radius: 17px;
                color: #D30E11;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
                color: white;
            }
        """)
        self.cancel_shopping_btn.clicked.connect(self.show_cancel_dialog)
        self.cancel_shopping_btn.hide()  # Initially hidden
        header_layout.addWidget(self.cancel_shopping_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)

        # Add fixed header to main layout
        self.right_layout.addWidget(self.header_widget)

        # Content area (scrollable)
        self.content_widget = QFrame()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 20, 0, 0)
        self.right_layout.addWidget(self.content_widget)

        # Initialize cart display
        self.update_cart_display()

        main_layout.addWidget(left_section)
        main_layout.addWidget(self.right_section)  # Use stored reference

    def create_button(self, text, icon_path):
            button = QPushButton()
            button.setFixedSize(170, 40)  
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #507849;
                    border: none;
                    border-radius: 16px;
                    padding: 0px;  
                    text-align: center;
                }
            """)

            # Button Layout
            button_layout = QHBoxLayout(button)
            button_layout.setContentsMargins(5, 0, 5, 0)  
            button_layout.setSpacing(5)  
            button_layout.setAlignment(Qt.AlignCenter)  # Center the layout contents

            # Add left stretch to push content to center
            button_layout.addStretch()

            # Icon
            icon_label = QLabel()
            if text == "SCAN":
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    'assets', 'scanbutton_hover.png')
                text_color = "#FFFF00"  # Yellow for SCAN
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                            'assets', 'productinfobutton.png')
                text_color = "white"  # White for PRODUCT INFO

            if icon_path:
                icon_pixmap = QPixmap(icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(icon_pixmap)
                icon_label.setStyleSheet("background: transparent;")  
                button_layout.addWidget(icon_label)

            # Text
            text_label = QLabel(text)
            text_label.setStyleSheet(f"""
                color: {text_color}; 
                font-family: Inter;
                font-weight: bold;
                font-size: 12px;
                background: transparent;
                padding: 0px;
            """)
            text_label.setAlignment(Qt.AlignCenter)  # Center the text
            button_layout.addWidget(text_label)

            # Add right stretch to push content to center
            button_layout.addStretch()

            return button

    def update_cart_display(self):
        """Memory-optimized cart display"""
        # Clear widgets properly
        self.clear_layout(self.content_layout)
        
        # Update background color based on cart state
        self.right_section.setStyleSheet(
            f"background-color: {'#F3F3F3' if self.cart_state.cart_items else 'white'};"
        )
        
        # Keep header transparent
        self.header_widget.setStyleSheet("background-color: transparent;")

        if not self.cart_state.cart_items:
            # Empty cart display
            empty_container = QWidget()
            empty_layout = QVBoxLayout(empty_container)
            empty_layout.setContentsMargins(0, 20, 0, 0)  # Reduced top margin from 50 to 20
            
            empty_layout.addStretch(2)  # Reduced stretch from 3 to 2
            
            empty_text = QLabel("Empty")
            empty_text.setFont(QFont("Inria Sans", 30))
            empty_text.setStyleSheet("color: #F68003;")
            empty_text.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(empty_text)
            
            empty_layout.addSpacing(20)
            
            empty_cart_label = QLabel()
            empty_cart_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                         'assets', 'emptycart.png')
            empty_cart_pixmap = QPixmap(empty_cart_path)
            if not empty_cart_pixmap.isNull():
                empty_cart_label.setPixmap(empty_cart_pixmap.scaled(100, 100, 
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation))
            empty_cart_label.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(empty_cart_label)
            
            empty_layout.addStretch(3)  # Increased stretch from 2 to 3
            
            self.content_layout.addWidget(empty_container)
        else:
            # Container for cart items
            scroll_container = QWidget()
            scroll_layout = QVBoxLayout(scroll_container)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            
            # Create scroll area for items with custom scrolling behavior
            scroll_area = CartItemsScrollArea()
            
            # Items container
            items_container = QWidget()
            items_layout = QVBoxLayout(items_container)
            items_layout.setSpacing(30)
            items_layout.setContentsMargins(0, 0, 0, 0)  # Remove right margin

            # Add cart items
            highlighted_name = getattr(self, '_highlight_product_name', None)
            for i, (product, quantity) in enumerate(reversed(self.cart_state.cart_items)):
                item_widget = CartItemWidget(product, quantity)
                item_widget.quantityChanged.connect(
                    lambda q, idx=len(self.cart_state.cart_items)-1-i: self.update_item_quantity(idx, q)
                )
                item_widget.itemRemoved.connect(
                    lambda idx=len(self.cart_state.cart_items)-1-i: self.remove_cart_item(idx)
                )
                
                if highlighted_name and product['name'] == highlighted_name:
                    item_widget.highlight()
                    self._highlight_product_name = None
                    
                items_layout.addWidget(item_widget)

            # Add stretch to push items up
            items_layout.addStretch()
            
            # Set items container to scroll area
            scroll_area.setWidget(items_container)
            scroll_layout.addWidget(scroll_area)
            
            # Add scroll container to main content
            self.content_layout.addWidget(scroll_container, stretch=1)  # Add stretch=1 here

        # Show/hide cancel shopping button based on cart state
        self.cancel_shopping_btn.setVisible(bool(self.cart_state.cart_items))

        # Calculate total amount
        total_amount = sum(float(product['price']) * quantity for product, quantity in self.cart_state.cart_items) if self.cart_state.cart_items else 0
        formatted_total = "{:,.0f}".format(total_amount).replace(',', '.')

        # Create footer container for total and payment
        footer_container = QWidget()
        footer_container.setStyleSheet("background-color: transparent;")
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(0, 10, 0, 10)  # Add padding
        footer_layout.addStretch()
        
        # Total label
        total_label = QLabel()
        total_label.setText(f'<span style="color: #000000;">Total </span>'
                          f'<span style="color: #D30E11;">{formatted_total} vnđ</span>')
        total_label.setTextFormat(Qt.RichText)
        total_label.setStyleSheet("""
            margin-right: 30px;  /* Tăng từ 15px lên 30px */
            font-family: Inter;
            font-weight: bold;
            font-size: 14px;
        """)
        footer_layout.addWidget(total_label)
        
        # Payment button
        payment_button = QPushButton("PAYMENT")
        payment_button.setObjectName("payment_button")  # Set object name for finding later
        payment_button.setFixedSize(170, 40)
        payment_button.setStyleSheet("""
            QPushButton {
                background-color: #4E8F5F;
                color: white;
                border-radius: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2C513F;
            }
        """)
        payment_button.clicked.connect(self.show_payment_page)
        footer_layout.addWidget(payment_button)
        
        # Add footer to main layout at the bottom
        self.content_layout.addStretch()  # Push everything up
        self.content_layout.addWidget(footer_container, alignment=Qt.AlignBottom)  # Align to bottom

    def show_payment_page(self):
        """Enhanced transition to payment page with optimized performance"""
        # Bắt đầu đo thời gian
        transition_start_time = time.time()
        print(f"[TIMING] Starting page transition at: {transition_start_time}")
        
        total_amount = sum(float(product['price']) * quantity 
                         for product, quantity in self.cart_state.cart_items)
        if total_amount == 0:
            self.animate_disabled_payment()
            return
            
        if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
            self.transition_in_progress = True
            
            # Start transition overlay immediately
            self.transition_overlay.fadeIn()
            print(f"[TIMING] Transition overlay started at: {time.time() - transition_start_time:.4f}s")
            
            # Lưu ý QUAN TRỌNG: KHÔNG khởi tạo QTimer trong thread khác
            # Stop monitors trực tiếp
            if hasattr(self, 'session_monitor'):
                self.session_monitor.stop()
                # Không dùng wait() để tránh blocking
                print("Stopped session monitor before payment page")
                
            if hasattr(self, 'payment_monitor'):
                self.payment_monitor.stop()
                # Không dùng wait() để tránh blocking
                print("Stopped payment monitor before payment page")
                
            print(f"[TIMING] Monitors stopped at: {time.time() - transition_start_time:.4f}s")
            
            # Pre-cleanup để giảm tải
            if self.camera:
                self.stop_camera()
                print(f"[TIMING] Camera stopped at: {time.time() - transition_start_time:.4f}s")
            
            # Load QR page trong main thread để tránh lỗi QTimer
            start_time = PageTiming.start_timing()
            
            # Chuẩn bị tải page mới
            print(f"[TIMING] Starting to load QRCodePage at: {time.time() - transition_start_time:.4f}s")
            from page5_qrcode import QRCodePage
            
            # Khởi tạo page với tham số đồng bộ
            print(f"[TIMING] Creating QRCodePage at: {time.time() - transition_start_time:.4f}s")
            self.payment_page = QRCodePage()
            self.payment_page.payment_completed.connect(self.handle_payment_completed)
            
            # Hiển thị trang mới và ẩn trang hiện tại
            def show_new_page():
                page_ready_time = time.time()
                print(f"[TIMING] QRCodePage ready at: {page_ready_time - transition_start_time:.4f}s")
                self.payment_page.show()
                print(f"[TIMING] QRCodePage shown at: {time.time() - transition_start_time:.4f}s")
                self.transition_overlay.fadeOut(lambda: self.hide())
                # Kết thúc đo thời gian
                total_time = time.time() - transition_start_time
                print(f"[TIMING] Total transition time: {total_time:.4f}s")
                PageTiming.end_timing(start_time, "ShoppingPage", "QRCodePage")
            
            # Dùng QTimer ở main thread
            QTimer.singleShot(100, show_new_page)
            
            # Cleanup nặng để chạy sau khi đã chuyển trang
            def background_cleanup():
                try:
                    # Clear caches
                    self._image_cache.clear()
                    self._widgets_cache.clear()
                    
                    # Clean up modals
                    if hasattr(self, '_product_modal') and self._product_modal:
                        self._product_modal.hide()
                    
                    if hasattr(self, '_cancel_modal') and self._cancel_modal:
                        self._cancel_modal.hide()
                    
                    # Force garbage collection
                    import gc
                    gc.collect()
                    
                    print(f"[TIMING] Background cleanup completed at: {time.time() - transition_start_time:.4f}s")
                except Exception as e:
                    print(f"Error in cleanup: {e}")
            
            # Chạy cleanup sau khi đã chuyển trang
            QTimer.singleShot(500, background_cleanup)

    def handle_payment_completed(self, success):
        """Xử lý khi thanh toán hoàn tất"""
        self.payment_completed = success
        if success:
            # Tạm thời chỉ đánh dấu flag, chưa clear cart ngay
            # Để page6 có thể lấy dữ liệu gửi server trước
            # Cart sẽ được clear khi page này được show lại
            self.payment_completed = True
            # KHÔNG clear cart ở đây nữa
            # self.cart_state.clear_cart()
            # self.cart_state.save_to_json()

    def animate_disabled_payment(self):
        """Animate payment button when cart is empty"""
        payment_button = self.findChild(QPushButton, "payment_button")  
        if not payment_button:
            return
            
        # Save original style
        original_style = payment_button.styleSheet()
        
        # Create all animations at once
        button_anim = QParallelAnimationGroup()
        
        # Scale animation
        scale_anim = QPropertyAnimation(payment_button, b"geometry")
        scale_anim.setDuration(1000)
        
        # Get original geometry
        orig_geom = payment_button.geometry()
        center = orig_geom.center()
        
        # Calculate scaled geometries
        scaled_width = int(orig_geom.width() * 1.8)
        scaled_height = int(orig_geom.height() * 1.8)
        scaled_x = int(center.x() - scaled_width/2)
        scaled_y = int(center.y() - scaled_height/2)
        scaled_geom = QRect(scaled_x, scaled_y, scaled_width, scaled_height)
        
        # Set keyframes for scale animation
        scale_anim.setKeyValueAt(0, orig_geom)
        scale_anim.setKeyValueAt(0.25, scaled_geom)
        scale_anim.setKeyValueAt(0.75, scaled_geom)
        scale_anim.setKeyValueAt(1, orig_geom)
        
        button_anim.addAnimation(scale_anim)
        
        # Show toast with same duration as button animation
        if self.toast_label:
            self.toast_label.hide()
        self.show_synchronized_toast("Cart is empty! Please add items to proceed.")
        print("Cart is empty! Please add items to proceed.")
        
        # Change button color
        payment_button.setStyleSheet("""
            QPushButton {
                background-color: #F4A261;
                color: black;
                border-radius: 20px;
                font-weight: bold;
            }
        """)
        
        # Create a single timer for both animations
        def reset_all():
            payment_button.setStyleSheet(original_style)
            if self.toast_label:
                self.toast_label.hide()
                
        # Start animations and set timer
        button_anim.start()
        QTimer.singleShot(1000, reset_all)

    def show_synchronized_toast(self, message):
        """Show toast message without its own timer"""
        if not self.toast_label:
            self.toast_label = QLabel(self)
            self.toast_label.setStyleSheet("""
                QLabel {
                    background-color: #264653;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 10px;
                    font-family: Baloo;
                    font-size: 13px;
                    border: 1px solid white;
                    margin: 10px;
                }
            """)
                
        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        
        # Position toast
        x = (self.width() - self.toast_label.width()) // 2
        self.toast_label.setGeometry(x, 20, self.toast_label.width(), self.toast_label.height())
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 2)
        self.toast_label.setGraphicsEffect(shadow)
        
        # Show immediately
        self.toast_label.show()

    def update_item_quantity(self, index, quantity):
        self.cart_state.update_quantity(index, quantity)
        self.update_cart_display()

    def remove_cart_item(self, index):
        """Handle cart item removal with improved safety"""
        try:
            # Lấy thông tin trước khi xóa
            removed_product = self.cart_state.cart_items[index][0].copy()  # Tạo bản sao của product
            
            # Thực hiện xóa item
            self.cart_state.remove_item(index)
            
            # Update cart display trước
            self.update_cart_display()
            
            # Kiểm tra và cập nhật product modal
            if (self.product_modal and 
                self.product_modal.isVisible() and 
                self.product_modal.current_product and 
                self.product_modal.current_product['name'] == removed_product['name']):
                
                # Tạo product modal mới với sản phẩm đã xóa
                self.recreate_product_modal(removed_product)
            
        except Exception as e:
            print(f"Error removing cart item: {e}")

    def recreate_product_modal(self, product):
        """Recreate product modal safely after item removal"""
        try:
            # Lưu vị trí cũ
            old_pos = self.product_modal.pos()
            
            # Tạo modal mới
            camera_height = 299
            new_modal = ProductModal(camera_height=camera_height//2)
            new_modal.setParent(self)
            new_modal.add_to_cart.connect(self.add_to_cart)
            new_modal.cancel_clicked.connect(self.handle_cancel)
            
            # Di chuyển đến vị trí cũ
            new_modal.move(old_pos)
            
            # Cập nhật sản phẩm 
            new_modal.update_product(product)
            
            # Xóa modal cũ
            if self.product_modal:
                self.product_modal.hide()
                self.product_modal.deleteLater()
            
            # Cập nhật reference
            self.product_modal = new_modal
            
            # Hiển thị modal mới
            self.product_modal.show()
            self.product_modal.raise_()
            
        except Exception as e:
            print(f"Error recreating product modal: {e}")

    def show_product_page(self):
        from import_module import ImportModule
        # Stop camera and session monitor before switching page
        if self.camera_active:
            self.stop_camera()
            
        if hasattr(self, 'session_monitor'):
            self.session_monitor.stop() 
            self.session_monitor.wait()
            print("Stopped session monitor before product page")
            
        product_page = ImportModule.get_product_page()
        product_page.show()
        self.hide()

    def toggle_camera(self):
        if self.camera_active:
            self.stop_camera()
        else:
            # Start camera immediately without delay
            self.product_detected = False
            
            if hasattr(self, 'product_modal') and self.product_modal and not sip.isdeleted(self.product_modal):
                self.product_modal.hide()
            else:
                self.product_modal = self.get_product_modal()
                
            self.start_camera()  # Remove delay_detection parameter
            self.camera_frame.show()

    def start_camera(self):
        """Start camera with immediate detection"""
        if self.camera is None:
            self.camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            if not self.camera.isOpened():
                print("Error: Could not open camera")
                return
                
        # Reset states and start showing frames immediately
        self.camera_active = True
        self._processing = False
        self.camera_frame.show()
        self.camera_label.show()
        self.timer.start(33)  # Start camera feed immediately
        self.detection_start_time = None  # Enable detection immediately

    def stop_camera(self):
        """Enhanced camera cleanup"""
        self.camera_active = False
        self.timer.stop()
        
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            
        # Safely handle _current_frame
        if hasattr(self, '_current_frame') and self._current_frame is not None:
            del self._current_frame
            self._current_frame = None
            
        if not self.product_detected:
            self.camera_label.clear()
        
        self._processing = False
        if self.countdown_overlay:
            self.countdown_overlay.stop()

    def update_frame(self):
        if not (self.camera and self.camera_active and not self.product_detected) or self._processing:
            return

        self._processing = True
        ret, frame = self.camera.read()
        if not ret:
            self._processing = False
            return

        try:
            if self._current_frame is not None:
                del self._current_frame
                self._current_frame = None

            # Process frame for display
            display_frame = frame.copy()
            display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = display_frame.shape
            self._current_frame = QImage(display_frame.data, w, h, w * ch, QImage.Format_RGB888)
            self.camera_label.setPixmap(QPixmap.fromImage(self._current_frame))

            # Only run detection if conditions are met
            current_time = time.time()
            if (self.frame_count % 10 == 0 and  # Reduced from 3 to 10 frames
                not self.detection_start_time and 
                current_time - self.last_detect_time > 0.5):  # Min 0.5s between detections
                
                # Check frame quality
                if self.is_frame_stable(frame):
                    # Process frame for detection
                    detect_frame = frame.copy()
                    detect_frame = cv2.cvtColor(detect_frame, cv2.COLOR_BGR2RGB)
                    detect_frame = cv2.convertScaleAbs(detect_frame, alpha=1.2, beta=10)

                    # Save frame to detect
                    frame_name = f'frame_{int(time.time()*1000)}.jpg'
                    to_detect_path = os.path.join(self.temp_detect_folder, frame_name)
                    cv2.imwrite(to_detect_path, cv2.cvtColor(detect_frame, cv2.COLOR_RGB2BGR))

                    product = self.get_detector().detect_product(detect_frame)

                    if product:
                        # Save detected frame
                        detected_path = os.path.join(self.temp_detected_folder, frame_name)
                        cv2.imwrite(detected_path, cv2.COLOR_RGB2BGR)
                        # Delete the to_detect frame since detection succeeded
                        try:
                            os.remove(to_detect_path)
                        except:
                            pass
                        
                        self.last_detect_time = current_time
                        self.handle_product_detection(product)
                        self._processing = False
                        return

                    del detect_frame

        except Exception as e:
            print(f"Error in frame processing: {e}")
        finally:
            self.frame_count += 1
            self._processing = False

    def is_frame_stable(self, frame, threshold=100):
        """Check if frame is stable enough for detection"""
        # Convert to grayscale for blur detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate Laplacian variance (blur detection)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Calculate frame brightness
        brightness = np.mean(gray)
        
        # Check if frame meets quality criteria
        is_stable = (blur_value > threshold and  # Not too blurry
                    brightness > 30 and          # Not too dark
                    brightness < 220)            # Not too bright
                    
        return is_stable

    def add_to_cart(self, product, quantity):
        """Enhanced add to cart with safety checks"""
        try:
            # Start timing
            self.add_cart_start_time = time.time()
            print(f"Starting add to cart for {product['name']} at {self.add_cart_start_time}")
            
            # Add item
            is_existing = self.cart_state.add_item(product, quantity)
            
            # Update UI safely
            if self.product_modal and not self.product_modal.isHidden():
                self.product_modal.hide()
            
            # Cập nhật giỏ hàng không đồng bộ
            QTimer.singleShot(50, self.update_cart_display)
            
            self.update_cart_display()
            # Log timing after update
            end_time = time.time()
            duration = (end_time - self.add_cart_start_time)  # Convert to milliseconds
            print(f"✓ Added {product['name']} to cart - Time taken: {duration:.4f}s")
            
            # Reset timer
            self.add_cart_start_time = None
            
            # Reset camera view
            self.product_detected = False
            self.camera_frame.show()
            self.camera_label.show()
            
            # Start camera with delay
            QTimer.singleShot(100, lambda: self.start_camera())
            
            return is_existing
            
        except Exception as e:
            print(f"Error adding to cart: {e}")
            return False

    def resume_camera_after_add(self):
        """This method is no longer needed"""
        pass

    def resume_camera(self):
        if self.product_modal.isVisible():
            return
        
        self.product_detected = False
        self.camera_frame.show()
        self.camera_label.show()
        self.start_camera()  # Remove delay_detection parameter

    def handle_product_detection(self, product):
        """Handle detected product and show product modal"""
        self.product_detected = True
        self.camera_frame.hide()
        
        # Stop camera when showing modal
        self.stop_camera()
        
        # Check if product already exists in cart
        existing_quantity = None
        for cart_product, quantity in self.cart_state.cart_items:
            if cart_product['name'] == product['name']:
                existing_quantity = quantity
                # Move the existing product to top of the cart
                self.cart_state.move_to_top(product['name'])
                # Update the display with highlighting
                self._highlight_product_name = product['name']  # Store name for highlighting
                self.update_cart_display()
                break
                
        # Get product modal using lazy loading
        product_modal = self.get_product_modal()
        product_modal.setParent(self)
        
        # Position modal more centered
        camera_pos = self.camera_frame.pos()
        camera_center_x = camera_pos.x() + (self.camera_frame.width() // 2)
        modal_x = camera_center_x - (product_modal.width() // 2)  # Center align
        modal_y = camera_pos.y() + (self.camera_frame.height() - product_modal.height()) // 2
        product_modal.setGeometry(modal_x, modal_y, 271, 270)
        
        # Update and show modal
        product_modal.update_product(product, existing_quantity)
        product_modal.show()
        product_modal.raise_()
        
        # Stop camera processing
        self._processing = False

    def handle_cancel(self):
        """Handle cancel button click from product modal"""
        self.product_modal.hide()
        self.camera_frame.show()
        self.product_detected = False
        self.start_camera()  # Remove delay_detection parameter
        self.camera_label.show()

    def show_cancel_dialog(self):
        if self.camera_active:
            self.stop_camera()

        # Create new effects each time
        self.blur_effect = QGraphicsBlurEffect()
        self.blur_effect.setBlurRadius(0)
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1)

        # Create blur container
        self.blur_container = QWidget(self)
        self.blur_container.setGeometry(0, 0, self.width(), self.height())
        self.blur_container.setStyleSheet("background-color: rgba(255, 255, 255, 0.5);")
        self.blur_container.setGraphicsEffect(self.blur_effect)
        
        def finish_cleanup():
            if self.blur_effect:
                self.blur_effect.setBlurRadius(0)
            if self.opacity_effect:
                self.opacity_effect.setOpacity(1)
            if self.blur_container:
                self.blur_container.hide()
                self.blur_container.deleteLater()
            self.blur_container = None
            self.blur_effect = None
            self.opacity_effect = None
            
            # Chỉ resume camera nếu không có modal nào đang hiển thị
            if not self.product_modal.isVisible():
                self.resume_camera()

        # Kết nối signal not_now với hàm cleanup
        self.cancel_modal.not_now.connect(finish_cleanup)
        
        # Position modal in center
        modal_x = (self.width() - self.cancel_modal.width()) // 2
        modal_y = (self.height() - self.cancel_modal.height()) // 2 
        self.cancel_modal.move(modal_x, modal_y)
        
        # Show and animate
        self.blur_container.show()
        self.blur_container.raise_()
        self.cancel_modal.show()
        self.cancel_modal.raise_()
        
        # Animate blur
        blur_anim = QPropertyAnimation(self.blur_effect, b"blurRadius")
        blur_anim.setDuration(200)
        blur_anim.setStartValue(0)
        blur_anim.setEndValue(15)
        blur_anim.start()

        # Update button style when modal shows
        self.cancel_shopping_btn.setStyleSheet("""
            QPushButton {
                background-color: #FED87B;
                border: 1px solid #FED87B;
                border-radius: 17px;
                color: #D30E11;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #B71C1C;
                color: white;
            }
        """)
        
        # Show modal
        self.blur_container.show()
        self.blur_container.raise_()
        self.cancel_modal.show()
        self.cancel_modal.raise_()
        
        def cleanup():
            # Reset button style when modal hides
            self.cancel_shopping_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F3F3F3;
                    border: 1px solid #D30E11;
                    border-radius: 17px;
                    color: #D30E11;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                    color: white;
                }
            """)
            if self.blur_effect:
                self.blur_effect.setBlurRadius(0)
            if self.opacity_effect:
                self.opacity_effect.setOpacity(1)
            if self.blur_container:
                self.blur_container.hide()
                self.blur_container.deleteLater()
            self.blur_container = None
            self.blur_effect = None
            self.opacity_effect = None
            self.resume_camera()

        self.cancel_modal.not_now.connect(cleanup)

        # Chỉnh sửa handler cho cancel modal
        def handle_cancel_payment():
            # Cleanup effects và blur container
            if self.blur_effect:
                self.blur_effect.setBlurRadius(0)
            if self.opacity_effect:
                self.opacity_effect.setOpacity(1)
            if self.blur_container:
                self.blur_container.hide()
                self.blur_container.deleteLater()
                
            self.blur_container = None
            self.blur_effect = None
            self.opacity_effect = None

            # Set payment_completed flag để trigger reset
            self.payment_completed = True
            
            # Chuyển về home page
            self.go_home()

        # Kết nối cancel signal với handler mới
        self.cancel_modal.cancelled.connect(handle_cancel_payment)

    def handle_cancel_payment(self):
        """Single handler for cancel payment - API call moved to modal"""
        if not self.transition_in_progress:
            self.transition_in_progress = True

            def switch_to_home():
                # Cleanup effects and blur container first
                if self.blur_effect:
                    self.blur_effect.setBlurRadius(0)
                if self.opacity_effect:
                    self.opacity_effect.setOpacity(1)
                if self.blur_container:
                    self.blur_container.hide()
                    self.blur_container.deleteLater()
                    
                self.blur_container = None
                self.blur_effect = None
                self.opacity_effect = None

                # Clear cart data
                self.cart_state.clear_cart()
                self.cart_state.save_to_json()
                
                # Show transition overlay
                def transition_complete():
                    from page1_welcome import WelcomePage
                    self.home_page = WelcomePage()
                    self.home_page.show()
                    self.transition_overlay.fadeOut(lambda: self.close())
                    
                self.transition_overlay.fadeIn(transition_complete)

            switch_to_home()

    def go_home(self):
        """Enhanced going back to home page with transition"""
        if not self.transition_in_progress:  # Check if transition is already in progress
            self.transition_in_progress = True  # Set the flag to indicate transition is in progress
            
            # Stop monitors before switching page
            if hasattr(self, 'session_monitor'):
                self.session_monitor.stop()
                self.session_monitor.wait()
                print("Stopped session monitor before going home")
                
            if hasattr(self, 'payment_monitor'):
                self.payment_monitor.stop()
                self.payment_monitor.wait()
                print("Stopped payment monitor before going home")
                
            def switch_to_home():
                start_time = PageTiming.start_timing()
                from page1_welcome import WelcomePage
                
                def show_new_page():
                    self.home_page = WelcomePage()
                    self.home_page.show()
                    self.transition_overlay.fadeOut(lambda: self.close())
                    PageTiming.end_timing(start_time, "ShoppingPage", "WelcomePage")
                    
                self.transition_overlay.fadeIn(show_new_page)
                
            # Only reset page if payment was completed
            if self.payment_completed:
                self.reset_page()
            switch_to_home()

    def handle_remote_session_end(self):
        """Handle session end from remote (mobile app)"""
        print("Session ended remotely")
        if not self.transition_in_progress:
            self.transition_in_progress = True
            
            # Stop monitoring since we're ending the session
            if hasattr(self, 'session_monitor'):
                self.session_monitor.stop()
                self.session_monitor.wait()
                print("Stopped session monitor after remote end")
                
            # Clear phone number
            try:
                file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    'config', 'phone_number.json')
                with open(file_path, 'w') as f:
                    json.dump({"phone_number": ""}, f)
                print("Successfully cleared phone number")
            except Exception as e:
                print(f"Error clearing phone number: {e}")

            # Switch to home page - simplified version without blur effects
            def switch_to_home():
                # Clear cart data
                self.cart_state.clear_cart()
                self.cart_state.save_to_json()
                
                # Show transition overlay
                def transition_complete():
                    from page1_welcome import WelcomePage
                    self.home_page = WelcomePage()
                    self.home_page.show()
                    self.transition_overlay.fadeOut(lambda: self.close())
                    
                self.transition_overlay.fadeIn(transition_complete)

            switch_to_home()

    def handle_payment_signal(self):
        """Handle received payment signal by switching to QR page"""
        print("Payment signal received, preparing QR page")
        if not self.transition_in_progress:
            self.transition_in_progress = True
            
            # Stop both monitors
            self.session_monitor.stop()
            self.session_monitor.wait()
            self.payment_monitor.stop()
            self.payment_monitor.wait()
            print("Stopped monitors before QR page")
            
            # Switch to QR page
            self.show_payment_page()

    def closeEvent(self, event):
        # Stop all monitoring and cleanup before closing
        if hasattr(self, 'session_monitor'):
            self.session_monitor.stop()
            self.session_monitor.wait()
            print("Stopped session monitor on page close")
            
        self.cleanup_resources()
        self.reset_page()  # Reset state when closing
        if hasattr(self, 'home_page') and self.home_page:
            self.home_page.show()
        # Stop session monitor before closing
        if hasattr(self, 'session_monitor'):
            self.session_monitor.stop()
            self.session_monitor.wait()
        if hasattr(self, 'payment_monitor'):
            self.payment_monitor.stop()
            self.payment_monitor.wait()
        super().closeEvent(event)
        
    def cleanup_resources(self):
        """Enhanced resource cleanup"""
        try:
            # Clear all caches
            self._image_cache.clear()
            self._widgets_cache.clear()
            
            if self._current_frame:
                del self._current_frame
                
            # Stop camera and release resources
            if self.camera:
                self.stop_camera()
                
            # Clean up detector
            if self._detector:
                self._detector = None

            # Clean up modals with safety check
            if hasattr(self, '_product_modal') and self._product_modal and not sip.isdeleted(self._product_modal):
                self._product_modal.deleteLater()
            if hasattr(self, '_cancel_modal') and self._cancel_modal and not sip.isdeleted(self._cancel_modal):
                self._cancel_modal.deleteLater()
                
            self._product_modal = None
            self._cancel_modal = None

            # Clean up effects and animations
            for effect in [self.blur_effect, self.opacity_effect]:
                if effect:
                    effect.deleteLater()
                    effect = None

            # Remove the warning animation cleanup since we removed the animation
            if hasattr(self, 'warning_animation') and self.warning_animation:
                self.warning_animation = None

            # Clean up temp files
            for folder in [self.temp_detect_folder, self.temp_detected_folder]:
                if os.path.exists(folder):
                    for file in os.listdir(folder):
                        if file.endswith('.jpg'):
                            try:
                                os.remove(os.path.join(folder, file))
                            except:
                                pass

            # Force garbage collection
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"Error in cleanup_resources: {e}")

    def lazy_init_modals(self):
        """Lazy initialization of modals"""
        if not hasattr(self, '_product_modal'):
            camera_height = 299
            self._product_modal = ProductModal(camera_height=camera_height//2)
            self._product_modal.add_to_cart.connect(self.add_to_cart)
            self._product_modal.cancel_clicked.connect(self.resume_camera)
            self._product_modal.hide()

        if not hasattr(self, '_cancel_modal'):
            self._cancel_modal = CancelShoppingModal(self)
            self._cancel_modal.cancelled.connect(self.go_home)
            self._cancel_modal.hide()

    def get_product_modal(self):
        """Lazy load product modal"""
        if self._product_modal is None:
            camera_height = 299
            self._product_modal = ProductModal(camera_height=camera_height//2)
            self._product_modal.add_to_cart.connect(self.add_to_cart)
            self._product_modal.cancel_clicked.connect(self.handle_cancel)  # Kết nối với handle_cancel
            self._product_modal.hide()
        return self._product_modal

    def get_detector(self):
        """Lazy load product detector"""
        if self._detector is None:
            self._detector = ProductDetector()
        return self._detector

    def clear_layout(self, layout):
        """Properly clear layout and widgets"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def setup_temp_folder(self):
        """Setup temp folders for storing detection images"""
        self.temp_base_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
        self.temp_detect_folder = os.path.join(self.temp_base_folder, 'to_detect')
        self.temp_detected_folder = os.path.join(self.temp_base_folder, 'detected')
        
        # Create folders if they don't exist
        for folder in [self.temp_base_folder, self.temp_detect_folder, self.temp_detected_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
            else:
                # Clean up old temp files in each folder
                for file in os.listdir(folder):
                    if file.endswith('.jpg'):
                        try:
                            os.remove(os.path.join(folder, file))
                        except:
                            pass

    def show_toast(self, message, duration=1000):
        """Show temporary toast message"""
        if not self.toast_label:
            self.toast_label = QLabel(self)
            self.toast_label.setStyleSheet("""
                QLabel {
                    background-color: #264653;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 10px;
                    font-family: Baloo;
                    font-size: 13px;
                    # font-weight: bold;
                    border: 1px solid white;
                    margin: 10px;
                }
            """)
            self.toast_label.hide()

        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        
        # Position toast at top center with some margin from top
        x = (self.width() - self.toast_label.width()) // 2
        self.toast_label.setGeometry(x, 20, self.toast_label.width(), self.toast_label.height())
        
        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 2)
        self.toast_label.setGraphicsEffect(shadow)
        
        # Show with fade in animation
        opacity_effect = QGraphicsOpacityEffect()
        self.toast_label.setGraphicsEffect(opacity_effect)
        
        fade_in = QPropertyAnimation(opacity_effect, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        
        # Show and start animation
        self.toast_label.show()
        fade_in.start()
        
        # Hide after duration with fade out
        def hide_toast():
            fade_out = QPropertyAnimation(opacity_effect, b"opacity")
            fade_out.setDuration(200)
            fade_out.setStartValue(1)
            fade_out.setEndValue(0)
            fade_out.finished.connect(self.toast_label.hide)
            fade_out.start()
            
        QTimer.singleShot(duration, hide_toast)

    def reset_page(self):
        """Reset page state to initial conditions"""
        # Reset camera state
        self.camera_active = False 
        self._processing = False
        self.product_detected = False
        
        # Cleanup effects and widgets in correct order
        try:
            # 1. Reset camera view first
            if hasattr(self, 'camera_label'):
                self.camera_label.clear()
            if hasattr(self, 'camera_frame'):
                self.camera_frame.show()
                
            # 2. Hide and cleanup modals safely
            if hasattr(self, 'product_modal') and self.product_modal and not sip.isdeleted(self.product_modal):
                self.product_modal.hide()
                
            if hasattr(self, 'cancel_modal') and self.cancel_modal and not sip.isdeleted(self.cancel_modal):
                self.cancel_modal.hide()
                
            # 3. Cleanup blur effects safely
            if hasattr(self, 'blur_container') and self.blur_container and not sip.isdeleted(self.blur_container):
                self.blur_container.hide()
                self.blur_container.deleteLater()
                
            if hasattr(self, 'blur_effect') and self.blur_effect and not sip.isdeleted(self.blur_effect):
                self.blur_effect.deleteLater()
                
            if hasattr(self, 'opacity_effect') and self.opacity_effect and not sip.isdeleted(self.opacity_effect):
                self.opacity_effect.deleteLater()
                
            # 4. Reset references
            self.blur_container = None
            self.blur_effect = None 
            self.opacity_effect = None
            
            # 5. Reset cart state
            self.cart_state.clear_cart()
            self.cart_items = []
            self.update_cart_display()
            
            # 6. Stop camera if active
            if hasattr(self, 'camera') and self.camera:
                self.stop_camera()
                
            # Reset cancel shopping button style
            if hasattr(self, 'cancel_shopping_btn'):
                self.cancel_shopping_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F3F3F3;
                        border: 1px solid #D30E11;
                        border-radius: 17px;
                        color: #D30E11;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #D32F2F;
                        color: white;
                    }
                """)
                self.cancel_shopping_btn.hide()  # Hide the button
                
        except Exception as e:
            print(f"Error in reset_page: {e}")

    def showEvent(self, event):
        """Enhanced showEvent with better cleanup"""
        super().showEvent(event)
        
        # Cleanup payment page resources properly
        if hasattr(self, 'payment_page') and self.payment_page:
            # Ensure transaction check is stopped
            self.payment_page.stop_transaction_check.set()
            self.payment_page.transaction_check_stopped = True
            
            if hasattr(self.payment_page, 'transaction_thread'):
                if self.payment_page.transaction_thread:
                    self.payment_page.transaction_thread.join(timeout=0.5)
                    
            # Cleanup other resources
            QTimer.singleShot(0, lambda: self.cleanup_payment_page())
            self.payment_page = None
            
        # Reset page if payment was completed
        if self.payment_completed:
            QTimer.singleShot(0, self.reset_page)
            self.payment_completed = False

    def cleanup_payment_page(self):
        """Cleanup payment page resources in background"""
        try:
            if hasattr(self, 'payment_page'):
                self.payment_page.cleanup_resources()
        except Exception as e:
            print(f"Error cleaning up payment page: {e}")

    def preload_images(self):
        """Preload commonly used images"""
        try:
            images = [
                'logo.png',
                'scanbutton_hover.png', 
                'productinfobutton.png',
                'scanarea.png',
                'emptycart.png'
            ]
            for img_name in images:
                path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', img_name)
                if img_name not in self._image_cache:
                    self._image_cache[img_name] = QPixmap(path)
        except Exception as e:
            print(f"Error preloading images: {e}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app_icon = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png'))
    app.setWindowIcon(app_icon)
    
    shopping_page = ShoppingPage()
    shopping_page.show()
    sys.exit(app.exec_())