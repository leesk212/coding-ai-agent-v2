FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    DEEPAGENTS_DEPLOYMENT_TOPOLOGY=split \
    MEMORY_DIR=/data/memory \
    STATE_DIR=/data/state

WORKDIR /opt/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && \
    pip install .

RUN mkdir -p /workspace /data/memory /data/state /root/.deepagents

WORKDIR /workspace

EXPOSE 8501

CMD ["python", "-m", "coding_agent"]
