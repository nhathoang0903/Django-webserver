from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QPushButton, QApplication, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QObject, QEvent, QTimer
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon, QImage
import os
import cv2
from product_detector import ProductDetector
from product_modal import ProductModal
from cart_item_widget import CartItemWidget

class ShoppingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.cart_items = []
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.camera_active = False
        self.load_fonts()
        self.init_ui()
        self.detector = ProductDetector()
        self.product_modal = ProductModal()  # Remove camera_frame as parent
        self.product_modal.setGeometry(0, 0, 271, 299)  # Match camera frame size
        self.product_modal.add_to_cart.connect(self.add_to_cart)
        self.product_modal.hide()
        self.product_detected = False  # Add new flag
        
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
        # Make inner frame slightly smaller than outer frame
        self.scan_area.setFixedSize(231, 314)  
        self.scan_area.move(20, 20)  

        # Create corner borders for inner frame
        corner_size = 20
        line_width = 2

        # Add scan area icon
        self.camera_icon = QLabel(self.scan_area)
        scan_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    'assets', 'scanarea.png')
        self.camera_icon.setPixmap(QPixmap(scan_icon_path)
                            .scaled(97, 97, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.camera_icon.setAlignment(Qt.AlignCenter)
        
        # Center the icon in the inner frame
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
        right_section = QWidget()
        right_section.setFixedWidth(400)
        right_section.setStyleSheet("background-color: white;")
        self.right_layout = QVBoxLayout(right_section)
        self.right_layout.setContentsMargins(20, 35, 20, 20) 
        # Cart Header
        cart_header = QLabel("Your Cart")
        cart_header.setFont(QFont("Baloo", 24))
        cart_header.setStyleSheet("""
            color: black;
            padding-top: 10px;  
        """)
        self.right_layout.addWidget(cart_header)

        # Cart Content Area
        self.update_cart_display()

        main_layout.addWidget(left_section)
        main_layout.addWidget(right_section)

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
        # Clear existing cart display
        for i in reversed(range(self.right_layout.count())):
            widget = self.right_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add cart header
        cart_header = QLabel("Your Cart")
        cart_header.setFont(QFont("Baloo", 24))
        cart_header.setStyleSheet("color: black;")
        self.right_layout.addWidget(cart_header)

        # Cart content
        cart_content = QFrame()
        cart_content.setStyleSheet("background-color: white;")
        cart_layout = QVBoxLayout(cart_content)
        cart_layout.setContentsMargins(0, 50, 0, 30)  # Increase top padding to 50

        if not self.cart_items:
            # Add top stretch to push content down
            cart_layout.addStretch(3)  # Increase top stretch ratio

            # Empty cart text
            empty_text = QLabel("Empty")
            empty_text.setFont(QFont("Inria Sans", 30))
            empty_text.setStyleSheet("color: #F68003;")
            empty_text.setAlignment(Qt.AlignCenter)
            cart_layout.addWidget(empty_text)

            # Add spacing between text and icon
            cart_layout.addSpacing(20)  # Increase spacing between text and icon

            # Empty cart icon
            empty_cart_label = QLabel()
            empty_cart_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                         'assets', 'emptycart.png')
            empty_cart_pixmap = QPixmap(empty_cart_path)
            if not empty_cart_pixmap.isNull():
                empty_cart_label.setPixmap(empty_cart_pixmap.scaled(100, 100, 
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation))
            empty_cart_label.setAlignment(Qt.AlignCenter)
            cart_layout.addWidget(empty_cart_label)

            # Add bottom stretch with smaller ratio
            cart_layout.addStretch(2)  # Decrease bottom stretch ratio

        if self.cart_items:
            cart_content = QFrame()
            cart_content.setStyleSheet("background-color: #F3F3F3;")
            cart_layout = QVBoxLayout(cart_content)
            
            total_amount = 0
            for product, quantity in self.cart_items:
                item_widget = CartItemWidget(product, quantity)
                cart_layout.addWidget(item_widget)
                total_amount += product['price'] * quantity
            
            self.right_layout.addWidget(cart_content)
            
            # Update total
            total_label.setText(f"Total {total_amount} vnđ")

        self.right_layout.addWidget(cart_content)
        
        # Use stretching to push total/payment to bottom
        self.right_layout.addStretch(1)  # This will push the following widgets to the bottom
        
        # Add total and payment button
        total_container = QWidget()
        total_layout = QHBoxLayout(total_container)
        total_layout.setContentsMargins(0, 0, 0, 10)  # Add bottom margin
        
        # Add stretch to push total text towards payment button
        total_layout.addStretch()
        
        # Add total with right margin
        total_label = QLabel("Total 0 vnđ")
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
        total_layout.addWidget(payment_button)
        self.right_layout.addWidget(total_container)

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
                # Detect products
                product = self.detector.detect_product(frame)
                
                if product:
                    # Remove camera frame and replace with modal
                    self.camera_frame.hide()
                    self.product_modal.setParent(self)  # Set parent to main window
                    # Position modal at same location as camera frame
                    camera_pos = self.camera_frame.pos()
                    self.product_modal.setGeometry(
                        camera_pos.x(), 
                        camera_pos.y(), 
                        271, 299
                    )
                    self.product_modal.show()
                    self.product_modal.raise_()
                    self.product_modal.update_product(product)
                    self.product_detected = True  # Set flag when product detected
                    self.stop_camera()  # Stop camera when product is detected
                
                # Update camera view (behind modal)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                scale = min(1,1)
                new_w, new_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
                
                bytes_per_line = ch * new_w
                qt_image = QImage(frame.data, new_w, new_h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.camera_label.setPixmap(pixmap)

    def add_to_cart(self, product, quantity):
        self.cart_items.append((product, quantity))
        self.update_cart_display()

    def closeEvent(self, event):
        self.stop_camera()
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
