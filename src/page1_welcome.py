from base_page import BasePage
from PyQt5.QtWidgets import (QVBoxLayout, QLabel, QWidget,
                           QPushButton, QApplication, QMessageBox, QHBoxLayout, QDialog,
                           QGraphicsDropShadowEffect, QSizePolicy, QGraphicsBlurEffect)
import requests
import json
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon, QColor, QMovie
from page2_instruction import InstructionPage  
import os
from cart_state import CartState  
from page_timing import PageTiming
from components.PageTransitionOverlay import PageTransitionOverlay
import qrcode
from io import BytesIO
from config import DEVICE_ID, CUSTOMER_HISTORY_LINK_URL, CART_STATUS_API, CART_CONNECT


class WelcomePage(BasePage):  # Changed from QWidget to BasePage
    # Add signal definitions
    switch_to_page = pyqtSignal(int)
    switch_to_login = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Add signal connections
        self.switch_to_page.connect(self.on_switch_page)
        self.switch_to_login.connect(self.on_switch_login)
        # Clear any existing cart data when welcome page opens
        cart_state = CartState()
        cart_state.clear_cart()
        self.load_fonts()
        self.init_ui()
        self.transition_overlay = PageTransitionOverlay(self)
        
        # Initialize frames immediately
        self.select_mode_frame = SelectModeFrame(self)
        self.qr_frame = MemberQRFrame(self)
        
        # Hide frames initially
        self.select_mode_frame.hide()
        self.qr_frame.hide()
        
        # Install event filter for Ctrl+X detection
        self.installEventFilter(self)
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # Add welcome message overlay
        self.welcome_overlay = QWidget(self)
        self.welcome_overlay.setGeometry(self.rect())
        self.welcome_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(245, 249, 247, 0.8);  /* Semi-transparent background */
            }
        """)
        self.welcome_overlay.hide()
        
        # Add blur effect for background
        self.blur_effect = QGraphicsBlurEffect()
        self.blur_effect.setBlurRadius(10)
        
        # Create welcome container
        self.welcome_container = QWidget(self.welcome_overlay)
        self.welcome_container.setFixedSize(500, 400)  # Increased container size
        self.welcome_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        
        # Create welcome layout
        self.welcome_layout = QVBoxLayout(self.welcome_container)
        self.welcome_layout.setSpacing(20)
        self.welcome_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create gif container
        self.gif_container = QWidget(self.welcome_container)
        self.gif_container.setFixedSize(305, 305)
        self.gif_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        
        # Create gif label
        self.gif_label = QLabel(self.gif_container)
        gif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'welcome_member.gif')
        self.gif_movie = QMovie(gif_path)
        self.gif_label.setMovie(self.gif_movie)
        
        # Set size policy to maintain aspect ratio
        self.gif_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.gif_label.setScaledContents(True)  # This will maintain aspect ratio
        self.gif_label.setFixedSize(305, 305)  # Match container size
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        
        # Create gif container layout
        gif_layout = QVBoxLayout(self.gif_container)
        gif_layout.setContentsMargins(0, 0, 0, 0)
        gif_layout.setSpacing(0)
        gif_layout.addWidget(self.gif_label)
        
        # Create welcome message label
        self.welcome_msg = QLabel(self.welcome_container)
        self.welcome_msg.setFont(QFont("Inter", 18, QFont.Bold))
        self.welcome_msg.setStyleSheet("""
            QLabel {
                color: #3D6F4A;
                background: transparent;
                padding: 10px;
                border: none;
            }
        """)
        self.welcome_msg.setAlignment(Qt.AlignCenter)
        
        # Add widgets to layout
        self.welcome_layout.addWidget(self.gif_container, alignment=Qt.AlignCenter)
        self.welcome_layout.addWidget(self.welcome_msg, alignment=Qt.AlignCenter)
        
        # Create overlay layout
        self.overlay_layout = QVBoxLayout(self.welcome_overlay)
        self.overlay_layout.setContentsMargins(0, 0, 0, 0)
        self.overlay_layout.addWidget(self.welcome_container, alignment=Qt.AlignCenter)

    def load_fonts(self):
        # Load custom fonts from font-family directory
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        
        # Load Tillana Bold
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        
        # Load Inria Sans Bold
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Bold.ttf'))
        
        # Load Poppins Italic
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        
        # Load Inter Bold
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))

        # Load Segoe UI Emoji
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Segoe_UI_Emoji/seguiemj.ttf'))

    def init_ui(self):
        self.setWindowTitle('Smart Shopping Cart')
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
        
        # Update stylesheet for full coverage
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F9F7;
            }
            QPushButton {
                background-color: #507849;
                color: white;
                border-radius: 24px;
                padding: 15px 10px;
                font-size: 14px;
                border: none;
                text-transform: uppercase;
                font-weight: bold;
                width: 145px;
                height: 18px;
            }
            QPushButton:hover {
                background-color: #3e5c38;
            }
        """)

        # Main layout
        layout = QHBoxLayout()
        layout.setContentsMargins(30, 8, 50, 50)  # Reduced top margin from 20 to 10
        layout.setSpacing(30)

        # Left side content
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # Changed to AlignTop
        left_layout.setSpacing(10)  # Reduced spacing from 15 to 10

        # Logo at the top left
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignLeft)
        left_layout.addWidget(logo_label)

        # Add some spacing
        left_layout.addSpacing(10)  

        # Welcome text using Inria Sans Bold
        welcome_label = QLabel("Welcome to Cartsy !")
        welcome_label.setFont(QFont("Inria Sans", 30, QFont.Bold))
        welcome_label.setStyleSheet("color: #3D6F4A;")
        left_layout.addWidget(welcome_label)

        # Tagline using Poppins Italic
        tagline_label = QLabel('"Shop smarter, enjoy life more"')
        tagline_label.setFont(QFont("Poppins", 15))
        tagline_label.setStyleSheet("""
            color: #E72225;
            font-style: italic;
        """)
        left_layout.addWidget(tagline_label)

        # Add less spacing before button
        left_layout.addSpacing(10) 

        # Get Started button using Inter Bold
        start_button = QPushButton("GET STARTED")
        start_button.setFont(QFont("Inter", QFont.Bold))
        start_button.setCursor(Qt.PointingHandCursor)
        start_button.clicked.connect(self.start_shopping)
        left_layout.addWidget(start_button, alignment=Qt.AlignLeft)

        # Reduce stretch factor
        left_layout.addStretch(1) 

        # Right side image
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 0, 0) 
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Keep VCenter alignment for instruction image
        
        welcome_img_label = QLabel()
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'welcome-instruction.png')
        img_pixmap = QPixmap(img_path)
        if not img_pixmap.isNull():
            welcome_img_label.setPixmap(img_pixmap.scaled(370, 345, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        welcome_img_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Keep VCenter alignment
        right_layout.addWidget(welcome_img_label)

        # Add containers to main layout
        layout.addWidget(left_container, 1)
        layout.addWidget(right_container, 1)

        self.setLayout(layout)

    def start_shopping(self):
        """Show select mode frame and handle mode selection"""
        self.select_mode_frame.selected_mode = None  # Reset mode
        self.select_mode_frame.show()
        
        # Wait for frame to hide
        while self.select_mode_frame.isVisible():
            QApplication.processEvents()
        
        # Check selected mode
        mode = self.select_mode_frame.selected_mode
        if mode == 1:  # Guest
            print("Selected mode: Guest")
            self.switch_to_page.emit(2)
        elif mode == 2:  # Member
            print("Selected mode: Member")
            self.switch_to_login.emit()

    # Add signal handlers
    def on_switch_page(self, page_number):
        if page_number == 2:
            start_time = PageTiming.start_timing()
            self.instruction_page = InstructionPage()
            
            def show_new_page():
                self.instruction_page.show()
                self.transition_overlay.fadeOut(lambda: self.hide())
                PageTiming.end_timing(start_time, "WelcomePage", "InstructionPage")
                
            self.transition_overlay.fadeIn(show_new_page)
            
    def on_switch_login(self):
        print("Opening Member QR Frame...")
        self.qr_frame.show()

    def show_select_mode(self):
        """Helper method to show select mode frame"""
        self.select_mode_frame.show()

    def proceed_to_instruction(self):
        """Switch to instruction page"""
        # Stop gif animation
        self.gif_movie.stop()
        
        # Hide welcome overlay
        self.welcome_overlay.hide()
        
        # Create and show instruction page directly
        start_time = PageTiming.start_timing()
        self.instruction_page = InstructionPage()
        
        def show_new_page():
            self.instruction_page.show()
            self.transition_overlay.fadeOut(lambda: self.hide())
            PageTiming.end_timing(start_time, "WelcomePage", "InstructionPage")
            
        self.transition_overlay.fadeIn(show_new_page)

    def show_welcome_message(self, customer_name):
        """Show welcome message with blurred background"""
        # Apply blur to main content
        for child in self.findChildren(QWidget):
            if child != self.welcome_overlay and child.isVisible():
                # Create blur effect for each visible widget
                blur = QGraphicsBlurEffect()
                blur.setBlurRadius(5)  # Lighter blur
                child.setGraphicsEffect(blur)
        
        # Update welcome message
        self.welcome_msg.setText(f"Hello, {customer_name}!")
        
        # Start gif animation
        self.gif_movie.start()
        
        # Show overlay
        self.welcome_overlay.show()
        self.welcome_overlay.raise_()
        
        # Schedule page transition
        QTimer.singleShot(2000, self.proceed_to_instruction)

class BaseOverlayFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(parent.geometry() if parent else QWidget().geometry())
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            BaseOverlayFrame {
                background-color: rgba(80, 120, 73, 0.15);
            }
        """)
        
        self.container = QWidget(self)
        self.container.setAttribute(Qt.WA_StyledBackground, True)
        
        # Try to add shadow effect, fall back gracefully if not supported
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 50))
            shadow.setOffset(0, 0)
            self.container.setGraphicsEffect(shadow)
        except Exception:
            # If shadow effect fails, add a border instead
            self.container.setStyleSheet("""
                border: 2px solid rgba(0, 0, 0, 0.1);
            """)
        
        self.main_layout = QVBoxLayout(self)  # Store layout as instance variable
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.container)

    def showEvent(self, event):
        """Center the frame when shown"""
        if self.parent():
            parent_geo = self.parent().geometry()
            self.setGeometry(parent_geo)
            container_x = (parent_geo.width() - self.container.width()) // 2
            container_y = (parent_geo.height() - self.container.height()) // 2
            self.container.move(container_x, container_y)
        super().showEvent(event)

class MemberQRFrame(BaseOverlayFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.welcome_page = parent
        self.container.setFixedSize(400, 500)  # Reduced from 450x550
        
        # Main layout with adjusted margins
        layout = QVBoxLayout()
        layout.setSpacing(0)  # Reduce overall spacing
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(45, 50)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(80, 120, 73, 0.1);
                color: #507849;
                border: none;
                border-radius: 20px;
                font-size: 28px;
                font-weight: bold;
                margin: 0;
            }
            QPushButton:hover {
                background-color: rgba(80, 120, 73, 0.2);
            }
        """)
        close_btn.clicked.connect(self.hide)
        
        title = QLabel("Member Login")
        title.setFont(QFont("Inter", 24, QFont.Bold))
        title.setStyleSheet("color: #3D6F4A; border: none;")
        
        header_layout.addWidget(close_btn, alignment=Qt.AlignLeft)
        header_layout.addWidget(title, alignment=Qt.AlignCenter)
        header_layout.addSpacing(40)  # Match close button width
        layout.addWidget(header)
        
        # Main content container
        content = QWidget()
        content.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 20px;
            }
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)  # Reduced spacing
        content_layout.setContentsMargins(25, 20, 25, 15)  # Smaller margins
        
        # QR Section
        qr_title = QLabel("Scan QR Code")
        qr_title.setFont(QFont("Inter", 16, QFont.Bold))
        qr_title.setStyleSheet("color: #3D6F4A; background: transparent;")
        qr_title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(qr_title)
        # Instructions below section
        instruction = QLabel("Open CARTSY mobile app and\nscan this QR code")
        instruction.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(instruction)
        
        content_layout.addSpacing(8)  # Add spacing between title and QR code
        
        # QR code container without border
        qr_container = QWidget()
        qr_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: none;
            }
        """)
        qr_container.setFixedSize(250, 250)
        
        qr_layout = QVBoxLayout(qr_container)
        qr_layout.setContentsMargins(0, 0, 0, 0)  # Remove padding
        qr_layout.setSpacing(0)
        qr_layout.setAlignment(Qt.AlignCenter)
        
        # QR code generation and display
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_data = DEVICE_ID
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="#507849", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_pixmap = QPixmap()
        qr_pixmap.loadFromData(buffer.getvalue())
        
        qr_label = QLabel()
        qr_label.setFixedSize(250, 250)  # Match container size
        qr_label.setPixmap(qr_pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        qr_label.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(qr_label)
        
        content_layout.addWidget(qr_container, alignment=Qt.AlignCenter)
        
        content_layout.addSpacing(25)  # Increased spacing between QR code and instruction
        
        # Spacer widget to push instruction down
        spacer = QWidget()
        spacer.setFixedHeight(25)  # Adjust this value to move instruction down
        spacer.setStyleSheet("background: transparent;")
        content_layout.addWidget(spacer)

        # Add a stretch to push the button down
        content_layout.addStretch(1)
        
        # Guest mode button at bottom
        guest_btn = QPushButton("Or continue as guest")  
        guest_btn.setFont(QFont("Inter", 12))  
        guest_btn.setCursor(Qt.PointingHandCursor)
        guest_btn.setFixedSize(250, 55)
        guest_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #507849;
                border: 2px solid #507849;
                border-radius: 22px;
                padding: 8px 20px;
                margin-bottom: 5px;
            }
            QPushButton:hover {
                background-color: rgba(80, 120, 73, 0.1);
            }
        """)
        guest_btn.clicked.connect(self.switch_to_guest)
        content_layout.addWidget(guest_btn, alignment=Qt.AlignCenter)
        
        layout.addWidget(content)
        
        self.container.setStyleSheet("""
            QWidget {
                background: white;
                border: none;
                border-radius: 25px;
            }
        """)
        
        # Add shadow effect with larger blur radius
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(30)
            shadow.setColor(QColor(0, 0, 0, 60))
            shadow.setOffset(0, 4)
            self.container.setGraphicsEffect(shadow)
        except Exception:
            self.container.setStyleSheet(self.container.styleSheet() + """
                border: 1px solid rgba(0, 0, 0, 0.1);
            """)
            
        self.container.setLayout(layout)
        
        # Add timer for polling
        self.poll_timer = QTimer()
        self.poll_timer.setInterval(500)  # 500ms interval
        self.poll_timer.timeout.connect(self.check_cart_status)
        
        # Add success message label
        self.success_msg = QLabel()
        self.success_msg.setFont(QFont("Inter", 18, QFont.Bold))  # Increased font size
        self.success_msg.setStyleSheet("""
            QLabel {
                color: #3D6F4A;
                background: transparent;
                padding: 20px;
            }
        """)
        self.success_msg.setAlignment(Qt.AlignCenter)
        self.success_msg.hide()
        content_layout.addWidget(self.success_msg)
        
        # Store content widgets that need to be hidden/blurred
        self.content = content
        self.qr_container = qr_container
        
        # Create blur effect
        self.blur_effect = QGraphicsBlurEffect()
        self.blur_effect.setBlurRadius(10)
        self.content.setGraphicsEffect(self.blur_effect)
        self.blur_effect.setEnabled(False)

    def showEvent(self, event):
        super().showEvent(event)
        # Start polling when QR frame is shown
        self.poll_timer.start()
        
    def hideEvent(self, event):
        super().hideEvent(event)
        # Stop polling when QR frame is hidden
        self.poll_timer.stop()
        
    def check_cart_status(self):
        """Poll cart status API"""
        try:
            response = requests.get(f"{CART_STATUS_API}{DEVICE_ID}/")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "in_use" and data.get("customer_phone"):
                    # Stop polling and hide QR frame
                    self.poll_timer.stop()
                    self.hide()
                    
                    # Save phone number
                    self.save_phone_number(data["customer_phone"])
                    
                    # Show welcome message on main page
                    if self.welcome_page:
                        self.welcome_page.show_welcome_message(data['customer_name'])
                        # Switch to instruction page after 2 seconds
                        QTimer.singleShot(2000, self.proceed_to_instruction)
                    
        except Exception as e:
            print(f"Error checking cart status: {e}")
            
    def save_phone_number(self, phone):
        """Save phone number to JSON file"""
        try:
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'config', 'phone_number.json')
            with open(file_path, 'w') as f:
                json.dump({"phone_number": phone}, f)
        except Exception as e:
            print(f"Error saving phone number: {e}")
            
    def proceed_to_instruction(self):
        """Switch to instruction page"""
        self.hide()
        if self.welcome_page:
            self.welcome_page.select_mode_frame.selected_mode = 2  # Set member mode
            self.welcome_page.switch_to_page.emit(2)  # Switch to instruction page

    def switch_to_guest(self):
        """Switch to guest mode and connect to server"""
        try:
            # Prepare data for guest mode
            data = {
                "phone_number": "",
                "device_id": DEVICE_ID
            }
            
            # Send POST request to connect API
            response = requests.post(CART_CONNECT, json=data)
            
            if response.status_code == 200:
                self.hide()
                if self.welcome_page:
                    self.welcome_page.select_mode_frame.selected_mode = 1  # Set guest mode
                    self.welcome_page.switch_to_page.emit(2)  # Switch to instruction page
            else:
                QMessageBox.warning(self, "Connection Error", 
                    "Failed to connect as guest. Please try again.")
                
        except Exception as e:
            print(f"Error connecting to server: {e}")
            QMessageBox.warning(self, "Connection Error", 
                "Failed to connect to server. Please try again.")

class SelectModeFrame(BaseOverlayFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_mode = None
        self.container.setFixedSize(500, 400)
        self.container.setStyleSheet("""
            QWidget {
                background: white;
                border: 2px solid #507849;
                border-radius: 25px;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self.container)
        layout.setSpacing(25)
        layout.setContentsMargins(35, 35, 35, 35)
        
        # Header container
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Back button
        back_btn = QPushButton("←")
        back_btn.setFixedSize(45, 45)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #507849;
                border: none;
                font-size: 32px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #3e5c38;
            }
        """)
        back_btn.clicked.connect(self.close)
        
        # Title
        title = QLabel("Shopping Mode")
        title.setFont(QFont("Inter", 24, QFont.Bold))
        title.setStyleSheet("color: #3D6F4A; border: none;")
        
        header_layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        header_layout.addWidget(title, alignment=Qt.AlignCenter)
        header_layout.addSpacing(45)  # Balance the back button
        
        layout.addWidget(header)
        
        # Subtitle
        subtitle = QLabel("Choose your shopping experience")
        subtitle.setFont(QFont("Inter", 14))
        subtitle.setStyleSheet("color: #666666; border: none;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # Buttons container
        button_layout = QHBoxLayout()
        button_layout.setSpacing(25)
        
        # Guest button
        guest_btn = self._create_mode_button("👤", "Guest", 
            "Quick shopping without\nregistration", 1)
        
        # Member button
        member_btn = self._create_mode_button("👥", "Member",
            "Access exclusive member\nbenefits", 2)
        
        button_layout.addWidget(guest_btn)
        button_layout.addWidget(member_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QWidget {
                background: white;
                border: 2px solid #507849;
                border-radius: 25px;
            }
        """)
        
        self.selected_mode = None

    def _create_mode_button(self, icon, title, description, mode):
        btn = QPushButton()
        btn.setFixedSize(200, 160)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.mode_selected(mode))
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 20))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Inter", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #3D6F4A; background: transparent; border: none;")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Inter", 10))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; background: transparent; border: none;")
        desc_label.setWordWrap(True)
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        
        btn.setLayout(layout)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 2px solid #E0E0E0;
                border-radius: 20px;
            }
            QPushButton:hover {
                border-color: #507849;
            }
            QPushButton > QWidget {
                background: transparent;
            }
        """)
        
        return btn

    def mode_selected(self, mode):
        """Handle mode selection and API connection"""
        self.selected_mode = mode
        
        if mode == 1:  # Guest mode
            try:
                # Prepare data for guest mode
                data = {
                    "phone_number": "",
                    "device_id": DEVICE_ID
                }
                
                print("Sending guest mode connection request...")
                print(f"Request data: {data}")
                print(f"API URL: {CART_CONNECT}")
                
                # Send POST request to connect API
                response = requests.post(CART_CONNECT, json=data)
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text}")
                
                if response.status_code == 200:
                    self.hide()
                else:
                    QMessageBox.warning(self, "Connection Error", 
                        "Failed to connect as guest. Please try again.")
                    return
                    
            except Exception as e:
                print(f"Error connecting to server: {e}")
                QMessageBox.warning(self, "Connection Error", 
                    "Failed to connect to server. Please try again.")
                return
        
        self.hide()  # Hide frame after successful connection or if member mode selected

    def close(self):
        self.hide()  # Always hide instead of close

if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    welcome = WelcomePage()
    welcome.show()

    sys.exit(app.exec_())