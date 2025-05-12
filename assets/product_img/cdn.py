import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name="dmuau2ipk",
    api_key="861583644799878",
    api_secret="WoZQy1pnqUs6aElJ0WsfllLTYmg"
)

def upload_image(image_path):
    response = cloudinary.uploader.upload(image_path)
    return response["secure_url"]

def upload_directory_images(directory_path):
    image_urls = {}
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    
    for filename in os.listdir(directory_path):
        if any(filename.lower().endswith(ext) for ext in valid_extensions):
            image_path = os.path.join(directory_path, filename)
            try:
                response = cloudinary.uploader.upload(image_path)
                url = response["secure_url"]
                image_urls[filename] = url
                print(f"Uploaded {filename}: {url}")
            except Exception as e:
                print(f"Error uploading {filename}: {str(e)}")
    
    # Save URLs to url.txt
    with open('../url.txt', 'w') as f:
        for url in image_urls.values():
            f.write(f"{url}\n")
    
    return image_urls

# Upload all images in the current directory
directory_path = os.path.dirname(os.path.abspath(__file__))
image_urls = upload_directory_images(directory_path)

