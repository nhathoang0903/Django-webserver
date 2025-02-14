from rembg import remove
from PIL import Image

# Mở ảnh đầu vào
input_path = "../model/test1.jpeg"
output_path = "../model/test1rm.png"

# Xử lý ảnh
with Image.open(input_path) as img:
    output = remove(img)
    output.save(output_path)

print("Xóa nền ảnh thành công!")
