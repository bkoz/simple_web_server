# Container Build Guide

## Overview

This project uses **Hummingbird distroless Python images** for minimal, secure container deployments. The build uses a multi-stage Dockerfile approach to install dependencies in a full builder image, then copy them to a minimal runtime image.

## The Challenge

Hummingbird's distroless images are minimal and secure but don't include:
- Shell (`/bin/sh`)
- Package managers (`dnf`, `yum`, `apt`)
- Build tools

This means you cannot run `RUN pip install` directly in the distroless runtime image.

## The Solution: Multi-Stage Build

### Stage 1: Builder
Uses `quay.io/hummingbird/python:3.14-builder` which includes:
- Full OS with package managers
- Ability to install Python packages with pip
- Build tools for compiling extensions

### Stage 2: Runtime
Uses `quay.io/hummingbird/python:latest` (distroless) which provides:
- Minimal attack surface
- Small image size
- Only Python runtime and essential libraries

## Critical Implementation Details

### Python Package Paths

Python packages install to different locations depending on their type:

- **Pure Python packages**: `/usr/local/lib/python3.14/site-packages`
- **Compiled extensions**: `/usr/local/lib64/python3.14/site-packages`

**Both paths must be copied** from the builder to the runtime stage, otherwise packages with C extensions (like `markupsafe`, `pillow`) will fail with `ModuleNotFoundError`.

## Building the Container

```bash
podman build --pull --rm -f 'Dockerfile' -t 'simplewebserver:latest' '.'
```

### Build Options Explained

- `--pull`: Always pull the latest base images
- `--rm`: Remove intermediate containers after build
- `-f 'Dockerfile'`: Specify the Dockerfile
- `-t 'simplewebserver:latest'`: Tag the image

## Running the Container

```bash
podman run -d --name simplewebserver -p 8000:8000 simplewebserver:latest
```

### Run Options Explained

- `-d`: Run in detached mode (background)
- `--name simplewebserver`: Name the container
- `-p 8000:8000`: Map host port 8000 to container port 8000

## Checking Container Status

```bash
# View logs
podman logs simplewebserver

# Check if running
podman ps

# Stop the container
podman stop simplewebserver

# Remove the container
podman rm simplewebserver
```

## Platform Warning

When building/running on Apple Silicon (ARM64), you may see:
```
WARNING: image platform (linux/amd64) does not match the expected platform (linux/arm64)
```

This is expected since the Dockerfile specifies `--platform=linux/amd64`. The container will run via emulation.

## Environment Variables

The container uses these environment variables (set in Dockerfile):

- `LLM_URL`: URL for the LLM service (default: `http://localhost:11434/v1`)
- `LLM_API_KEY`: API key for authentication
- `LLM_MODEL`: Model name to use (default: `qwen3.5:2b`)

Override at runtime with:
```bash
podman run -d --name simplewebserver -p 8000:8000 \
  -e LLM_URL=http://my-llm-server:8080/v1 \
  -e LLM_API_KEY=my-key \
  -e LLM_MODEL=my-model \
  simplewebserver:latest
```

## Dockerfile Structure

```dockerfile
# Build stage - full image with package managers
FROM quay.io/hummingbird/python:3.14-builder AS builder
USER root
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage - minimal distroless image
FROM quay.io/hummingbird/python:latest
WORKDIR /app

# Copy BOTH lib and lib64 to capture all Python packages
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/lib64/python3.14/site-packages /usr/local/lib64/python3.14/site-packages

# Copy application files
COPY app.py .
COPY templates/ templates/

# Set environment and expose port
ENV LLM_URL=http://localhost:11434/v1
ENV LLM_API_KEY=<apikey_goes_here>
ENV LLM_MODEL=qwen3.5:2b
EXPOSE 8000

CMD ["python3", "app.py"]
```

## Troubleshooting

### ModuleNotFoundError
If you see `ModuleNotFoundError: No module named 'X'`:
- Ensure both `/usr/local/lib/` and `/usr/local/lib64/` are copied
- Verify the package is in `requirements.txt`
- Rebuild without cache: `podman build --no-cache ...`

### Container Exits Immediately
Check logs to see the error:
```bash
podman logs simplewebserver
```

### Port Already in Use
If port 8000 is busy:
```bash
podman run -d --name simplewebserver -p 8080:8000 simplewebserver:latest
```
Access at http://localhost:8080 instead.

## Benefits of This Approach

1. **Security**: Distroless images have minimal attack surface
2. **Size**: Smaller final image (no OS bloat)
3. **Reproducibility**: Builder stage ensures consistent dependency installation
4. **Best Practice**: Separates build-time and runtime concerns
