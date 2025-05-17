import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from rembg import remove
from PIL import Image
import io
import tempfile
from django.conf import settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

def process_image(image_data):
    """Process image by removing background and optimizing"""
    try:
        # Remove background
        output_data = remove(image_data)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(output_data))
        
        # Optimize image size
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        
        # Convert to bytes
        output_buffer = io.BytesIO()
        image.save(output_buffer, format='PNG', optimize=True, quality=85)
        processed_image = output_buffer.getvalue()
        
        return processed_image
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return image_data

def upload_image(image_data, product_name):
    try:
        # Process image first
        processed_image = process_image(image_data)
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            processed_image,
            folder="products",
            public_id=product_name,
            resource_type="image",
            transformation=[
                {"width": 800, "height": 800, "crop": "fill"},
                {"quality": "auto"},
                {"fetch_format": "auto"}
            ]
        )
        
        # Return the secure URL of the uploaded image
        return result.get('secure_url')
        
    except Exception as e:
        print(f"Error uploading image to Cloudinary: {str(e)}")
        return None

def upload_directory_images(directory_path):
    image_urls = {}
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    
    for filename in os.listdir(directory_path):
        if any(filename.lower().endswith(ext) for ext in valid_extensions):
            image_path = os.path.join(directory_path, filename)
            try:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                url = upload_image(image_data, os.path.splitext(filename)[0])
                if url:
                    image_urls[filename] = url
                    print(f"Uploaded {filename}: {url}")
            except Exception as e:
                print(f"Error uploading {filename}: {str(e)}")
    
    return image_urls

# Upload all images in the current directory
directory_path = os.path.dirname(os.path.abspath(__file__))
image_urls = upload_directory_images(directory_path)

