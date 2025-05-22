from page3_productsinfo import CartManager, ProductPage


@classmethod
def clear_cache(cls):
    """Method to manually clear cache if needed"""
    try:
        # Xóa các card và đánh dấu cho garbage collection
        for card in cls._cards_cache:
            try:
                card.deleteLater()
            except:
                pass
        
        # Xóa cache
        cls._products_cache = None
        cls._cards_cache = []
        cls._category_indices = {}
        
        # Gợi ý garbage collector
        import gc
        gc.collect()
        
        # Reset instance nếu cần
        if cls._instance:
            cls._instance = None
            
    except Exception as e:
        print(f"[Page3] Error in clear_cache: {e}")

# Đoạn code sửa lỗi cho hàm ensure_cards_have_grid_pos
def fixed_ensure_cards_have_grid_pos(self):
    """Đảm bảo tất cả cards đều có thuộc tính grid_pos và hợp lệ"""
    # Kiểm tra các card không hợp lệ trước
    valid_cards = []
    for card in ProductPage._cards_cache:
        try:
            # Thử truy cập thuộc tính để đảm bảo card vẫn hợp lệ
            _ = card.product['name']
            valid_cards.append(card)
        except Exception as e:
            print(f"[Page3] Found invalid card, error: {e}")
    
    # Cập nhật lại cache nếu có card không hợp lệ
    if len(valid_cards) != len(ProductPage._cards_cache):
        print(f"[Page3] Updating cache - removed {len(ProductPage._cards_cache) - len(valid_cards)} invalid cards")
        ProductPage._cards_cache = valid_cards
    
    # Đảm bảo tất cả cards đều có thuộc tính grid_pos
    for i, card in enumerate(ProductPage._cards_cache):
        if not hasattr(card, 'grid_pos'):
            row = (i // 5) * 2  # Changed from 4 to 5 products per row
            col = i % 5  # Changed from 4 to 5 columns
            card.grid_pos = (row, col)
            print(f"[Page3] Added missing grid_pos ({row}, {col}) to card {i}")
    
    # Giới hạn số lượng card trong cache nếu vượt quá
    if len(ProductPage._cards_cache) > self._max_cards:
        # Giữ lại _max_cards card đầu tiên
        excess_cards = ProductPage._cards_cache[self._max_cards:]
        ProductPage._cards_cache = ProductPage._cards_cache[:self._max_cards]
        
        # Xóa các card thừa
        for card in excess_cards:
            try:
                card.deleteLater()
            except:
                pass
        
        print(f"[Page3] Reduced cache from {len(ProductPage._cards_cache) + len(excess_cards)} to {len(ProductPage._cards_cache)} cards")

# Đoạn code sửa lỗi cho hàm filter_products - phần else trong khối else
def fixed_filter_products_part(self, category, valid_cards):
    # Fallback: lọc sản phẩm theo danh mục, dựa trên tên danh mục tiếng Anh
    filtered_cards = [card for card in valid_cards 
                    if card.product['category'] == category]
    
    return filtered_cards

# Đoạn code sửa lỗi cho hàm update_cart_count
def fixed_update_cart_count(self):
    """Update the cart count display - optimized version"""
    try:
        cart_count = CartManager().get_cart_count()
        
        # Chỉ cập nhật UI nếu count thực sự thay đổi
        if not hasattr(self, '_last_cart_count'):
            self._last_cart_count = -1
            
        if cart_count != self._last_cart_count:
            print(f"[Page3] Updating cart count: {cart_count}")
            self._last_cart_count = cart_count
            
            # Cập nhật cart_count_text nếu có
            if hasattr(self, 'cart_count_text'):
                if cart_count > 0:
                    self.cart_count_text.setText(f"({cart_count})")
                    self.cart_count_text.show()
                else:
                    self.cart_count_text.setText("")
                    self.cart_count_text.hide()
            
            # Cập nhật cart_btn nếu có
            if hasattr(self, 'cart_btn'):
                self.cart_btn.update_count(cart_count)
        
    except Exception as e:
        print(f"[Page3] Error updating cart count: {e}") 