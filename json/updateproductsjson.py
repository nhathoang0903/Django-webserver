import json
import os
import sys
import requests
import logging

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import PRODUCTS_CHECK_NEW_API, PRODUCTS_CHECK_EDITS_API, PRODUCTS_CHECK_DELETIONS_API

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

def fetch_edited_products():
    """Fetch edited products from the API"""
    try:
        response = requests.get(PRODUCTS_CHECK_EDITS_API)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API request failed with status code {response.status_code} for edits: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching edited products: {e}")
        return None

def fetch_deleted_products():
    """Fetch deleted products from the API"""
    try:
        response = requests.get(PRODUCTS_CHECK_DELETIONS_API)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API request failed with status code {response.status_code} for deletions: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching deleted products: {e}")
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
        # Continue to check for edits and deletions even if new product fetching fails
    
    # Extract products from response
    new_products_data = api_response.get("products", []) if api_response else []
    if not new_products_data and api_response : # Only log if api_response was successful but no products
        logger.info("No new products found.")
    
    # Count how many new products we found
    new_products_added = 0
    products_changed = False
    
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
            products_changed = True
            logger.info(f"Added new product: {product.get('name')} (ID: {product_id})")

    # Fetch and process edited products
    edited_response = fetch_edited_products()
    if edited_response and "edits" in edited_response:
        edited_products_data = edited_response.get("edits", [])
        if not edited_products_data:
            logger.info("No product edits found.")
        else:
            for edit in edited_products_data:
                product_id_to_edit = edit.get("product_id")
                field_to_change = edit.get("field_changed")
                new_value = edit.get("new_value")

                if product_id_to_edit is not None and field_to_change and new_value is not None:
                    for product in current_products:
                        if product.get("product_id") == product_id_to_edit:
                            if field_to_change in product and product[field_to_change] != new_value:
                                logger.info(f"Updating product ID {product_id_to_edit}: field '{field_to_change}' from '{product[field_to_change]}' to '{new_value}'")
                                product[field_to_change] = new_value
                                products_changed = True
                            elif field_to_change not in product:
                                logger.info(f"Adding new field to product ID {product_id_to_edit}: field '{field_to_change}' with value '{new_value}'")
                                product[field_to_change] = new_value
                                products_changed = True
                            break 
                    else: # Inner loop else, executes if break was not hit
                        logger.warning(f"Product ID {product_id_to_edit} from edit log not found in current products.")
    else:
        logger.error("Failed to fetch or parse edited products.")

    # Fetch and process deleted products
    deleted_response = fetch_deleted_products()
    if deleted_response and "deletions" in deleted_response:
        deleted_products_data = deleted_response.get("deletions", [])
        if not deleted_products_data:
            logger.info("No product deletions found.")
        else:
            product_ids_to_delete = {deletion.get("product_id") for deletion in deleted_products_data if deletion.get("product_id") is not None}
            if product_ids_to_delete:
                original_count = len(current_products)
                current_products = [p for p in current_products if p.get("product_id") not in product_ids_to_delete]
                deleted_count = original_count - len(current_products)
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} products: IDs {product_ids_to_delete}")
                    products_changed = True
            else:
                logger.info("No valid product IDs found in deletion data.")

    else:
        logger.error("Failed to fetch or parse deleted products.")
    
    # Save updated products
    if products_changed:
        if new_products_added > 0:
            logger.info(f"Added {new_products_added} new products")
        return save_products(current_products)
    else:
        logger.info("No new products to add, edit or delete.")
        return True

if __name__ == "__main__":
    logger.info("Starting products update process")
    success = update_products()
    if success:
        logger.info("Products update completed successfully")
    else:
        logger.error("Products update failed")
