from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
                           QPushButton, QWidget, QSizePolicy, QGraphicsOpacityEffect)
from PyQt5.QtGui import QPixmap, QFont, QIcon, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QTimer
import os
from page3_productsinfo import SimpleImageLoader  

class CartItemWidget(QFrame):
    quantityChanged = pyqtSignal(int)  # Signal for quantity changes
    itemRemoved = pyqtSignal()  # New signal for item removal
    
    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Istok_Web/IstokWeb-Regular.ttf'))

    def __init__(self, product, quantity, parent=None):
        super().__init__(parent)
        from cart_state import CartState
        self.cart_state = CartState()  # Get singleton instance
        self.load_fonts()
        self.quantity = quantity
        self.product = product
        
        # Add instance variables for price
        self.unit_price = float(product['price'])
        self.current_price = self.unit_price * quantity
        
        self.setFixedHeight(120)  # Increased from 110 to 120
        self.setFixedWidth(370)   # Increased from 350 to 370 to give more space
        
        # Main frame styling
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        
        # Track drag state
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_threshold = 10  # Pixels to consider as drag vs click
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 5, 5)  # Further reduced right margin
        layout.setSpacing(3)  # Reduced spacing from 8 to 3
        
        # Left: Image
        image_container = QWidget()
        image_container.setStyleSheet("background-color: transparent;")
        image_container.setFixedWidth(60)  # Reduced from 65 to 60
        
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)
        
        self.image_label = QLabel()
        # Set image size based on category - increased size
        category = product.get('category', '')
        if (category == "Snack"):
            image_size = (75, 95)  
        elif (category == "Beverage"):
            image_size = (75, 95) 
        elif (category == "Food"):
            image_size = (75, 95) 
        else:
            image_size = (75, 95) 
            
        self.image_label.setFixedSize(*image_size)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                margin: 0;
                padding: 0;
            }
        """)
        
        # Get image URL with default value
        image_url = product.get('image_url', '')
        
        if image_url:  # Only try to load image if URL exists
            cache_key = f"{image_url}_{image_size[0]}x{image_size[1]}"
            
            if cache_key in SimpleImageLoader._cache:
                pixmap = SimpleImageLoader._cache[cache_key]
                self.image_label.setPixmap(pixmap)
                print(f"Loaded image from cache: {image_url}, size: {image_size}")
            else:
                pixmap = SimpleImageLoader.load_image(image_url, image_size)
                if pixmap:
                    self.image_label.setPixmap(pixmap)
                    print(f"Loaded image: {image_url}, size: {image_size}")
                else:
                    self.image_label.setText("N/A")
                    print(f"Failed to load image: {image_url}")
        else:
            self.image_label.setText("N/A")
            print("No image URL provided")

        self.image_label.setAlignment(Qt.AlignCenter)
        
        # Simpler layout - center the image vertically
        image_layout.addStretch(1)
        image_layout.addWidget(self.image_label, 0, Qt.AlignCenter)
        image_layout.addStretch(1)
        
        layout.addWidget(image_container)
        
        # Middle: Name and Quantity Controls
        middle_widget = QWidget()
        middle_widget.setStyleSheet("background-color: white;")
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins 
        middle_layout.setSpacing(2)
        
        # Product name container with more content space
        name_container = QWidget()
        name_container.setFixedWidth(195)  # Reduced from 220 to 195
        name_container.setStyleSheet("background-color: white; border: none;")
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 5)
        name_layout.setSpacing(0)
        
        # Format name with custom line breaks
        raw_name = product['name'].replace('_', ' ')
        words = raw_name.split()
        if len(words) > 2:
            # Format with line breaks based on character length, not just word count
            first_line = words[0]
            current_line = first_line
            
            for word in words[1:]:
                if len(current_line + " " + word) <= 15:  # Adjust character threshold as needed
                    current_line += " " + word
                else:
                    if first_line == current_line:
                        first_line = current_line
                        current_line = word
                    else:
                        break
            
            # Join remaining words for second line
            remaining_words = words[len(first_line.split()):]
            formatted_name = first_line + '\n' + ' '.join(remaining_words)
        else:
            formatted_name = raw_name
            
        name_label = QLabel(formatted_name)
        name_label.setFont(QFont("Inria Sans", 12, QFont.Bold))
        name_label.setWordWrap(True)
        # Removed fixed width constraints
        name_label.setStyleSheet("""
            QLabel {
                color: #000000; 
                background-color: white;
                border: none;
                qproperty-alignment: AlignLeft | AlignVCenter;
                margin: 0px;
                padding-left: 8px;
                padding-right: 0px;
                min-height: 50px;
                line-height: 1.3;
            }
        """)
        
        # Modify the name_layout to be proper for the name_label
        name_layout.addWidget(name_label, 1, Qt.AlignLeft | Qt.AlignVCenter)
        middle_layout.addWidget(name_container, 1, Qt.AlignLeft)  # Removed AlignTop to center it
        middle_layout.addStretch(1)  # Reduced stretch ratio to accommodate taller name container

        # Quantity controls with larger size
        control_size = 32  # Increased from 24 to 32

        # Quantity controls with center alignment
        quantity_container = QWidget()
        quantity_container.setFixedHeight(control_size)
        quantity_layout = QHBoxLayout(quantity_container)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(0)  # Ensure no spacing between buttons

        # Create a horizontal container to align controls 
        quantity_controls = QHBoxLayout()
        quantity_controls.setContentsMargins(0, 0, 0, 0)
        quantity_controls.setSpacing(0)  # No spacing between buttons
        quantity_controls.addStretch(1)  # Push controls to center

        # Decrease button
        decrease_btn = QPushButton("-")
        decrease_btn.setFixedSize(control_size, control_size)
        decrease_btn.setFont(QFont("Inria Sans", 16, QFont.Bold))  # Increased font size
        decrease_btn.setStyleSheet("""
            QPushButton {
                background-color: #D8D8D8;
                color: #000000;
                border: none;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
            }
        """)
        decrease_btn.clicked.connect(self.decrease_quantity)
        
        # Quantity label with larger font and red color
        self.quantity_label = QLabel(str(quantity))
        self.quantity_label.setFixedSize(control_size + 15, control_size)  # Wider for larger numbers
        self.quantity_label.setFont(QFont("Inria Sans", 18, QFont.Bold))  # Increased font size
        self.quantity_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #FF0000;
                border: none;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
            }
        """)
        
        # Increase button
        increase_btn = QPushButton("+")
        increase_btn.setFixedSize(control_size, control_size)
        increase_btn.setFont(QFont("Inria Sans", 16, QFont.Bold))  # Increased font size
        increase_btn.setStyleSheet("""
            QPushButton {
                background-color: #D8D8D8;
                color: #000000;
                border: none;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
            }
        """)
        increase_btn.clicked.connect(self.increase_quantity)
        
        # Add controls to layout without spacing
        quantity_controls.addWidget(decrease_btn)
        quantity_controls.addWidget(self.quantity_label)
        quantity_controls.addWidget(increase_btn)
        quantity_controls.addStretch(1)  # Push controls to center
        
        quantity_layout.addLayout(quantity_controls)
        
        # Use a proper QHBoxLayout for quantity controls centered
        middle_layout.addSpacing(1)  # Reduced from 3 to 1
        middle_layout.addWidget(quantity_container, 0, Qt.AlignCenter)  # Centered alignment
        middle_layout.addSpacing(0)  # Reduced from 2 to 0
        
        layout.addWidget(middle_widget, 2)  # Give middle section more proportion (changed from 1 to 2)
        
        # Right side: Price and Remove button
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: white;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(2, 5, 5, 0)  # Reduced left margin to 2
        right_layout.setSpacing(3)
        
        # Modify price label to show total price
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Istok Web", 14))  # Increased from 12 to 14
        self.price_label.setFixedHeight(35)  # Increased from 30 to 35
        self.price_label.setStyleSheet("""
            background-color: white;
            color: #FF0000;
            padding-right: 5px;
        """)
        self.price_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Ensure vertical centering
        self.update_price_display()  # Update initial price display
        right_layout.addWidget(self.price_label)
        
        # Remove button container to center it horizontally
        remove_container = QWidget()
        remove_container.setStyleSheet("background-color: white;")
        remove_layout = QHBoxLayout(remove_container)
        remove_layout.setContentsMargins(0, 0, 0, 0)
        
        # Remove button with larger icon
        remove_btn = QPushButton()
        remove_btn.setFixedSize(36, 36)  # Increased from 30x30 to 36x36
        remove_icon = QPixmap(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                       'assets', 'remove.png'))
        scaled_icon = remove_icon.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Increased icon size
        remove_btn.setIconSize(scaled_icon.size())  # Set icon size independently
        remove_btn.setIcon(QIcon(scaled_icon))
        remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 15px;  /* Increased from 12px to 15px */
            }
        """)
        remove_btn.clicked.connect(self.remove_item)
        
        # Add equal stretch on both sides to center the button
        remove_layout.addStretch(1)
        remove_layout.addWidget(remove_btn)
        remove_layout.addStretch(1)
        
        # Add remove container to right layout
        right_layout.addWidget(remove_container)
        
        layout.addWidget(right_widget)
        
        # Setup animation properties - thay đổi phần này
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.slide_animation.finished.connect(self._on_animation_finished)
        
        self.image_loaded = False

    def update_price_display(self):
        """Update the price display based on current quantity"""
        self.current_price = self.unit_price * self.quantity
        price_str = "{:,.0f}".format(self.current_price).replace(',', '.')
        # Use HTML to add bold styling and increase size
        self.price_label.setText(f"<span style='font-weight: bold; font-size: 14pt;'>{price_str} vnđ</span>")

    def increase_quantity(self):
        self.quantity += 1
        self.quantity_label.setText(str(self.quantity))
        self.update_price_display()  # Update price when quantity changes
        self.quantityChanged.emit(self.quantity)
        
    def decrease_quantity(self):
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.setText(str(self.quantity))
            self.update_price_display()  # Update price when quantity changes
            self.quantityChanged.emit(self.quantity)
        else:
            self.remove_item()
    
    def remove_item(self):
        # Start slide animation
        current_pos = self.pos()
        end_pos = QPoint(self.width() + 50, current_pos.y())
        
        self.slide_animation.setStartValue(current_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.start()

    def _on_animation_finished(self):
        self.hide()  # Hide widget after animation
        self.itemRemoved.emit()  # Emit signal to trigger removal

    def highlight(self):
        """Highlight the widget with animation"""
        # Set style trực tiếp trước
        self.setStyleSheet("""
            QFrame {
                background-color: #F8FFAA;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        
        # Set style cho tất cả widget con
        for widget in self.findChildren(QWidget):
            current_style = widget.styleSheet()
            widget.setStyleSheet(current_style + "background-color: #F8FFAA;")
        
        # Tạo animation để chuyển về màu trắng sau 5s
        def reset_styles():
            self.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 15px;
                    padding: 5px;
                }
            """)
            for widget in self.findChildren(QWidget):
                widget.setStyleSheet(widget.styleSheet().replace("background-color: #F8FFAA;", "background-color: white;"))
        
        QTimer.singleShot(5000, reset_styles)

    def mousePressEvent(self, event):
        """Track mouse press for potential drag operations"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse movement to differentiate between drag and click"""
        if event.buttons() & Qt.LeftButton and self.drag_start_pos is not None:
            # Calculate distance moved
            distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if distance > self.drag_threshold:
                self.is_dragging = True
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release event"""
        self.drag_start_pos = None
        self.is_dragging = False
        super().mouseReleaseEvent(event)