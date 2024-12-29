#!/bin/sh
alembic revision --autogenerate -m "auto migration" && alembic upgrade head