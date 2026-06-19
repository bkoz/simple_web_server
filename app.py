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

load_dotenv()

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

# Test database connection on startup
db_connection = test_db_connection()

# Global flag to track if database is initialized
db_initialized = False

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

        # Get visit count - handle case where table doesn't exist yet
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM connections")
            visit_count = cursor.fetchone()[0]
            message = 'Connected'
        except Exception as table_error:
            # Table doesn't exist yet - initialization in progress
            if 'does not exist' in str(table_error):
                visit_count = 0
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
