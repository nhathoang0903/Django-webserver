import json
import os

class CartState:
    _instance = None
    JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'shopping_process.json')
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CartState, cls).__new__(cls)
            cls._instance.cart_items = []
            # No need to create folder since json folder already exists
        return cls._instance

    def save_to_json(self):
        """Save cart state to JSON file in json folder"""
        cart_data = {
            "detected_products": [
                {
                    "product_name": product["name"],
                    "quantity": quantity,
                    "price": float(product["price"]) * quantity
                }
                for product, quantity in self.cart_items
            ],
            "total_bill": sum(float(product["price"]) * quantity 
                            for product, quantity in self.cart_items)
        }
        
        try:
            with open(self.JSON_PATH, 'w') as f:
                json.dump(cart_data, f, indent=4)
        except Exception as e:
            print(f"Error saving cart data: {e}")

    def add_item(self, product, quantity):
        for i, (existing_product, existing_quantity) in enumerate(self.cart_items):
            if existing_product['name'] == product['name']:
                updated_quantity = existing_quantity + quantity
                self.cart_items[i] = (existing_product, updated_quantity)
                self.save_to_json()
                return True
        self.cart_items.append((product, quantity))
        self.save_to_json()
        return False

    def remove_item(self, index):
        if 0 <= index < len(self.cart_items):
            del self.cart_items[index]
            self.save_to_json()
            
    def update_quantity(self, index, quantity):
        if 0 <= index < len(self.cart_items):
            product = self.cart_items[index][0]
            self.cart_items[index] = (product, quantity)
            self.save_to_json()
    
    def clear_cart(self):
        """Clear cart and remove JSON file"""
        self.cart_items = []
        try:
            if os.path.exists(self.JSON_PATH):
                os.remove(self.JSON_PATH)
                print("Cart data file removed successfully")
            # Re-initialize with empty cart
            self.save_to_json()  # Add this line to create new empty cart file
        except Exception as e:
            print(f"Error removing cart data file: {e}")