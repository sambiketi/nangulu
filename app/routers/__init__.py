"""
Routers for Nangulu POS
"""

from .auth import router as auth_router
from .inventory import router as inventory_router

__all__ = ["auth_router", "inventory_router"]
