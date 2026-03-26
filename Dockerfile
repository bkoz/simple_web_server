# Dockerfile for simple web server
FROM --platform=linux/amd64 registry.access.redhat.com/ubi9/python-311

# Set up working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY templates/ templates/

# Expose port 8000
EXPOSE 8000

# Run time env vars
ENV LLM_URL=http://localhost:11434/v1
ENV LLM_API_KEY=<apikey_goes_here>
ENV LLM_MODEL=qwen3.5:2b


# Run the application
CMD ["python3", "app.py"]
