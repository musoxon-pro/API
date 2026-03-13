# This file is for PythonAnywhere web app tab
# It keeps the bot running

import os
import sys
import logging
from main import main

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def application(environ, start_response):
    """WSGI application for PythonAnywhere"""
    try:
        # Check if bot is already running
        if not hasattr(application, "bot_running"):
            # Start bot in background
            import threading
            bot_thread = threading.Thread(target=main)
            bot_thread.daemon = True
            bot_thread.start()
            application.bot_running = True
            
        # Return simple response for web requests
        status = '200 OK'
        output = b'Bot is running on PythonAnywhere!'
        
        response_headers = [
            ('Content-type', 'text/plain'),
            ('Content-Length', str(len(output)))
        ]
        start_response(status, response_headers)
        return [output]
        
    except Exception as e:
        status = '500 Internal Server Error'
        output = f'Error: {str(e)}'.encode()
        
        response_headers = [
            ('Content-type', 'text/plain'),
            ('Content-Length', str(len(output)))
        ]
        start_response(status, response_headers)
        return [output]
