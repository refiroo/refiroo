FROM python:3.12-slim

WORKDIR /app
COPY backend/pyproject.toml .
COPY backend/app ./app
RUN pip install --no-cache-dir .
COPY model /model

ENV RDM_MODEL_PATH=/model/rdm-starter.json
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
