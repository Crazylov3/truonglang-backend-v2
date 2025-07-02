# Import the main router that includes all sub-routers
from .courses import router

# Export the router for the main app to use
__all__ = ["router"] 