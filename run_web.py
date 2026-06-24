"""Entrypoint for the web dashboard."""
from apps.web.app import app
import os

if __name__ == "__main__":
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "5050"))
    print(f"🌐 Web UI:  http://localhost:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)
