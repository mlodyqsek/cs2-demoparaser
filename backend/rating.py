#since this may seem to be complicated you get some instructions:
"""
CS2 Player Rating Module

This module handles player rating calculations based on match performance.
Implements ELO-like rating system for CS2 players.
"""

import pandas as pd
from typing import Dict, List, Optional
from .parser import CS2DemoParser


class PlayerRatingCalculator:
    """
    Calculates player ratings based on match performance using an ELO-like system.
    """

    def __init__(self, k_factor: float = 32.0, base_rating: float = 1500.0):
        """
        Initialize rating calculator.

        Args:
            k_factor: Rating change multiplier (higher = more volatile ratings)
            base_rating: Default rating for new players
        """
        self.k_factor = k_factor
        self.base_rating = base_rating
        self.player_ratings: Dict[str, float] = {}

    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calculate expected score for player A against player B.

        Args:
            rating_a: Rating of player A
            rating_b: Rating of player B

        Returns:
            Expected score (0-1) for player A
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_ratings(self, player_stats: pd.DataFrame) -> Dict[str, float]:
        """
        Update player ratings based on match performance.

        Args:
            player_stats: DataFrame with player statistics

        Returns:
            Dictionary of updated player ratings
        """
        # Initialize ratings for new players
        for player in player_stats['player_name']:
            if player not in self.player_ratings:
                self.player_ratings[player] = self.base_rating

        # Simple rating update based on K/D ratio
        # In a real implementation, this would be more sophisticated
        for _, row in player_stats.iterrows():
            player = row['player_name']
            kd_ratio = row['kd_ratio']

            # Calculate performance score (0-1 scale)
            # Higher K/D = better performance
            performance_score = min(kd_ratio / 2.0, 1.0)  # Cap at 2.0 KD

            # Expected score based on current rating vs average
            avg_rating = sum(self.player_ratings.values()) / len(self.player_ratings)
            expected_score = self.calculate_expected_score(self.player_ratings[player], avg_rating)

            # Rating change
            rating_change = self.k_factor * (performance_score - expected_score)
            self.player_ratings[player] += rating_change

        return self.player_ratings.copy()

    def get_player_rating(self, player_name: str) -> Optional[float]:
        """
        Get current rating for a player.

        Args:
            player_name: Name of the player

        Returns:
            Player's rating or None if not found
        """
        return self.player_ratings.get(player_name)

    def generate_rating_report(self, stats: pd.DataFrame, multikills: Dict) -> pd.DataFrame:
        """
        Generate comprehensive rating report combining all performance metrics.

        Args:
            stats: DataFrame with basic player statistics
            multikills: Dictionary of multi-kill data

        Returns:
            DataFrame with ratings and rankings
        """
        # Start with basic stats
        rated_stats = stats.copy()

        # Calculate component scores (0-100 scale)
        rated_stats['kd_score'] = self._calculate_kd_score(rated_stats['kd_ratio'])
        rated_stats['hs_score'] = self._calculate_hs_score(rated_stats['hs_percentage'])
        rated_stats['adr_score'] = self._calculate_adr_score(rated_stats['adr'])
        rated_stats['multikill_score'] = self._calculate_multikill_score(rated_stats['player_name'], multikills)

        # Calculate overall rating using weights (redistributed without clutch)
        rated_stats['overall_rating'] = (
            rated_stats['kd_score'] * 0.35 +
            rated_stats['hs_score'] * 0.20 +
            rated_stats['adr_score'] * 0.30 +
            rated_stats['multikill_score'] * 0.15
        )

        # Add ranking based on overall rating
        rated_stats['rank'] = rated_stats['overall_rating'].rank(ascending=False, method='dense').astype(int)

        return rated_stats

    def _calculate_kd_score(self, kd_ratios: pd.Series) -> pd.Series:
        """Calculate K/D component score (0-100)."""
        # Normalize K/D ratio to 0-100 scale (cap at 3.0 KD)
        normalized = kd_ratios.clip(0, 3.0) / 3.0 * 100
        return normalized.round(1)

    def _calculate_hs_score(self, hs_percentages: pd.Series) -> pd.Series:
        """Calculate headshot percentage component score (0-100)."""
        # Headshot percentage is already 0-100, but weight it appropriately
        return hs_percentages.round(1)

    def _calculate_adr_score(self, adrs: pd.Series) -> pd.Series:
        """Calculate ADR component score (0-100)."""
        # Normalize ADR (typical range 50-150, cap at 150)
        normalized = adrs.clip(0, 150) / 150 * 100
        return normalized.round(1)

    def _calculate_multikill_score(self, player_names: pd.Series, multikills: Dict) -> pd.Series:
        """Calculate multi-kill component score (0-100)."""
        scores = []
        for player in player_names:
            if player in multikills:
                # Count total multi-kills and weight by kill count
                total_score = 0
                for mk in multikills[player]:
                    kill_count = mk['kill_count']
                    if kill_count >= 5:  # Ace
                        total_score += 50
                    elif kill_count == 4:  # Quad
                        total_score += 30
                    elif kill_count == 3:  # Triple
                        total_score += 15
                    elif kill_count == 2:  # Double
                        total_score += 5
                # Cap at 100 and normalize
                scores.append(min(total_score, 100))
            else:
                scores.append(0)
        return pd.Series(scores, index=player_names.index)

    def _calculate_clutch_score(self, player_names: pd.Series, clutches: Dict) -> pd.Series:
        """Calculate clutch component score (0-100)."""
        scores = []
        for player in player_names:
            if player in clutches:
                # Simple scoring based on number of clutch wins
                clutch_wins = sum(1 for c in clutches[player] if c.get('won', False))
                scores.append(min(clutch_wins * 20, 100))  # 20 points per clutch win, max 100
            else:
                scores.append(0)
        return pd.Series(scores, index=player_names.index)


def calculate_ratings_from_parser(parser: CS2DemoParser, k_factor: float = 32.0) -> Dict[str, float]:
    """
    Convenience function to calculate ratings directly from a parsed demo.

    Args:
        parser: Parsed CS2DemoParser instance
        k_factor: Rating change multiplier

    Returns:
        Dictionary mapping player names to their calculated ratings
    """
    calculator = PlayerRatingCalculator(k_factor=k_factor)

    try:
        player_stats = parser.get_player_statistics()
        return calculator.update_ratings(player_stats)
    except ValueError:
        # Demo not parsed yet
        return {}