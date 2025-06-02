from typing import Dict, List, Tuple, Callable
import json
import os
from PIL import Image 
import requests
from io import BytesIO
import threading
from functools import lru_cache
import time
from threading import Thread, Event, Lock
from config import DEVICE_ID
from queue import Queue
from count_item import update_cart_count  

class CartState:
    JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'json', 'shopping_process.json')

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._image_lock = threading.Lock()
            self._initialized = True
            self.load_from_json()  # Add this
            self.start_monitoring()  # Add this to auto-start monitoring

    _instance = None
    _original_images = {}  # Cache for original images 
    _processed_images = {} # Cache for processed images
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CartState, cls).__new__(cls)
            # Define JSON path (Corrected to be project_root/json)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            json_dir = os.path.join(project_root, 'json')
            if not os.path.exists(json_dir):
                os.makedirs(json_dir)
            cls._instance.JSON_PATH = os.path.join(json_dir, 'shopping_process.json')
            # Initialize other attributes
            cls._instance.cart_items = []
            cls._instance._image_cache = {}  # Add image cache at instance creation
            cls._instance._original_images = {}
            cls._instance._processed_images = {}
            cls._instance._file_monitor = None
            cls._instance._stop_monitoring = Event()
            cls._instance._change_callbacks = []
            cls._instance._last_modified = 0
            # We don't need monitor queue and API related attributes anymore
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._image_lock = threading.Lock()
            self._initialized = True
            self.load_from_json()  # Add this
            self.start_monitoring()  # Add this to auto-start monitoring
            # Removed _start_monitor_worker call

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

    # Removed _start_monitor_worker and _process_monitor_queue methods

    def save_to_json(self):
        """Optimized save with debouncing"""
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
            # Save to JSON file
            with open(self.JSON_PATH, 'w') as f:
                json.dump(cart_data, f, indent=4)

            # Notify all registered callbacks
            for callback in self._change_callbacks:
                try:
                    callback(cart_data)
                except Exception as e:
                    print(f"Error in cart state callback: {e}")
            
            # Removed monitor API related code

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
        """Update item quantity with improved change detection"""
        if 0 <= index < len(self.cart_items):
            product = self.cart_items[index][0]
            # Store old quantity for comparison
            old_quantity = self.cart_items[index][1]
            
            # Only update if quantity actually changed
            if quantity != old_quantity:
                self.cart_items[index] = (product, quantity)
                # Force file modification by updating timestamp
                self.save_to_json()
                print(f"Updated quantity from {old_quantity} to {quantity}")

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

    def start_monitoring(self, callback: Callable = None):
        """Start monitoring JSON file for changes"""
        if callback:
            self._change_callbacks.append(callback)
            
        if self._file_monitor is None:
            self._stop_monitoring.clear()
            self._file_monitor = Thread(target=self._monitor_file, daemon=True)
            self._file_monitor.start()
            print("Started JSON file monitoring")

    def stop_monitoring(self):
        """Stop monitoring JSON file"""
        if self._file_monitor:
            self._stop_monitoring.set()
            self._file_monitor.join()
            self._file_monitor = None
            print("Stopped JSON file monitoring")

    # Removed _send_monitor_data method

    def _monitor_file(self):
        """Optimized file monitoring"""
        last_hash = None
        
        while not self._stop_monitoring.is_set():
            try:
                if os.path.exists(self.JSON_PATH):
                    # Quick hash check instead of reading full file
                    current_hash = hash(os.path.getmtime(self.JSON_PATH))
                    
                    if current_hash != last_hash:
                        with open(self.JSON_PATH, 'r') as f:
                            new_data = json.load(f)
                            
                        # Only update if content actually changed
                        if self._content_changed(new_data):
                            self._update_cart_items(new_data)
                            # Removed monitor API related code
                        last_hash = current_hash

            except Exception as e:
                print(f"Monitor error: {e}")
                
            time.sleep(0.5)  # Keep checking interval

    def _content_changed(self, new_data):
        """Check if cart content actually changed"""
        new_items = {
            (item["product_name"], item["quantity"]) 
            for item in new_data.get("detected_products", [])
        }
        
        current_items = {
            (p["name"], q) 
            for p, q in self.cart_items
        }
        
        return new_items != current_items

    def _update_cart_items(self, new_data):
        """Update cart items from new data"""
        self.cart_items = [
            ({"name": item["product_name"],
              "price": item["price"] / item["quantity"]},
             item["quantity"])
            for item in new_data.get("detected_products", [])
        ]
        
        # Notify callbacks
        for callback in self._change_callbacks:
            try:
                callback(new_data)
            except Exception as e:
                print(f"Callback error: {e}")

    def register_change_callback(self, callback: Callable):
        """Register a callback to be notified of cart changes"""
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)

    def unregister_change_callback(self, callback: Callable):
        """Remove a change callback"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def load_from_json(self):
        """Load cart state from JSON file with image URLs"""
        try:
            if os.path.exists(self.JSON_PATH):
                with open(self.JSON_PATH, 'r') as f:
                    data = json.load(f)
                    
                # Load product details from products.json
                products_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                          'json', 'products.json')
                product_details = []
                try:
                    with open(products_path, 'r') as f:
                        product_details = json.load(f)
                except Exception as e:
                    print(f"Error loading product details: {e}")
                    
                # Create lookup dictionary for product details
                product_lookup = {
                    p['name']: p for p in product_details
                }
                
                # Convert JSON data to cart items format with image URLs
                self.cart_items = []
                for item in data.get("detected_products", []):
                    product_name = item["product_name"]
                    details = product_lookup.get(product_name, {})
                    product = {
                        "name": product_name,
                        "price": item["price"] / item["quantity"],
                        "image_url": details.get("image_url", ""),  # Default to empty string if not found
                        "category": details.get("category", ""),
                    }
                    self.cart_items.append((product, item["quantity"]))
                
            else:
                # Create empty cart file if doesn't exist
                self.save_to_json()
                
        except Exception as e:
            print(f"Error loading cart data: {e}")
            self.cart_items = []
            self.save_to_json()