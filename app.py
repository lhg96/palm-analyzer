from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64
import os
import time
from werkzeug.utils import secure_filename
from PIL import Image
import io
from modules.palm_detector import PalmLineDetector

app = Flask(__name__)

# 설정
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 최대 업로드 크기
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# 업로드 폴더 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """허용된 파일 확장자인지 확인"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_uploaded_image(file_data):
    """업로드된 이미지 데이터를 처리하여 OpenCV 이미지로 변환"""
    try:
        # PIL Image로 변환
        image = Image.open(io.BytesIO(file_data))
        
        # RGB로 변환 (RGBA인 경우)
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # NumPy 배열로 변환
        img_array = np.array(image)
        
        # BGR로 변환 (OpenCV 형식)
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_array
    
    except Exception as e:
        print(f"이미지 처리 오류: {e}")
        return None

def encode_image_to_base64(image):
    """OpenCV 이미지를 Base64 문자열로 인코딩"""
    try:
        # 이미지를 JPEG로 인코딩
        _, buffer = cv2.imencode('.jpg', image)
        
        # Base64로 인코딩
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return image_base64
    
    except Exception as e:
        print(f"Base64 인코딩 오류: {e}")
        return None

def classify_lines_by_type(lines):
    """라인들을 타입별로 분류"""
    line_counts = {
        'major_vertical': 0,
        'major_horizontal': 0,
        'medium': 0,
        'minor': 0
    }
    
    line_types = []
    
    for line_data in lines:
        line_type = line_data.get('type', 'minor')
        if line_type in line_counts:
            line_counts[line_type] += 1
            if line_type not in line_types:
                line_types.append(line_type)
    
    return line_counts, line_types

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_palm():
    """손금 분석 API 엔드포인트"""
    start_time = time.time()
    
    try:
        # 업로드된 파일 확인
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'message': '이미지 파일이 없습니다.'
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '파일이 선택되지 않았습니다.'
            }), 400
        
        # 파일 형식 확인
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': '지원하지 않는 파일 형식입니다. (PNG, JPG, JPEG, GIF, BMP만 지원)'
            }), 400
        
        # 파일 데이터 읽기
        file_data = file.read()
        
        # 이미지 처리
        image = process_uploaded_image(file_data)
        
        if image is None:
            return jsonify({
                'success': False,
                'message': '이미지를 처리할 수 없습니다.'
            }), 400
        
        # 임시 파일 저장
        filename = secure_filename(f"temp_{int(time.time())}_{file.filename}")
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        cv2.imwrite(temp_path, image)
        
        try:
            # 손금 분석 수행
            detector = PalmLineDetector()
            result = detector.analyze_palm_lines(temp_path)
            
            if result is None:
                return jsonify({
                    'success': False,
                    'message': '손금 분석에 실패했습니다. 손바닥이 선명하게 보이는 이미지를 사용해주세요.'
                }), 400
            
            # 결과 이미지 생성
            result_image = detector.visualize_results(result)
            
            if result_image is None:
                return jsonify({
                    'success': False,
                    'message': '결과 이미지를 생성할 수 없습니다.'
                }), 500
            
            # 결과 이미지를 Base64로 인코딩
            result_base64 = encode_image_to_base64(result_image)
            
            if result_base64 is None:
                return jsonify({
                    'success': False,
                    'message': '결과 이미지 인코딩에 실패했습니다.'
                }), 500
            
            # 라인 분류
            line_counts, line_types = classify_lines_by_type(result['lines'])
            
            # 처리 시간 계산
            processing_time = round(time.time() - start_time, 2)
            
            # 성공 응답
            response_data = {
                'success': True,
                'processed_image': result_base64,
                'total_lines': result['total_lines'],
                'major_lines': line_counts['major_vertical'] + line_counts['major_horizontal'],
                'medium_lines': line_counts['medium'],
                'minor_lines': line_counts['minor'],
                'line_types': line_types,
                'processing_time': processing_time,
                'image_size': {
                    'width': result['original_image'].shape[1],
                    'height': result['original_image'].shape[0]
                }
            }
            
            return jsonify(response_data)
        
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
        return jsonify({
            'success': False,
            'message': f'서버 내부 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/health')
def health_check():
    """서버 상태 확인"""
    return jsonify({
        'status': 'healthy',
        'message': 'Palm Analyzer is running'
    })

@app.errorhandler(413)
def too_large(e):
    """파일 크기 초과 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': '파일 크기가 너무 큽니다. 16MB 이하의 파일을 업로드해주세요.'
    }), 413

@app.errorhandler(404)
def not_found(e):
    """404 에러 핸들러"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """500 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': '서버 내부 오류가 발생했습니다.'
    }), 500

if __name__ == '__main__':
    print("=== Palm Analyzer 서버 시작 ===")
    print("접속 URL: http://localhost:8000")
    print("Ctrl+C로 서버를 중지할 수 있습니다.")
    print("=" * 40)
    
    app.run(
        host='0.0.0.0',  # 외부에서도 접근 가능
        port=8000,       # 포트 변경
        debug=True,      # 개발 모드
        threaded=True    # 멀티 스레드 지원
    )