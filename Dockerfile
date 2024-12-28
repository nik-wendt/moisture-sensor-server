FROM python:3.12-slim AS base

WORKDIR /app

    # python
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # poetry
    # https://python-poetry.org/docs/configuration/#using-environment-variables
    POETRY_VERSION=1.0.3 \
    # make poetry install to this location
    POETRY_HOME="/opt/poetry" \
    # make poetry create the virtual environment in the project's root
    # it gets named `.venv`
#    POETRY_VIRTUALENVS_IN_PROJECT=true \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1

COPY pyproject.toml poetry.lock ./

RUN pip install poetry

RUN poetry install

FROM base AS alert_service
CMD ["poetry", "run", "python", "app.py"]
#CMD ["sleep", "1000"]

FROM base AS api_service
CMD ["uvicorn", "app:app", "--host", "http://192.168.1.138", "--port", "8000"]