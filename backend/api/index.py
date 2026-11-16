"""Vercel entry point: exposes the Django WSGI app as `app`."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.wsgi import application as app  # noqa: E402,F401
