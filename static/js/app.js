class PalmAnalyzer {
    constructor() {
        this.camera = null;
        this.canvas = null;
        this.context = null;
        this.isRecording = false;
        
        this.initializeElements();
        this.bindEvents();
    }
    
    initializeElements() {
        // DOM 요소들 초기화
        this.elements = {
            startCamera: document.getElementById('start-camera'),
            capturePhoto: document.getElementById('capture-photo'),
            cameraPreview: document.getElementById('camera-preview'),
            captureCanvas: document.getElementById('capture-canvas'),
            uploadForm: document.getElementById('upload-form'),
            imageUpload: document.getElementById('image-upload'),
            uploadBtn: document.getElementById('upload-btn'),
            capturedPreview: document.getElementById('captured-preview'),
            capturedImage: document.getElementById('captured-image'),
            analyzeCaptured: document.getElementById('analyze-captured'),
            analysisResult: document.getElementById('analysis-result'),
            loadingIndicator: document.getElementById('loading-indicator')
        };
        
        // Canvas 컨텍스트 설정
        this.canvas = this.elements.captureCanvas;
        this.context = this.canvas.getContext('2d');
    }
    
    bindEvents() {
        // 카메라 관련 이벤트
        this.elements.startCamera.addEventListener('click', () => this.startCamera());
        this.elements.capturePhoto.addEventListener('click', () => this.capturePhoto());
        
        // 파일 업로드 관련 이벤트
        this.elements.uploadForm.addEventListener('submit', (e) => this.handleUpload(e));
        this.elements.imageUpload.addEventListener('change', (e) => this.previewUploadedImage(e));
        
        // 분석 시작 이벤트
        this.elements.analyzeCaptured.addEventListener('click', () => this.analyzeImage());
        
        // 드래그 앤 드롭 이벤트 (향후 확장용)
        this.setupDragAndDrop();
    }
    
    async startCamera() {
        try {
            // 사용자 미디어 접근 권한 요청
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                } 
            });
            
            this.elements.cameraPreview.srcObject = stream;
            this.elements.cameraPreview.classList.add('active');
            this.elements.capturePhoto.disabled = false;
            this.elements.startCamera.textContent = '카메라 중지';
            this.elements.startCamera.classList.replace('btn-success', 'btn-danger');
            this.elements.startCamera.onclick = () => this.stopCamera();
            
            this.camera = stream;
            this.isRecording = true;
            
            this.showMessage('카메라가 시작되었습니다. 손바닥을 화면에 맞춰주세요.', 'success');
            
        } catch (error) {
            console.error('카메라 접근 오류:', error);
            this.showMessage('카메라에 접근할 수 없습니다. 브라우저 설정을 확인해주세요.', 'error');
        }
    }
    
    stopCamera() {
        if (this.camera) {
            this.camera.getTracks().forEach(track => track.stop());
            this.elements.cameraPreview.srcObject = null;
            this.elements.cameraPreview.classList.remove('active');
            this.elements.capturePhoto.disabled = true;
            this.elements.startCamera.textContent = '카메라 시작';
            this.elements.startCamera.classList.replace('btn-danger', 'btn-success');
            this.elements.startCamera.onclick = () => this.startCamera();
            
            this.camera = null;
            this.isRecording = false;
        }
    }
    
    capturePhoto() {
        if (!this.isRecording) {
            this.showMessage('먼저 카메라를 시작해주세요.', 'error');
            return;
        }
        
        const video = this.elements.cameraPreview;
        
        // Canvas 크기를 비디오 크기에 맞춤
        this.canvas.width = video.videoWidth;
        this.canvas.height = video.videoHeight;
        
        // 비디오 프레임을 Canvas에 그리기
        this.context.drawImage(video, 0, 0, this.canvas.width, this.canvas.height);
        
        // Canvas에서 이미지 데이터 추출
        const imageDataUrl = this.canvas.toDataURL('image/jpeg', 0.9);
        
        // 미리보기 이미지 설정
        this.elements.capturedImage.src = imageDataUrl;
        this.elements.capturedPreview.style.display = 'block';
        
        // 카메라 중지
        this.stopCamera();
        
        this.showMessage('사진이 촬영되었습니다. 분석 버튼을 클릭하세요.', 'success');
    }
    
    previewUploadedImage(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // 파일 타입 검증
        if (!file.type.startsWith('image/')) {
            this.showMessage('이미지 파일만 업로드 가능합니다.', 'error');
            return;
        }
        
        // 파일 크기 검증 (5MB 제한)
        if (file.size > 5 * 1024 * 1024) {
            this.showMessage('파일 크기는 5MB를 초과할 수 없습니다.', 'error');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            this.elements.capturedImage.src = e.target.result;
            this.elements.capturedPreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
    
    async handleUpload(event) {
        event.preventDefault();
        
        const fileInput = this.elements.imageUpload;
        const file = fileInput.files[0];
        
        if (!file) {
            this.showMessage('업로드할 이미지를 선택해주세요.', 'error');
            return;
        }
        
        // FormData 생성
        const formData = new FormData();
        formData.append('image', file);
        
        await this.sendImageForAnalysis(formData);
    }
    
    async analyzeImage() {
        const imageElement = this.elements.capturedImage;
        if (!imageElement.src) {
            this.showMessage('분석할 이미지가 없습니다.', 'error');
            return;
        }
        
        // Canvas에서 Blob 데이터 생성
        this.canvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append('image', blob, 'captured_image.jpg');
            
            await this.sendImageForAnalysis(formData);
        }, 'image/jpeg', 0.9);
    }
    
    async sendImageForAnalysis(formData) {
        try {
            // 로딩 상태 시작
            this.showLoading(true);
            
            // 서버에 이미지 전송 및 분석 요청
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }
            
            const result = await response.json();
            
            // 분석 결과 표시
            this.displayAnalysisResult(result);
            
        } catch (error) {
            console.error('분석 오류:', error);
            this.showMessage(`분석 중 오류가 발생했습니다: ${error.message}`, 'error');
        } finally {
            // 로딩 상태 종료
            this.showLoading(false);
        }
    }
    
    displayAnalysisResult(result) {
        const resultContainer = this.elements.analysisResult;
        
        if (result.success) {
            resultContainer.innerHTML = `
                <div class="fade-in-up">
                    <h5 class="mb-3">
                        <i class="fas fa-check-circle text-success me-2"></i>
                        분석 완료
                    </h5>
                    
                    <!-- 결과 이미지 -->
                    <div class="text-center mb-4">
                        <img src="data:image/jpeg;base64,${result.processed_image}" 
                             class="result-image" alt="분석된 손금 이미지">
                    </div>
                    
                    <!-- 통계 정보 -->
                    <div class="line-stats">
                        <div class="row text-center">
                            <div class="col-6 col-md-3">
                                <div class="stats-number">${result.total_lines}</div>
                                <div class="stats-label">총 라인 수</div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="stats-number">${result.major_lines}</div>
                                <div class="stats-label">주요 라인</div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="stats-number">${result.medium_lines}</div>
                                <div class="stats-label">중간 라인</div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="stats-number">${result.minor_lines}</div>
                                <div class="stats-label">세부 라인</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 라인 타입별 분류 -->
                    <div class="mt-3">
                        <h6 class="mb-2">검출된 라인 유형:</h6>
                        <div class="d-flex flex-wrap">
                            ${result.line_types.map(type => `
                                <span class="line-type ${type.toLowerCase().replace('_', '-')}">${type}</span>
                            `).join('')}
                        </div>
                    </div>
                    
                    <!-- 처리 시간 -->
                    <div class="mt-3 text-muted small">
                        <i class="fas fa-clock me-1"></i>
                        처리 시간: ${result.processing_time}초
                    </div>
                    
                    <!-- 다운로드 버튼 -->
                    <div class="mt-3 d-grid">
                        <button class="btn btn-outline-primary" onclick="palmAnalyzer.downloadResult('${result.processed_image}')">
                            <i class="fas fa-download me-2"></i>결과 이미지 다운로드
                        </button>
                    </div>
                </div>
            `;
        } else {
            resultContainer.innerHTML = `
                <div class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                    <h5>분석 실패</h5>
                    <p class="mb-0">${result.message || '알 수 없는 오류가 발생했습니다.'}</p>
                </div>
            `;
        }
    }
    
    downloadResult(base64Image) {
        try {
            // Base64 이미지를 Blob으로 변환
            const byteCharacters = atob(base64Image);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'image/jpeg' });
            
            // 다운로드 링크 생성 및 클릭
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `palm_analysis_${new Date().getTime()}.jpg`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            this.showMessage('이미지가 다운로드되었습니다.', 'success');
        } catch (error) {
            console.error('다운로드 오류:', error);
            this.showMessage('다운로드 중 오류가 발생했습니다.', 'error');
        }
    }
    
    showLoading(show) {
        const loadingIndicator = this.elements.loadingIndicator;
        const analysisResult = this.elements.analysisResult;
        
        if (show) {
            loadingIndicator.style.display = 'block';
            analysisResult.style.display = 'none';
        } else {
            loadingIndicator.style.display = 'none';
            analysisResult.style.display = 'block';
        }
    }
    
    showMessage(message, type = 'info') {
        // 기존 메시지 제거
        const existingMessage = document.querySelector('.alert-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // 새 메시지 생성
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show alert-message`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // 메시지를 첫 번째 카드 상단에 추가
        const firstCard = document.querySelector('.card');
        firstCard.parentNode.insertBefore(alertDiv, firstCard);
        
        // 3초 후 자동 제거
        setTimeout(() => {
            if (alertDiv && alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
    
    setupDragAndDrop() {
        const uploadForm = this.elements.uploadForm;
        
        // 드래그 오버 이벤트 방지
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadForm.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        // 드래그 시 시각적 피드백
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadForm.addEventListener(eventName, () => {
                uploadForm.classList.add('upload-area', 'dragover');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadForm.addEventListener(eventName, () => {
                uploadForm.classList.remove('dragover');
            });
        });
        
        // 드롭 이벤트 처리
        uploadForm.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.elements.imageUpload.files = files;
                this.previewUploadedImage({ target: { files: files } });
            }
        });
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.palmAnalyzer = new PalmAnalyzer();
    
    // 브라우저 호환성 체크
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        document.getElementById('camera-section').innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                이 브라우저는 카메라 기능을 지원하지 않습니다. 파일 업로드를 사용해주세요.
            </div>
        `;
    }
});