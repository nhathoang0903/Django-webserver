from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
                           QPushButton, QWidget, QSizePolicy, QGraphicsOpacityEffect)
from PyQt5.QtGui import QPixmap, QFont, QIcon, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QTimer
import os
from page3_productsinfo import SimpleImageLoader  
import weakref
from utils.translation import _, get_current_language

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
        
        # Add cooldown mechanism to prevent rapid clicking
        self.button_cooldown = False
        self.cooldown_timer = QTimer(self)
        self.cooldown_timer.timeout.connect(self.reset_cooldown)
        self.cooldown_duration = 1000  # milliseconds between clicks
        
        self.setFixedHeight(280) 
        self.setFixedWidth(780)   
        
        # Main frame styling
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 30px;
                padding: 18px;
                border: none;
            }
        """)
        
        # Track drag state
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_threshold = 10  # Pixels to consider as drag vs click
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 20, 15, 20)
        layout.setSpacing(15) 
        
        # Left: Image - push further left but ensure not cut
        image_container = QWidget()
        image_container.setStyleSheet("background-color: transparent;")
        image_container.setFixedWidth(140)  # Increased from 130 to 140 to avoid cutting
        
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)
        
        self.image_label = QLabel()
        # Set image size based on category - with consistent sizes
        category = product.get('category', '')
        image_size = (140, 160) 
            
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
        
        # Simpler layout - center the image vertically and ensure visible
        image_layout.addStretch(1)
        image_layout.addWidget(self.image_label, 0, Qt.AlignCenter)  # Removed AlignRight to prevent cutting
        image_layout.addStretch(1)
        
        layout.addWidget(image_container)

        spacer_widget = QWidget()
        spacer_widget.setFixedWidth(10)
        spacer_widget.setStyleSheet("background-color: transparent;")
        layout.addWidget(spacer_widget)
        
        # Middle: Name and Quantity Controls 
        middle_widget = QWidget()
        middle_widget.setStyleSheet("background-color: white;")
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(15, 0, 0, 0)
        middle_layout.setSpacing(15)
        
        # Product name container
        name_container = QWidget()
        name_container.setFixedWidth(390)  # Increased from 380 to 390
        name_container.setStyleSheet("background-color: white; border: none;")
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 15)
        name_layout.setSpacing(0)
        
        raw_name = product['name'].replace('_', ' ')
        words = raw_name.split()
        
        # Print original name information for debugging
        print(f"Processing name: '{raw_name}' - Length: {len(raw_name)}, Word count: {len(words)}")
        
        # Intelligent line break algorithm based on word count and length
        if len(words) >= 2:
            # For 4 or more words, typically break after word 2 or 3
            if len(words) >= 4:
                # Check if first 3 words aren't too long
                first_three = ' '.join(words[:3])
                if len(first_three) <= 16:  # More conservative limit for longer names
                    first_line = first_three
                    second_line = ' '.join(words[3:])
                    print(f"4+ words: Breaking after word 3 - First line: '{first_line}' ({len(first_line)} chars)")
                else:
                    # First 3 words too long, break after word 2
                    first_two = ' '.join(words[:2])
                    first_line = first_two
                    second_line = ' '.join(words[2:])
                    print(f"4+ words: Breaking after word 2 - First line: '{first_line}' ({len(first_line)} chars)")
            
            # For exactly 3 words
            elif len(words) == 3:
                # Check if first 2 words aren't too long
                first_two = ' '.join(words[:2])
                if len(first_two) <= 16:
                    first_line = first_two
                    second_line = words[2]
                    print(f"3 words: Breaking after word 2 - First line: '{first_line}' ({len(first_line)} chars)")
                else:
                    # First 2 words too long, break after word 1
                    first_line = words[0]
                    second_line = ' '.join(words[1:])
                    print(f"3 words: Breaking after word 1 - First line: '{first_line}' ({len(first_line)} chars)")
            
            # For exactly 2 words
            else:
                total_length = len(' '.join(words))
                if total_length <= 18:  # If total is short enough, keep on one line
                    first_line = ' '.join(words)
                    second_line = ""
                    print(f"2 words: Keeping on one line - '{first_line}' ({len(first_line)} chars)")
                else:
                    # Split into two lines
                    first_line = words[0]
                    second_line = words[1]
                    print(f"2 words: Breaking after word 1 - First line: '{first_line}' ({len(first_line)} chars)")
            
            # Build final formatted name
            if second_line:
                formatted_name = first_line + '\n' + second_line
                print(f"Final format: Two lines - '{first_line}' and '{second_line}'")
            else:
                formatted_name = first_line
                print(f"Final format: Single line - '{first_line}'")
        
        else:  # Single word
            formatted_name = raw_name
            print(f"Single word name: '{formatted_name}'")
        
        name_label = QLabel(formatted_name)
        name_label.setFont(QFont("Inria Sans", 24, QFont.Bold))
        name_label.setWordWrap(True)
        name_label.setStyleSheet("""
            QLabel {
                color: #000000; 
                background-color: transparent;
                border: none;
                qproperty-alignment: AlignVCenter;
                margin: 0px;
                padding-left: 0px; 
                padding-right: 0px;
                min-height: 100px;
                line-height: 1.5;
            }
        """)
        
        # Modify the name_layout to be proper for the name_label
        name_layout.addWidget(name_label, 1, Qt.AlignLeft | Qt.AlignVCenter)
        middle_layout.addWidget(name_container, 1, Qt.AlignLeft)
        middle_layout.addStretch(1)

        # Quantity controls
        control_size = 74

        # Quantity controls with center alignment
        quantity_container = QWidget()
        quantity_container.setFixedHeight(control_size)
        quantity_layout = QHBoxLayout(quantity_container)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(0)

        quantity_controls = QHBoxLayout()
        quantity_controls.setContentsMargins(0, 0, 0, 0)
        quantity_controls.setSpacing(0) 
        
        # Don't add stretch here to align with name
        # quantity_controls.addStretch(1)  # Push controls to center

        # Decrease button
        decrease_btn = QPushButton("-")
        decrease_btn.setFixedSize(control_size, control_size)
        decrease_btn.setFont(QFont("Inria Sans", 24, QFont.Bold))
        decrease_btn.setStyleSheet("""
            QPushButton {
                background-color: #D8D8D8;
                color: #000000;
                border: none;
                border-radius: 18px;  
                font-size: 46px;  
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #909090;
            }
        """)
        decrease_btn.clicked.connect(self.decrease_quantity)
        
        # Quantity label with larger font and red color
        self.quantity_label = QLabel(str(quantity))
        self.quantity_label.setFixedSize(control_size + 30, control_size)
        self.quantity_label.setFont(QFont("Inria Sans", 28, QFont.Bold))
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
        increase_btn.setFont(QFont("Inria Sans", 24, QFont.Bold))
        increase_btn.setStyleSheet("""
            QPushButton {
                background-color: #D8D8D8;
                color: #000000;
                border: none;
                border-radius: 18px; 
                font-size: 46px;  
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #909090;
            }
        """)
        increase_btn.clicked.connect(self.increase_quantity)
        
        # Store references to buttons for enabling/disabling
        self.decrease_btn = decrease_btn
        self.increase_btn = increase_btn
        
        # Add controls to layout without spacing
        quantity_controls.addWidget(decrease_btn)
        quantity_controls.addWidget(self.quantity_label)
        quantity_controls.addWidget(increase_btn)
        quantity_controls.addStretch(1)  # Push controls to the left
        
        quantity_layout.addLayout(quantity_controls)
        
        # Use a proper QHBoxLayout for quantity controls aligned with name
        middle_layout.addSpacing(5)
        middle_layout.addWidget(quantity_container, 0, Qt.AlignLeft)  # Changed from AlignCenter to AlignLeft
        middle_layout.addSpacing(5)
        
        layout.addWidget(middle_widget, 3)
        
        # Right side: Price and Remove button - adjust width
        right_widget = QWidget()
        right_widget.setFixedWidth(240)  # Increased from 230 to 240
        right_widget.setStyleSheet("background-color: white;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 10, 15, 10)
        right_layout.setSpacing(5)
        
        # Price container with fixed alignment
        price_container = QWidget()
        price_layout = QVBoxLayout(price_container)
        price_layout.setContentsMargins(0, 0, 0, 0)
        
        # Price label
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Istok Web", 24))
        self.price_label.setStyleSheet("color: #FF0000; background-color: white;")
        self.price_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.update_price_display()
        price_layout.addWidget(self.price_label)
        
        # Add price_container to right_layout
        right_layout.addWidget(price_container, 1, Qt.AlignTop | Qt.AlignRight)
        
        # Add spacer to push elements apart
        right_layout.addStretch(1)
        
        # Container for remove button to align with price - adjusted position
        remove_container = QWidget()
        remove_container_layout = QHBoxLayout(remove_container)
        remove_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Remove button
        remove_btn = QPushButton()
        remove_btn.setFixedSize(60, 60)
        remove_icon = QPixmap(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      'assets', 'remove.png'))
        scaled_icon = remove_icon.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        remove_btn.setIconSize(scaled_icon.size())
        remove_btn.setIcon(QIcon(scaled_icon))
        remove_btn.setStyleSheet("QPushButton {border: none; background-color: transparent;} QPushButton:hover {background-color: #f0f0f0; border-radius: 30px;}")
        remove_btn.clicked.connect(self.remove_item)
        
        # Add button to container layout, adjusted to align with price
        remove_container_layout.addStretch(1)  # Push button to match price alignment
        remove_container_layout.addWidget(remove_btn)
        remove_container_layout.addSpacing(5)  # Small right spacing
        
        # Add remove container to right layout
        right_layout.addWidget(remove_container, 0, Qt.AlignBottom)
        
        layout.addWidget(right_widget)
        
        # Setup animation properties
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.slide_animation.finished.connect(self._on_animation_finished)
        
        self.image_loaded = False

    def reset_cooldown(self):
        """Reset the button cooldown state"""
        self.button_cooldown = False
        print("[CartItemWidget] Button cooldown ended")

    def update_price_display(self):
        """Update the price display based on current quantity"""
        self.current_price = self.unit_price * self.quantity
        price_str = "{:,.0f}".format(self.current_price).replace(',', '.')
        
        # Adjust font size based on price length to prevent overflow
        if len(price_str) > 7:
            font_size = 19
        else:
            font_size = 21
            
        self.price_label.setText(f"<span style='font-weight: bold; font-size: {font_size}pt;'>{price_str} vnđ</span>")

    def increase_quantity(self):
        # Check if we're in cooldown period
        if self.button_cooldown:
            return
            
        # Apply cooldown
        self.button_cooldown = True
        
        # Increment quantity
        self.quantity += 1
        self.quantity_label.setText(str(self.quantity))
        self.update_price_display()  # Update price when quantity changes
        self.quantityChanged.emit(self.quantity)
        
        # Start cooldown timer
        self.cooldown_timer.start(self.cooldown_duration)
        
    def decrease_quantity(self):
        # Check if we're in cooldown period
        if self.button_cooldown:
            return
            
        # Apply cooldown
        self.button_cooldown = True
        
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.setText(str(self.quantity))
            self.update_price_display()  # Update price when quantity changes
            self.quantityChanged.emit(self.quantity)
            
            # Start cooldown timer
            self.cooldown_timer.start(self.cooldown_duration)
        else:
            # For removal, we don't need cooldown
            self.button_cooldown = False
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
                border-radius: 20px;  
                padding: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        # Set style cho tất cả widget con
        for widget in self.findChildren(QWidget):
            current_style = widget.styleSheet()
            widget.setStyleSheet(current_style + "background-color: #F8FFAA;")
        
        # Tạo biến để theo dõi widget
        # Sử dụng weakref để tránh giữ reference khi widget đã bị xóa
        self_ref = weakref.ref(self)
        
        # Tạo animation để chuyển về màu trắng sau 5s
        def reset_styles():
            # Kiểm tra xem widget có còn tồn tại không
            self_widget = self_ref()
            if self_widget is None or not hasattr(self_widget, 'setStyleSheet'):
                print("Widget đã bị xóa, bỏ qua reset styles")
                return
                
            try:
                self_widget.setStyleSheet("""
                    QFrame {
                        background-color: white;
                        border-radius: 20px;  /* Increased from 15px to 20px */
                        padding: 8px;  /* Increased from 5px to 8px */
                        border: 1px solid #E0E0E0;
                    }
                """)
                
                for widget in self_widget.findChildren(QWidget):
                    try:
                        current_style = widget.styleSheet()
                        widget.setStyleSheet(current_style.replace("background-color: #F8FFAA;", "background-color: white;"))
                    except RuntimeError:
                        # Bỏ qua nếu widget con đã bị xóa
                        continue
            except RuntimeError as e:
                print(f"Lỗi khi reset styles: {e}")
        
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