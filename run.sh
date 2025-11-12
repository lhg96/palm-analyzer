#!/bin/bash

echo "=== Palm Analyzer 서버 시작 ==="

# 가상환경이 활성화되어 있는지 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "가상환경을 활성화합니다..."
    source palm_env/bin/activate
fi

# 서버 시작
echo "서버를 시작합니다..."
python app.py