# Simple Flask chatbot with OpenAI-compatible LLM
import os
import io
import base64
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import qrcode
import psycopg
from psycopg import OperationalError
import time
import threading
from threading import Lock
import requests
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get LLM configuration from environment variables
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_URL = os.getenv('LLM_URL', 'http://localhost:11434/v1')
LLM_MODEL = os.getenv('LLM_MODEL', 'qwen3.5-4b')

print(f"LLM Configuration:")
print(f"  LLM_URL: {LLM_URL}")
print(f"  LLM_MODEL: {LLM_MODEL}")

if not LLM_API_KEY or not LLM_URL:
    print("Warning: LLM_API_KEY and LLM_URL environment variables must be set")

# Initialize OpenAI client with custom base URL
client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_URL
) if LLM_API_KEY and LLM_URL else None

# PostgreSQL Database Configuration
POSTGRES_HOST = os.getenv('POSTGRES_HOST', '127.0.0.1')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

def test_model_inference():
    """Test LLM model inference and print status"""
    print("\n" + "="*50)
    print("LLM Model Inference Test")
    print("="*50)
    print(f"LLM URL: {LLM_URL}")
    print(f"API Key: {'Set' if LLM_API_KEY else 'Not set'}")
    print("-"*50)

    logger.info("Starting LLM model inference test")
    logger.info(f"LLM URL: {LLM_URL}")

    if not LLM_URL or not LLM_API_KEY:
        error_msg = "LLM client not initialized (check LLM_API_KEY and LLM_URL)"
        print(f"❌ Inference Status: FAILED")
        print(f"Error: {error_msg}")
        print("="*50 + "\n")
        logger.error(f"Inference test failed: {error_msg}")
        return None

    try:
        # Query available models from the v1/models endpoint
        models_url = f"{LLM_URL.rstrip('/')}/models"
        print(f"Querying models endpoint: {models_url}")
        logger.info(f"Querying models endpoint: {models_url}")

        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
        response = requests.get(models_url, headers=headers, timeout=10)
        response.raise_for_status()

        models_data = response.json()
        logger.info(f"Models API response: {models_data}")

        # Extract model IDs from the response
        available_models = [model['id'] for model in models_data.get('data', [])]

        if not available_models:
            error_msg = "No models available on the server"
            print(f"❌ Inference Status: FAILED")
            print(f"Error: {error_msg}")
            print("="*50 + "\n")
            logger.error(f"Inference test failed: {error_msg}")
            return None

        # Use the first available model
        test_model = available_models[0]
        print(f"Available models: {', '.join(available_models)}")
        print(f"Using model for test: {test_model}")
        logger.info(f"Available models: {available_models}")
        logger.info(f"Selected model for inference test: {test_model}")
        print("-"*50)

        # Perform a simple test inference
        if not client:
            client_local = OpenAI(api_key=LLM_API_KEY, base_url=LLM_URL)
        else:
            client_local = client

        logger.info(f"Sending test inference request with model: {test_model}")
        test_response = client_local.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.0
        )

        response_text = test_response.choices[0].message.content
        print("✅ Inference Status: SUCCESSFUL")
        print(f"Test response: {response_text[:50]}..." if len(response_text) > 50 else f"Test response: {response_text}")
        print("="*50 + "\n")
        logger.info(f"Inference test successful. Response: {response_text}")
        return True

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to query models endpoint: {str(e)}"
        print(f"❌ Inference Status: FAILED")
        print(f"Error: {error_msg}")
        print("="*50 + "\n")
        logger.error(f"Inference test failed: {error_msg}")
        return None
    except Exception as e:
        error_msg = f"Error during inference test: {str(e)}"
        print(f"❌ Inference Status: FAILED")
        print(f"Error: {error_msg}")
        print("="*50 + "\n")
        logger.error(f"Inference test failed: {error_msg}", exc_info=True)
        return None

def test_db_connection():
    """Test PostgreSQL database connection and print status"""
    print("\n" + "="*50)
    print("PostgreSQL Connection Test")
    print("="*50)
    print(f"Host: {POSTGRES_HOST}")
    print(f"Port: {POSTGRES_PORT}")
    print(f"Database: {POSTGRES_DB}")
    print(f"User: {POSTGRES_USER}")
    print(f"Password: {'*' * len(POSTGRES_PASSWORD) if POSTGRES_PASSWORD else 'Not set'}")
    print("-"*50)

    if not POSTGRES_PASSWORD:
        print("❌ Connection Status: FAILED")
        print("Error: POSTGRES_PASSWORD environment variable is not set")
        print("="*50 + "\n")
        return None

    try:
        connection = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )

        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()

        print("✅ Connection Status: SUCCESSFUL")
        print(f"PostgreSQL version: {db_version[0]}")

        cursor.close()
        connection.close()
        print("="*50 + "\n")
        return True

    except OperationalError as e:
        print("❌ Connection Status: FAILED")
        print(f"Error: {str(e)}")
        print("="*50 + "\n")
        return None

# Test model inference on startup (before database test)
model_inference = test_model_inference()

# Test database connection on startup
db_connection = test_db_connection()

# Global flag to track if database is initialized
db_initialized = False

# Cached visit count and lock for thread safety
cached_visit_count = 0
visit_count_lock = Lock()
last_visit_count_update = 0

def init_database_once():
    """Attempt to initialize database tables once"""
    global db_initialized

    if not POSTGRES_PASSWORD:
        print("Skipping database initialization - POSTGRES_PASSWORD not set")
        return False

    try:
        connection = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=5
        )

        cursor = connection.cursor()

        # Create connections table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()
        cursor.close()
        connection.close()
        print("✅ Database tables initialized successfully")
        db_initialized = True
        return True

    except Exception as e:
        print(f"❌ Failed to initialize database tables: {str(e)}")
        return False

def init_database_with_retry():
    """Initialize database with retry logic using exponential backoff"""
    if not POSTGRES_PASSWORD:
        print("Skipping database initialization - POSTGRES_PASSWORD not set")
        return

    max_retries = 10
    retry_delay = 1  # Start with 1 second
    max_delay = 60   # Max 60 seconds between retries

    for attempt in range(1, max_retries + 1):
        print(f"🔄 Attempting database initialization (attempt {attempt}/{max_retries})...")

        if init_database_once():
            return  # Success!

        if attempt < max_retries:
            print(f"⏳ Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            # Exponential backoff: 1, 2, 4, 8, 16, 32, 60, 60, 60, 60
            retry_delay = min(retry_delay * 2, max_delay)
        else:
            print(f"❌ Failed to initialize database after {max_retries} attempts")
            print("⚠️  Database features will not be available until database is ready")

def init_database_background():
    """Run database initialization in background thread"""
    thread = threading.Thread(target=init_database_with_retry, daemon=True)
    thread.start()

def update_visit_count_cache():
    """Update the cached visit count from database"""
    global cached_visit_count, last_visit_count_update

    if not POSTGRES_PASSWORD or not db_initialized:
        return

    try:
        connection = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=3
        )

        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM connections")
        count = cursor.fetchone()[0]
        cursor.close()
        connection.close()

        # Thread-safe update
        with visit_count_lock:
            cached_visit_count = count
            last_visit_count_update = time.time()

    except Exception as e:
        print(f"⚠️  Failed to update visit count cache: {str(e)}")

def visit_count_updater_loop():
    """Background thread that periodically updates visit count"""
    # Wait for database to be initialized
    while not db_initialized:
        time.sleep(1)

    # Update cache every 5 seconds
    update_interval = 5

    while True:
        try:
            update_visit_count_cache()
        except Exception as e:
            print(f"⚠️  Error in visit count updater: {str(e)}")

        time.sleep(update_interval)

def start_visit_count_updater():
    """Start background thread for visit count updates"""
    thread = threading.Thread(target=visit_count_updater_loop, daemon=True)
    thread.start()
    print("📊 Visit count updater started (updates every 5 seconds)")

def log_connection(ip_address):
    """Log a user connection to the database"""
    if not POSTGRES_PASSWORD:
        return

    try:
        connection = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )

        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO connections (ip_address) VALUES (%s)",
            (ip_address,)
        )
        connection.commit()
        cursor.close()
        connection.close()
        print(f"📝 Logged connection from IP: {ip_address}")

    except Exception as e:
        print(f"❌ Failed to log connection: {str(e)}")

def get_db_status():
    """Get current database connection status and visit count"""
    if not POSTGRES_PASSWORD:
        return {'connected': False, 'message': 'Database not configured', 'visits': 0}

    try:
        connection = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=3
        )

        # Get visit count directly from database
        cursor = connection.cursor()
        visit_count = 0
        message = 'Connected'

        try:
            cursor.execute("SELECT COUNT(*) FROM connections")
            visit_count = cursor.fetchone()[0]
        except Exception as table_error:
            # Table doesn't exist yet - initialization in progress
            if 'does not exist' in str(table_error):
                message = 'Connected (initializing...)'
            else:
                raise

        cursor.close()
        connection.close()

        return {'connected': True, 'message': message, 'visits': visit_count}
    except Exception as e:
        return {'connected': False, 'message': str(e), 'visits': 0}

# Initialize database tables in background with retry logic
init_database_background()

@app.route('/')
def home():
    # Log the connection
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip:
        # Handle X-Forwarded-For which may contain multiple IPs
        client_ip = client_ip.split(',')[0].strip()
    log_connection(client_ip)

    return render_template('index.html')

@app.route('/api/db-status')
def db_status():
    """API endpoint to check database status"""
    status = get_db_status()
    return jsonify(status)

@app.route('/health')
@app.route('/healthz')
def health():
    """Health check endpoint for container orchestration"""
    health_status = {
        'status': 'healthy',
        'service': 'simple-web-server',
        'checks': {
            'llm': {
                'configured': client is not None,
                'url': LLM_URL,
                'model': LLM_MODEL
            },
            'database': get_db_status()
        }
    }

    # Determine overall health
    db_status = health_status['checks']['database']
    if not db_status['connected']:
        health_status['status'] = 'degraded'

    if not health_status['checks']['llm']['configured']:
        health_status['status'] = 'degraded'

    # Return 200 if healthy or degraded, 503 if unhealthy
    status_code = 200 if health_status['status'] in ['healthy', 'degraded'] else 503

    return jsonify(health_status), status_code

@app.route('/chat', methods=['POST'])
def chat():
    if not client:
        return jsonify({
            'error': 'LLM not configured. Please set LLM_API_KEY and LLM_URL environment variables.'
        }), 500

    try:
        data = request.json
        user_message = data.get('message', '')
        conversation_history = data.get('history', [])

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Build messages array for the LLM
        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        # Call the LLM
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        assistant_message = response.choices[0].message.content

        return jsonify({
            'message': assistant_message
        })

    except Exception as e:
        return jsonify({
            'error': f'Error communicating with LLM: {str(e)}'
        }), 500

@app.route('/qr', methods=['POST'])
def generate_qr():
    try:
        data = request.json
        url = data.get('url', '')

        if not url:
            return jsonify({'error': 'No URL provided'}), 400

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return jsonify({
            'qr_code': f'data:image/png;base64,{img_str}',
            'url': url
        })

    except Exception as e:
        return jsonify({
            'error': f'Error generating QR code: {str(e)}'
        }), 500

def init_app():
    """Initialize application (called once per worker when using Gunicorn)"""
    print("🚀 Initializing worker process...")
    # Background threads are already started at module level
    # Each worker gets its own background threads

if __name__ == '__main__':
    # Development server (not for production)
    print("⚠️  Running development server - use Gunicorn for production!")
    app.run(host='0.0.0.0', port=8000, threaded=True)
else:
    # Production mode with Gunicorn
    init_app()
