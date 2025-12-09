"""
CS2 Demo Analyzer - Streamlit Frontend

Professional web interface for analyzing CS2 demo files.
Provides interactive statistics, visualizations, and player ratings.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
import json
import numpy as np

# Add backend
sys.path.append(str(Path(__file__).parent.parent))

from backend.parser import CS2DemoParser
from backend.rating import PlayerRatingCalculator


# Page configuration
st.set_page_config(
    page_title="CS2 Demo Analyzer",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #1a1d29 100%);
    }
    /* Metric card styling */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00d9ff;
    }
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1a1d29;
    }
    /* Headers */
    h1, h2, h3 {
        color: #00d9ff;
    }
    /* Data frame styling */
    .dataframe {
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """
    Initialize session state variables for maintaining app state.
    
    Session state persists data across reruns, essential for
    maintaining parsed demo data without re-parsing on every interaction.
    """
    if 'parser' not in st.session_state:
        st.session_state.parser = None
    if 'stats' not in st.session_state:
        st.session_state.stats = None
    if 'rated_stats' not in st.session_state:
        st.session_state.rated_stats = None
    if 'demo_parsed' not in st.session_state:
        st.session_state.demo_parsed = False


def sidebar_controls():
    """
    Render sidebar with file upload and configuration controls.
    
    Returns:
        Tuple of (uploaded_file, custom_weights dict)
    """
    st.sidebar.title("CS2 Demo Analyzer")
    st.sidebar.markdown("---")
    
    # File upload 
    st.sidebar.subheader("Upload Demo")
    uploaded_file = st.sidebar.file_uploader(
        "Choose a .dem file",
        type=['dem'],
        help="Upload a CS2 demo file for analysis"
    )
    
    st.sidebar.markdown("---")
    
    # Rating weights CNFG
    st.sidebar.subheader("Rating Configuration")
    st.sidebar.markdown("Adjust weights to customize player rating calculation:")
    
    # Weight sliders 
    kd_weight = st.sidebar.slider(
        "K/D Weight",
        min_value=0.0,
        max_value=1.0,
        value=0.30,
        step=0.05,
        help="Importance of Kill/Death ratio in overall rating"
    )
    
    hs_weight = st.sidebar.slider(
        "Headshot % Weight",
        min_value=0.0,
        max_value=1.0,
        value=0.15,
        step=0.05,
        help="Importance of headshot accuracy in overall rating"
    )
    
    adr_weight = st.sidebar.slider(
        "ADR Weight",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.05,
        help="Importance of Average Damage per Round in overall rating"
    )
    
    # Package weights into dictionary for rating calculator
    custom_weights = {
        'kd_weight': kd_weight,
        'hs_weight': hs_weight,
        'adr_weight': adr_weight
    }
    
    # Display weight sum warning 
    weight_sum = sum(custom_weights.values())
    if not (0.99 <= weight_sum <= 1.01):
        st.sidebar.warning(f"Weights sum to {weight_sum:.2f}. They will be normalized to 1.0")
    
    st.sidebar.markdown("---")
    
    # Additional info
    st.sidebar.info("Tip: Upload a demo file to start analyzing player performance!")
    
    return uploaded_file, custom_weights


def parse_demo_file(uploaded_file):
    """
    Parse uploaded demo file and store results in session state.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    """
    # Save uploaded file temporarily
    temp_path = Path("temp_demo.dem")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Initialize parser and parse demo
    with st.spinner("🔄 Parsing demo file... This may take a moment."):
        try:
            parser = CS2DemoParser(str(temp_path))
            success = parser.parse_demo()
            
            if success:
                # Store parser
                st.session_state.parser = parser
                st.session_state.stats = parser.get_player_statistics()
                st.session_state.demo_parsed = True
                st.success("Demo parsed successfully!")
            else:
                st.error("Failed to parse demo file. Please check the file format.")
        except Exception as e:
            st.error(f"Error parsing demo: {str(e)}")
        finally:
            # Clean up temporary file
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except PermissionError:
                    
                    pass


def display_overview_metrics(stats):
    """
    Display key match statistics in metric cards.
    
    Args:
        stats: DataFrame with player statistics
    """
    st.subheader("Match Overview")
    
    # Calculate aggregate statistics
    total_kills = stats['kills'].sum()
    total_deaths = stats['deaths'].sum()
    avg_adr = stats['adr'].mean()
    avg_hs = stats['hs_percentage'].mean()
    
    # Display in columnsut
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Kills", f"{int(total_kills)}")
    with col2:
        st.metric("Total Deaths", f"{int(total_deaths)}")
    with col3:
        st.metric("Avg ADR", f"{avg_adr:.1f}")
    with col4:
        st.metric("Avg HS%", f"{avg_hs:.1f}%")


def display_player_statistics_table(rated_stats):
    """
    Display comprehensive player statistics in an interactive table.
    
    Args:
        rated_stats: DataFrame with rated player statistics
    """
    st.subheader("Player Statistics & Ratings")
    
    # Select most relevant columns for display
    display_cols = [
        'player_name', 'kills', 'deaths', 'assists', 'kd_ratio',
        'hs_percentage', 'adr', 'overall_rating', 'rank'
    ]
    
    # check if all columns exist in the dataframe
    available_cols = [col for col in display_cols if col in rated_stats.columns]
    display_df = rated_stats[available_cols].copy()
    
    # Format numeric columns 
    if 'kd_ratio' in display_df.columns:
        display_df['kd_ratio'] = display_df['kd_ratio'].round(2)
    if 'hs_percentage' in display_df.columns:
        display_df['hs_percentage'] = display_df['hs_percentage'].round(1)
    if 'adr' in display_df.columns:
        display_df['adr'] = display_df['adr'].round(1)
    
    # Rename columns 
    display_df = display_df.rename(columns={
        'player_name': 'Player',
        'kills': 'K',
        'deaths': 'D',
        'assists': 'A',
        'kd_ratio': 'K/D',
        'hs_percentage': 'HS%',
        'adr': 'ADR',
        'overall_rating': 'Rating',
        'rank': 'Rank'
    })
    
    # Display dataframe with highlighting
    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True
    )


def create_rating_comparison_chart(rated_stats):
    """
    Create interactive bar chart comparing player ratings.
    
    Args:
        rated_stats: DataFrame with player ratings
        
    Returns:
        Plotly figure object
    """
    # Sort by rating
    plot_data = rated_stats.sort_values('overall_rating', ascending=True)
    
    # horizontal bar chart
    fig = go.Figure(go.Bar(
        x=plot_data['overall_rating'],
        y=plot_data['player_name'],
        orientation='h',
        marker=dict(
            color=plot_data['overall_rating'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Rating")
        ),
        text=plot_data['overall_rating'].round(1),
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Player Rating Comparison",
        xaxis_title="Overall Rating",
        yaxis_title="Player",
        height=400,
        template="plotly_dark",
        showlegend=False
    )
    
    return fig


def create_rating_components_chart(rated_stats, selected_player):
    """
    Create radar chart showing rating component breakdown for a player.
    
    Args:
        rated_stats: DataFrame with player ratings
        selected_player: Name of player to analyze
        
    Returns:
        Plotly figure object
    """
    # Get player data
    player_data = rated_stats[rated_stats['player_name'] == selected_player].iloc[0]
    
    # Extract component scores
    categories = ['K/D', 'Headshot %', 'ADR', 'Multi-kills']
    values = [
        player_data.get('kd_score', 50),
        player_data.get('hs_score', 50),
        player_data.get('adr_score', 50),
        player_data.get('multikill_score', 50)
    ]
    
    # radar chart
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        marker=dict(color='#00d9ff')
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        title=f"{selected_player} - Rating Breakdown",
        template="plotly_dark",
        height=400
    )
    
    return fig


def create_kd_comparison_chart(stats):
    """
    Create scatter plot comparing K/D ratio vs ADR for all players.

    Args:
        stats: DataFrame with player statistics

    Returns:
        Plotly figure object
    """
    fig = px.scatter(
        stats,
        x='adr',
        y='kd_ratio',
        size='kills',
        color='hs_percentage',
        hover_data=['player_name'],
        labels={
            'adr': 'Average Damage per Round',
            'kd_ratio': 'K/D Ratio',
            'hs_percentage': 'HS%'
        },
        color_continuous_scale='Turbo'
    )

    fig.update_layout(
        title="Player Performance: K/D vs ADR",
        template="plotly_dark",
        height=500
    )

    return fig


def create_round_by_round_chart(parser, selected_player):
    """
    Create line chart showing round-by-round performance for a player.

    Args:
        parser: CS2DemoParser instance
        selected_player: Name of player to analyze

    Returns:
        Plotly figure object
    """
    round_stats = parser.get_round_by_round_stats()
    if round_stats.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No round-by-round data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(template="plotly_dark", height=400)
        return fig

    player_rounds = round_stats[round_stats['player_name'] == selected_player]

    if player_rounds.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No round data for {selected_player}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(template="plotly_dark", height=400)
        return fig

    fig = go.Figure()

    # Add kills line
    fig.add_trace(go.Scatter(
        x=player_rounds['round'],
        y=player_rounds['kills'],
        mode='lines+markers',
        name='Kills',
        line=dict(color='#00d9ff', width=3),
        marker=dict(size=8)
    ))

    # Add deaths line
    fig.add_trace(go.Scatter(
        x=player_rounds['round'],
        y=player_rounds['deaths'],
        mode='lines+markers',
        name='Deaths',
        line=dict(color='#ff4444', width=3),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title=f"{selected_player} - Round by Round Performance",
        xaxis_title="Round",
        yaxis_title="Count",
        template="plotly_dark",
        height=400,
        showlegend=True
    )

    return fig


def create_weapon_usage_chart(parser, selected_player):
    """
    Create bar chart showing weapon usage statistics for a player.

    Args:
        parser: CS2DemoParser instance
        selected_player: Name of player to analyze

    Returns:
        Plotly figure object
    """
    weapon_stats = parser.get_weapon_usage_stats()
    if weapon_stats.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No weapon usage data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(template="plotly_dark", height=400)
        return fig

    player_weapons = weapon_stats[weapon_stats['player_name'] == selected_player]

    if player_weapons.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No weapon data for {selected_player}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(template="plotly_dark", height=400)
        return fig

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=player_weapons['weapon'],
        y=player_weapons['kills'],
        marker=dict(color='#00d9ff'),
        text=player_weapons['kills'],
        textposition='auto'
    ))

    fig.update_layout(
        title=f"{selected_player} - Weapon Usage",
        xaxis_title="Weapon",
        yaxis_title="Kills",
        template="plotly_dark",
        height=400
    )

    return fig


def create_performance_trends_chart(parser, selected_player):
    """
    Create line chart showing performance trends over the match.

    Args:
        parser: CS2DemoParser instance
        selected_player: Name of player to analyze

    Returns:
        Plotly figure object
    """
    trends = parser.get_performance_trends()
    if trends.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No performance trend data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(template="plotly_dark", height=400)
        return fig

    player_trends = trends[trends['player_name'] == selected_player]

    if player_trends.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No trend data for {selected_player}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(template="plotly_dark", height=400)
        return fig

    fig = go.Figure()

    # Cumulative K/D ratio
    fig.add_trace(go.Scatter(
        x=player_trends['round'],
        y=player_trends['cumulative_kd'],
        mode='lines+markers',
        name='Cumulative K/D',
        line=dict(color='#00d9ff', width=3),
        marker=dict(size=6)
    ))

    fig.update_layout(
        title=f"{selected_player} - Performance Trends",
        xaxis_title="Round",
        yaxis_title="Cumulative K/D Ratio",
        template="plotly_dark",
        height=400
    )

    return fig






def export_data_section(parser, rated_stats):
    """
    Provide options to export analyzed data in various formats.
    
    Args:
        parser: CS2DemoParser instance
        rated_stats: DataFrame with rated statistics
    """
    st.subheader("Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export statistics as CSV
        csv = rated_stats.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="cs2_stats.csv",
            mime="text/csv"
        )
    
    with col2:
        # Export statistics as JSON
        json_data = rated_stats.to_json(orient='records', indent=2)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name="cs2_stats.json",
            mime="application/json"
        )
    
    with col3:
        # Export multi-kill data
        multikills = parser.get_multi_kills()
        multikill_json = json.dumps(multikills, indent=2)
        st.download_button(
            label="Download Multi-kills",
            data=multikill_json,
            file_name="cs2_multikills.json",
            mime="application/json"
        )


def main():
    """
    Main application flow.
    
    Orchestrates the entire UI: sidebar controls, file parsing,
    data visualization, and interactive elements.
    """
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar
    uploaded_file, custom_weights = sidebar_controls()
    
    # Main header
    st.title("CS2 Demo Analyzer")
    st.markdown("### Professional Match Analysis & Player Rating System")
    st.markdown("---")
    
    # Handle file upload 
    if uploaded_file is not None:
        # Parse demo if not already parsed or if new file uploaded
        if not st.session_state.demo_parsed or st.session_state.parser is None:
            parse_demo_file(uploaded_file)
        
        # Display analysis if demo is successfully parsed
        if st.session_state.demo_parsed and st.session_state.parser is not None:
            parser = st.session_state.parser
            stats = st.session_state.stats
            
            # Calculate ratings with custom weights
            calculator = PlayerRatingCalculator(custom_weights)
            multikills = parser.get_multi_kills()
            rated_stats = calculator.generate_rating_report(stats, multikills)
            st.session_state.rated_stats = rated_stats
            
            # Display overview metrics
            display_overview_metrics(stats)
            st.markdown("---")
            
            # Display statistics table
            display_player_statistics_table(rated_stats)
            st.markdown("---")
            
            # Visualizations section
            st.subheader("Performance Visualizations")
            
            # Rating comparison chart
            st.plotly_chart(
                create_rating_comparison_chart(rated_stats),
                width='stretch'
            )
            
            # Two-column layout for additional charts
            col1, col2 = st.columns(2)
            
            with col1:
                # K/D vs ADR scatter plot
                st.plotly_chart(
                    create_kd_comparison_chart(rated_stats),
                    width='stretch'
                )
            
            with col2:
                # Player selector for detailed analysis
                selected_player = st.selectbox(
                    "Select player for detailed analysis:",
                    options=rated_stats['player_name'].tolist()
                )
                
                # Radar chart for selected player
                st.plotly_chart(
                    create_rating_components_chart(rated_stats, selected_player),
                    width='stretch'
                )
            
            st.markdown("---")

            # Advanced Analytics Section
            st.subheader("🔍 Advanced Analytics")

            # Create tabs for different analysis types
            tab1, tab2, tab3 = st.tabs(["Round by Round", "Weapon Usage", "Performance Trends"])

            with tab1:
                st.plotly_chart(
                    create_round_by_round_chart(parser, selected_player),
                    width='stretch'
                )

            with tab2:
                st.plotly_chart(
                    create_weapon_usage_chart(parser, selected_player),
                    width='stretch'
                )

            with tab3:
                st.plotly_chart(
                    create_performance_trends_chart(parser, selected_player),
                    width='stretch'
                )

            st.markdown("---")

            # Export section
            export_data_section(parser, rated_stats)
            
    else:
        # Welcome screen when no file is uploaded
        st.info("Upload a CS2 demo file from the sidebar to begin analysis")
        
        # Feature showcase
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
                ### Comprehensive Stats
                - K/D Ratio & ADR
                - Headshot Percentage
                - Multi-kill Analysis
                - Round-by-Round Analysis
            """)

        with col2:
            st.markdown("""
                ### 🎯 Advanced Rating
                - Weighted Performance Metrics
                - Customizable Rating Formula
                - Skill Rank Classification
                - Component Breakdown
            """)

        with col3:
            st.markdown("""
                ### Rich Visualizations
                - Interactive Charts
                - Performance Comparison
                - Weapon Usage Statistics
                - Performance Trends
            """)


if __name__ == "__main__":
    main()
