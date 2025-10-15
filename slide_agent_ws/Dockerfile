FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal runtime deps (need git for pip VCS installs)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps (myagent from git, plus extras)
RUN pip install --no-cache-dir \
    "myagent @ git+https://github.com/JasonDZS/myagent.git@v0.1.2" \
    pymysql \
    python-dotenv

# Copy slide_agent sources
COPY slide_agent /app/slide_agent

# Ensure workdir exists for outputs
RUN mkdir -p /app/slide_agent/workdir/ppt

EXPOSE 8080

WORKDIR /app
CMD ["python", "slide_agent/server.py", "--host", "0.0.0.0", "--port", "8080"]
