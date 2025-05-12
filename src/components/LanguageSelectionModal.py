from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QWidget, QGraphicsDropShadowEffect, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QFont, QIcon, QColor
import os
from utils.translation import _, set_language, get_current_language
from utils.font_helpers.vietnamese import VietnameseFontHelper

class LanguageSelectionModal(QDialog):
    language_selected = pyqtSignal(str)  # Signal to emit selected language

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("languageModal.title"))
        self.setFixedSize(330, 320)  # Tăng chiều cao cho việc thêm nút đóng
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Đăng ký các font tiếng Việt
        VietnameseFontHelper.register_vietnamese_fonts()
        
        # Tạo shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setOffset(0, 0)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        
        # Container chính với background màu trắng
        self.container = QWidget(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            #container {
                background-color: white;
                border-radius: 10px;
            }
        """)
        self.container.setGraphicsEffect(shadow)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.container)
        
        # Container layout
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(20, 20, 20, 20)
        self.container_layout.setSpacing(15)
        
        # Header container
        self.header_container = QWidget()
        self.header_layout = QHBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        self.title = QLabel(_("languageModal.title"))
        
        # Sử dụng VietnameseFontHelper cho tiêu đề nếu ngôn ngữ hiện tại là tiếng Việt
        if get_current_language() == "vi":
            VietnameseFontHelper.optimize_vietnamese_font(self.title, "Inter", 16, bold=True)
        else:
            self.title.setFont(QFont("Inter", 16, QFont.Bold))
            
        self.title.setStyleSheet("color: #3D6F4A;")
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.header_layout.addWidget(self.title)
        
        # Close button container để thuận tiện cho việc căn chỉnh
        self.close_btn_container = QWidget()
        self.close_btn_container.setFixedSize(35, 35)
        close_btn_layout = QVBoxLayout(self.close_btn_container)
        close_btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border-radius: 15px;
                font-size: 20px;
                font-weight: bold;
                color: #505050;
                text-align: center;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        close_btn_layout.addWidget(self.close_btn)
        
        self.header_layout.addWidget(self.close_btn_container, alignment=Qt.AlignRight)
        self.container_layout.addWidget(self.header_container)
        
        # Divider line
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFrameShadow(QFrame.Sunken)
        self.divider.setStyleSheet("background-color: #E0E0E0;")
        self.container_layout.addWidget(self.divider)
        
        # Thêm các tùy chọn ngôn ngữ
        self.add_language_button("Tiếng Việt", "vietnamese_flag.png")
        self.add_language_button("English", "english_flag.jpg")
        self.add_language_button("日本語", "japanese_flag.png")
        self.add_language_button("Français", "french_flag.png")
        
        self.setStyleSheet("""
            QPushButton#languageButton {
                background-color: #F8F8F8;
                border-radius: 8px;
                text-align: left;
                padding: 5px 15px;
                height: 45px;
                border: none;
            }
            QPushButton#languageButton:hover {
                background-color: #F0F0F0;
            }
        """)
        
    def add_language_button(self, language_name, flag_filename):
        button = QPushButton()
        button.setObjectName("languageButton")
        button.setCursor(Qt.PointingHandCursor)
        
        # Layout cho nút
        button_layout = QHBoxLayout(button)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(15)
        
        # Cờ quốc gia
        flag_label = QLabel()
        flag_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               'assets', flag_filename)
        flag_pixmap = QPixmap(flag_path)
        flag_label.setPixmap(flag_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        button_layout.addWidget(flag_label)
        
        # Tên ngôn ngữ
        name_label = QLabel(language_name)
        
        # Sử dụng VietnameseFontHelper cho tên ngôn ngữ trong các nút
        if language_name == "Tiếng Việt":
            VietnameseFontHelper.optimize_vietnamese_font(name_label, "Inter", 14, bold=True)
        else:
            name_label.setFont(QFont("Inter", 14))
            
        button_layout.addWidget(name_label)
        button_layout.addStretch()
        
        # Kết nối sự kiện và thêm vào layout
        button.clicked.connect(lambda checked, name=language_name: self.on_language_selected(name))
        self.container_layout.addWidget(button)
        
    def on_language_selected(self, language_name):
        self.language_selected.emit(language_name)
        self.close() 