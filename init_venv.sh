#!/bin/bash

if ! command -v python3 &> /dev/null; then
    echo "Python3 не установлен. Пожалуйста, установите Python3."
    exit 1
fi

# apt install python3.10-venv

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
