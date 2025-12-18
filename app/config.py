import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///parking.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = 'parking_images'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)