"""
CS2 Demo Parser Module

This module handles parsing of CS2 demo files using demoparser2.
It extracts player statistics, round data, and positional information
for comprehensive match analysis.
"""

import pandas as pd
from demoparser2 import DemoParser
from pathlib import Path
from typing import Dict, List, Optional
import json


class CS2DemoParser:
    """
    Main parser class for CS2 demo files.
    
    Handles extraction of kills, deaths, damage, round outcomes,
    and player positions for heatmap generation.
    """
    
    def __init__(self, demo_path: str):
        """
        Initialize parser with demo file path.
        
        Args:
            demo_path: Path to the .dem file to be analyzed
        """
        self.demo_path = Path(demo_path)
        self.parser = DemoParser(str(self.demo_path))
        self.df_kills = None
        self.df_damages = None
        self.df_rounds = None
        self.df_ticks = None
        
    def parse_demo(self) -> bool:
        """
        Parse the demo file and extract all relevant data.

        Returns:
            bool: True if parsing successful, False otherwise
        """
        try:
            # Parse kills - essential for K/D  and hs%
            # Include weapon information
            self.df_kills = self.parser.parse_event("player_death", other=["weapon", "assister_name"])

            # damage events needed for ADR calculation
            self.df_damages = self.parser.parse_event("player_hurt")

            # Parse round end events 
            self.df_rounds = self.parser.parse_event("round_end")

            # Parse tick data for positional heatmaps
            # We sample every 32 ticks (~1 second) to balance detail and performance
            self.df_ticks = self.parser.parse_ticks(["X", "Y", "Z", "health"])

            # Add round information to kills dataframe
            if self.df_kills is not None and self.df_rounds is not None:
                self._assign_rounds_to_kills()

            return True
        except Exception as e:
            print(f"Error parsing demo: {e}")
            return False

    def _assign_rounds_to_kills(self):
        """
        Assign round numbers to kill events based on round_end events.
        """
        if self.df_kills is None or self.df_rounds is None:
            return

        # Sort round ends by tick
        round_ends = self.df_rounds.sort_values('tick')

        # Create round mapping
        round_mapping = []
        current_round = 1

        for _, round_end in round_ends.iterrows():
            round_mapping.append({
                'round': current_round,
                'start_tick': round_end['tick'] if current_round == 1 else round_mapping[-1]['end_tick'],
                'end_tick': round_end['tick']
            })
            current_round += 1

        # Convert to DataFrame for easier lookup
        round_df = pd.DataFrame(round_mapping)

        # Function to find round for a given tick
        def find_round(tick):
            for _, row in round_df.iterrows():
                if row['start_tick'] <= tick <= row['end_tick']:
                    return int(row['round'])
            return 1  # Default to round 1 if not found

        # Add round column to kills
        self.df_kills['round'] = self.df_kills['tick'].apply(find_round)
    
    def get_player_statistics(self) -> pd.DataFrame:
        """
        Calculate comprehensive statistics for all players in the match.
        
        Returns:
            DataFrame with columns: player_name, kills, deaths, assists, 
                                   headshots, damage, adr, kd_ratio, hs_percentage
        """
        if self.df_kills is None or self.df_damages is None:
            raise ValueError("Demo must be parsed before calculating statistics")
        
        # Aggregate kill statistics
        # Group by attacker to count total kills per player
        kills_stats = self.df_kills.groupby('attacker_name').agg({
            'attacker_name': 'count',  # Total kills
            'headshot': 'sum'  # Headshot kills
        }).rename(columns={'attacker_name': 'kills', 'headshot': 'headshots'})
        
        # Aggregate death statistics
        # Group by victim to count deaths per player
        deaths_stats = self.df_kills.groupby('user_name').size().rename('deaths')
        
        # Aggregate assist statistics
        # Some demos may not have assist data, handle gracefully
        if 'assister_name' in self.df_kills.columns:
            assists_stats = self.df_kills[self.df_kills['assister_name'].notna()].groupby('assister_name').size().rename('assists')
        else:
            assists_stats = pd.Series(dtype=int, name='assists')
        
        # Aggregate damage statistics for ADR calculation
        # Group by attacker and sum all damage dealt
        damage_stats = self.df_damages.groupby('attacker_name')['dmg_health'].sum().rename('total_damage')
        
        # Combine all statistics into a single DataFrame
        stats = pd.concat([kills_stats, deaths_stats, assists_stats, damage_stats], axis=1).fillna(0)
        
        # Calculate derived metrics
        # K/D ratio: handle division by zero (perfect K/D if no deaths)
        stats['kd_ratio'] = stats.apply(
            lambda row: row['kills'] / row['deaths'] if row['deaths'] > 0 else row['kills'], 
            axis=1
        )
        
        # Headshot percentage: percentage of kills that were headshots
        stats['hs_percentage'] = (stats['headshots'] / stats['kills'] * 100).fillna(0)
        
        # ADR (Average Damage per Round): total damage divided by number of rounds played
        total_rounds = len(self.df_rounds) if self.df_rounds is not None else 1
        stats['adr'] = stats['total_damage'] / total_rounds
        
        # Reset index to make player_name a column instead of index
        stats = stats.reset_index().rename(columns={'index': 'player_name'})
        
        return stats
    
    def get_multi_kills(self) -> Dict[str, List[Dict]]:
        """
        Identify multi-kill rounds (2K, 3K, 4K, 5K ace) for each player.
        
        Returns:
            Dictionary mapping player names to list of multi-kill events
            Each event contains: round_num, kill_count, round_time
        """
        if self.df_kills is None:
            return {}
        
        # Add round number to kills for grouping
        # This assumes round_num exists in the kills dataframe
        if 'round' not in self.df_kills.columns:
            return {}
        
        multi_kills = {}
        
        # Group kills by player and round to count kills per round
        kills_per_round = self.df_kills.groupby(['attacker_name', 'round']).agg({
            'attacker_name': 'count',
            'tick': 'min'  # Get first kill tick of the round
        }).rename(columns={'attacker_name': 'kill_count'})
        
        # Filter for rounds with 2+ kills (multi-kills)
        multi_kill_rounds = kills_per_round[kills_per_round['kill_count'] >= 2]
        
        # Organize by player
        for (player, round_num), row in multi_kill_rounds.iterrows():
            if player not in multi_kills:
                multi_kills[player] = []
            
            multi_kills[player].append({
                'round_num': int(round_num),
                'kill_count': int(row['kill_count']),
                'tick': int(row['tick'])
            })
        
        return multi_kills
    
    def get_clutch_situations(self) -> Dict[str, List[Dict]]:
        """
        Identify clutch situations (1vX) and their outcomes.

        A clutch is when a player is the last alive on their team
        and faces multiple enemies.

        Returns:
            Dictionary mapping player names to clutch situations
            Each situation contains: round_num, enemies_count, won
        """
  
    def get_round_by_round_stats(self) -> pd.DataFrame:
        """
        Calculate player statistics broken down by round.

        Returns:
            DataFrame with round-by-round stats for each player
        """
        if self.df_kills is None:
            return pd.DataFrame()

        # Check if round column exists
        if 'round' not in self.df_kills.columns:
            print("Warning: 'round' column not found in kill data. Available columns:", list(self.df_kills.columns))
            return pd.DataFrame()

        # Group kills by round and player
        round_kills = self.df_kills.groupby(['round', 'attacker_name']).size().reset_index(name='kills')

        # Group deaths by round and player
        round_deaths = self.df_kills.groupby(['round', 'user_name']).size().reset_index(name='deaths')

        # Merge kills and deaths
        round_stats = pd.merge(round_kills, round_deaths, left_on=['round', 'attacker_name'],
                              right_on=['round', 'user_name'], how='outer').fillna(0)

        # Clean up columns
        round_stats['player_name'] = round_stats['attacker_name'].fillna(round_stats['user_name'])
        round_stats = round_stats[['round', 'player_name', 'kills', 'deaths']]

        # Calculate K/D per round
        round_stats['kd_ratio'] = round_stats.apply(
            lambda row: row['kills'] / row['deaths'] if row['deaths'] > 0 else row['kills'],
            axis=1
        )

        return round_stats.sort_values(['round', 'player_name'])

    def get_weapon_usage_stats(self) -> pd.DataFrame:
        """
        Calculate weapon usage statistics for each player.

        Returns:
            DataFrame with weapon usage breakdown
        """
        if self.df_kills is None:
            return pd.DataFrame()

        # Check if weapon column exists
        if 'weapon' not in self.df_kills.columns:
            print("Warning: 'weapon' column not found in kill data. Available columns:", list(self.df_kills.columns))
            return pd.DataFrame()

        # Group by player and weapon
        weapon_stats = self.df_kills.groupby(['attacker_name', 'weapon']).agg({
            'attacker_name': 'count',  # Kill count per weapon
            'headshot': 'sum'  # Headshot count per weapon
        }).rename(columns={'attacker_name': 'kills', 'headshot': 'headshots'})

        # Calculate headshot percentage per weapon
        weapon_stats['hs_percentage'] = (weapon_stats['headshots'] / weapon_stats['kills'] * 100).fillna(0)

        # Reset index
        weapon_stats = weapon_stats.reset_index().rename(columns={'attacker_name': 'player_name'})

        return weapon_stats.sort_values(['player_name', 'kills'], ascending=[True, False])

    def get_match_timeline(self) -> pd.DataFrame:
        """
        Create a timeline of key match events.

        Returns:
            DataFrame with timestamped events
        """
        if self.df_rounds is None:
            return pd.DataFrame()

        # Extract round end events
        timeline = self.df_rounds[['tick', 'round', 'winner']].copy()
        timeline['event_type'] = 'round_end'
        timeline['description'] = timeline.apply(
            lambda row: f"Round {int(row['round'])} won by {row['winner']}",
            axis=1
        )

        # Add bomb events if available
        if hasattr(self, 'df_bomb_events') and self.df_bomb_events is not None:
            bomb_events = self.df_bomb_events[['tick', 'event']].copy()
            bomb_events['round'] = None  # Would need to map to rounds
            bomb_events['winner'] = None
            bomb_events['event_type'] = 'bomb'
            bomb_events['description'] = bomb_events['event']
            timeline = pd.concat([timeline, bomb_events], ignore_index=True)

        return timeline.sort_values('tick')

    def get_performance_trends(self) -> pd.DataFrame:
        """
        Calculate performance trends over the course of the match.

        Returns:
            DataFrame with cumulative stats over rounds
        """
        round_stats = self.get_round_by_round_stats()
        if round_stats.empty:
            return pd.DataFrame()

        # Calculate cumulative stats
        trends = round_stats.groupby('player_name').apply(
            lambda group: group.assign(
                cumulative_kills=group['kills'].cumsum(),
                cumulative_deaths=group['deaths'].cumsum(),
                cumulative_kd=group['kd_ratio'].expanding().mean()
            )
        ).reset_index(drop=True)

        return trends

    def get_grenade_usage_stats(self) -> pd.DataFrame:
        """
        Calculate grenade usage statistics.

        Returns:
            DataFrame with grenade usage breakdown
        """
        # This would require parsing grenade events
        # For now, return placeholder
        return pd.DataFrame()

    def get_crosshair_placement_stats(self) -> pd.DataFrame:
        """
        Calculate crosshair placement accuracy statistics.

        Returns:
            DataFrame with crosshair placement metrics
        """
        # This would require advanced analysis of player aim data
        # For now, return placeholder
        return pd.DataFrame()

    def get_reaction_time_stats(self) -> pd.DataFrame:
        """
        Calculate reaction time measurements.

        Returns:
            DataFrame with reaction time metrics
        """
        # This would require analyzing time between events
        # For now, return placeholder
        return pd.DataFrame()

    def get_utility_damage_stats(self) -> pd.DataFrame:
        """
        Calculate damage dealt by utility (grenades, etc.).

        Returns:
            DataFrame with utility damage breakdown
        """
        # This would require parsing utility damage events
        # For now, return placeholder
        return pd.DataFrame()
    
    def get_positions_for_heatmap(self, player_name: str, event_type: str = 'kills') -> pd.DataFrame:
        """
        Extract player positions for heatmap visualization.

        Args:
            player_name: Name of the player to track
            event_type: 'kills' or 'deaths' to determine which positions to extract

        Returns:
            DataFrame with columns: x, y, z coordinates
        """
        if self.df_ticks is None or self.df_ticks.empty:
            return pd.DataFrame()

        if self.df_kills is None or self.df_kills.empty:
            return pd.DataFrame()

        try:
            # Get tick numbers for the player's kills/deaths
            if event_type == 'kills':
                event_ticks = self.df_kills[self.df_kills['attacker_name'] == player_name]['tick']
            elif event_type == 'deaths':
                event_ticks = self.df_kills[self.df_kills['user_name'] == player_name]['tick']
            else:
                return pd.DataFrame()

            if event_ticks.empty:
                return pd.DataFrame()

            # Get positions from tick data for these ticks
            # Find the closest tick positions for each event
            positions = []
            for event_tick in event_ticks:
                # Find the closest tick in position data
                closest_idx = (self.df_ticks['tick'] - event_tick).abs().idxmin()
                closest_tick = self.df_ticks.loc[closest_idx]

                # Only include if it's reasonably close (within 32 ticks = ~1 second)
                if abs(closest_tick['tick'] - event_tick) <= 32:
                    positions.append({
                        'x': closest_tick['X'],
                        'y': closest_tick['Y'],
                        'z': closest_tick['Z']
                    })

            if not positions:
                return pd.DataFrame()

            return pd.DataFrame(positions)

        except Exception as e:
            # Any error in position extraction
            print(f"Error getting positions: {e}")
            return pd.DataFrame()
    
    def export_statistics(self, output_dir: str = "results"):
        """
        Export parsed statistics to CSV and JSON formats.
        
        Args:
            output_dir: Directory where files will be saved
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Get and save player statistics
        stats = self.get_player_statistics()
        
        # Export to CSV for easy viewing in spreadsheet applications
        csv_path = output_path / f"{self.demo_path.stem}_stats.csv"
        stats.to_csv(csv_path, index=False)
        
        # Export to JSON for programmatic access
        json_path = output_path / f"{self.demo_path.stem}_stats.json"
        stats.to_json(json_path, orient='records', indent=2)
        
        # Export multi-kills data
        multi_kills = self.get_multi_kills()
        multi_kills_path = output_path / f"{self.demo_path.stem}_multifrags.json"
        with open(multi_kills_path, 'w') as f:
            json.dump(multi_kills, f, indent=2)
        
        print(f"Statistics exported to {output_dir}/")
        
        return csv_path, json_path


def quick_parse(demo_path: str) -> pd.DataFrame:
    """
    Convenience function for quick parsing and statistics extraction.
    
    Args:
        demo_path: Path to demo file
        
    Returns:
        DataFrame with player statistics
    """
    parser = CS2DemoParser(demo_path)
    if parser.parse_demo():
        return parser.get_player_statistics()
    return pd.DataFrame()


#----------------==-:..........:*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------=-..          ..:#%%%#*+==+*##%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#---------------=:...            ..++:...   ....-*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#--------------=-..               ...           ...+%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-------------=-:..                               ...*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#---------------:..                                 ..=%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------...                                 ..:*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------..                                   ..*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#------------------......                               ..=#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------==----:..                               ..:*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------:..                                 ..-*=-=*#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------:..                                   ......:*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------------.                                          ..+%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------------...                                         ..+%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------------..                                            .*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------:.                                             .-%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------:..                                            ..#%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#------------------===-:.        .....                               ..:%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#------------------=-:....       ..:..                              ..-#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-------------------:..        .......                                .+%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-------------------:..                                               ..#%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-------------------:.                                                ..*%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#--------------------..          ..    .....                          ..#%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------==-..        ..........-..                          .:%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------=-...        ..:-=-----:..                          ...*%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------=-...       ...----==-...                            ..=%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------==-..       ...-=----...                             ..=%%%%%%%%%%%%%%%%%%%%%%%%%%%
#--------------------..       .:-----:...                              ..=%%%%%%%%%%%%%%%%%%%%%%%%%%%
#--------------------..       .:-=-=-...                               ..*%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------=-:...      .:----..                                 ..#%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------=-...      ..:-=-...               ......            ..*%%%%%%%%%%%%%%%%%%%%%%%%%%%
#-----------------=-:.....  ..:---:...             ...--=:...          ..+%%%%%%%%%%%%%%%%%%%%%%%%%%%
#------------------------.. ...-=:..             ...-==-==-..          ..=%%%%%%%%%%%%%%%%%%%%%%%%%%%
#---------------------==-......--..              ..-==--==-:.           .:#%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------=-..  ..:...            ..:==------=-.            :#%%%%%%%%%%%%%%%%%%%%%%%%%%
#------------------------..   ....         .....-===--------:.           :#%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------=-..              ...::-==---------=--..          .+%%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------=-..              ..:-====----------==-..         ..*%%%%%%%%%%%%%%%%%%%%%%%%%
#----------------------=-..              ..:==---------------==....       ..=%%%%%%%%%%%%%%%%%%%%%%%%
#------------------------..               ..:==--------------===-..        ..=%%%%%%%%%%%%%%%%%%%%%%%
#------------------------..                .:==----------------==-.         ..-%%%%%%%%%%%%%%%%%%%%%%
#------------------------..   .....        .:=------------------=-..         ..+%%%%%%%%%%%%%%%%%%%%%
#------------------------..   ....         .--=-------------------..         ..=%%%%%%%%%%%%%%%%%%%%%
#------------------------...  ....       ...-==------------------=-..         ..*%%%%%%%%%%%%%%%%%%%%
#------------------------..  .....       ..:=-=------------------==-...       ...*%%%%%%%%%%%%%%%%%%%
#------------------------.....:-:..      ..-=-----------------------:.          .-%%%%%%%%%%%%%%%%%%%
#------------------------....--=-..      .:-==---------------------=-..         .-%%%%%%%%%%%%%%%%%%%
#------------------------.. .--=-..     ..:=-----------------------==-..       ..+%%%%%%%%%%%%%%%%%%%
#------------------------....:-=-..     ..:=------------------------==-:..      .=%%%%%%%%%%%%%%%%%%%
#------------------------.. .:--...     ..:=--------------------------==:..     ..#%%%%%%%%%%%%%%%%%%
#------------------------....::..        ..-=--------------------------==..     ..=%%%%%%%%%%%%%%%%%%
#------------------------:. ....         ..-=---------------------------=..     ..:#%%%%%%%%%%%%%%%%%
#---------------------==-..              ..:=--------------------------==..      ..+%%%%%%%%%%%%%%%%%
#-----------------------:..        ........:---------------------------=-..       .:%%%%%%%%%%%%%%%%%
#------------------------..    .....::------=---------------------------:.       ..:%%%%%%%%%%%%%%%%%

# counter strik 2 ^^^^
# made by qsek, good luck using this code lol
# atleast i tried to make it look cool and not just plain :P