#!/bin/zsh
# 메뉴바 앱 + 대시보드(http://127.0.0.1:8765) 실행
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then echo "먼저 ./setup.sh 를 실행하세요"; exit 1; fi
exec .venv/bin/python menubar.py
