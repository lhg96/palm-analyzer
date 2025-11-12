import cv2
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt


class PalmLineDetector:
    """
    손금 추출을 위한 클래스
    Stack Overflow의 제안사항을 반영한 고도화된 알고리즘 적용:
    1. 형태학적 필터링
    2. 라인 분류 (길이, 대비 영역에 따른)
    3. 손바닥 영역을 그리드로 분할하여 분석
    4. 그래디언트 이미지와 방향성 활용
    """
    
    def __init__(self):
        self.original_image = None
        self.processed_image = None
        self.palm_lines = []
        
    def load_image(self, image_path):
        """이미지 로드"""
        self.original_image = cv2.imread(image_path)
        return self.original_image is not None
    
    def preprocess_image(self, img):
        """이미지 전처리"""
        # 그레이스케일 변환
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 히스토그램 균등화
        equalized = cv2.equalizeHist(gray)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization) 적용
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        clahe_img = clahe.apply(gray)
        
        # 가우시안 블러로 노이즈 제거
        blurred = cv2.GaussianBlur(clahe_img, (5, 5), 0)
        
        return blurred
    
    def detect_hand_region(self, img):
        """손 영역 검출"""
        # 피부색 검출을 위한 HSV 변환
        hsv = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2HSV)
        
        # 피부색 범위 설정
        lower_skin = np.array([0, 20, 70])
        upper_skin = np.array([20, 255, 255])
        
        # 피부색 마스크 생성
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # 형태학적 연산으로 마스크 정제
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 가장 큰 컨투어 찾기 (손 영역)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            hand_mask = np.zeros_like(mask)
            cv2.fillPoly(hand_mask, [largest_contour], 255)
            return hand_mask, largest_contour
        
        return None, None
    
    def enhance_palm_lines(self, img, hand_mask=None):
        """손금 강화를 위한 고급 필터링 - OpenCV 기반"""
        # 그래디언트 계산
        grad_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # 방향성 정보 계산
        gradient_direction = np.arctan2(grad_y, grad_x)
        
        # 라플라시안 필터로 엣지 강화 (Ridge filter 대체)
        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        ridge_filter = np.abs(laplacian)
        
        # 형태학적 연산으로 선 구조 강화 (morphology.white_tophat 대체)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        enhanced = cv2.morphologyEx(img, cv2.MORPH_TOPHAT, kernel)
        
        # 여러 방법의 결과를 조합
        combined = np.maximum(ridge_filter * 0.5, enhanced.astype(np.float64))
        combined = np.maximum(combined, gradient_magnitude * 0.3)
        
        if hand_mask is not None:
            combined = cv2.bitwise_and(combined.astype(np.uint8), hand_mask)
        
        return combined.astype(np.uint8), gradient_direction
    
    def detect_lines_advanced(self, img, gradient_direction=None):
        """고급 라인 검출"""
        # Canny 엣지 검출
        edges = cv2.Canny(img, 30, 100)
        
        # 형태학적 연산으로 라인 연결
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Hough Line Transform
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=20, 
                               minLineLength=30, maxLineGap=10)
        
        if lines is None:
            return []
        
        # 라인 필터링 및 분류
        filtered_lines = self.filter_and_classify_lines(lines, img.shape, gradient_direction)
        
        return filtered_lines
    
    def filter_and_classify_lines(self, lines, image_shape, gradient_direction=None):
        """라인 필터링 및 분류"""
        if lines is None:
            return []
        
        filtered_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # 라인 길이 계산
            length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            
            # 너무 짧은 라인 제거
            if length < 20:
                continue
            
            # 라인 각도 계산
            angle = np.arctan2(y2-y1, x2-x1)
            
            # 수직에 가까운 라인들 우선 (손금의 특성)
            angle_deg = np.abs(np.degrees(angle))
            if 60 < angle_deg < 120 or angle_deg < 30 or angle_deg > 150:
                filtered_lines.append({
                    'line': line[0],
                    'length': length,
                    'angle': angle_deg,
                    'type': self.classify_line_type(length, angle_deg)
                })
        
        # DBSCAN을 이용한 클러스터링으로 유사한 라인들 그룹화
        if len(filtered_lines) > 0:
            filtered_lines = self.cluster_similar_lines(filtered_lines)
        
        return filtered_lines
    
    def classify_line_type(self, length, angle):
        """라인 타입 분류"""
        if length > 80:
            if 70 < angle < 110:
                return "major_vertical"  # 주요 세로 라인
            else:
                return "major_horizontal"  # 주요 가로 라인
        elif length > 40:
            return "medium"  # 중간 라인
        else:
            return "minor"  # 작은 라인
    
    def cluster_similar_lines(self, lines):
        """유사한 라인들을 클러스터링"""
        if len(lines) < 2:
            return lines
        
        # 라인의 중점과 각도를 특성으로 사용
        features = []
        for line_data in lines:
            x1, y1, x2, y2 = line_data['line']
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            features.append([center_x, center_y, line_data['angle']])
        
        features = np.array(features)
        
        # DBSCAN 클러스터링
        clustering = DBSCAN(eps=30, min_samples=2).fit(features)
        labels = clustering.labels_
        
        # 클러스터별로 대표 라인 선택
        clustered_lines = []
        unique_labels = set(labels)
        
        for label in unique_labels:
            if label == -1:  # 노이즈 포인트들은 개별적으로 처리
                noise_indices = np.where(labels == label)[0]
                for idx in noise_indices:
                    clustered_lines.append(lines[idx])
            else:
                # 클러스터 내에서 가장 긴 라인 선택
                cluster_indices = np.where(labels == label)[0]
                longest_line = max([lines[i] for i in cluster_indices], 
                                 key=lambda x: x['length'])
                clustered_lines.append(longest_line)
        
        return clustered_lines
    
    def divide_palm_into_grid(self, image_shape, hand_contour):
        """손바닥을 그리드로 분할"""
        if hand_contour is None:
            return None
        
        # 손의 바운딩 박스 계산
        x, y, w, h = cv2.boundingRect(hand_contour)
        
        # 4x4 그리드로 분할
        grid_w = w // 4
        grid_h = h // 4
        
        grid_regions = []
        for i in range(4):
            for j in range(4):
                region = {
                    'x': x + i * grid_w,
                    'y': y + j * grid_h,
                    'w': grid_w,
                    'h': grid_h,
                    'grid_pos': (i, j)
                }
                grid_regions.append(region)
        
        return grid_regions
    
    def analyze_palm_lines(self, image_path):
        """메인 분석 함수"""
        # 이미지 로드
        if not self.load_image(image_path):
            return None
        
        # 이미지 전처리
        processed = self.preprocess_image(self.original_image)
        
        # 손 영역 검출
        hand_mask, hand_contour = self.detect_hand_region(processed)
        
        # 손금 강화
        enhanced, gradient_direction = self.enhance_palm_lines(processed, hand_mask)
        
        # 라인 검출
        lines = self.detect_lines_advanced(enhanced, gradient_direction)
        
        # 그리드 분할
        grid_regions = self.divide_palm_into_grid(self.original_image.shape, hand_contour)
        
        # 결과 정리
        result = {
            'original_image': self.original_image,
            'processed_image': enhanced,
            'lines': lines,
            'hand_mask': hand_mask,
            'grid_regions': grid_regions,
            'total_lines': len(lines)
        }
        
        return result
    
    def visualize_results(self, result):
        """결과 시각화"""
        if result is None:
            return None
        
        # 결과 이미지 생성
        output_img = result['original_image'].copy()
        
        # 검출된 라인 그리기
        for line_data in result['lines']:
            x1, y1, x2, y2 = line_data['line']
            
            # 라인 타입별 색상 지정
            if line_data['type'] == 'major_vertical':
                color = (0, 0, 255)  # 빨간색
                thickness = 3
            elif line_data['type'] == 'major_horizontal':
                color = (0, 255, 0)  # 초록색
                thickness = 3
            elif line_data['type'] == 'medium':
                color = (255, 0, 0)  # 파란색
                thickness = 2
            else:
                color = (255, 255, 0)  # 시안색
                thickness = 1
            
            cv2.line(output_img, (x1, y1), (x2, y2), color, thickness)
        
        # 그리드 표시 (선택적)
        if result['grid_regions']:
            for region in result['grid_regions']:
                x, y, w, h = region['x'], region['y'], region['w'], region['h']
                cv2.rectangle(output_img, (x, y), (x+w, y+h), (128, 128, 128), 1)
        
        return output_img