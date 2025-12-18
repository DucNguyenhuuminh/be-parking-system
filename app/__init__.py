from flask import Flask
from app.config import Config
from app.extensions import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from app.controllers.parking_controller import parking_bp 
    
    app.register_blueprint(parking_bp)
    

    with app.app_context():

        from app.models import parking_db 
        db.create_all()

    @app.route('/healthy')
    def healthy():
        return {'status': 'healthy', 'message': 'Server is running!'}
    
    return app