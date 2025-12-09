"""
Configuration Module

Central configuration for the CS2 Demo Analyzer application.
Modify these settings to customize behavior.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
NOTEBOOKS_DIR.mkdir(exist_ok=True)

# Rating system configuration
DEFAULT_RATING_WEIGHTS = {
    'kd_weight': 0.30,      # Kill/Death ratio importance
    'hs_weight': 0.15,      # Headshot percentage importance
    'adr_weight': 0.25,     # Average damage per round importance
    'multikill_weight': 0.20,  # Multi-frag impact importance
    'clutch_weight': 0.10   # Clutch ability importance
}

# Rank thresholds (rating -> rank mapping)
RANK_THRESHOLDS = {
    90: "Global Elite",
    80: "Supreme",
    70: "Legendary Eagle",
    60: "Distinguished Master Guardian",
    50: "Master Guardian",
    40: "Gold Nova",
    30: "Silver Elite",
    0: "Silver"
}

# Multi-kill scoring system
MULTIKILL_SCORES = {
    2: 1,   # Double kill
    3: 3,   # Triple kill
    4: 6,   # Quad kill
    5: 10   # Ace
}

# Clutch scoring system
CLUTCH_SCORES = {
    1: 2,   # 1v1
    2: 5,   # 1v2
    3: 10,  # 1v3
    4: 15   # 1v4+
}

# Parsing configuration
TICK_SAMPLING_RATE = 32  # Sample every N ticks for heatmaps (lower = more detail, slower)

# Visualization configuration
PLOTLY_THEME = "plotly_dark"
PRIMARY_COLOR = "#00d9ff"
SECONDARY_COLOR = "#ff6b35"

# Color scales for heatmaps
HEATMAP_COLORSCALE = "Hot"
RATING_COLORSCALE = "Viridis"

# Export configuration
EXPORT_CSV_ENCODING = "utf-8"
EXPORT_JSON_INDENT = 2

# Streamlit configuration
STREAMLIT_THEME = {
    "primaryColor": PRIMARY_COLOR,
    "backgroundColor": "#0e1117",
    "secondaryBackgroundColor": "#1a1d29",
    "textColor": "#ffffff",
    "font": "sans serif"
}

# File size limits (in MB)
MAX_DEMO_FILE_SIZE = 500  # Maximum demo file size to process

# Performance settings
ENABLE_CACHING = True  # Cache parsed demo data
CACHE_EXPIRY_HOURS = 24  # How long to keep cached data

# Feature flags
ENABLE_CLUTCH_DETECTION = False  # Full clutch detection (computationally expensive)
ENABLE_TIME_TO_DAMAGE = False    # Time-to-damage analysis (requires tick-by-tick analysis)
ENABLE_CROSSHAIR_PLACEMENT = False  # Crosshair placement analysis (future feature)

# Debug settings
DEBUG_MODE = False
VERBOSE_LOGGING = False

# API configuration (for future API endpoints)
API_ENABLED = False
API_PORT = 8000
API_HOST = "0.0.0.0"


def get_rank_from_rating(rating: float) -> str:
    """
    Get rank string from rating value.
    
    Args:
        rating: Player rating (0-100)
        
    Returns:
        Rank string
    """
    for threshold, rank in sorted(RANK_THRESHOLDS.items(), reverse=True):
        if rating >= threshold:
            return rank
    return "Silver"


def validate_config():
    """
    Validate configuration settings.
    
    Ensures weights sum to 1.0 and all settings are valid.
    """
    weight_sum = sum(DEFAULT_RATING_WEIGHTS.values())
    if not (0.99 <= weight_sum <= 1.01):
        print(f"Warning: Rating weights sum to {weight_sum:.2f}, should be 1.0")
    
    if TICK_SAMPLING_RATE < 1:
        print("Warning: TICK_SAMPLING_RATE must be at least 1")
    
    if MAX_DEMO_FILE_SIZE <= 0:
        print("Warning: MAX_DEMO_FILE_SIZE must be positive")


# Run validation on import
if DEBUG_MODE:
    validate_config()
