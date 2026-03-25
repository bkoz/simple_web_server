# Dockerfile for simple web server
FROM registry.access.redhat.com/ubi9/python-311

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

# Run the application
CMD ["python3", "app.py"]