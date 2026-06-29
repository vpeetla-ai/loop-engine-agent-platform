FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml backend/requirements.txt ./
COPY src ./src
COPY backend ./backend
COPY corpus ./corpus
COPY loops ./loops
RUN pip install --no-cache-dir -r backend/requirements.txt && pip install --no-cache-dir -e ".[dev]"
ENV PYTHONPATH=/app/src:/app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
