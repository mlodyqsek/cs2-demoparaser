"""
CS2 Demo Analyzer - Backend Package

This package contains the core parsing and rating logic for CS2 demo analysis.
"""

from .parser import CS2DemoParser, quick_parse
from .rating import PlayerRatingCalculator, calculate_ratings_from_parser

__version__ = "1.0.0"
__all__ = [
    'CS2DemoParser',
    'quick_parse',
    'PlayerRatingCalculator',
    'calculate_ratings_from_parser'
]
