import json
import weakref
from functools import lru_cache
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QPushButton, QApplication, QFrame, QGridLayout, QScrollArea, QDialog, QGraphicsBlurEffect, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QMessageBox)
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
from config import DEVICE_ID, CART_CHECK_PAYMENT_SIGNAL, CART_END_SESSION_API
from threading import Thread
from count_item import update_cart_count
from utils.translation import _, get_current_language
from utils.font_helpers.vietnamese import VietnameseFontHelper

class SessionMonitor(QThread):
    """Thread to monitor cart session status"""
    session_ended = pyqtSignal()  # Signal when session ends

    def __init__(self, page_name="page4"):
        super().__init__()
        self.is_running = True
        self.page_name = page_name  

    def run(self):
        # This method no longer makes API calls to CART_END_SESSION_STATUS_API
        if self.page_name != "page4":  # Ensure this thread only runs in page4
            print(f"SessionMonitor is disabled for {self.page_name}")
            return
            
        # Just keep the thread alive without API calls
        while self.is_running:
            time.sleep(0.5)  # Small sleep to avoid CPU usage

    def stop(self):
        self.is_running = False

class PaymentSignalMonitor(QThread):
    """Thread to monitor payment signals"""
    payment_signal_received = pyqtSignal()  # Signal when payment is requested

    def __init__(self, page_name="page4"):
        super().__init__()
        self.is_running = True
        self.page_name = page_name

    def run(self):
        # Thread now only waits to be manually triggered
        # No simulation or background checking is performed
        while self.is_running:
            time.sleep(0.5)  # Small sleep to avoid CPU usage
            
        print("Payment Signal Monitor: Stopped")

    def stop(self):
        self.is_running = False
        
    def trigger_payment_signal(self):
        """Method to manually trigger payment signal from UI"""
        if self.is_running:
            print("Payment Signal Monitor: Manually triggered payment signal")
            self.payment_signal_received.emit()

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
                border-radius: 15px;
                width: 45px;  /* Tăng từ 25px lên 45px */
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
        try:
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
            
            # IMPORTANT: Disconnect any previous connections to prevent multiple signals
            try:
                self.cancel_modal.cancelled.disconnect()
            except:
                pass
                
            # Connect cancelled signal to go_home first, then to handle_cancel_payment
            print("Connecting cancel_modal.cancelled signal to handle_cancel_payment")
            self.cancel_modal.cancelled.connect(self.handle_cancel_payment)
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
            
            # Connect signals - remove connection to session_ended as it's no longer emitted
            # self.session_monitor.session_ended.connect(self.handle_remote_session_end)
            self.payment_monitor.payment_signal_received.connect(self.handle_payment_signal)
            
            # Start both monitors with offset
            self.session_monitor.start()
            QTimer.singleShot(250, self.payment_monitor.start)  # Start with 250ms offset
            self.payment_page = None  # Add reference to payment page
            self.preload_images()  # Preload images for faster loading
            
            # Print confirmation of initialized page
            print("ShoppingPage initialized successfully with cancel handler connected")
            
        except Exception as e:
            print(f"Critical error initializing ShoppingPage: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to cleanup any partial initialization
            self.cleanup_resources()
            
            # Create an emergency message widget
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error initializing Shopping Page")
            msg.setInformativeText(f"Error: {str(e)}")
            msg.setWindowTitle("Error")
            msg.exec_()
            
            # Try to go back to welcome page
            try:
                from page1_welcome import WelcomePage
                self.home_page = WelcomePage()
                self.home_page.show()
                self.close()
            except:
                pass

    @lru_cache(maxsize=32)
    def load_cached_image(self, path):
        """Cache image loading to reduce memory usage"""
        if (path not in self._image_cache):
            self._image_cache[path] = QPixmap(path)
        return self._image_cache[path]
        
    def load_fonts(self):
        # Register fonts for this page
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        self.setWindowTitle(_('shoppingPage.title'))
        # Remove setGeometry and setFixedSize since handled by BasePage
        
        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Section
        left_section = QWidget()
        left_section.setFixedWidth(960)  # Increased from 400 to 960
        left_section.setStyleSheet("background-color: #F0F6F1;")
        
        # Change to QGridLayout with adjusted spacing
        left_layout = QGridLayout(left_section)
        left_layout.setContentsMargins(50, 30, 50, 40)  # Increased margins
        left_layout.setSpacing(10)  # Increased spacing

        # Buttons Container - Row 0 (moved up from Row 1)
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(40)  # Increased spacing from 10 to 40
        buttons_layout.setContentsMargins(0, 0, 0, 20)  # Increased bottom margin

        # Scan Button
        scan_button = self.create_button(_("shoppingPage.scan"), icon_path="camera.png")
        scan_button.clicked.connect(self.toggle_camera)
        buttons_layout.addWidget(scan_button)

        # Product Info Button
        product_info_button = self.create_button(_("shoppingPage.productInfo"), icon_path="info.png")
        product_info_button.clicked.connect(self.show_product_page)
        # print("Open product info page")
        buttons_layout.addWidget(product_info_button)

        left_layout.addWidget(buttons_container, 0, 0, 1, 2)  # row 0, col 0, rowspan 1, colspan 2

        # Camera View Area - Row 1 (moved up from Row 2)
        # Create outer dashed border container
        self.dash_border_container = QWidget()
        self.dash_border_container.setFixedSize(880, 870)  
        self.dash_border_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: 3px dashed #507849;  /* Green dashed border */
                border-radius: 20px;
            }
        """)
        dash_border_layout = QVBoxLayout(self.dash_border_container)
        dash_border_layout.setContentsMargins(5, 5, 5, 5)  # Reduced padding to minimize gap
        dash_border_layout.setSpacing(0)
        
        # Inner camera frame (will completely fill inside dashed border)
        self.camera_frame = QFrame()
        self.camera_frame.setFixedSize(860, 850) 
        self.camera_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-radius: 15px;
                border: none;
            }
        """)
        
        # Create a label for camera display
        self.camera_label = QLabel(self.camera_frame)
        self.camera_label.setFixedSize(860, 850) 
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("background-color: transparent;")
        
        # Create scan area overlay
        self.scan_area = QFrame(self.camera_frame)
        self.scan_area.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        # Make scan area fixed size and center it in camera frame
        self.scan_area.setFixedSize(800, 800) 
        self.scan_area.move(
            (self.camera_frame.width() - self.scan_area.width()) // 2,  # Center horizontally (changed from original)
            (self.camera_frame.height() - self.scan_area.height()) // 2  # Center vertically
        )

        # Add scan area icon
        self.camera_icon = QLabel(self.scan_area)
        scan_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    'assets', 'scanarea.png')
        self.camera_icon.setPixmap(QPixmap(scan_icon_path)
                            .scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Tăng từ 220x220 lên 250x250
        self.camera_icon.setAlignment(Qt.AlignCenter)
        
        # Position the icon slightly to the left within scan_area
        self.camera_icon.setGeometry(
            (self.scan_area.width() - 250) // 2 + 20, 
            (self.scan_area.height() - 250) // 2,
            250, 250
        )
        
        # Add camera frame to dashed border
        dash_border_layout.addWidget(self.camera_frame, 0, Qt.AlignCenter)
        
        # Add dash border container to layout
        left_layout.addWidget(self.dash_border_container, 1, 0, 1, 2, Qt.AlignCenter)

        # Set vertical spacing between rows
        left_layout.setVerticalSpacing(20)  # Increased from 0 to 20

        # Add vertical stretch at the bottom if needed
        left_layout.setRowStretch(2, 1)  # Make row 2 (was 3) stretch

        # Right Section (Cart)
        self.right_section = QWidget()
        self.right_section.setFixedWidth(960)  # Increased from 400 to 960
        self.right_section.setStyleSheet("background-color: white;")

        # Main right layout
        self.right_layout = QVBoxLayout(self.right_section)
        self.right_layout.setContentsMargins(50, 30, 50, 40)  # Increased margins
        self.right_layout.setSpacing(10)  # Increased spacing from 0 to 10

        # Fixed header container with horizontal layout
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(80)  # Increased from 40 to 80
        self.header_widget.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Cart Header (left aligned)
        self.cart_header = QLabel(_("shoppingPage.yourCart"))
        self.cart_header.setFont(QFont("Baloo", 40))  # Increased from 24 to 40
        self.cart_header.setStyleSheet("color: black;")
        header_layout.addWidget(self.cart_header, alignment=Qt.AlignLeft | Qt.AlignTop)

        # Cart count label for items (will be updated when items are added)
        self.cart_count_label = QLabel("")
        self.cart_count_label.setFont(QFont("Baloo", 40))  # Increased from 24 to 40
        self.cart_count_label.setStyleSheet("color: #D30E11;")
        header_layout.addWidget(self.cart_count_label, alignment=Qt.AlignLeft | Qt.AlignTop)

        # Cancel Shopping button (right aligned)
        self.cancel_shopping_btn = QPushButton(_("shoppingPage.cancelShopping"))
        self.cancel_shopping_btn.setFixedSize(250, 60)  # Increased from 160x40 to 250x60
        self.cancel_shopping_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_shopping_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #D30E11;
                border-radius: 30px;
                color: #D30E11;
                font-weight: bold;
                font-size: 22px;  /* Tăng từ 20px lên 22px */
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
                color: white;
                border: 2px solid #D32F2F;
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
        self.content_layout.setContentsMargins(0, 30, 0, 0)  # Increased from 20 to 30
        self.right_layout.addWidget(self.content_widget)

        # Initialize cart display
        self.update_cart_display()

        main_layout.addWidget(left_section)
        main_layout.addWidget(self.right_section)  # Use stored reference

    def create_button(self, text, icon_path):
            button = QPushButton()
            button.setFixedSize(400, 100)  
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #507849;
                    border: none;
                    border-radius: 50px;  /* Increased from 40px to 50px for larger button */
                    padding: 0px;  
                    text-align: center;
                }
            """)

            # Button Layout
            button_layout = QHBoxLayout(button)
            button_layout.setContentsMargins(25, 0, 25, 0)  # Increased from 15 to 25
            button_layout.setSpacing(20)  # Increased from 15 to 20
            button_layout.setAlignment(Qt.AlignCenter)  # Center the layout contents

            # Add left stretch to push content to center
            button_layout.addStretch()

            # Setup icon and text label
            icon_label = QLabel()
            text_label = QLabel(text)
            
            # Store references for updating in event handlers
            button.icon_label = icon_label
            button.text_label = text_label
            
            # Configure based on button type
            if text == _("shoppingPage.scan"):  # Compare with translated text instead of hardcoded "SCAN"
                # For SCAN button - default state (camera off)
                scan_hover_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'assets', 'scanbutton_hover.png')
                scan_normal_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'assets', 'scanbutton.png')
                
                # Set initial state to normal (white text)
                icon_path = scan_normal_path
                text_color = "white"  # Default white text
                
                # Store paths for event handling
                button.scan_hover_path = scan_hover_path
                button.scan_normal_path = scan_normal_path
                
                # Install event filter for hover effects
                button.installEventFilter(self)
                button.setObjectName("SCAN_BUTTON")
                
            else:
                # For PRODUCT INFO button
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                            'assets', 'productinfobutton.png')
                text_color = "white"  # White for PRODUCT INFO

            # Set icon
            if icon_path:
                icon_pixmap = QPixmap(icon_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Tăng từ 36x36 lên 40x40
                icon_label.setPixmap(icon_pixmap)
                icon_label.setStyleSheet("background: transparent;")  
                button_layout.addWidget(icon_label)

            # Set text
            text_label.setStyleSheet(f"""
                color: {text_color}; 
                font-family: Inter;
                font-weight: bold;
                font-size: 28px;  /* Tăng từ 24px lên 28px */
                background: transparent;
                padding: 0px;
            """)
            text_label.setAlignment(Qt.AlignCenter)  # Center the text
            button_layout.addWidget(text_label)

            # Add right stretch to push content to center
            button_layout.addStretch()

            return button

    def eventFilter(self, obj, event):
        """Handle state changes for SCAN button"""
        if obj.objectName() == "SCAN_BUTTON":
            if event.type() == QEvent.Enter:
                # Only apply hover effect if camera is not active
                if not self.camera_active:
                    obj.text_label.setStyleSheet("""
                        color: #FFFF00; 
                        font-family: Inter;
                        font-weight: bold;
                        font-size: 28px;
                        background: transparent;
                        padding: 0px;
                    """)
                    icon_pixmap = QPixmap(obj.scan_hover_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    obj.icon_label.setPixmap(icon_pixmap)
                return True
            elif event.type() == QEvent.Leave:
                # Only revert hover effect if camera is not active
                if not self.camera_active:
                    obj.text_label.setStyleSheet("""
                        color: white; 
                        font-family: Inter;
                        font-weight: bold;
                        font-size: 28px;
                        background: transparent;
                        padding: 0px;
                    """)
                    icon_pixmap = QPixmap(obj.scan_normal_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    obj.icon_label.setPixmap(icon_pixmap)
                return True
                
        return super().eventFilter(obj, event)
        
    def toggle_camera(self):
        # Thêm debug để tìm ra vấn đề
        print(f"toggle_camera called. Current camera_active: {self.camera_active}")
        
        if self.camera_active:
            print("Camera active - stopping camera")
            self.stop_camera()
            
            # Update scan button appearance after camera is stopped
            scan_button = self.findChild(QPushButton, "SCAN_BUTTON")
            if scan_button:
                scan_button.text_label.setStyleSheet("""
                    color: white; 
                    font-family: Inter;
                    font-weight: bold;
                    font-size: 28px;  /* Tăng từ 24px lên 28px */
                    background: transparent;
                    padding: 0px;
                """)
                icon_pixmap = QPixmap(scan_button.scan_normal_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Tăng từ 36x36 lên 40x40
                scan_button.icon_label.setPixmap(icon_pixmap)
        else:
            # Start camera immediately without delay
            print("Camera not active - starting camera")
            self.product_detected = False
            
            # Ngăn không gọi stop_camera khi đang xử lý transition
            if hasattr(self, 'transition_in_progress') and self.transition_in_progress:
                print("Ignoring camera toggle during transition")
                return
                
            if hasattr(self, 'product_modal') and self.product_modal and not sip.isdeleted(self.product_modal):
                self.product_modal.hide()
            else:
                self.product_modal = self.get_product_modal()
                
            self.start_camera()  # Remove delay_detection parameter
            self.camera_frame.show()
            self.dash_border_container.show()  # Hiển thị lại khung dash line
            
            # Update scan button appearance after camera is started - set YELLOW for active camera
            scan_button = self.findChild(QPushButton, "SCAN_BUTTON")
            if scan_button:
                scan_button.text_label.setStyleSheet("""
                    color: #FFFF00; 
                    font-family: Inter;
                    font-weight: bold;
                    font-size: 28px;  /* Tăng từ 24px lên 28px */
                    background: transparent;
                    padding: 0px;
                """)
                icon_pixmap = QPixmap(scan_button.scan_hover_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Tăng từ 36x36 lên 40x40
                scan_button.icon_label.setPixmap(icon_pixmap)

    def show_product_page(self):
        """Cải tiến chuyển đổi từ trang shopping về trang sản phẩm"""
        if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
            self.transition_in_progress = True
            
            # Dừng camera và session monitor trước khi chuyển trang
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
                
            # Tạo overlay màu xanh toàn màn hình trước
            background_overlay = QWidget(self)
            background_overlay.setGeometry(self.rect())
            background_overlay.setStyleSheet("background-color: #3D6F4A;")  # Giữ màu sắc app
            background_overlay.show()
            background_overlay.raise_()
            
            # Đảm bảo overlay hiển thị ngay lập tức
            QApplication.processEvents()
            
            # Bắt đầu tính thời gian
            start_time = PageTiming.start_timing()
            
            # Tạo transition overlay với loading
            from components.PageTransitionOverlay import PageTransitionOverlay
            loading_overlay = PageTransitionOverlay(self, show_loading_text=True)
                
            # Import ProductPage và tạo instance
            from page3_productsinfo import ProductPage
            product_page = ProductPage()
            product_page.from_page1 = False  # Đánh dấu không phải từ page1
            
            def show_new_page():
                # Hiển thị trang sản phẩm
                product_page.show()
                # Sau đó fade out overlay và ẩn trang hiện tại
                loading_overlay.fadeOut(lambda: self.hide())
                background_overlay.deleteLater()  # Xóa overlay nền
                # Ghi nhận thời gian và reset cờ
                PageTiming.end_timing(start_time, "ShoppingPage", "ProductPage")
                self.transition_in_progress = False
            
            # Hiện overlay trước, sau đó gọi hàm show_new_page khi overlay đã hiện
            loading_overlay.fadeIn(show_new_page)

    def start_camera(self):
        """Start camera with immediate detection"""
        if self.camera is None:
            # Sử dụng V4L2 cho hiệu suất tốt nhất trên Linux
            self.camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            
            # Thiết lập với độ phân giải thấp hơn để tránh lỗi timeout
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)     # Giảm xuống 640x480 - độ phân giải chuẩn webcam
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)    # Giảm xuống độ phân giải tiêu chuẩn webcam
            self.camera.set(cv2.CAP_PROP_FPS, 15)              # Giảm FPS xuống 15 để ổn định hơn
            
            # Tăng timeout cho camera
            self.camera.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000)  # Tăng lên 2 giây
            
            # Thiết lập thêm một số tham số để tối ưu hiệu suất
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 2)        # Giảm buffer size xuống 2
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # Định dạng MJPG nhanh hơn
            
            if not self.camera.isOpened():
                print("Error: Could not open camera")
                return
                
        # Reset states and start showing frames immediately
        self.camera_active = True
        self._processing = False
        self.frame_read_errors = 0  # Đếm số lần lỗi đọc frame liên tiếp
        
        # Reset frame counter trong detector
        detector = self.get_detector()
        detector.reset_frame_counter()
        self.frame_count = 0
        
        # In thông tin về camera đã mở
        width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = self.camera.get(cv2.CAP_PROP_FPS)
        format_code = int(self.camera.get(cv2.CAP_PROP_FOURCC))
        format_name = chr(format_code & 0xFF) + chr((format_code >> 8) & 0xFF) + chr((format_code >> 16) & 0xFF) + chr((format_code >> 24) & 0xFF)
        
        print(f"Camera started: {width}x{height}@{fps}fps, format: {format_name}")
        
        # Camera frame is already set to black background in init_ui
        self.camera_frame.show()
        
        # Tối ưu: Sử dụng timer với khoảng thời gian ngắn hơn để có FPS cao hơn
        self.timer.start(16)  # ~60 FPS (16.67ms mỗi frame) thay vì 33ms (~30 FPS)
        
        self.detection_start_time = None  # Enable detection immediately

    def stop_camera(self):
        """Enhanced camera cleanup"""
        self.camera_active = False
        self.timer.stop()
        
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        
        # Keep camera frame with black background when inactive
        # (removed the code that was changing it back to #F0F6F1)
            
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
        """Cập nhật và xử lý frame từ camera, thực hiện phát hiện sản phẩm định kỳ"""
        if not (self.camera and self.camera_active and not self.product_detected) or self._processing:
            return

        self._processing = True
        
        # Đọc frame từ camera với cơ chế xử lý lỗi
        ret, frame = self.camera.read()
        if not ret:
            self._processing = False
            self.frame_read_errors += 1
            print(f"Lỗi khi đọc frame từ camera (lần thứ {self.frame_read_errors})")
            
            # Nếu gặp lỗi liên tục quá 5 lần, thử khởi động lại camera
            if self.frame_read_errors >= 5:
                print("Thử khởi động lại camera sau nhiều lần lỗi...")
                self.stop_camera()
                QTimer.singleShot(500, self.start_camera)  # Thử lại sau 500ms
            return
            
        # Reset bộ đếm lỗi nếu đọc frame thành công
        self.frame_read_errors = 0
            
        # Lấy FPS từ detector
        detector = self.get_detector()
        current_fps = detector.get_fps()
        print(f"Current FPS value: {current_fps}")

        try:
            if self._current_frame is not None:
                del self._current_frame
                self._current_frame = None

            # Tối ưu: Giảm kích thước frame ngay từ đầu để tăng hiệu suất xử lý
            display_frame = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_AREA)
            display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            # Get the current frame dimensions
            h, w, ch = display_frame.shape
            
            # For a true 0.5x zoom (wider field of view), we need to 
            # resize the original frame to a smaller size, then place it on a canvas
            
            # Calculate the size to resize the original frame to simulate 0.5x zoom
            zoom_factor = 2
            resized_w = int(w * zoom_factor)  # Make the frame smaller
            resized_h = int(h * zoom_factor)
            
            # Tối ưu: Sử dụng INTER_NEAREST cho tốc độ nhanh hơn thay vì INTER_AREA
            resized_frame = cv2.resize(display_frame, (resized_w, resized_h), interpolation=cv2.INTER_NEAREST)
            
            # Adjust target dimensions to better fit the dash border
            target_width = 880
            target_height = 870
            
            # Scale the resized frame to fill the target area
            scale_w = target_width / resized_w
            scale_h = target_height / resized_h
            
            # Use the larger scaling factor to ensure we fill the entire area
            scale = max(scale_w, scale_h)
            
            # Apply scaling to get dimensions that will fill the target area
            fill_w = int(resized_w * scale)
            fill_h = int(resized_h * scale)
            
            # Resize again to fill the target area - use faster INTER_LINEAR
            filled_frame = cv2.resize(resized_frame, (fill_w, fill_h), interpolation=cv2.INTER_LINEAR)
            
            # If the filled frame is larger than the target area, crop the center
            if fill_w > target_width or fill_h > target_height:
                # Calculate crop coordinates
                start_x = (fill_w - target_width) // 2
                start_y = (fill_h - target_height) // 2
                
                # Crop to exact target size
                filled_frame = filled_frame[start_y:start_y+target_height, start_x:start_x+target_width]
            
            # Make sure the array is contiguous in memory before creating QImage
            filled_frame = np.ascontiguousarray(filled_frame)
            
            # Vẽ thông tin FPS lên frame nếu có
            # Hiển thị FPS lớn hơn và rõ ràng hơn để dễ nhìn thấy
            if current_fps > 0:
                fps_text = f"FPS: {current_fps:.1f}"
                print(f"Drawing FPS text: {fps_text}")
                # Bỏ tạo nền đen để hiển thị nhẹ nhàng hơn
                # cv2.rectangle(filled_frame, (10, 10), (250, 100), (0, 0, 0), -1)
                # Vẽ viền đen bên ngoài với kích thước nhỏ hơn
                cv2.putText(filled_frame, fps_text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                            1.5, (0, 0, 0), 5)  # Giảm kích thước từ 2.5 xuống 1.5, từ 80 xuống 60
                # Vẽ text màu vàng bên trong với kích thước nhỏ hơn
                cv2.putText(filled_frame, fps_text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                            1.5, (0, 255, 255), 3)  # Giảm kích thước từ 2.5 xuống 1.5, từ 80 xuống 60
            
            # Convert to QImage
            self._current_frame = QImage(filled_frame.data, target_width, target_height, 
                                        target_width * ch, QImage.Format_RGB888)
            
            # Set the pixmap
            self.camera_label.setPixmap(QPixmap.fromImage(self._current_frame))

            # Phát hiện sản phẩm - toàn bộ logic đã được di chuyển vào ProductDetector
            product = self.get_detector().detect_product(frame)
            if product:
                # Nếu tìm thấy sản phẩm, xử lý sự kiện
                self.handle_product_detection(product)
                self._processing = False
                return

        except Exception as e:
            print(f"Error in frame processing: {e}")
        finally:
            self.frame_count += 1
            self._processing = False

# Đã di chuyển phương thức is_frame_stable sang ProductDetector

    def add_to_cart(self, product, quantity):
        """Enhanced add to cart with safety checks"""
        try:
            # Start timing
            self.add_cart_start_time = time.time()
            print(f"[Page4] Starting add to cart for {product['name']} at {self.add_cart_start_time}")
            
            # Add item
            is_existing = self.cart_state.add_item(product, quantity)
            print(f"[Page4] Added product to cart: {product['name']}")
            print(f"[Page4] Is existing item: {is_existing}")
            print(f"[Page4] Current cart items: {self.cart_state.cart_items}")
            
            # Update cart count label
            cart_count = len(self.cart_state.cart_items)
            print(f"[Page4] New cart count: {cart_count}")
            self.cart_count_label.setText(f"({cart_count})")
            
            # Update UI safely
            if self.product_modal and not self.product_modal.isHidden():
                self.product_modal.hide()
            
            # Cập nhật giỏ hàng không đồng bộ
            QTimer.singleShot(50, self.update_cart_display)
            
            self.update_cart_display()
            # Log timing after update
            end_time = time.time()
            duration = (end_time - self.add_cart_start_time)  # Convert to milliseconds
            print(f"[Page4] ✓ Added {product['name']} to cart - Time taken: {duration:.4f}s")
            
            # Reset timer
            self.add_cart_start_time = None
            
            # Reset camera view
            self.product_detected = False
            self.camera_frame.show()
            self.dash_border_container.show()  # Hiển thị lại khung dash line
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
        self.dash_border_container.show()  # Show dashed border container when resuming camera
        self.camera_label.show()
        self.start_camera()  # Remove delay_detection parameter

    def handle_product_detection(self, product):
        """Handle detected product and show product modal"""
        self.product_detected = True
        self.camera_frame.hide()
        self.dash_border_container.hide()  # Hide dashed border container when showing modal
        
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
        
        # Tìm left section và đặt modal ở giữa
        left_section = None
        for child in self.children():
            if isinstance(child, QWidget) and child.width() == 960:  # Tìm left section với width 960
                if child.styleSheet().find("#F0F6F1") > -1:  # Kiểm tra background color
                    left_section = child
                    break
        
        if left_section:
            # Đặt modal ở giữa left section, điều chỉnh cho kích thước mới của modal (750x550)
            modal_x = left_section.x() + (left_section.width() - product_modal.width()) // 2
            modal_y = left_section.y() + (left_section.height() - product_modal.height()) // 2
            product_modal.setGeometry(modal_x, modal_y, product_modal.width(), product_modal.height())
        else:
            # Fallback nếu không tìm thấy left section
            modal_x = 480 - product_modal.width() // 2  # Giá trị 480 là một nửa của 960 (width của left section)
            modal_y = 400  # Giá trị này có thể điều chỉnh tùy theo vị trí mong muốn trên màn hình
            product_modal.setGeometry(modal_x, modal_y, product_modal.width(), product_modal.height())
        
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
        self.dash_border_container.show()  # Show dashed border container when hiding modal
        self.product_detected = False
        self.start_camera()  # Remove delay_detection parameter
        self.camera_label.show()

    def show_cancel_dialog(self):
        # Kiểm tra xem giỏ hàng có trống không
        if not self.cart_state.cart_items:
            # Nếu giỏ hàng trống, hủy phiên trực tiếp mà không hiển thị modal
            self.handle_cancel_without_warning()
            return

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

        # Disconnect previous connections if they exist to avoid multiple signals
        try:
            self.cancel_modal.cancelled.disconnect()
        except:
            pass
            
        try:
            self.cancel_modal.not_now.disconnect()
        except:
            pass
            
        # Kết nối signal not_now với hàm cleanup
        self.cancel_modal.not_now.connect(finish_cleanup)
        
        # Kết nối cancel signal với handler cho đúng
        self.cancel_modal.cancelled.connect(self.handle_cancel_payment)
        
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
                border-radius: 20px;
                color: #D30E11;
                font-weight: bold;
                font-size: 22px;  /* Tăng từ 14px lên 22px */
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #B71C1C;
                color: white;
                border: 1px solid #B71C1C;
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
                    background-color: white;
                    border: 1px solid #D30E11;
                    border-radius: 20px;
                    color: #D30E11;
                    font-weight: bold;
                    font-size: 22px;  /* Tăng từ 14px lên 22px */
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                    color: white;
                    border: 1px solid #D32F2F;
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
        
        # REDUNDANT - Already connected above
        # self.cancel_modal.cancelled.connect(self.handle_cancel_payment)

    def handle_cancel_without_warning(self):
        """Hủy phiên mua sắm trực tiếp không cần hiển thị cảnh báo"""
        try:
            # Gọi API để hủy phiên
            url = f"{CART_END_SESSION_API}{DEVICE_ID}/"
            print(f"Ending session via API: {url}")
            response = requests.post(url)
            
            if response.status_code == 200:
                print("Session ended successfully")
            else:
                print(f"Error ending session: {response.status_code}, {response.text}")
                
        except Exception as e:
            print(f"Error calling end session API: {e}")
            
        # Set payment_completed flag để trigger reset
        self.payment_completed = True
        
        # Chuyển về home page
        self.go_home()

    def go_home(self):
        """Enhanced going back to home page with transition"""
        print("go_home called - checking transition status")
        if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:  # Check if transition is already in progress
            print("Starting transition to home page")
            self.transition_in_progress = True  # Set the flag to indicate transition is in progress
            
            # Stop monitors before switching page
            if hasattr(self, 'session_monitor'):
                self.session_monitor.stop()
                if hasattr(self.session_monitor, 'wait'):
                    self.session_monitor.wait()
                print("Stopped session monitor before going home")
                
            if hasattr(self, 'payment_monitor'):
                self.payment_monitor.stop()
                if hasattr(self.payment_monitor, 'wait'):
                    self.payment_monitor.wait()
                print("Stopped payment monitor before going home")
            
            # Tạo WelcomePage trước, sau đó mới bắt đầu transition
            try:
                from page1_welcome import WelcomePage
                self.home_page = WelcomePage()
                print(f"Created WelcomePage instance: {self.home_page}")
            except Exception as e:
                print(f"Error creating WelcomePage: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # Only reset page if payment was completed
            if self.payment_completed:
                print("Resetting page before transition")
                self.reset_page()
                
            # Force show welcome page and close this page without transition
            self.home_page.show()
            print("WelcomePage shown")
            QApplication.processEvents()
            self.close()
            print("ShoppingPage closed")
        else:
            print("Transition already in progress - skipping")
            
    def show_welcome_page(self):
        """New method to show welcome page after transition"""
        print("show_welcome_page called - showing welcome page")
        if hasattr(self, 'home_page') and self.home_page:
            self.home_page.show()
            if hasattr(self, 'transition_overlay') and self.transition_overlay:
                print("Fading out transition overlay")
                self.transition_overlay.fadeOut(lambda: self.close())
            else:
                print("No transition overlay - closing directly")
                self.close()

    def handle_remote_session_end(self):
        """Handle session end from remote (mobile app)"""
        print("Session ended remotely - using local handling instead of API")
        if not self.transition_in_progress:
            self.transition_in_progress = True
            
            # Stop monitoring since we're ending the session
            if hasattr(self, 'session_monitor'):
                self.session_monitor.stop()
                if hasattr(self.session_monitor, 'wait'):
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
        """Xử lý tín hiệu thanh toán từ monitor thread với hiệu ứng chuyển trang đồng nhất"""
        print("Payment signal received, preparing QR page")
        
        if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
            print("Starting transition to QR page due to payment signal")
            
            # Kiểm tra nếu cart rỗng hoặc tổng tiền = 0 thì không cần chuyển trang
            total_amount = sum(float(product['price']) * quantity 
                            for product, quantity in self.cart_state.cart_items)
            if total_amount == 0:
                print("Cart is empty or total is 0, ignoring payment signal")
                self.animate_disabled_payment()
                return
                
            self.transition_in_progress = True
            
            # Dừng camera và session monitor trước khi chuyển trang
            if self.camera_active:
                self.stop_camera()
                
            if hasattr(self, 'session_monitor'):
                self.session_monitor.stop()
                if hasattr(self.session_monitor, 'wait'):
                    self.session_monitor.wait()
                print("Stopped session monitor before QR page")
                
            if hasattr(self, 'payment_monitor'):
                self.payment_monitor.stop()
                if hasattr(self.payment_monitor, 'wait'):
                    self.payment_monitor.wait()
                print("Stopped payment monitor before QR page")
            
            # Tạo overlay màu xanh toàn màn hình trước
            background_overlay = QWidget(self)
            background_overlay.setGeometry(self.rect())
            background_overlay.setStyleSheet("background-color: #3D6F4A;")  # Giữ màu sắc app
            background_overlay.show()
            background_overlay.raise_()
            
            # Đảm bảo overlay hiển thị ngay lập tức
            QApplication.processEvents()
            
            # Bắt đầu tính thời gian
            start_time = PageTiming.start_timing()
            
            # Tạo transition overlay với loading
            from components.PageTransitionOverlay import PageTransitionOverlay
            loading_overlay = PageTransitionOverlay(self, show_loading_text=True)
            
            try:
                # Import và tạo QR page
                from page5_qrcode import QRCodePage
                self.payment_page = QRCodePage()
                
                if hasattr(self.payment_page, 'payment_completed'):
                    self.payment_page.payment_completed.connect(self.handle_payment_completed)
                    print("Connected payment_completed signal")
                else:
                    print("ERROR: payment_page does not have payment_completed signal")
                
                def show_new_page():
                    # Hiển thị trang QR
                    self.payment_page.show()
                    # Sau đó fade out overlay và ẩn trang hiện tại
                    loading_overlay.fadeOut(lambda: self.hide())
                    background_overlay.deleteLater()  # Xóa overlay nền
                    # Ghi nhận thời gian và reset cờ
                    PageTiming.end_timing(start_time, "ShoppingPage", "QRCodePage")
                    self.transition_in_progress = False
                
                # Hiện overlay trước, sau đó gọi hàm show_new_page khi overlay đã hiện
                loading_overlay.fadeIn(show_new_page)
            
            except Exception as e:
                print(f"Error handling payment signal: {e}")
                import traceback
                traceback.print_exc()
                
                # Reset transition flag so user can try again
                self.transition_in_progress = False
                
                # Show error message
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error opening payment page")
                msg.setInformativeText(f"Error: {str(e)}")
                msg.setWindowTitle("Error")
                msg.exec_()
        else:
            print("Payment signal ignored - transition already in progress")

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
                    padding: 20px 40px;
                    border-radius: 15px;
                    font-family: Baloo;
                    font-size: 20px;
                    border: 2px solid white;
                    margin: 15px;
                }
            """)
            self.toast_label.hide()

        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        
        # Position toast at top center with some margin from top
        x = (self.width() - self.toast_label.width()) // 2
        self.toast_label.setGeometry(x, 40, self.toast_label.width(), self.toast_label.height())
        
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
            if hasattr(self, 'dash_border_container'):
                self.dash_border_container.show()  # Hiển thị lại khung dash line
                
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
            self.cart_count_label.setText("")
            self.update_cart_display()
            
            # 6. Stop camera if active
            if hasattr(self, 'camera') and self.camera:
                self.stop_camera()
                
            # Reset cancel shopping button style
            if hasattr(self, 'cancel_shopping_btn'):
                self.cancel_shopping_btn.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        border: 1px solid #D30E11;
                        border-radius: 20px;
                        color: #D30E11;
                        font-weight: bold;
                        font-size: 22px;  /* Tăng từ 14px lên 22px */
                        padding: 0px;
                        margin: 0px;
                    }
                    QPushButton:hover {
                        background-color: #D32F2F;
                        color: white;
                        border: 1px solid #D32F2F;
                    }
                """)
                self.cancel_shopping_btn.hide()  # Hide the button
                
        except Exception as e:
            print(f"Error in reset_page: {e}")

    def showEvent(self, event):
        """Xử lý sự kiện khi trang được hiển thị"""
        super().showEvent(event)
        
        # Đảm bảo trang hiển thị đầy đủ
        self.setWindowOpacity(1.0)
        
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

    def update_cart_display(self):
        """Memory-optimized cart display"""
        # Clear widgets properly
        self.clear_layout(self.content_layout)
        
        # Update cart count label to match page3's style
        cart_count = len(self.cart_state.cart_items)
        print(f"[Page4] Updating cart display - Current count: {cart_count}")
        print(f"[Page4] Current cart items: {self.cart_state.cart_items}")
        
        if cart_count > 0:
            self.cart_count_label.setText(f"({cart_count})")
            self.cart_count_label.show()
        else:
            self.cart_count_label.setText("")
            self.cart_count_label.hide()
        
        # Update background color based on cart state
        self.right_section.setStyleSheet(
            f"background-color: {'#F3F3F3' if self.cart_state.cart_items else 'white'};"
        )
        
        # Keep header transparent
        self.header_widget.setStyleSheet("background-color: transparent;")
        
        # Luôn hiển thị nút cancel shopping, không phụ thuộc vào trạng thái giỏ hàng
        self.cancel_shopping_btn.setVisible(True)

        if not self.cart_state.cart_items:
            # Empty cart display
            empty_container = QWidget()
            empty_layout = QVBoxLayout(empty_container)
            empty_layout.setContentsMargins(0, 50, 0, 0)
            
            empty_layout.addStretch(2)
            
            empty_text = QLabel(_("productPage.empty"))
            empty_text.setFont(QFont("Inria Sans", 48))  # Increased from 30 to 48
            empty_text.setStyleSheet("color: #F68003;")
            empty_text.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(empty_text)
            
            empty_layout.addSpacing(40)  # Increased from 20 to 40
            
            empty_cart_label = QLabel()
            empty_cart_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                         'assets', 'emptycart.png')
            empty_cart_pixmap = QPixmap(empty_cart_path)
            if not empty_cart_pixmap.isNull():
                empty_cart_label.setPixmap(empty_cart_pixmap.scaled(200, 200, 
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Increased from 100x100
            empty_cart_label.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(empty_cart_label)
            
            empty_layout.addStretch(3)
            
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
            self.content_layout.addWidget(scroll_container, stretch=1)

        # Calculate total amount
        total_amount = sum(float(product['price']) * quantity for product, quantity in self.cart_state.cart_items) if self.cart_state.cart_items else 0
        formatted_total = "{:,.0f}".format(total_amount).replace(',', '.')
        
        # Create footer container for total and payment
        footer_container = QWidget()
        footer_container.setStyleSheet("background-color: transparent;")
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(0, 20, 0, 10)  # Increased vertical margins
        footer_layout.setSpacing(20)  # Increased from 10 to 20
        footer_layout.addStretch()
        
        # Total label
        total_label = QLabel()
        total_label.setText(f'<span style="color: #000000;">{_("shoppingPage.total")} </span>'
                          f'<span style="color: #D30E11;">{formatted_total} vnđ</span>')
        total_label.setTextFormat(Qt.RichText)
        total_label.setStyleSheet("""
            margin-right: 60px;  /* Increased from 50px to 60px */
            font-family: Inter;
            font-weight: bold;
            font-size: 32px;  /* Increased from 28px to 32px */
            padding: 10px;  /* Added padding */
        """)
        footer_layout.addWidget(total_label)
        
        # Payment button
        payment_button = QPushButton(_("shoppingPage.payment"))
        payment_button.setObjectName("payment_button")
        payment_button.setFixedSize(360, 90)  # Increased from 320x80 to 360x90
        payment_button.setStyleSheet("""
            QPushButton {
                background-color: #4E8F5F;
                color: white;
                border-radius: 45px;  /* Increased from 40px to 45px */
                font-weight: bold;
                font-size: 32px;  /* Increased from 28px to 32px */
                padding: 6px;  /* Added padding */
            }
            QPushButton:hover {
                background-color: #2C513F;
            }
        """)
        payment_button.clicked.connect(self.show_payment_page)
        footer_layout.addWidget(payment_button)
        
        # Create more space in footer
        footer_container.setFixedHeight(120)  # Set fixed height to make more space
        footer_layout.setContentsMargins(0, 30, 0, 20)  # Increased margins
        
        # Add footer to main layout at the bottom with more space
        self.content_layout.addStretch()  # Push everything up
        self.content_layout.addWidget(footer_container, alignment=Qt.AlignBottom)

    def show_payment_page(self):
        """Cải tiến chuyển đổi sang trang thanh toán QR với hiệu ứng đồng nhất"""
        # Kiểm tra xem đã có transition đang chạy chưa
        if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
            # Tính tổng tiền trước khi chuyển trang
            total_amount = sum(float(product['price']) * quantity 
                             for product, quantity in self.cart_state.cart_items)
            if total_amount == 0:
                self.animate_disabled_payment()
                return
            
            # Đánh dấu đang trong quá trình chuyển trang
            self.transition_in_progress = True
            
            # Dừng camera và session monitor trước khi chuyển trang
            if self.camera_active:
                self.stop_camera()
                
            if hasattr(self, 'session_monitor'):
                self.session_monitor.stop() 
                if hasattr(self.session_monitor, 'wait'):
                    self.session_monitor.wait()
                print("Stopped session monitor before QR page")
                
            if hasattr(self, 'payment_monitor'):
                self.payment_monitor.stop()
                if hasattr(self.payment_monitor, 'wait'):
                    self.payment_monitor.wait()
                print("Stopped payment monitor before QR page")
            
            # Tạo overlay màu xanh toàn màn hình trước
            background_overlay = QWidget(self)
            background_overlay.setGeometry(self.rect())
            background_overlay.setStyleSheet("background-color: #3D6F4A;")  # Giữ màu sắc app
            background_overlay.show()
            background_overlay.raise_()
            
            # Đảm bảo overlay hiển thị ngay lập tức
            QApplication.processEvents()
            
            # Bắt đầu tính thời gian
            start_time = PageTiming.start_timing()
            
            # Tạo transition overlay với loading
            from components.PageTransitionOverlay import PageTransitionOverlay
            loading_overlay = PageTransitionOverlay(self, show_loading_text=True)
            
            # Import và tạo QR page
            from page5_qrcode import QRCodePage
            self.payment_page = QRCodePage()
            
            if hasattr(self.payment_page, 'payment_completed'):
                self.payment_page.payment_completed.connect(self.handle_payment_completed)
                print("Connected payment_completed signal")
            else:
                print("ERROR: payment_page does not have payment_completed signal")
            
            def show_new_page():
                # Hiển thị trang QR
                self.payment_page.show()
                # Sau đó fade out overlay và ẩn trang hiện tại
                loading_overlay.fadeOut(lambda: self.hide())
                background_overlay.deleteLater()  # Xóa overlay nền
                # Ghi nhận thời gian và reset cờ
                PageTiming.end_timing(start_time, "ShoppingPage", "QRCodePage")
                self.transition_in_progress = False
            
            # Hiện overlay trước, sau đó gọi hàm show_new_page khi overlay đã hiện
            loading_overlay.fadeIn(show_new_page)
            
        else:
            print("Payment page transition already in progress, ignoring request")

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
        self.show_synchronized_toast(_("shoppingPage.emptyCartMessage"))
        print(_("shoppingPage.emptyCartMessage"))
        
        # Change button color
        payment_button.setStyleSheet("""
            QPushButton {
                background-color: #F4A261;
                color: black;
                border-radius: 45px;  /* Increased from 35px to 45px */
                font-weight: bold;
                font-size: 32px;  /* Increased from 24px to 32px */
                padding: 6px;  /* Added padding to match the normal state */
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
                    padding: 20px 40px;
                    border-radius: 15px;
                    font-family: Baloo;
                    font-size: 20px;
                    border: 2px solid white;
                    margin: 15px;
                }
            """)
                
        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        
        # Position toast
        x = (self.width() - self.toast_label.width()) // 2
        self.toast_label.setGeometry(x, 40, self.toast_label.width(), self.toast_label.height())
        
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
            print(f"[Page4] Removing product from cart: {removed_product['name']}")
            
            # Thực hiện xóa item
            self.cart_state.remove_item(index)
            print(f"[Page4] Removed item at index {index}")
            print(f"[Page4] Current cart items: {self.cart_state.cart_items}")
            
            # Update cart count label
            cart_count = len(self.cart_state.cart_items)
            print(f"[Page4] New cart count after removal: {cart_count}")
            if self.cart_state.cart_items:
                self.cart_count_label.setText(f"({cart_count})")
                self.cart_count_label.show()
            else:
                self.cart_count_label.setText("")
                self.cart_count_label.hide()
            
            # Update cart display trước
            self.update_cart_display()
            
            # Kiểm tra và cập nhật product modal
            if (self.product_modal and 
                self.product_modal.isVisible() and 
                self.product_modal.current_product and 
                self.product_modal.current_product['name'] == removed_product['name']):
                
                # Thay vì recreate_product_modal, chỉ cần ẩn nó đi
                self.product_modal.hide()
                
                # Khôi phục camera để người dùng scan lại
                self.product_detected = False
                self.camera_frame.show()
                self.dash_border_container.show()  # Hiển thị lại khung dash line
                self.camera_label.show()
                QTimer.singleShot(100, lambda: self.start_camera())
            
        except Exception as e:
            print(f"Error removing cart item: {e}")

    def recreate_product_modal(self, product):
        """Recreate product modal safely after item removal"""
        try:
            # Kiểm tra xem sản phẩm còn trong giỏ hàng không
            product_in_cart = False
            for cart_product, _ in self.cart_state.cart_items:
                if cart_product['name'] == product['name']:
                    product_in_cart = True
                    break
                    
            # Nếu sản phẩm không còn trong giỏ hàng, chỉ cần ẩn modal và khôi phục camera
            if not product_in_cart:
                self.product_modal.hide()
                self.product_detected = False
                self.camera_frame.show()
                self.dash_border_container.show()  # Hiển thị lại khung dash line
                self.camera_label.show()
                QTimer.singleShot(100, lambda: self.start_camera())
                return
                
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
            
            # Xóa modal cũ một cách an toàn
            old_modal = self.product_modal
            self.product_modal = new_modal  # Cập nhật reference trước khi đóng modal cũ
            
            if old_modal:
                old_modal.hide()
                QTimer.singleShot(100, lambda: old_modal.deleteLater())  # Delay việc xóa để tránh lỗi
            
            # Hiển thị modal mới
            self.product_modal.show()
            self.product_modal.raise_()
            
        except Exception as e:
            print(f"Error recreating product modal: {e}")

    def handle_cancel_payment(self):
        """Single handler for cancel payment - API call moved to modal"""
        print("handle_cancel_payment called - transitioning to home page")
        # Ngăn gọi nhiều lần
        if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
            self.transition_in_progress = True
            
            # Set payment_completed flag để trigger reset sau này
            self.payment_completed = True

            # Ẩn modal nếu đang hiển thị
            if hasattr(self, 'cancel_modal') and self.cancel_modal and self.cancel_modal.isVisible():
                self.cancel_modal.hide()

            # Dọn dẹp các effect
            if hasattr(self, 'blur_effect') and self.blur_effect:
                self.blur_effect.setBlurRadius(0)
            if hasattr(self, 'opacity_effect') and self.opacity_effect:
                self.opacity_effect.setOpacity(1)
            if hasattr(self, 'blur_container') and self.blur_container:
                self.blur_container.hide()
                self.blur_container.deleteLater()
                
            self.blur_container = None
            self.blur_effect = None
            self.opacity_effect = None

            # Xóa giỏ hàng
            self.cart_state.clear_cart()
            self.cart_state.save_to_json()
            
            print("Directly switching to home page without timer")
            
            # Force create the welcome page now, not in the transition handler
            from page1_welcome import WelcomePage
            self.home_page = WelcomePage()
            print(f"Created WelcomePage instance: {self.home_page}")
            
            # Process events before continuing
            QApplication.processEvents()
            
            # Just close this page and show welcome page directly without transitions
            self.home_page.show()
            print("WelcomePage shown")
            QApplication.processEvents()
            self.close()
            print("ShoppingPage closed")
            
            # No need to call go_home() since we're directly handling the transition here
            
    def setup_camera_section(self):
        camera_container = QWidget()
        camera_layout = QVBoxLayout(camera_container)
        camera_layout.setContentsMargins(10, 10, 10, 0)  # Tăng margin top từ 5 lên 10
        camera_layout.setSpacing(20)  # Increased from 15 to 20
        
        # Dashed border container for camera
        dash_border_container = QWidget()
        dash_border_container.setFixedSize(880, 850)
        dash_border_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: 3px dashed #507849;  /* Green dashed border */
                border-radius: 20px;
            }
        """)
        dash_border_layout = QVBoxLayout(dash_border_container)
        dash_border_layout.setContentsMargins(5, 5, 5, 5)  
        dash_border_layout.setSpacing(0)
        
        # Camera frame (placed inside dashed border container)
        self.camera_frame = QLabel("Camera not available")
        self.camera_frame.setFixedSize(860, 830) 
        self.camera_frame.setAlignment(Qt.AlignCenter)
        self.camera_frame.setStyleSheet("""
            QLabel {
                background-color: #000000;
                color: white;
                font-family: "Inter";
                font-size: 24px;
                border-radius: 15px;
            }
        """)
        
        # Add camera frame to dashed border container
        dash_border_layout.addWidget(self.camera_frame, 0, Qt.AlignCenter)
        
        # Add dashed border container to camera layout
        camera_layout.addWidget(dash_border_container, 0, Qt.AlignCenter)
        
        # Scan area overlay (700x700 square)
        self.scan_area_size = 700
        self.scan_x = int((self.camera_frame.width() - self.scan_area_size) / 2)
        self.scan_y = int((self.camera_frame.height() - self.scan_area_size) / 2)
        
        # Setup timer and detector
        self.detector = ProductDetector()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera)
        
        # Buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 15, 0, 0)  # Increased top margin from 10 to 15
        button_layout.setSpacing(50)  # Increased from 30 to 50
        
        # SCAN button
        self.scan_button = self.create_button(_("shoppingPage.scan"), None)
        self.scan_button.clicked.connect(self.toggle_scanning)
        
        # PRODUCT INFO button
        product_info_btn = self.create_button(_("shoppingPage.productInfo"), None)
        product_info_btn.clicked.connect(self.navigate_to_product_info)
        
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(product_info_btn)
        
        camera_layout.addWidget(button_container, 0, Qt.AlignCenter)
        
        return camera_container

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app_icon = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png'))
    app.setWindowIcon(app_icon)
    
    shopping_page = ShoppingPage()
    shopping_page.show()
    sys.exit(app.exec_())
