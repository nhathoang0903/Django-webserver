import json
import os
import sys
import requests
import logging

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import PRODUCTS_CHECK_NEW_API

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/products_update.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("products_update")

def get_products_json_path():
    """Return the full path to products.json"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'products.json')

def load_current_products():
    """Load the current products from the JSON file"""
    try:
        with open(get_products_json_path(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading products.json: {e}")
        return []

def save_products(products):
    """Save the updated products to the JSON file"""
    try:
        with open(get_products_json_path(), 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved {len(products)} products to products.json")
        return True
    except Exception as e:
        logger.error(f"Error saving products.json: {e}")
        return False

def fetch_new_products():
    """Fetch new products from the API"""
    try:
        response = requests.get(PRODUCTS_CHECK_NEW_API)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching new products: {e}")
        return None

def update_products():
    """Main function to update products.json with new products from the API"""
    # Load current products
    current_products = load_current_products()
    if not current_products:
        logger.error("Failed to load current products. Exiting.")
        return False
    
    # Get existing product IDs
    existing_product_ids = {product["product_id"] for product in current_products}
    logger.info(f"Loaded {len(current_products)} existing products")
    
    # Fetch new products
    api_response = fetch_new_products()
    if not api_response:
        logger.error("Failed to fetch new products. Exiting.")
        return False
    
    # Extract products from response
    new_products_data = api_response.get("products", [])
    if not new_products_data:
        logger.info("No new products found.")
        return True
    
    # Count how many new products we found
    new_products_added = 0
    
    # Check for new products
    for product in new_products_data:
        product_id = product.get("product_id")
        if product_id and product_id not in existing_product_ids:
            # Remove low_stock_threshold field if present
            if "low_stock_threshold" in product:
                del product["low_stock_threshold"]
                
            # Add new product to current products
            current_products.append(product)
            existing_product_ids.add(product_id)
            new_products_added += 1
            logger.info(f"Added new product: {product.get('name')} (ID: {product_id})")
    
    # Save updated products
    if new_products_added > 0:
        logger.info(f"Added {new_products_added} new products")
        return save_products(current_products)
    else:
        logger.info("No new products to add")
        return True

if __name__ == "__main__":
    logger.info("Starting products update process")
    success = update_products()
    if success:
        logger.info("Products update completed successfully")
    else:
        logger.error("Products update failed")
