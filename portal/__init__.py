"""Noctipede Web Portal - Live Metrics Dashboard."""

# Import app only when explicitly requested to avoid dependency issues
def get_app():
    from .main import app
    return app

__all__ = ['get_app']
