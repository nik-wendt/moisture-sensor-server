#!/bin/sh

export DEBUG=1
source ./.venv/bin/activate

uvicorn app:app --reload --host 192.168.1.138 --port 8000