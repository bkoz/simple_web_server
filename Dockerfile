# Dockerfile for simple web server

# Build stage - uses full Python image with package manager
FROM --platform=linux/amd64 quay.io/hummingbird/python:3.14-builder AS builder

USER root
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage - distroless Python image
FROM --platform=linux/amd64 quay.io/hummingbird/python:latest

WORKDIR /app

# Copy Python packages from builder (both lib and lib64 for compiled extensions)
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/lib64/python3.14/site-packages /usr/local/lib64/python3.14/site-packages

# Copy application files
COPY app.py .
COPY gunicorn_config.py .
COPY templates/ templates/

# Runtime environment variables
ENV LLM_URL=http://localhost:11434/v1
ENV LLM_API_KEY=<apikey_goes_here>
ENV LLM_MODEL=qwen3.5:2b
ENV GUNICORN_WORKERS=4

# Expose port 8000
EXPOSE 8000

# Run the application with Gunicorn
CMD ["python3", "-m", "gunicorn", "--config", "gunicorn_config.py", "app:app"]
