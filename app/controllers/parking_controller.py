from flask import Blueprint, request, jsonify, send_file
from app.services.parking_service import ParkingService
import os
from datetime import datetime
from app.models.parking_db import ParkingRecord
from app.extensions import db

parking_bp = Blueprint('parking', __name__, url_prefix='/parking')

@parking_bp.route('/entry', methods=['POST'])
def entry():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        name = request.form.get('name', 'Unknown')
        
        data = ParkingService.handle_entry(file, name)
        return jsonify({'success': True, 'message': 'Entry recorded', 'record': data}), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parking_bp.route('/exit', methods=['POST'])
def exit():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        data = ParkingService.handle_exit(file)
        return jsonify({'success': True, 'message': 'Exit recorded', 'record': data}), 200

    except ValueError as e:
        status_code = 404 if "No entry record" in str(e) else 400
        return jsonify({'success': False, 'error': str(e)}), status_code
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@parking_bp.route('/current', methods=['GET'])
def get_current():
    try:
        records = ParkingRecord.query.filter_by(status='parked').order_by(ParkingRecord.entry_time.desc()).all()
        
        result = []
        for record in records:
            d = record.to_dict()
            d['current_duration'] = int((datetime.now() - record.entry_time).total_seconds()/60)
            result.append(d)
        return jsonify({'success': True, 'vehicle': result}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@parking_bp.route('/stats', methods=['GET'])
def stats():
    
    try:
        total = ParkingRecord.query.count()
        parked = ParkingRecord.query.filter_by(status='parked').count()
        return jsonify({'success': True, 'total_records': total, 'currently_parked': parked}), 200
    
    except Exception as e:
         return jsonify({'error': str(e)}), 500

@parking_bp.route('/history', methods=['GET'])
def get_parking_history():
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        license_plate = request.args.get('license_plate', None)

        query = ParkingRecord.query

        if license_plate:
            query = query.filter_by(license_plate=license_plate.upper())

        records = query.order_by(ParkingRecord.entry_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'total': records.total,
            'page': page,
            'per_page': per_page,
            'records': [r.to_dict() for r in records.items]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@parking_bp.route('/license/<license_plate>', methods=['GET'])
def get_license_plate(license_plate):
    
    try:
        records = ParkingRecord.query.filter_by(
            license_plate=license_plate.upper()
        ).order_by(ParkingRecord.entry_time.desc()).all()

        results = []
        for record in records:
            data = record.to_dict()
            
            data['entry_image_url'] = f'/parking/image/entry/{record.id}'
            data['exit_image_url'] = f'/parking/image/exit/{record.id}' if record.exit_image_path else None
            results.append(data)

        return jsonify({
            'success': True,
            'license_plate': license_plate.upper(),
            'total_records': len(results),
            'records': results
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parking_bp.route('/image/entry/<int:record_id>', methods=['GET'])
def get_entry_image(record_id):
    try:
        record = ParkingRecord.query.get_or_404(record_id)
        if os.path.exists(record.entry_image_path):
            return send_file(record.entry_image_path, mimetype='image/jpeg')
        return jsonify({'error': 'File not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@parking_bp.route('/image/exit/<int:record_id>', methods=['GET'])
def get_exit_image(record_id):
    try:
        record = ParkingRecord.query.get_or_404(record_id)
        
        if not record.exit_image_path:
            return jsonify({'error': 'Vehicle has not exited yet'}), 404
            
        if os.path.exists(record.exit_image_path):
            return send_file(record.exit_image_path, mimetype='image/jpeg')
            
        return jsonify({'error': 'Exit image file not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500