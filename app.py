# Simple Flask chatbot with OpenAI-compatible LLM
import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

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

@app.route('/')
def home():
    return render_template('index.html')

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
