from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                           QPushButton, QApplication, QHBoxLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QIcon
import os
from page3_productsinfo import ProductPage  
from page_timing import PageTiming
from components.PageTransitionOverlay import PageTransitionOverlay

class InstructionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_slide = 0
        self.total_slides = 5
        self.slide_timer = QTimer()
        self.slide_timer.timeout.connect(self.next_slide)
        self.slide_timer.start(2000)  # 2 seconds for changing slides

        # For slide 5's animation
        self.slide5_index = 0
        self.slide5_timer = QTimer()
        self.slide5_timer.timeout.connect(self.toggle_slide5_image)
        
        self.load_fonts()
        self.init_ui()
        self.load_slides()
        self.transition_overlay = PageTransitionOverlay(self)

        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

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
        title_label.setFont(QFont("Inria Sans", 24, QFont.Bold))
        title_label.setStyleSheet("color: #3D6F4A;")
        left_layout.addWidget(title_label)

        # Tagline using Poppins Italic
        tagline_label = QLabel('“Shop smarter, enjoy life more”')
        tagline_label.setFont(QFont("Poppins", 12))
        tagline_label.setStyleSheet("color: #E72225; font-style: italic;")
        left_layout.addWidget(tagline_label)

        left_layout.addSpacing(10)

        # Next button using Inter Bold
        next_button = QPushButton("SHOP NOW")
        next_button.setFont(QFont("Inter", QFont.Bold))
        next_button.setCursor(Qt.PointingHandCursor)
        next_button.clicked.connect(self.next_page)
        left_layout.addWidget(next_button, alignment=Qt.AlignLeft)

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
        
        # Left arrow
        left_arrow = QLabel()
        left_arrow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'left-arrow.jpg')
        left_arrow_pixmap = QPixmap(left_arrow_path)
        if not left_arrow_pixmap.isNull():
            left_arrow.setPixmap(left_arrow_pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        left_arrow.setCursor(Qt.PointingHandCursor)
        left_arrow.setFixedSize(40, 40)  # Ensure fixed size for arrow
        left_arrow.mousePressEvent = lambda e: self.navigate_slide('prev')
        
        # Center content
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(20) 
        content_layout.setContentsMargins(0, 0, 0, 0)  # Reset margins
        content_layout.setAlignment(Qt.AlignCenter)  # Center align all content

        # Instruction text container
        text_container = QWidget()
        text_container.setFixedSize(550, 80) 
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(-60, 5, 80, 5)  # Tăng left margin âm và right margin
        text_layout.setAlignment(Qt.AlignLeft)  # Căn lề trái

        # Instruction text label
        self.instruction_text = QLabel()
        self.instruction_text.setFixedWidth(520)  # Tăng width tương ứng
        self.instruction_text.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # Thay đổi policy
        self.instruction_text.setFont(QFont("Poppins", 9))
        self.instruction_text.setStyleSheet("""
            color: #E72225;
            padding: 5px 35px 10px 50px;
            margin-left: -100px;  
            margin-right: 30px; 
        """)
        self.instruction_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.instruction_text.setWordWrap(True)
        text_layout.addWidget(self.instruction_text)
        
        # Add text container to main content layout with left alignment
        content_layout.addSpacing(20)
        content_layout.addWidget(text_container, 0, Qt.AlignLeft)  # Đảm bảo căn lề trái
        content_layout.addSpacing(20)

        # Slide image container to ensure consistent positioning
        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setAlignment(Qt.AlignCenter)  # Center alignment
        
        # Slide image
        self.slide_label = QLabel()
        self.slide_label.setFixedSize(209, 230)  # Set fixed size for slide images
        self.slide_label.setAlignment(Qt.AlignCenter)
        self.slide_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
            }
        """)
        image_layout.addWidget(self.slide_label)
        
        # Add padding to push image right
        image_container.setContentsMargins(30, 0, 0, 0)  # Add left margin to push right

        content_layout.addWidget(image_container, 1)  # Give image container the remaining space

        # Right arrow (same settings as left arrow)
        right_arrow = QLabel()
        right_arrow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'right-arrow.jpg')
        right_arrow_pixmap = QPixmap(right_arrow_path)
        if not right_arrow_pixmap.isNull():
            right_arrow.setPixmap(right_arrow_pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        right_arrow.setCursor(Qt.PointingHandCursor)
        right_arrow.setFixedSize(40, 40)  # Ensure fixed size for arrow
        right_arrow.mousePressEvent = lambda e: self.navigate_slide('next')

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
            "Take your favorite shopping cart\nand start your shopping",
            "Select the product you want to buy\n",  
            "Put the product in front of the\ncamera and wait for a second",
            "Make changes directly on the\ndashboard or in your cart", 
            "Use the QR code for payment and\nwait for the transaction verify"
        ]
        
        slides_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        
        # Load normal slides
        for i in range(1, 5):
            slide_path = os.path.join(slides_dir, f'instruction{i}.png')
            self.slides.append([QPixmap(slide_path)])
            
        # Load slide 5 with two alternating images
        slide5_path1 = os.path.join(slides_dir, 'instruction5_1.png')
        slide5_path2 = os.path.join(slides_dir, 'instruction5_2.png')
        self.slides.append([QPixmap(slide5_path1), QPixmap(slide5_path2)])
        
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
            self.slide5_timer.start(1000)  # 1 second
            self.slide_label.setPixmap(current_images[self.slide5_index].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.slide5_timer.stop()
            self.slide_label.setPixmap(current_images[0].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def navigate_slide(self, direction):
        self.slide_timer.stop()  # Reset timer
        if direction == 'prev':
            self.current_slide = (self.current_slide - 1) % self.total_slides
        else:
            self.current_slide = (self.current_slide + 1) % self.total_slides
        self.update_slide()
        self.slide_timer.start(2000)

    def next_slide(self):
        self.navigate_slide('next')

    def toggle_slide5_image(self):
        if self.current_slide == 4:  # Only for slide 5
            self.slide5_index = (self.slide5_index + 1) % 2
            self.slide_label.setPixmap(self.slides[4][self.slide5_index].scaled(209, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    instruction = InstructionPage()
    instruction.show()
    sys.exit(app.exec_())
