import os
import sys

# Add project root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app as flask_app


class VercelPathMiddleware:
    """
    Middleware to ensure PATH_INFO is correctly preserved on Vercel deployments.
    If Vercel rewrites the path to /api/index or /api/index.py, restore the
    original client request path from Vercel headers.
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get("PATH_INFO", "")
        # If PATH_INFO is the serverless entrypoint, inspect headers for actual request path
        if path_info in ("/api/index", "/api/index.py"):
            forwarded = (
                environ.get("HTTP_X_FORWARDED_URI")
                or environ.get("HTTP_X_MATCHED_PATH")
                or environ.get("HTTP_X_REWRITE_URL")
                or environ.get("REQUEST_URI")
            )
            if forwarded and forwarded not in ("/api/index", "/api/index.py"):
                environ["PATH_INFO"] = forwarded.split("?")[0]
            else:
                environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


# Wrap Flask application with path normalization middleware
app = VercelPathMiddleware(flask_app)
