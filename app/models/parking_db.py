from datetime import datetime
from app.extensions import db

class ParkingRecord(db.Model):
    __tablename__ = 'parking_records'
    
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False, index=True)
    entry_image_path = db.Column(db.String(500), nullable=False)
    exit_image_path = db.Column(db.String(500), nullable=True)
    confidence = db.Column(db.Float)
    entry_time = db.Column(db.DateTime, default=datetime.now)
    exit_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="parked")
    duration = db.Column(db.Integer, nullable=True)
    has_monthly_ticket = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'license_plate': self.license_plate,
            'entry_img_path': self.entry_image_path,
            'exit_img_path': self.exit_image_path,
            'confidence': self.confidence,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'status': self.status,
            'parking_duration': self.duration
        }

