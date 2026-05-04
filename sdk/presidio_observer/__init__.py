from .emitter import init_emitter
from .patcher import patch

def init(endpoint: str = "http://localhost:8000"):
    """
    Initialize the presidio-observer.
    This should be called before importing any Presidio modules.
    
    Args:
        endpoint: The base URL of the observer backend.
    """
    init_emitter(endpoint)
    patch()
