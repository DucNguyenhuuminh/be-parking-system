from datetime import time
from PIL import Image
from app.config import Config

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def preprocess_img(image_path):
    img = Image.open(image_path)
    img = img.convert('RGB')
    return img

def calculate_fee(exit_time):
    exit_t = exit_time.time()
    day_start = time(6, 0)
    day_end = time(18, 0)
    evening_end = time(21, 0)

    if day_start <= exit_t <= day_end:
        return 3000
    elif day_end < exit_t <= evening_end:
        return 5000
    else:
        return 20000