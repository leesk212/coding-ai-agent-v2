FROM python:3.13-slim

WORKDIR /app

# System deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps (install separately for layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir hatchling && \
    mkdir -p src/coding_agent && \
    touch src/coding_agent/__init__.py && \
    pip install --no-cache-dir -e . && \
    rm -rf src/coding_agent

# Copy source
COPY src/ src/
COPY .env.example .env.example

# Re-install with actual source
RUN pip install --no-cache-dir -e .

# Memory persistence volume
RUN mkdir -p /root/.coding_agent/memory
VOLUME /root/.coding_agent/memory

# Streamlit port
EXPOSE 8501

# Default: WebUI mode
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["python", "-m", "coding_agent", "--webui"]
