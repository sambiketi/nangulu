"""
Frontend configuration for vanilla HTML/CSS/JS.
Contract: Earth colors, KG precision, transparency.
"""
from decimal import Decimal, ROUND_HALF_UP

class FrontendConfig:
    """Configuration following contract rules."""
    
    # Contract: KG precision
    KG_PRECISION = 3
    KG_ROUNDING = ROUND_HALF_UP
    
    # Contract: Earth color palette
    COLORS = {
        "earth_dark": "#2D2424",
        "earth_medium": "#5C3D2E", 
        "earth_light": "#B85C38",
        "earth_sand": "#E0C097",
        "success": "#4C956C",
        "warning": "#FF9F1C",
        "danger": "#D90429",
        "info": "#2A9D8F"
    }
    
    # Contract: API settings
    API_BASE_PATH = "/api"
    CORS_ENABLED = True
    
    # Contract: Real-time updates (ms)
    POLLING_INTERVALS = {
        "dashboard": 30000,
        "stock": 60000,
        "alerts": 120000
    }
    
    @staticmethod
    def format_kg(value):
        """Format KG with 3 decimal places (contract)."""
        try:
            dec = Decimal(str(value))
            return f"{dec.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)} kg"
        except:
            return "0.000 kg"
    
    @staticmethod  
    def format_price(amount):
        """Format price with 2 decimal places."""
        try:
            dec = Decimal(str(amount))
            return f"${dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
        except:
            return "$0.00"

# Global instance
config = FrontendConfig()
