from PyQt5.QtGui import QFont, QFontDatabase
import os

class VietnameseFontHelper:
    """Helper class for handling Vietnamese font issues"""
    
    @staticmethod
    def register_vietnamese_fonts():
        """Register all Vietnamese-friendly fonts"""
        # Đường dẫn tới thư mục font
        font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'font-family')
        
        # Đăng ký các font phù hợp với tiếng Việt
        fonts_to_register = [
            ('Inria_Sans/InriaSans-Regular.ttf', 'Inria Sans'),
            ('Inria_Sans/InriaSans-Bold.ttf', 'Inria Sans'),
            ('Poppins/Poppins-Regular.ttf', 'Poppins'),
            ('Poppins/Poppins-Italic.ttf', 'Poppins'),
            ('Inter/static/Inter_24pt-Regular.ttf', 'Inter'),
            ('Inter/static/Inter_24pt-Bold.ttf', 'Inter'),
            ('Segoe_UI_Emoji/seguiemj.ttf', 'Segoe UI Emoji')
        ]
        
        for font_file, font_name in fonts_to_register:
            full_path = os.path.join(font_dir, font_file)
            if os.path.exists(full_path):
                QFontDatabase.addApplicationFont(full_path)
            else:
                print(f"Font not found: {full_path}")
    
    @staticmethod
    def optimize_vietnamese_font(label, font_family, size, bold=False, italic=False):
        """Optimize font for Vietnamese text"""
        font = QFont(font_family, size)
        
        # Điều chỉnh trọng lượng font cho tiếng Việt - tăng weight lên một chút
        if bold:
            font.setWeight(60)  # Tăng từ 58 lên 60 cho nét đậm hơn 
        else:
            font.setWeight(53)  # Tăng từ 50 lên 53 cho nét đậm hơn một chút
        
        # Giảm hinting để cải thiện chất lượng nhưng vẫn giữ nét đậm vừa phải
        font.setHintingPreference(QFont.PreferVerticalHinting)
        
        # Giảm khoảng cách giữa các ký tự hơi gần nhau một chút (từ 105 xuống 103)
        # nhưng vẫn tránh chồng chéo dấu
        font.setLetterSpacing(QFont.PercentageSpacing, 103)
        
        # Cài đặt style strategy cho chất lượng tốt nhất
        font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        
        if italic:
            font.setItalic(True)
        
        # Áp dụng font đã tối ưu cho label
        label.setFont(font)
        
        return font

    @staticmethod
    def optimize_title_font(label, font_family="Inria Sans", size=30):
        """Đặc biệt tối ưu font cho tiêu đề tiếng Việt"""
        font = QFont(font_family, size)
        
        # Tăng trọng lượng font cho tiêu đề
        font.setWeight(60)  # Tăng từ 57 lên 60
        
        # Điều chỉnh letter spacing vừa phải
        font.setLetterSpacing(QFont.PercentageSpacing, 104)  # Giảm từ 107 xuống 104
        
        # Điều chỉnh hinting 
        font.setHintingPreference(QFont.PreferVerticalHinting)
        
        # Cài đặt style strategy đặc biệt cho tiêu đề
        font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        
        # Áp dụng font đã tối ưu cho label
        label.setFont(font)
        
        return font 