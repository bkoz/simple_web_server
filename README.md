# AI Chatbot

A lightweight Flask web application that provides a chat interface powered by OpenAI-compatible LLM APIs. This project demonstrates integration with any OpenAI-compatible endpoint, including OpenAI, Azure OpenAI, local LLMs (like LM Studio, Ollama), and other compatible services.

## Features

- Interactive chat interface with conversation history
- Support for any OpenAI-compatible LLM API
- Configurable via environment variables
- podman containerization using Red Hat UBI 10 base image
- Heroku deployment ready (Procfile included)
- Responsive web interface with modern design
- Real-time message streaming

## Technology Stack

- **Framework**: Flask 3.0.2
- **Language**: Python 3
- **LLM Integration**: OpenAI Python SDK
- **Container**: podman with Red Hat UBI 10
- **Deployment**: Compatible with Heroku and other PaaS platforms

## Prerequisites

- Python 3.x
- pip (Python package manager)
- Access to an OpenAI-compatible LLM API (OpenAI, Azure OpenAI, local LLM, etc.)
- API key for your chosen LLM service
- podman (optional, for containerized deployment)

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

3. Configure environment variables:
```bash
cp .env.example .env
```

Edit the `.env` file and set your LLM configuration:
- `LLM_URL`: The base URL for your OpenAI-compatible API endpoint
- `LLM_API_KEY`: Your API key for authentication
- `LLM_MODEL`: The model to use 

### Example Configurations

**Ollama:**
```bash
LLM_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=llama2
```

## Usage

### Running Locally

Start the Flask development server:
```bash
python app.py
```

The chatbot interface will be available at `http://localhost:8000`

### Running with podman

1. Build the podman image:
```bash
podman build -t simplewebserver .
```

2. Run the container with environment variables:
```bash
podman run --rm -it --name=simplewebserver -p 8000:8000 \
  -e LLM_URL=https://api.mymodelserver.com/v1 \
  -e LLM_API_KEY=your-api-key \
  -e LLM_MODEL=your-model \
  simplewebserver
```

Access the chatbot at `http://localhost:8000`

## Project Structure

```
simple_web_server/
├── app.py              # Main Flask application with chat endpoints
├── requirements.txt    # Python dependencies
├── .env.example       # Example environment configuration
├── Dockerfile         # Docker configuration
├── Procfile          # Heroku deployment configuration
├── templates/
│   └── index.html    # Chat interface template
└── README.md         # This file
```

## Configuration

### Server Configuration

- **Port**: 8000 (configurable in `app.py`)
- **Host**: 0.0.0.0 (listens on all network interfaces)

## Troubleshooting

### LLM not configured error
Make sure you have set the `LLM_URL` and `LLM_API_KEY` environment variables either in your `.env` file or in your system environment.

### Connection refused error
If using a local LLM (like Ollama or LM Studio), ensure the service is running and accessible at the URL you specified.

### Invalid API key error
Verify that your API key is correct and has the necessary permissions for the API endpoint you're using.

### Model not found error
Check that the model name in `LLM_MODEL` matches an available model on your LLM service. You can often omit this variable to use the service's default model.

## Compatible LLM Services

This chatbot works with any OpenAI-compatible API, including:
- OpenAI (GPT-3.5, GPT-4, etc.)
- Azure OpenAI Service
- Anthropic Claude (via OpenAI-compatible proxies)
- Local LLMs via:
  - LM Studio
  - Ollama
  - LocalAI
  - text-generation-webui
- Open-source model providers:
  - Together AI
  - Anyscale
  - Fireworks AI

## License

This project is open source and available for educational purposes.
