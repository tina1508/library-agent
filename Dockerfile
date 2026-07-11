FROM python:3.11-slim

LABEL maintainer="library-agent"
LABEL description="IBM watsonx.ai Library AI Agent"

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Non-root user for security
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Environment defaults (overridden at runtime)
ENV DEMO_MODE=false \
    PORT=5000 \
    HOST=0.0.0.0

EXPOSE 5000

CMD ["gunicorn", "main:create_app()", "--workers", "2", "--bind", "0.0.0.0:5000", "--timeout", "120"]
