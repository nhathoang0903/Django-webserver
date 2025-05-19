from base_page import BasePage
from PyQt5.QtWidgets import (QVBoxLayout, QLabel, QWidget,
                           QPushButton, QApplication, QMessageBox, QHBoxLayout, QDialog,
                           QGraphicsDropShadowEffect, QSizePolicy, QGraphicsBlurEffect)
import requests
import json
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon, QColor, QMovie
from page3_productsinfo import ProductPage  
import os
from cart_state import CartState  
from page_timing import PageTiming
from components.PageTransitionOverlay import PageTransitionOverlay
from components.LanguageSelectionModal import LanguageSelectionModal
from config import DEVICE_ID, CART_CONNECT
from utils.translation import _, set_language, get_current_language
from utils.font_helpers.vietnamese import VietnameseFontHelper

class WelcomePage(BasePage):  # Changed from QWidget to BasePage
    # Add signal definitions
    switch_to_page = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        # Add signal connections
        self.switch_to_page.connect(self.on_switch_page)
        # Clear any existing cart data when welcome page opens
        cart_state = CartState()
        cart_state.clear_cart()
        self.load_fonts()
        self.init_ui()
        self.transition_overlay = PageTransitionOverlay(self)
        
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
        # Đăng ký tất cả font qua helper class
        VietnameseFontHelper.register_vietnamese_fonts()

    def init_ui(self):
        # Sử dụng translation cho tiêu đề
        self.setWindowTitle(_('app.title'))
        
        # Update stylesheet for full coverage
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F9F7;
            }
            QPushButton {
                background-color: #507849;
                color: white;
                border-radius: 35px;
                padding: 25px 30px;
                font-size: 20px;
                border: none;
                text-transform: uppercase;
                font-weight: bold;
                width: 250px;
                height: 30px;
            }
            QPushButton:hover {
                background-color: #3e5c38;
            }
            #languageButton {
                background-color: #F5F9F7;
                border: 3px solid #000000;
                padding: 0px;
                width: 80px;
                height: 80px;
                border-radius: 40px;
            }
            #languageButton:hover {
                background-color: #E8F0EB;
            }
            #startButton {
                font-size: 48px;
            }
        """)

        # Main layout
        layout = QHBoxLayout()
        layout.setContentsMargins(80, 30, 80, 80)  # Further increased margins
        layout.setSpacing(40)  # Adjusted spacing

        # Left side content
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        left_layout.setSpacing(30)  # Further increased spacing

        # Top bar with logo and language button
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(40)  # Further increased spacing
        
        # Logo at the top left - much larger size
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(450, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignLeft)
        top_bar_layout.addWidget(logo_label)
        
        # Add language button - larger size
        self.language_btn = QPushButton()
        self.language_btn.setObjectName("languageButton")
        self.language_btn.setFixedSize(80, 80)
        self.language_btn.setCursor(Qt.PointingHandCursor)
        self.language_btn.clicked.connect(self.show_language_modal)
        
        # Set language icon (using Vietnamese flag as default)
        self.update_language_icon(get_current_language())
        
        top_bar_layout.addWidget(self.language_btn)
        top_bar_layout.addStretch()
        left_layout.addWidget(top_bar)

        # Welcome text using Inria Sans - even larger font
        self.welcome_label = QLabel(_("welcomePage.welcome"))
        
        # Xử lý font đặc biệt cho tiếng Việt ở welcome_label
        if get_current_language() == "vi":
            VietnameseFontHelper.optimize_title_font(self.welcome_label, "Inria Sans", 90)
        else:
            self.configure_font_for_label(self.welcome_label, "Inria Sans", 90, True)
            
        self.welcome_label.setStyleSheet("color: #3D6F4A;")
        left_layout.addWidget(self.welcome_label)

        # Tagline using Poppins Italic - even larger font
        self.tagline_label = QLabel(_("welcomePage.tagline"))
        if get_current_language() == "vi":
            VietnameseFontHelper.optimize_vietnamese_font(self.tagline_label, "Poppins", 40, bold=False, italic=True)
        else:
            self.configure_font_for_label(self.tagline_label, "Poppins", 40, False, True)
            
        self.tagline_label.setStyleSheet("""
            color: #E72225;
            font-style: italic;
        """)
        left_layout.addWidget(self.tagline_label)

        # Add spacing before button
        left_layout.addSpacing(50) 

        # Get Started button - much larger size
        self.start_button = QPushButton(_("welcomePage.getStarted"))
        self.start_button.setObjectName("startButton")
        self.configure_font_for_button(self.start_button, "Inter", QFont.Bold, 41)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setStyleSheet("""
            font-size: 41px;
            padding: 25px 30px;
        """)
        self.start_button.setMinimumWidth(470)
        self.start_button.setMinimumHeight(105)
        self.start_button.clicked.connect(self.start_shopping)
        left_layout.addWidget(self.start_button, alignment=Qt.AlignLeft)

        # Reduce stretch factor
        left_layout.addStretch(1) 

        # Right side image - much larger size and shifted left
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)  # Reduced left margin to shift image left
        right_layout.setAlignment(Qt.AlignCenter)  # Center alignment instead of right
        
        welcome_img_label = QLabel()
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'welcome-instruction.png')
        img_pixmap = QPixmap(img_path)
        if not img_pixmap.isNull():
            welcome_img_label.setPixmap(img_pixmap.scaled(700, 910, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        welcome_img_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(welcome_img_label)

        # Add containers to main layout with adjusted proportions
        layout.addWidget(left_container, 5)  # Increased proportion for left side
        layout.addWidget(right_container, 6)  # Increased proportion for right side with image

        self.setLayout(layout)

    def configure_font_for_label(self, label, family, size, bold=False, italic=False):
        """Configure font for label with better Vietnamese support"""
        font = QFont(family, size)
        
        # Xử lý đặc biệt cho welcome_label khi hiển thị tiếng Việt
        if label == self.welcome_label and get_current_language() == "vi":
            # Tăng trọng lượng font cho welcome_label với tiếng Việt
            font.setWeight(63)  # Tăng từ 58 lên 63 để đậm hơn
            # Điều chỉnh letter spacing phù hợp cho welcome_label
            font.setLetterSpacing(QFont.PercentageSpacing, 103)
            # Điều chỉnh hinting cho văn bản tiếng Việt
            font.setHintingPreference(QFont.PreferVerticalHinting)
            # Điều chỉnh style strategy để tối ưu hiển thị
            font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        else:
            # Xử lý thông thường cho các label khác
            if bold:
                font.setWeight(QFont.Bold if get_current_language() != "vi" else 65)
            else:
                font.setWeight(QFont.Normal if get_current_language() != "vi" else 53)
            
            if get_current_language() == "vi":
                font.setHintingPreference(QFont.PreferVerticalHinting)
                font.setLetterSpacing(QFont.PercentageSpacing, 102)
            
        if italic:
            font.setItalic(True)
            
        label.setFont(font)

    def configure_font_for_button(self, button, family, weight=QFont.Normal, size=48):
        """Configure font for button with better Vietnamese support"""
        font = QFont(family, size)
        # Use specific weight for Vietnamese
        if get_current_language() == "vi":
            font.setWeight(65 if weight == QFont.Bold else 53)  # Tăng độ đậm cho chữ tiếng Việt
        else:
            font.setWeight(weight)
            
        # Make sure the font is hinting properly for Vietnamese
        font.setHintingPreference(QFont.PreferVerticalHinting if get_current_language() == "vi" else QFont.PreferDefaultHinting)
        
        # Set character spacing slightly wider for Vietnamese to avoid crowding with diacritics
        font.setLetterSpacing(QFont.PercentageSpacing, 102 if get_current_language() == "vi" else 100)
        
        button.setFont(font)

    def start_shopping(self):
        """Go directly to guest mode"""
        try:
            # Prepare data for guest mode
            data = {
                "phone_number": "",
                "device_id": DEVICE_ID
            }
            
            # Send POST request to connect API
            response = requests.post(CART_CONNECT, json=data)
            
            if response.status_code == 200:
                print("Successfully connected as guest")
                self.switch_to_page.emit(3)  # Switch to product page
            else:
                QMessageBox.warning(self, _("errorMessages.connectionError"), 
                    _("errorMessages.guestConnectionFailed"))
                
        except Exception as e:
            print(f"Error connecting to server: {e}")
            QMessageBox.warning(self, _("errorMessages.connectionError"), 
                _("errorMessages.serverConnectionFailed"))

    # Add signal handlers
    def on_switch_page(self, page_number):
        if page_number == 3:  # Changed from 2 to 3
            # Process any pending events first
            QApplication.processEvents()
            
            # Start timing
            start_time = PageTiming.start_timing()
            
            # Import and create ProductPage
            from page3_productsinfo import ProductPage  
            self.product_page = ProductPage()
            self.product_page.from_page1 = True  # Set flag to indicate coming from page1
            
            # Create transition overlay (full-screen)
            from components.PageTransitionOverlay import PageTransitionOverlay
            loading_overlay = PageTransitionOverlay(self, show_loading_text=True)
            
            def show_new_page():
                # Show the product page normally
                self.product_page.show()
                
                # Fade out the overlay and hide current page
                loading_overlay.fadeOut(lambda: self.hide())
                
                # Complete timing
                PageTiming.end_timing(start_time, "WelcomePage", "ProductPage")
            
            # Fade in the overlay (will call show_new_page when fully visible)
            loading_overlay.fadeIn(show_new_page)

    # def show_welcome_message(self, customer_name):
    #     """Show welcome message with blurred background"""
    #     # Apply blur to main content
    #     for child in self.findChildren(QWidget):
    #         if child != self.welcome_overlay and child.isVisible():
    #             # Create blur effect for each visible widget
    #             blur = QGraphicsBlurEffect()
    #             blur.setBlurRadius(5)  # Lighter blur
    #             child.setGraphicsEffect(blur)
        
    #     # Update welcome message
    #     self.welcome_msg.setText(f"Hello, {customer_name}!")
        
    #     # Start gif animation
    #     self.gif_movie.start()
        
    #     # Show overlay
    #     self.welcome_overlay.show()
    #     self.welcome_overlay.raise_()
        
    #     # Schedule page transition
    #     QTimer.singleShot(2000, self.proceed_to_instruction)

    def proceed_to_instruction(self):
        """Switch to instruction page"""
        # Stop gif animation
        self.gif_movie.stop()
        
        # Hide welcome overlay
        self.welcome_overlay.hide()
        
        # Create and show instruction page directly
        start_time = PageTiming.start_timing()
        # self.instruction_page = InstructionPage()
        
        def show_new_page():
            self.instruction_page.show()
            self.transition_overlay.fadeOut(lambda: self.hide())
            PageTiming.end_timing(start_time, "WelcomePage", "InstructionPage")
            
        self.transition_overlay.fadeIn(show_new_page)

    def show_language_modal(self):
        modal = LanguageSelectionModal(self)
        modal.language_selected.connect(self.on_language_selected)
        modal.exec_()

    def on_language_selected(self, language):
        # Mapping from displayed language name to language code
        language_code_mapping = {
            "Tiếng Việt": "vi",
            "English": "en",
            "日本語": "ja",
            "Français": "fr"
        }
        
        # Update the language button icon based on selected language
        flag_mapping = {
            "Tiếng Việt": "vietnamese_flag.png",
            "English": "english_flag.jpg",
            "日本語": "japanese_flag.png",
            "Français": "french_flag.png"
        }
        
        if language in flag_mapping:
            # Update flag icon
            flag_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'assets', flag_mapping[language])
            flag_icon = QIcon(flag_path)
            self.language_btn.setIcon(flag_icon)
            self.language_btn.setIconSize(QSize(60, 60))  # Further increased icon size
            
            # Set language in translator if language code exists in mapping
            if language in language_code_mapping:
                language_code = language_code_mapping[language]
                set_language(language_code)
                
                # Update UI text
                self.update_translations()

    def update_language_icon(self, language_code):
        """Update language button icon based on current language code"""
        # Mapping from language code to flag file
        flag_files = {
            "vi": "vietnamese_flag.png",
            "en": "english_flag.jpg",
            "ja": "japanese_flag.png",
            "fr": "french_flag.png"
        }
        
        flag_file = flag_files.get(language_code, "vietnamese_flag.png")  # Mặc định là cờ Việt Nam
        flag_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', flag_file)
        flag_icon = QIcon(flag_path)
        self.language_btn.setIcon(flag_icon)
        self.language_btn.setIconSize(QSize(60, 60))  # Further increased icon size

    def update_translations(self):
        """Update all UI texts with current language"""
        # Update window title
        self.setWindowTitle(_('app.title'))
        
        # Update main texts
        self.welcome_label.setText(_("welcomePage.welcome"))
        self.tagline_label.setText(_("welcomePage.tagline"))
        self.start_button.setText(_("welcomePage.getStarted"))
        
        # Cập nhật font dựa trên ngôn ngữ hiện tại, sử dụng helper class cho tiếng Việt
        if get_current_language() == "vi":
            VietnameseFontHelper.optimize_title_font(self.welcome_label, "Inria Sans", 90)
            VietnameseFontHelper.optimize_vietnamese_font(self.tagline_label, "Poppins", 40, bold=False, italic=True)
        else:
            self.configure_font_for_label(self.welcome_label, "Inria Sans", 90, True)
            self.configure_font_for_label(self.tagline_label, "Poppins", 40, False, True)
            
        self.configure_font_for_button(self.start_button, "Inter", QFont.Bold, 41)
        # Đảm bảo font size được giữ nguyên khi đổi ngôn ngữ
        self.start_button.setStyleSheet("""
            font-size: 48px;
            padding: 25px 30px;
            border-radius: 50px;
        """)

if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    welcome = WelcomePage()
    welcome.show()

    sys.exit(app.exec_())