from PyQt5.QtWidgets import QLabel, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt

def add_cart_count_label(widget):
    """Thêm nhãn 'Your Cart (n)' vào góc trái phía dưới của widget."""
    # Tạo container cho nhãn
    container = QHBoxLayout()
    
    # Tạo nhãn "Your Cart"
    your_cart_label = QLabel("Your Cart ")
    your_cart_label.setStyleSheet("font-size: 14px; color: black; font-weight: bold;")
    container.addWidget(your_cart_label)
    
    # Tạo nhãn số lượng "(n)"
    count_label = QLabel("(0)")
    count_label.setStyleSheet("font-size: 14px; color: #E72225; font-weight: bold;")
    container.addWidget(count_label)
    
    # Thêm khoảng trống để đẩy container xuống dưới
    spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
    widget.main_layout.addItem(spacer)
    
    # Thêm container vào layout chính
    widget.main_layout.addLayout(container)
    
    # Lưu tham chiếu để cập nhật sau
    widget.cart_count_label = count_label

def update_cart_count(widget):
    """Cập nhật số lượng loại sản phẩm trong giỏ hàng."""
    unique_item_count = len(widget.cart_state.cart_items)  # Đếm số loại sản phẩm
    if hasattr(widget, "cart_count_label"):
        widget.cart_count_label.setText(f"({unique_item_count})")