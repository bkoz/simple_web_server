# Simple Web Server

A lightweight Flask web application with containerization support. This project demonstrates a basic web server setup with Docker deployment capabilities and cloud platform compatibility.

## Features

- Simple Flask web server with styled HTML templates
- Docker containerization using Red Hat UBI 10 base image
- Heroku deployment ready (Procfile included)
- Minimal dependencies for easy maintenance
- Responsive web interface

## Technology Stack

- **Framework**: Flask 3.0.2
- **Language**: Python 3
- **Container**: Docker with Red Hat UBI 10
- **Deployment**: Compatible with Heroku and other PaaS platforms

## Prerequisites

- Python 3.x
- pip (Python package manager)
- Docker (optional, for containerized deployment)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd simple_web_server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running Locally

Start the Flask development server:
```bash
python app.py
```

The application will be available at `http://localhost:8000`

### Running with Docker

1. Build the Docker image:
```bash
docker build -t simple-web-server .
```

2. Run the container:
```bash
docker run -p 8000:8000 simple-web-server
```

Access the application at `http://localhost:8000`

### Deploying to Heroku

The project includes a `Procfile` for Heroku deployment:

```bash
heroku create your-app-name
git push heroku main
```

## Project Structure

```
simple_web_server/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── Procfile          # Heroku deployment configuration
├── templates/
│   └── index.html    # Homepage template
└── README.md         # This file
```

## Configuration

- **Port**: 8000 (configurable in `app.py`)
- **Host**: 0.0.0.0 (listens on all network interfaces)

## License

This project is open source and available for educational purposes.
