
class CartState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CartState, cls).__new__(cls)
            cls._instance.cart_items = []
        return cls._instance
    
    def add_item(self, product, quantity):
        for i, (existing_product, existing_quantity) in enumerate(self.cart_items):
            if existing_product['name'] == product['name']:
                updated_quantity = existing_quantity + quantity
                self.cart_items[i] = (existing_product, updated_quantity)
                return True
        self.cart_items.append((product, quantity))
        return False
    
    def remove_item(self, index):
        if 0 <= index < len(self.cart_items):
            del self.cart_items[index]
            
    def update_quantity(self, index, quantity):
        if 0 <= index < len(self.cart_items):
            product = self.cart_items[index][0]
            self.cart_items[index] = (product, quantity)