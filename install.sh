#!/bin/bash

echo "=== Palm Analyzer 설치 스크립트 ==="
echo "Python 가상환경 생성 및 패키지 설치를 시작합니다..."

# Python 가상환경 생성
echo "1. 가상환경 생성 중..."
python3 -m venv palm_env

# 가상환경 활성화
echo "2. 가상환경 활성화 중..."
source palm_env/bin/activate

# pip 업그레이드
echo "3. pip 업그레이드 중..."
pip install --upgrade pip

# 패키지 설치
echo "4. 필요한 패키지 설치 중..."
pip install -r requirements.txt

echo ""
echo "=== 설치 완료 ==="
echo "다음 명령어로 서버를 실행하세요:"
echo "1. source palm_env/bin/activate"
echo "2. python app.py"
echo ""
echo "웹 브라우저에서 http://localhost:5000 으로 접속하세요."