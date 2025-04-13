from base_page import BasePage
from PyQt5.QtWidgets import (QVBoxLayout, QLabel, QWidget,
                           QPushButton, QApplication, QHBoxLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QEvent, QPoint, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon, QColor
import os
from page3_productsinfo import ProductPage  
from page_timing import PageTiming
from components.PageTransitionOverlay import PageTransitionOverlay
import requests
import json
from config import CART_END_SESSION_API, DEVICE_ID  

class InstructionPage(BasePage): 
    def __init__(self):
        super().__init__()  # Call BasePage init
        self.start_pos = QPoint()  # Initialize start position for swipe detection
        
        self.current_slide = 0
        self.total_slides = 6
        self.slide_timer = QTimer()
        self.slide_timer.timeout.connect(self.next_slide)
        self.slide_timer.start(2000)  # 2 seconds for changing slides

        # For slide 5's animation
        self.slide5_index = 0
        self.slide5_timer = QTimer()
        self.slide5_timer.timeout.connect(self.toggle_slide5_image)
        
        # For slide 6's animation
        self.slide6_index = 0
        self.slide6_timer = QTimer()
        self.slide6_timer.timeout.connect(self.toggle_slide6_image)
        
        # For slide transition animation
        self.slide_animation = None
        self.slide_animation_duration = 300
        
        self.load_fonts()
        self.init_ui()
        self.load_slides()
        self.transition_overlay = PageTransitionOverlay(self)

        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))
        self.is_animating = False  # Add this flag

    def load_fonts(self):
        # Same font loading as page1
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))

    def init_ui(self):
        self.setWindowTitle('Instructions - Smart Shopping Cart')
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
        
        # Main layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # No margins to allow full height
        layout.setSpacing(0)
        
        # Left side content
        left_container = QWidget()
        left_container.setFixedWidth(400)  # Set fixed width for left container
        left_container.setStyleSheet("""
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
        
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(30, 8, 30, 50)
        left_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        left_layout.setSpacing(10)

        # Logo (same as page1)
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignLeft)
        left_layout.addWidget(logo_label)

        left_layout.addSpacing(10)

        # Title using Inria Sans Bold
        title_label = QLabel("Welcome to Cartsy !")
        title_label.setFont(QFont("Inria Sans", 28, QFont.Bold))
        title_label.setStyleSheet("color: #3D6F4A;")
        left_layout.addWidget(title_label)

        # Tagline using Poppins Italic
        tagline_label = QLabel('"Shop smarter, enjoy life more"')
        tagline_label.setFont(QFont("Poppins", 14))
        tagline_label.setStyleSheet("color: #E72225; font-style: italic;")
        left_layout.addWidget(tagline_label)

        left_layout.addSpacing(10)

        # Create button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(20)  # Add spacing between buttons

        # Next button using Inter Bold
        next_button = QPushButton("SHOP NOW")
        next_button.setFont(QFont("Inter", QFont.Bold))
        next_button.setCursor(Qt.PointingHandCursor)
        next_button.clicked.connect(self.next_page)
        button_layout.addWidget(next_button)

        # Add back to home button
        home_button = QPushButton("BACK TO HOME")
        home_button.setFont(QFont("Inter", QFont.Bold))
        home_button.setCursor(Qt.PointingHandCursor)
        home_button.clicked.connect(self.return_to_welcome)
        button_layout.addWidget(home_button)

        # Add button container to left layout
        left_layout.addWidget(button_container, alignment=Qt.AlignLeft)

        left_layout.addStretch(1)

        # Right side content with white background
        right_container = QWidget()
        right_container.setFixedWidth(400)
        right_container.setStyleSheet("background-color: #FFFFFF;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 20, 0, 20)  # Reduced horizontal margins

        # Slide container
        self.slide_container = QWidget()
        slide_layout = QHBoxLayout(self.slide_container)
        slide_layout.setContentsMargins(10, 0, 10, 0)  # Add some padding
        slide_layout.setSpacing(10)  # Add space between elements
        
        # Define arrow paths before using them
        left_arrow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'left-arrow.jpg')
        right_arrow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'right-arrow.jpg')
        
        # Left arrow
        left_arrow = QPushButton()
        left_arrow.setFixedSize(40, 40)
        left_arrow.setCursor(Qt.PointingHandCursor)
        left_arrow.setIcon(QIcon(left_arrow_path))
        left_arrow.setIconSize(QSize(40, 40))
        left_arrow.setStyleSheet("QPushButton { border: none; background: transparent; }")
        left_arrow.clicked.connect(lambda: self.navigate_slide('prev'))
        
        # Center content
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(20) 
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setAlignment(Qt.AlignLeft)

        # Instruction text container
        text_container = QWidget()
        text_container.setFixedWidth(450)  # Increased width to ensure text fits
        text_container.setFixedHeight(120)  # Fixed height to ensure consistent spacing
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(30, 5, 30, 5)  # Increased side margins
        text_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Center vertically

        # Instruction text label
        self.instruction_text = QLabel()
        self.instruction_text.setFixedWidth(390)  
        self.instruction_text.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.instruction_text.setFont(QFont("Poppins", 14))
        self.instruction_text.setStyleSheet("""
            color: #E72225;
            padding: 5px;
            margin: 0px;
        """)
        self.instruction_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.instruction_text.setWordWrap(True)
        text_layout.addWidget(self.instruction_text)
        
        # Add text container to main content layout with left alignment
        content_layout.addSpacing(20)
        content_layout.addWidget(text_container, 0, Qt.AlignLeft)
        content_layout.addSpacing(20)

        # Slide image container to ensure consistent positioning
        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setAlignment(Qt.AlignCenter)
        
        # Slide image
        self.slide_label = QLabel()
        self.slide_label.setFixedSize(209, 230)
        self.slide_label.setAlignment(Qt.AlignCenter)
        self.slide_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                margin-top: 20px;
            }
        """)
        
        # Create a second slide label for animation
        self.next_slide_label = QLabel()
        self.next_slide_label.setFixedSize(209, 230)
        self.next_slide_label.setAlignment(Qt.AlignCenter)
        self.next_slide_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                margin-top: 20px;
            }
        """)
        self.next_slide_label.hide()
        
        # Create stack for slide transition
        slide_stack = QWidget()
        slide_stack.setFixedSize(209, 230)
        slide_stack_layout = QVBoxLayout(slide_stack)
        slide_stack_layout.setContentsMargins(0, 0, 0, 0)
        slide_stack_layout.addWidget(self.slide_label)
        slide_stack_layout.addWidget(self.next_slide_label)
        
        image_layout.addWidget(slide_stack)
        
        # Add padding to push image right
        image_container.setContentsMargins(30, 0, 0, 0)

        content_layout.addWidget(image_container, 1)

        # Right arrow (same settings as left arrow)
        right_arrow = QPushButton()
        right_arrow.setFixedSize(40, 40)
        right_arrow.setCursor(Qt.PointingHandCursor)
        right_arrow.setIcon(QIcon(right_arrow_path))
        right_arrow.setIconSize(QSize(40, 40))
        right_arrow.setStyleSheet("QPushButton { border: none; background: transparent; }")
        right_arrow.clicked.connect(lambda: self.navigate_slide('next'))

        # Add all elements to slide layout
        slide_layout.addWidget(left_arrow, 0, Qt.AlignVCenter)
        slide_layout.addWidget(content_container, 1)
        slide_layout.addWidget(right_arrow, 0, Qt.AlignVCenter)

        # Dots indicator
        dots_container = QWidget()
        self.dots_layout = QHBoxLayout(dots_container)
        self.dots_layout.setAlignment(Qt.AlignCenter)
        self.dots_layout.setSpacing(10)
        self.dots = []
        
        for i in range(self.total_slides):
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet("""
                background-color: #D9D9D9;
                border-radius: 5px;
            """)
            self.dots.append(dot)
            self.dots_layout.addWidget(dot)

        right_layout.addWidget(self.slide_container, 1)
        right_layout.addWidget(dots_container)

        # Add containers to main layout
        layout.addWidget(left_container)
        layout.addWidget(right_container)
        layout.setStretchFactor(left_container, 1)
        layout.setStretchFactor(right_container, 1)

        self.setLayout(layout)

    def next_page(self):
        """Enhanced transition to product page"""
        def switch_page():
            start_time = PageTiming.start_timing()
            self.product_page = ProductPage()
            
            def show_new_page():
                self.product_page.show()
                self.transition_overlay.fadeOut(lambda: self.hide())
                PageTiming.end_timing(start_time, "InstructionPage", "ProductPage")
                
            self.transition_overlay.fadeIn(show_new_page)
            
        switch_page()

    def navigate_instructions(self, direction):
        if direction == 'prev':
            print("Navigate to previous instruction")
        else:
            print("Navigate to next instruction")

    def load_slides(self):
        self.slides = []
        self.instruction_texts = [
            "Take your favorite\nshopping cart and\nstart your shopping",
            "Select the product you\nwant to buy\n ", 
            "Put the product in front\nof the camera and\nwait for a second",
            "Make changes directly\non the dashboard or in\nyour cart", 
            "Use the QR code for\npayment and wait for the transaction\nconfirmation.",
            "After the transaction is\nsuccessfully processed,\ncomplete the order"
        ]
        
        slides_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        
        # Load normal slides
        for i in range(1, 5):
            slide_path = os.path.join(slides_dir, f'instruction{i}.png')
            self.slides.append([QPixmap(slide_path)])
            
        # Load slide 5 with only instruction5_1.png
        slide5_path = os.path.join(slides_dir, 'instruction5_1.png')
        self.slides.append([QPixmap(slide5_path)])
        
        # Load slide 6 with instruction5_2.png
        slide6_path = os.path.join(slides_dir, 'instruction5_2.png')
        self.slides.append([QPixmap(slide6_path)])
        
        self.update_slide()

    def update_slide(self):
        # Update instruction text
        self.instruction_text.setText(self.instruction_texts[self.current_slide])
        
        # Update dots
        for i, dot in enumerate(self.dots):
            dot.setStyleSheet(f"""
                background-color: {('#32B156' if i == self.current_slide else '#D9D9D9')};
                border-radius: 5px;
            """)
        
        # Update slide image with fixed size
        current_images = self.slides[self.current_slide]
        if self.current_slide == 4:  # Slide 5
            self.slide5_timer.stop()  # Stop the animation timer for slide 5
            self.slide6_timer.stop()  # Ensure slide 6 timer is stopped
            self.slide_label.setPixmap(current_images[0].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        elif self.current_slide == 5:  # Slide 6
            self.slide5_timer.stop()  # Ensure slide 5 timer is stopped
            self.slide_label.setPixmap(current_images[0].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.slide5_timer.stop()
            self.slide6_timer.stop()
            self.slide_label.setPixmap(current_images[0].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def navigate_slide(self, direction):
        # Check if animation is already running
        if self.is_animating:
            return
            
        self.slide_timer.stop()  # Reset timer
        self.is_animating = True  # Set flag
        
        # Store current slide index
        previous_slide = self.current_slide
        
        # Calculate new slide index
        if direction == 'prev':
            self.current_slide = (self.current_slide - 1) % self.total_slides
        else:
            self.current_slide = (self.current_slide + 1) % self.total_slides
            
        # Animate the slide transition
        self.animate_slide_transition(direction, previous_slide)
        
        self.slide_timer.start(2000)

    def animate_slide_transition(self, direction, previous_slide):
        # Update instruction text
        self.instruction_text.setText(self.instruction_texts[self.current_slide])
        
        # Update dots
        for i, dot in enumerate(self.dots):
            dot.setStyleSheet(f"""
                background-color: {('#32B156' if i == self.current_slide else '#D9D9D9')};
                border-radius: 5px;
            """)
        
        # Prepare the next slide image
        current_images = self.slides[self.current_slide]
        next_pixmap = current_images[0].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.next_slide_label.setPixmap(next_pixmap)
        
        # Set initial position based on direction
        self.next_slide_label.show()
        if direction == 'next':
            self.next_slide_label.move(self.slide_label.width(), 0)
            start_pos_current = 0
            end_pos_current = -self.slide_label.width()
            start_pos_next = self.slide_label.width()
            end_pos_next = 0
        else:  # 'prev'
            self.next_slide_label.move(-self.slide_label.width(), 0)
            start_pos_current = 0
            end_pos_current = self.slide_label.width()
            start_pos_next = -self.slide_label.width()
            end_pos_next = 0
        
        # Create animations
        self.anim_current = QPropertyAnimation(self.slide_label, b"pos")
        self.anim_current.setDuration(self.slide_animation_duration)
        self.anim_current.setStartValue(QPoint(start_pos_current, 0))
        self.anim_current.setEndValue(QPoint(end_pos_current, 0))
        self.anim_current.setEasingCurve(QEasingCurve.OutCubic)
        
        self.anim_next = QPropertyAnimation(self.next_slide_label, b"pos")
        self.anim_next.setDuration(self.slide_animation_duration)
        self.anim_next.setStartValue(QPoint(start_pos_next, 0))
        self.anim_next.setEndValue(QPoint(end_pos_next, 0))
        self.anim_next.setEasingCurve(QEasingCurve.OutCubic)
        
        # Connect animation finish signal
        self.anim_next.finished.connect(self.finish_slide_transition)
        
        # Start animations
        self.anim_current.start()
        self.anim_next.start()
        
    def finish_slide_transition(self):
        # Update main slide label with the content from next slide
        current_images = self.slides[self.current_slide]
        self.slide_label.setPixmap(current_images[0].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Reset positions
        self.slide_label.move(0, 0)
        self.next_slide_label.hide()
        self.is_animating = False  # Reset flag when animation is done
        
        # Stop all animation timers for slide 5 and 6 if not on those slides
        if self.current_slide == 4:  # Slide 5
            self.slide5_timer.stop()
            self.slide6_timer.stop()
        elif self.current_slide == 5:  # Slide 6
            self.slide5_timer.stop()
            self.slide6_timer.stop()
        else:
            self.slide5_timer.stop()
            self.slide6_timer.stop()

    def next_slide(self):
        self.navigate_slide('next')

    def toggle_slide5_image(self):
        # This method now does nothing since we're not alternating images for slide 5
        pass

    def toggle_slide6_image(self):
        if self.current_slide == 5:  # Only for slide 6
            self.slide_label.setPixmap(self.slides[5][0].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mousePressEvent(self, event):
        """Record the start position"""
        self.start_pos = event.pos()

    def mouseReleaseEvent(self, event):
        """Check the swipe direction"""
        dx = event.pos().x() - self.start_pos.x()
        
        if dx > 50:
            self.navigate_slide('prev')
        elif dx < -50:
            self.navigate_slide('next')

    def return_to_welcome(self):
        """Return to welcome page using CART_END_SESSION_API"""
        try:
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
                    
                # Return to page1
                from page1_welcome import WelcomePage
                self.welcome_page = WelcomePage()
                self.welcome_page.show()
                self.close()
            else:
                print(f"Error ending session: {response.text}")
        except Exception as e:
            print(f"Error returning to welcome page: {e}")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    instruction = InstructionPage()
    instruction.show()
    sys.exit(app.exec_())
