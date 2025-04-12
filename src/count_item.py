from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import json
import os

def add_cart_count_label(product_page):
    """
    Thêm widget hiển thị số giỏ hàng vào góc trái phía dưới của ProductPage.
    """
    # Lấy layout gốc của ProductPage
    main_layout = product_page.layout()

    # Tạo container chứa widget
    container = QWidget()
    container.setStyleSheet("background-color: transparent;")
    h_layout = QHBoxLayout(container)
    h_layout.setContentsMargins(10, 10, 10, 10)
    h_layout.setSpacing(2)

    # Tạo label "Your Cart"
    your_cart_label = QLabel("Your Cart")
    your_cart_label.setFont(QFont("Josefin Sans", 14, QFont.Bold))
    your_cart_label.setStyleSheet("color: black;")
    h_layout.addWidget(your_cart_label)

    # Tạo label đếm số lượng "(0)"
    count_label = QLabel("(0)")
    count_label.setFont(QFont("Josefin Sans", 14, QFont.Bold))
    count_label.setStyleSheet("color: #E72225;")
    h_layout.addWidget(count_label)

    h_layout.addStretch()

    # Thêm widget vào cuối layout và căn góc trái phía dưới
    main_layout.addWidget(container, 0, Qt.AlignLeft | Qt.AlignBottom)

    # Lưu lại tham chiếu để cập nhật sau
    product_page.cart_text_label = your_cart_label
    product_page.cart_count_label = count_label

def update_cart_count(product_page):
    """
    Cập nhật số đếm giỏ hàng dựa vào số lượng sản phẩm duy nhất (theo product_name) trong detected_products.
    """
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'shopping_process.json')
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            detected_products = data.get("detected_products", [])
            unique_product_names = {item.get("product_name") for item in detected_products}  # Lấy các product_name duy nhất
            unique_product_count = len(unique_product_names)  # Đếm số lượng sản phẩm duy nhất
            
            # Check if we're using the new separate labels structure
            if hasattr(product_page, "cart_count_label") and not hasattr(product_page, "cart_text_label"):
                # Old structure (single label)
                product_page.cart_count_label.setText(f"Your Cart ({unique_product_count})")
            elif hasattr(product_page, "cart_count_label") and hasattr(product_page, "cart_text_label"):
                # New structure (separate labels)
                product_page.cart_count_label.setText(f"({unique_product_count})")
            
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        if hasattr(product_page, "cart_count_label") and not hasattr(product_page, "cart_text_label"):
            # Old structure
            product_page.cart_count_label.setText("Your Cart (0)")
        elif hasattr(product_page, "cart_count_label") and hasattr(product_page, "cart_text_label"):
            # New structure
            product_page.cart_count_label.setText("(0)")