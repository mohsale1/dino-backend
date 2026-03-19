FROM python:3.11-slim

WORKDIR /app

# Deployment identity — injected at build time via --build-arg
# Baked into the image so every startup log shows exactly which build is running
ARG BUILD_ID=local
ARG DEPLOYED_AT=unknown
ENV BUILD_ID=${BUILD_ID}
ENV DEPLOYED_AT=${DEPLOYED_AT}

# Prevent Python from writing .pyc bytecode files into the image layer
# and force stdout/stderr to be unbuffered so logs appear immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run the application
CMD ["sh", "-c", "uvicorn src.Main:app --host 0.0.0.0 --port ${PORT:-8080}"]
