import weakref
from functools import lru_cache
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QPushButton, QApplication, QFrame, QGridLayout, QScrollArea, QDialog, QGraphicsBlurEffect, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QObject, QEvent, QTimer, QPropertyAnimation
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon, QImage
import os
import cv2
import numpy as np
import time
from product_detector import ProductDetector
from product_modal import ProductModal
from cart_item_widget import CartItemWidget
from cart_state import CartState
from cancelshopping_modal import CancelShoppingModal

class ShoppingPage(QWidget):
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
        super().__init__()
        
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
        
    @lru_cache(maxsize=32)
    def load_cached_image(self, path):
        """Cache image loading to reduce memory usage"""
        if path not in self._image_cache:
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
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

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
        self.camera_frame.setFixedSize(271, 299)  

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
        self.scan_area.setFixedSize(231, 231)  # Make it square
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
            button.setFixedSize(170, 32)  # Set both width and height
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
            empty_layout.setContentsMargins(0, 50, 0, 0)
            
            empty_layout.addStretch(3)
            
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
            
            empty_layout.addStretch(2)
            
            self.content_layout.addWidget(empty_container)
        else:
            # Create a scrollable area for cart items with adjusted style
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: white;
                    width: 15px;  /* Increased from 10px */
                    margin: 0px;
                    margin-left: 5px;  /* Push scrollbar right */
                }
                QScrollBar::handle:vertical {
                    background: #D9D9D9;
                    min-height: 20px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

            # Container for cart items
            items_container = QWidget()
            items_layout = QVBoxLayout(items_container)
            items_layout.setSpacing(30)
            items_layout.setContentsMargins(0, 0, 20, 0)  # Increased right margin

            # Add cart items in reverse order (newest first) 
            highlighted_name = getattr(self, '_highlight_product_name', None)  # Lấy tên sản phẩm cần highlight
            for i, (product, quantity) in enumerate(reversed(self.cart_state.cart_items)):
                item_widget = CartItemWidget(product, quantity)
                item_widget.quantityChanged.connect(
                    lambda q, idx=len(self.cart_state.cart_items)-1-i: self.update_item_quantity(idx, q)
                )
                item_widget.itemRemoved.connect(
                    lambda idx=len(self.cart_state.cart_items)-1-i: self.remove_cart_item(idx)
                )
                
                # Fix: Check product name against highlighted name and highlight immediately
                if highlighted_name and product['name'] == highlighted_name:
                    item_widget.highlight()
                    self._highlight_product_name = None  # Reset sau khi đã highlight
                    
                items_layout.addWidget(item_widget)

            # Adjust scrollbar positioning
            items_layout.setContentsMargins(0, 0, 0, 0)  # Remove right margin
            scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: white;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #D9D9D9;
                    min-height: 20px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

            # Only show scrollbar if there's more than one item
            scroll_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarAsNeeded if len(self.cart_state.cart_items) > 1 else Qt.ScrollBarAlwaysOff
            )

            # Add stretch at the end to push items to the top
            items_layout.addStretch()
            
            # Set the container as the scroll area widget
            scroll_area.setWidget(items_container)
            
            # Add scroll area to content layout with margins to avoid header/footer
            self.content_layout.addWidget(scroll_area)

        # Show/hide cancel shopping button based on cart state
        self.cancel_shopping_btn.setVisible(bool(self.cart_state.cart_items))

        # Calculate total amount
        total_amount = sum(float(product['price']) * quantity for product, quantity in self.cart_state.cart_items) if self.cart_state.cart_items else 0
        formatted_total = "{:,.0f}".format(total_amount).replace(',', '.')

        # Add single total and payment section
        total_container = QWidget()
        total_layout = QHBoxLayout(total_container)
        total_layout.setContentsMargins(0, 0, 0, 10)
        total_layout.addStretch()
        
        # Update total label with different colors
        total_label = QLabel()
        total_label.setText(f'<span style="color: #000000;">Total </span>'
                          f'<span style="color: #D30E11;">{formatted_total} vnđ</span>')
        total_label.setTextFormat(Qt.RichText)
        total_label.setStyleSheet("""
            margin-right: 15px;
            font-family: Inter;
            font-weight: bold;
            font-size: 14px;
        """)
        total_layout.addWidget(total_label)
        
        payment_button = QPushButton("PAYMENT")
        payment_button.setFixedSize(120, 40)
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
        payment_button.clicked.connect(self.show_payment_page)  # Thêm connection
        total_layout.addWidget(payment_button)
        
        # Add to content layout instead of right layout
        self.content_layout.addWidget(total_container)

    def show_payment_page(self):
        total_amount = sum(float(product['price']) * quantity 
                         for product, quantity in self.cart_state.cart_items)
        if total_amount == 0:
            # Just return if cart is empty - no animation
            return
            
        # Stop camera before switching to payment page
        if self.camera_active:
            self.stop_camera()
            
        # Only proceed if cart has items
        from page5_qrcode import QRCodePage
        self.payment_page = QRCodePage()
        self.payment_page.show()
        self.hide()

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
        # Stop camera before switching page
        if self.camera_active:
            self.stop_camera()
            
        product_page = ImportModule.get_product_page()
        product_page.show()
        self.hide()

    def toggle_camera(self):
        if self.camera_active:
            self.stop_camera()
        else:
            # Start camera immediately with detection delayed
            self.product_detected = False
            self.product_modal.hide()
            self.start_camera(delay_detection=True)
            self.camera_frame.show()

    def start_camera(self, delay_detection=False):
        """Start camera with optional detection delay"""
        if self.camera is None:
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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
        
        # Set detection delay if needed
        if delay_detection:
            self.detection_start_time = True  # Block detection initially
            QTimer.singleShot(5000, self.enable_detection)  # Enable detection after 5s
        else:
            self.detection_start_time = None  # No delay, enable detection immediately

    def enable_detection(self):
        """Callback to enable detection after delay"""
        self.detection_start_time = None  # Clear flag to enable detection

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
                        cv2.imwrite(detected_path, cv2.cvtColor(detect_frame, cv2.COLOR_RGB2BGR))
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
            # Add item
            is_existing = self.cart_state.add_item(product, quantity)
            
            # Update UI safely
            if self.product_modal and not self.product_modal.isHidden():
                self.product_modal.hide()
            
            self.update_cart_display()
            
            # Reset camera view
            self.product_detected = False
            self.camera_frame.show()
            self.camera_label.show()
            
            # Start camera with delay
            QTimer.singleShot(100, lambda: self.start_camera(delay_detection=True))
            
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
        self.start_camera(delay_detection=True)  # Start with 5s delay for detection

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
        
        # Position modal
        camera_pos = self.camera_frame.pos()
        modal_x = camera_pos.x() - 20
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
        self.start_camera(delay_detection=True)  # Start with 5s delay for detection
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

    def go_home(self):
        from page1_welcome import WelcomePage
        self.cart_state.clear_cart()
        self.home_page = WelcomePage()
        self.home_page.show()
        self.close()

    def closeEvent(self, event):
        self.cleanup_resources()
        if hasattr(self, 'home_page') and self.home_page:
            self.home_page.show()
        super().closeEvent(event)
        
    def cleanup_resources(self):
        """Enhanced resource cleanup"""
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

        # Clean up modals
        for modal in [self._product_modal, self._cancel_modal]:
            if modal:
                modal.deleteLater()
                modal = None

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

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app_icon = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png'))
    app.setWindowIcon(app_icon)
    
    shopping_page = ShoppingPage()
    shopping_page.show()
    sys.exit(app.exec_())
