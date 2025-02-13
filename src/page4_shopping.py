from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QPushButton, QApplication, QFrame, QGridLayout, QScrollArea, QDialog, QGraphicsBlurEffect, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QObject, QEvent, QTimer, QPropertyAnimation
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon, QImage
import os
import cv2
from product_detector import ProductDetector
from product_modal import ProductModal
from cart_item_widget import CartItemWidget
from cart_state import CartState
from cancelshopping_modal import CancelShoppingModal

class ShoppingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.home_page = None  # Add this line
        self.cart_state = CartState()  # Thêm dòng này
        self.cart_state.save_to_json()  # Initialize cart by saving empty state
        self.cart_items = []
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.camera_active = False
        self.product_detected = False  # Move initialization here
        self.load_fonts()
        self.right_section = None  # Add this line
        self.init_ui()
        self.detector = ProductDetector()
        camera_height = 299  # Camera frame height
        self.product_modal = ProductModal(camera_height=camera_height//2)  # Pass 50% of camera height
        self.product_modal.setGeometry(0, 0, 271, 299)  # Match camera frame size
        self.product_modal.add_to_cart.connect(self.add_to_cart)
        self.product_modal.hide()
        self.product_modal.cancel_clicked.connect(self.resume_camera)  # Connect new signal
        self.warning_animation = None
        self.blur_effect = QGraphicsBlurEffect()
        self.blur_effect.setBlurRadius(0)
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1)
        
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
        logo_pixmap = QPixmap(logo_path)
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
                background-color: white;
                border: 1px solid #D32F2F;
                border-radius: 17px;
                color: #D32F2F;
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
        # Clear only the content area
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

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
            for i, (product, quantity) in enumerate(reversed(self.cart_state.cart_items)):
                item_widget = CartItemWidget(product, quantity)
                item_widget.quantityChanged.connect(
                    lambda q, idx=len(self.cart_state.cart_items)-1-i: self.update_item_quantity(idx, q)
                )
                item_widget.itemRemoved.connect(
                    lambda idx=len(self.cart_state.cart_items)-1-i: self.remove_cart_item(idx)
                )
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
            # Create warning animation effect
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
            button = self.sender()  # Get the payment button that was clicked
            
            # Create scale animation
            self.warning_animation = QPropertyAnimation(button, b"geometry")
            self.warning_animation.setDuration(500)  # 500ms for zoom
            
            # Get current geometry
            current_geo = button.geometry()
            center = current_geo.center()
            
            # Set keyframes
            self.warning_animation.setKeyValueAt(0, current_geo)  # Start normal
            
            # Calculate zoomed geometry (10% larger)
            zoomed = current_geo.adjusted(-5, -2, 5, 2)
            zoomed.moveCenter(center)
            self.warning_animation.setKeyValueAt(0.5, zoomed)  # Middle zoomed
            
            self.warning_animation.setKeyValueAt(1, current_geo)  # End normal
            
            # Use easing curve for smooth animation
            self.warning_animation.setEasingCurve(QEasingCurve.OutElastic)
            
            # Change button color to yellow during animation
            button.setStyleSheet("""
                QPushButton {
                    background-color: #FF9966;
                    color: black;
                    border-radius: 20px;
                    font-weight: bold;
                }
            """)
            
            # Reset button style after animation
            def reset_style():
                button.setStyleSheet("""
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
            
            self.warning_animation.finished.connect(reset_style)
            self.warning_animation.start()
            return
            
        # Only proceed if cart has items
        from page5_qrcode import QRCodePage
        self.payment_page = QRCodePage()
        self.payment_page.show()
        self.hide()

    def update_item_quantity(self, index, quantity):
        self.cart_state.update_quantity(index, quantity)
        self.update_cart_display()

    def remove_cart_item(self, index):
        self.cart_state.remove_item(index)
        QTimer.singleShot(300, self.update_cart_display)  # 300ms = animation duration

    def show_product_page(self):
        from import_module import ImportModule
        product_page = ImportModule.get_product_page()
        product_page.show()
        print("Product Page")
        self.hide()

    def toggle_camera(self):
        if self.camera_active:
            self.stop_camera()
        else:
            self.start_camera()
            # Reset view when starting camera
            self.product_detected = False
            self.product_modal.hide()
            self.camera_frame.show()

    def start_camera(self):
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                print("Error: Could not open camera")
                return
        self.camera_active = True
        self.timer.start(30)  # Update every 30ms

    def stop_camera(self):
        self.camera_active = False
        self.timer.stop()
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        if not self.product_detected:  # Only clear if no product is detected
            self.camera_label.clear()

    def update_frame(self):
        if self.camera is not None and self.camera_active and not self.product_detected:
            ret, frame = self.camera.read()
            if ret:
                product = self.detector.detect_product(frame)
                
                if product:
                    self.camera_frame.hide()
                    self.product_modal.setParent(self)
                    camera_pos = self.camera_frame.pos()
                    modal_x = camera_pos.x() - 20
                    modal_y = camera_pos.y() + (self.camera_frame.height() - self.product_modal.height()) // 2
                    self.product_modal.setGeometry(modal_x, modal_y, 271, 270)
                    self.product_modal.show()
                    self.product_modal.raise_()
                    self.product_modal.update_product(product)
                    self.product_detected = True
                    self.stop_camera()
                
                # Update camera view (behind modal)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
                h, w, ch = frame.shape
                scale = min(0.8,0.8)
                new_w, new_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
                
                bytes_per_line = ch * new_w
                qt_image = QImage(frame.data, new_w, new_h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.camera_label.setPixmap(pixmap)

    def add_to_cart(self, product, quantity):
        is_existing = self.cart_state.add_item(product, quantity)
        self.update_cart_display()
        self.resume_camera()  # Add this line to resume camera after adding to cart
        return is_existing

    def resume_camera(self):
        self.product_detected = False
        self.camera_frame.show()
        self.start_camera()

    def show_cancel_dialog(self):
        # Stop camera if running
        if self.camera_active:
            self.stop_camera()

        # Create container for blurred background
        blur_container = QWidget(self)
        blur_container.setGeometry(0, 0, self.width(), self.height())
        blur_container.setStyleSheet("background-color: rgba(255, 255, 255, 0.5);")
        
        # Apply blur effect
        self.blur_effect.setBlurRadius(0)
        blur_container.setGraphicsEffect(self.blur_effect)
        
        # Show dialog
        dialog = CancelShoppingModal(self)
        dialog.timer = self.timer
        
        # Center dialog
        dialog_x = (self.width() - dialog.width()) // 2
        dialog_y = (self.height() - dialog.height()) // 2
        dialog.move(dialog_x, dialog_y)
        
        # Setup animations
        blur_anim = QPropertyAnimation(self.blur_effect, b"blurRadius")
        blur_anim.setDuration(200)

        # Show and animate in
        blur_container.show()
        blur_container.raise_()
        dialog.raise_()
        
        blur_anim.setStartValue(0)
        blur_anim.setEndValue(15)
        blur_anim.start()
        
        result = dialog.exec_()

        # Animate out and cleanup
        unblur_anim = QPropertyAnimation(self.blur_effect, b"blurRadius")
        unblur_anim.setDuration(200)
        unblur_anim.setStartValue(15)
        unblur_anim.setEndValue(0)
        
        def finish_cleanup():
            blur_container.deleteLater()
            # Resume camera only if Not Now was clicked
            if result == QDialog.Rejected and not dialog.home_page:
                self.resume_camera()
                
        unblur_anim.finished.connect(finish_cleanup)
        unblur_anim.start()

    def closeEvent(self, event):
        self.stop_camera()
        if hasattr(self, 'home_page') and self.home_page:
            self.home_page.show()
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app_icon = QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png'))
    app.setWindowIcon(app_icon)
    
    shopping_page = ShoppingPage()
    shopping_page.show()
    sys.exit(app.exec_())
