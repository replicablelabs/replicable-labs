FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
ARG LAB_DIR=src/replicable/labs/deep-agents-langgraph-101
COPY ${LAB_DIR}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ${LAB_DIR}/app.py ${LAB_DIR}/chatgpt_model.py src/replicable/openai_oauth.py ./
COPY ${LAB_DIR}/notes ./notes

CMD ["python", "app.py"]

