import os
import cv2
import urllib.parse
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from app.extensions import db, detector
from app.models.parking_db import ParkingRecord
from app.config import Config
from app.utils import allowed_file, preprocess_img, calculate_fee
import requests

NODE_SERVER_URL = "http://192.168.1.13:4000/api"

class ParkingService:

    @staticmethod
    def check_monthly_subscription(license_plate):
        try:
            response = requests.get(f"{NODE_SERVER_URL}/check-license/{license_plate}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return data.get('is_valid', False)
            return False
        except Exception as e:
            print(f"Error connecting to Node server: {e}")
            return False@staticmethod
    def check_monthly_subscription(license_plate):
        try:
            safe_license = urllib.parse.quote(license_plate)

            url = f"{NODE_SERVER_URL}/auth/check-license/{safe_license}"
            
            print(f"Checking URL: {url}")

            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('is_valid', False)
            
            print(f"NodeJS Error: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            print(f"Error connecting to Node server: {e}")
            return False
        
    
        
    @staticmethod
    def handle_entry(file, name='Unknown'):
        if not file or not allowed_file(file.filename):
            raise ValueError("Invalid file")

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"entry_{timestamp}_{filename}"
        image_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        file.save(image_path)

        try:
            pil_image = preprocess_img(image_path)
            result = detector.detect_and_recognize(pil_image)
        except Exception:
            os.remove(image_path)
            raise ValueError("Error processing image")

        if not result['detected']:
            os.remove(image_path)
            raise ValueError("License plate not detected")

        license_plate = result['license_plate']
        conf = result['confidence']
        bbox = result.get('bbox')

        if bbox:
            try:
                img_cv = cv2.imread(image_path)
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img_cv, f"{license_plate}", (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.imwrite(image_path, img_cv)
            except Exception:
                pass

        existing = ParkingRecord.query.filter_by(license_plate=license_plate, status='parked').first()
        if existing:
            raise ValueError("Vehicle already parked")

        # 
        print(f"Checking subscription for: {license_plate}")
        has_monthly = ParkingService.check_monthly_subscription(license_plate)

        record = ParkingRecord(
            license_plate=license_plate,
            entry_image_path=image_path,
            confidence=conf,
            entry_time=datetime.now(),
            status='parked',
            has_monthly_ticket=has_monthly
        )
        db.session.add(record)
        db.session.commit()

        response = record.to_dict()
        response['has_monthly_ticket'] = has_monthly
        
        return response

    @staticmethod
    def handle_exit(file):
        if not file or not allowed_file(file.filename):
            raise ValueError("Invalid file")

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"exit_{timestamp}_{filename}"
        image_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        file.save(image_path)

        try:
            pil_image = preprocess_img(image_path)
            result = detector.detect_and_recognize(pil_image)
        except Exception:
            os.remove(image_path)
            raise ValueError("Error processing image")

        if not result['detected']:
            os.remove(image_path)
            raise ValueError("License plate not detected")
        
        license_plate = result['license_plate']
        bbox = result.get('bbox')

        if bbox:
            try:
                img_cv = cv2.imread(image_path)
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img_cv, f"{license_plate}", (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.imwrite(image_path, img_cv)
            except Exception:
                pass

        record = ParkingRecord.query.filter_by(license_plate=license_plate, status='parked').first()
        if not record:
            raise ValueError("No entry record found for this vehicle")

        exit_time = datetime.now()
        duration = int((exit_time - record.entry_time).total_seconds()/60)
        
        record.exit_time = exit_time
        record.exit_image_path = image_path
        record.status = 'exited'
        record.duration = duration
        db.session.commit()

        response = record.to_dict()

        if record.has_monthly_ticket:
            response['parking_fee'] = 0
            response['fee_waived'] = True
            response['message'] = "Monthly Ticket - No Fee"
        else:
            response['parking_fee'] = calculate_fee(exit_time)
            response['fee_waived'] = False
            response['message'] = "Please pay the fee"

        return response