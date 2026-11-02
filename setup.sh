#!/bin/zsh
# 가상환경(.venv)을 만들고 필요한 패키지를 설치한다.
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10 이상이 필요합니다"'
"$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo "설치 완료. 다음: 키체인에 캘린더 주소 저장 → ./run.sh (README 참고)"
