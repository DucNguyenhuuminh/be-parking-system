from PIL import Image
import numpy as np
import os
import cv2
import re
from ultralytics import YOLO
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

class LicensePlateDetector:

    def __init__(self,model_path=None, trocr_model_path=None):
        self.model_path = model_path
        self.model = None
        self.is_loaded = False

        # TrOCR model and processor
        self.trocr_model = None
        self.trocr_processor = None
        self.trocr_loaded = False
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        print(f"Using device: {self.device}")

        if model_path:
            self.load_model(model_path)
        
        if trocr_model_path:
            self.load_trocr_model(trocr_model_path)

    def load_model(self,model_path):
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            self.model = YOLO(model_path)
            self.is_loaded = True
            print(f"Model loaded successfully from {model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.is_loaded = False

    # Load processor and model
    def load_trocr_model(self,model_path):
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"TrOCR model path not found: {model_path}")
            
            required_files = ['pytorch_model.bin','config.json']
            for file in required_files:
                file_path = os.path.join(model_path,file)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Require file not found: {file_path}")
            
            print(f"Loading TrOCR model from {model_path}......")

            self.trocr_processor = TrOCRProcessor.from_pretrained(model_path)
            self.trocr_model = VisionEncoderDecoderModel.from_pretrained(model_path)
            self.trocr_model.to(self.device)
            self.trocr_model.eval()

            self.trocr_loaded = True
            print(f"TrOCR model loaded successfully on {self.device}")
        
        except Exception as e:
            print(f"Error loading TrOCR model: {e}")
            self.trocr_loaded = False

    def detect_plate(self, image):
        if not self.is_loaded:
            print("DEBUG: Model YOLO not loaded!")
            return {'detected': False, 'error': 'Model not loaded'}
        
        try:
            img_input = None
            
            if isinstance(image, str):
                if not os.path.exists(image):
                    print(f"DEBUG: Image not existed {image}")
                    return {'detected': False, 'error': 'Image path invalid'}
                img_input = cv2.imread(image)
            
            elif isinstance(image, Image.Image):
                pil_image = image.convert('RGB')
                img_input = np.array(pil_image)
                img_input = cv2.cvtColor(img_input, cv2.COLOR_RGB2BGR)
            
            elif isinstance(image, np.ndarray):
                img_input = image
            
            else:
                print(f"DEBUG: Image type not support: {type(image)}")
                return {'detected': False, 'error': 'Unsupported image type'}

            if img_input is None:
                return {'detected': False, 'error': 'Image processing failed'}
            
            print(f"DEBUG: Image shape sent to YOLO: {img_input.shape}")
            results = self.model(img_input, verbose=False, conf=0.1) 

            if not results:
                print("DEBUG: YOLO not return any results")
                return {'detected': False, 'confidence': 0.0}

            # Kiểm tra xem có boxes nào không
            if len(results[0].boxes) > 0:
                box = results[0].boxes[0]
                conf = float(box.conf[0])
                bbox = box.xyxy[0].tolist()
                
                print(f"Plate found Conf: {conf}")
                return {
                    'detected': True,
                    'bbox': bbox,
                    'confidence': conf
                }
            else:
                print("DEBUG: Run success but not found any object")
                return {
                    'detected': False,
                    'confidence': 0.0
                }
        
        except Exception as e:
            print(f"DEBUG: Error in detect_plate: {e}")
            import traceback
            traceback.print_exc()
            return {
                'detected': False,
                'error': str(e)
            }
                    
    def recognize_text(self,image, bbox=True):
        if not self.trocr_loaded:
            print("TrOCR model not loaded")
            return ""
        
        try:
            if isinstance(image,np.ndarray):
                if len(image.shape) == 3 and image.shape[2] == 3:
                    image = cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
            
            if bbox is not None:
                x1,y1,x2,y2 = map(int,bbox)
                image = image.crop((x1,y1,x2,y2))

            image = image.convert('RGB')

            pixel_values = self.trocr_processor(image, return_tensors='pt').pixel_values
            pixel_values = pixel_values.to(self.device)

            with torch.no_grad():
                generated_ids = self.trocr_model.generate(pixel_values)

            generated_text = self.trocr_processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]

            cleaned_text = self.clean_plate_text(generated_text)

            return cleaned_text
        
        except Exception as e:
            print(f"Error in recognize text: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def detect_and_recognize(self,image):
        detection_result = self.detect_plate(image)
        if not detection_result['detected']:
            return {
                'detected': False,
                'license_plate': None,
                'confidence': 0.0,
                'bbox': None
            }

        if isinstance(image, str):
            img = cv2.imread(image)
        elif isinstance(image,Image.Image):
            img = np.array(image)
        else:
            img = image

        bbox = detection_result['bbox']
        license_text = self.recognize_text(img,bbox)

        return {
            'detected': True,
            'license_plate': license_text if license_text else "UNKNOWN",
            'confidence': detection_result['confidence'],
            'bbox':bbox
        }
    
    def clean_plate_text(self,text):
        if not text:
            return ""
        
        text = ' '.join(text.split())
        text = text.upper()
        text = re.sub(r'[^A-Z0-9\s]','',text)
        text = ' '.join(text.split())
        return text
    
    def validate_plate_format(self,plate_text):
        if not plate_text:
            return False
        
        clean_text = plate_text.replace(' ','').replace('-','')
        patterns = [
            r'[0-9]{2}[A-Z]{1,2}[0-9]{4-5}$'
        ]

        for pattern in patterns:
            if re.match(pattern, clean_text):
                return True
            
        return 5 <= len(clean_text) <= 10
    
    def batch_detect(self,images):
        results = []

        for idx,image in enumerate(images):
            print(f"Processing image {idx +1}/{len(images)}")

            result = self.detect_and_recognize(image)
            result['image_index'] = idx

            if isinstance(image,str):
                result['image_path'] = image
            results.append(result)
        return results
    
    def get_model_info(self):
        info = {
            'yolo_loaded': self.is_loaded,
            'yolo_model_path': self.model_path,
            'trocr_loaded': self.trocr_loaded,
            'device': str(self.device)
        }
        
        if self.is_loaded:
            try:
                if hasattr(self.model, 'names'):
                    info['yolo_class_names'] = self.model.names
            except:
                pass
        
        if self.trocr_loaded:
            info['trocr_model_type'] = 'VisionEncoderDecoderModel'
        
        return info
    
    def visualize_detection(self,image,save_path=None):
        result = self.detect_and_recognize(image)

        if isinstance(image,str):
            img = cv2.imread(image)
        elif isinstance(image,Image.Image):
            img = cv2.cvtColor(np.array(image),cv2.COLOR_RGB2BGR)
        else:
            img = image.copy()

        if result['detected']:
            bbox = result['bbox']
            x1,y1,x2,y2 = map(int,bbox)

            cv2.rectangle(img,(x1,y1),(x2,y2),(0,255,0),2)
            label = f"{result['license_plate']} ({result['confidence']:.2f})"

            (text_width,text_height), baseline = cv2.getTextSize(
                label,cv2.FONT_HERSHEY_SIMPLEX, 0.7,2
            )

            cv2.rectangle(img,(x1,y1-text_height-10),(x1+text_width,y1),(0,255,0),-1)
            cv2.putText(img,label,(x1,y1-5),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,0),2)

        if save_path:
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.',
                        exist_ok=True)
            cv2.imwrite(save_path,img)
            print(f"Result saved to: {save_path}")
        
        return img