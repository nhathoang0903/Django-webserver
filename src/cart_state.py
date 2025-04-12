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
from config import CART_SHOPPING_MONITOR_API, DEVICE_ID
from queue import Queue
from count_item import update_cart_count  # Import the update_cart_count function

class CartState:
    JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json', 'shopping_process.json')

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
            cls._instance._file_monitor = None
            cls._instance._stop_monitoring = Event()
            cls._instance._change_callbacks = []
            cls._instance._last_modified = 0
            # Add new attributes for optimization
            cls._instance._monitor_queue = Queue(maxsize=10)  # Queue for monitor data
            cls._instance._api_lock = Lock()  # Lock for API calls
            cls._instance._last_api_call = 0  # Track last API call time
            cls._instance._min_api_interval = 0.5  # Minimum seconds between API calls
            cls._instance._monitor_worker = None  # Background worker thread
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._image_lock = threading.Lock()
            self._initialized = True
            self.load_from_json()  # Add this
            self.start_monitoring()  # Add this to auto-start monitoring
            self._start_monitor_worker()  # Start background worker

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

    def _start_monitor_worker(self):
        """Start background worker for API calls"""
        if self._monitor_worker is None:
            self._monitor_worker = Thread(target=self._process_monitor_queue, daemon=True)
            self._monitor_worker.start()

    def _process_monitor_queue(self):
        """Process monitor data queue in background"""
        while True:
            try:
                # Get data from queue with timeout
                payload = self._monitor_queue.get(timeout=1.0)
                
                # Only process if cart has products
                if payload["cart_data"]["detected_products"]:
                    # Check if enough time has passed since last API call
                    current_time = time.time()
                    time_since_last = current_time - self._last_api_call
                    
                    if time_since_last < self._min_api_interval:
                        time.sleep(self._min_api_interval - time_since_last)

                    # Make API call with lock
                    with self._api_lock:
                        try:
                            response = requests.post(
                                CART_SHOPPING_MONITOR_API, 
                                json=payload,
                                timeout=3  # Add timeout
                            )
                            self._last_api_call = time.time()
                            
                            if response.status_code != 200:
                                print(f"API error: {response.status_code}")
                                
                        except Exception as e:
                            print(f"API call failed: {e}")

            except Exception:
                # Queue empty or other error, continue
                continue

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

            # Update the cart count dynamically
            from count_item import update_cart_count
            from page3_productsinfo import ProductPage
            update_cart_count(ProductPage._instance)

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

    def _send_monitor_data(self):
        """Send cart data to monitor API in separate thread"""
        try:
            # Get phone number
            phone_number = ""
            try:
                phone_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'config', 'phone_number.json')
                with open(phone_path, 'r') as f:
                    phone_data = json.load(f)
                    phone_number = phone_data.get("phone_number", "")
            except Exception as e:
                print(f"Error reading phone number: {e}")

            # Get cart data
            with open(self.JSON_PATH, 'r') as f:
                cart_data = json.load(f)

            # Prepare payload
            payload = {
                "phone_number": phone_number,
                "device_id": DEVICE_ID,
                "cart_data": cart_data
            }

            print(f"Sending monitor data: {payload}")  # Debug print

            # Send POST request
            response = requests.post(CART_SHOPPING_MONITOR_API, json=payload)
            if response.status_code == 200:
                print(f"Cart data sent to monitor API successfully: {response.json()}")
            else:
                print(f"Error sending to monitor API: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error in monitor thread: {e}")

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
                products_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
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