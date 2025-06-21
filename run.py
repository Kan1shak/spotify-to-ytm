import webview
import uvicorn
import threading
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from gui import app

APP_HOST = "127.0.0.1"
APP_PORT = 5001

def run_server():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)

if __name__ == '__main__':
    print("Starting desktop application...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    webview.create_window(
        'Spotify to YTM',
        f'http://{APP_HOST}:{APP_PORT}',
        width=800,
        height=600,
        resizable=True
    )
    webview.start()
    print("Desktop application closed.")