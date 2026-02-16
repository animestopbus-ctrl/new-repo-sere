from flask import Flask
from threading import Thread
import os
import logging

# Disable Flask startup logs to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Titanium 22.0 Engine is Online and Running 24/7!"

def run():
    # Render assigns a dynamic PORT via environment variables
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()