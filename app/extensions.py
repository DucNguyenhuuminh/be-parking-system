from flask_sqlalchemy import SQLAlchemy
from app.detector import LicensePlateDetector

db = SQLAlchemy()

print("Loading AI Models...")
detector = LicensePlateDetector(
    model_path='models/best.pt',
    trocr_model_path="models/trocr_result_model"
)
print("Models Loaded!")