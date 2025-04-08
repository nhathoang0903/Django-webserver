import os
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase Admin SDK
cred = credentials.Certificate("../../json/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'smartcartimages-cd600.appspot.com'
})

# Get bucket
bucket = storage.bucket()

def upload_image(file_path, destination_blob_name):
    """Uploads an image to Firebase Storage."""
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    # Make the blob publicly accessible
    blob.make_public()
    return blob.public_url

def main():
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get all files in the directory
    image_files = [f for f in os.listdir(current_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    
    # Upload each image
    for image_file in image_files:
        file_path = os.path.join(current_dir, image_file)
        try:
            # Upload to Firebase Storage with the same filename
            url = upload_image(file_path, f"products/{image_file}")
            print(f"Uploaded {image_file}: {url}")
        except Exception as e:
            print(f"Error uploading {image_file}: {str(e)}")

if __name__ == "__main__":
    main()
