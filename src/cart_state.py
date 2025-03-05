from typing import Dict, List, Tuple
import json
import os
from PIL import Image
import requests
from io import BytesIO
import threading
from functools import lru_cache
import time

class CartState:
    JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'shopping_process.json')

    def __init__(self):
        self.cart_items = []
        self.load_from_json()

    _instance = None
    _original_images = {}  # Cache for original images 
    _processed_images = {} # Cache for processed images
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CartState, cls).__new__(cls)
            # Define JSON path
            json_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json')
            if not os.path.exists(json_dir):
                os.makedirs(json_dir)
            cls._instance.JSON_PATH = os.path.join(json_dir, 'shopping_process.json')
            # Initialize other attributes
            cls._instance.cart_items = []
            cls._instance._image_cache = {}  # Add image cache at instance creation
            cls._instance._original_images = {}
            cls._instance._processed_images = {}
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._image_lock = threading.Lock()
            self._initialized = True

    @lru_cache(maxsize=32)
    def _fetch_and_process_image(self, image_url: str) -> Image:
        """Fetch và xử lý ảnh với cache"""
        with self._image_lock:
            if image_url in self._image_cache:
                return self._image_cache[image_url]
            
            start = time.time()
            try:
                response = requests.get(image_url, timeout=5)
                img = Image.open(BytesIO(response.content))
                # Thực hiện xử lý ảnh (resize, remove bg, etc)
                # ...
                self._image_cache[image_url] = img
                print(f"Image processing took {time.time() - start:.2f}s")
                return img
            except Exception as e:
                print(f"Error processing image: {e}")
                return None

    def clear_cache(self):
        """Clear image caches"""
        self._image_cache.clear()
        self._original_images.clear() 
        self._processed_images.clear()

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

    def add_item(self, product: Dict, quantity: int) -> bool:
        """Add item with optimized image handling"""
        start = time.time()
        
        # Pre-fetch image in background if not in cache
        if 'image_url' in product and product['image_url'] not in self._image_cache:
            thread = threading.Thread(
                target=self._fetch_and_process_image,
                args=(product['image_url'],)
            )
            thread.daemon = True
            thread.start()
        
        # Cart operations
        updated = False
        for idx, (existing_product, existing_quantity) in enumerate(self.cart_items):
            if existing_product['name'] == product['name']:
                self.cart_items[idx] = (existing_product, existing_quantity + quantity)
                updated = True
                break
                
        if not updated:
            self.cart_items.append((product, quantity))
            
        self.save_to_json()
        print(f"Cart operation took {time.time() - start:.2f}s")
        return updated

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

    def move_to_top(self, product_name):
        """Move an item to the top of the cart list"""
        for i, (product, quantity) in enumerate(self.cart_items):
            if product['name'] == product_name:
                item = self.cart_items.pop(i)
                self.cart_items.append(item)
                self.save_to_json()
                break

    def set_guest_name(self, name):
        with open(self.JSON_PATH, 'r+') as f:
            data = json.load(f)
            data['guest_name'] = name
            f.seek(0)
            json.dump(data, f)
            f.truncate()