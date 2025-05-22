from cart_item_widget import CartItemWidget
from PyQt5.QtCore import QTimer

def fixed_delayed_gc():
    """Sửa lỗi thụt lề trong hàm delayed_gc"""
    def delayed_gc():
        import gc
        gc.collect()
        gc.collect()  # Chạy hai lần để đảm bảo làm sạch triệt để
                
    QTimer.singleShot(100, delayed_gc)

def fixed_item_widget_creation(product, quantity, product_id):
    """Sửa lỗi thụt lề khi tạo item_widget"""
    item_widget = CartItemWidget(product, quantity)
    self._cart_widgets_cache[product_id] = item_widget
    
    return item_widget 