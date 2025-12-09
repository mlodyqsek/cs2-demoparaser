# 🎯 CS2 Demo Analyzer - Leetify Style

A professional Counter-Strike 2 demo analysis application built with Python and Streamlit, featuring comprehensive player statistics, interactive visualizations, and a customizable rating system.

![CS2 Demo Analyzer](https://img.shields.io/badge/CS2-Demo%20Analyzer-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-Latest-orange?style=for-the-badge)

Warning !!! if you wanna upload bigger demos use --server.maxUploadSize 2048 (or whatever size you want)
example  
streamlit run frontend/app.py  --server.maxUploadSize 2048


## ✨ Features

### 📊 Comprehensive Statistics
- **K/D Ratio** - Kill to death ratio analysis
- **HS% (Headshot Percentage)** - Accuracy measurement
- **ADR (Average Damage per Round)** - Damage efficiency
- **Multi-Kill Score** - Performance in rapid eliminations
- **Clutch Score** - Performance in 1vX situations
- **Crosshair Placement & Accuracy** - Shooting precision metrics
- **Time-to-Damage** - Reaction time analysis

### 🎯 Advanced Rating System
- **Weighted Rating Algorithm** - Customizable scoring system
- **Real-time Weight Adjustment** - Fine-tune rating parameters
- **Detailed Breakdown** - See how each metric contributes to rating
- **Percentile Rankings** - Compare players across matches

### 📈 Interactive Visualizations
- **Player Rating Distribution** - Histogram of team performance
- **K/D vs Rating Scatter Plot** - Performance correlation analysis
- **Rating Component Breakdown** - Bar charts showing metric contributions
- **Kill/Death Heatmaps** - Spatial analysis of engagements
- **Performance Trends** - Round-by-round progression

### 💾 Data Export
- **CSV Export** - Spreadsheet-compatible data
- **JSON Export** - Structured data for further analysis
- **Automated Saving** - Results saved to `/results` directory

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Counter-Strike 2 demo files (.dem format)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/cs2-demo-analyzer.git
   cd cs2-demo-analyzer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run frontend/app.py
   ```

4. **Open your browser** and navigate to `http://localhost:8501`

## 📖 Usage Guide

### Step 1: Upload Demo File
- Use the sidebar file uploader to select your `.dem` file
- The application will automatically parse the demo and extract statistics
- Processing time depends on demo length and complexity

### Step 2: Explore Overview
- View match summary with total players, average rating, and key metrics
- Browse the player table to see all participants' statistics

### Step 3: Analyze Individual Players
- Select a player from the dropdown in the sidebar
- Examine detailed metrics and rating breakdown
- View performance visualizations and trends

### Step 4: Customize Rating System
- Expand the "Rating Configuration" section in the sidebar
- Adjust weights for different performance metrics
- See real-time updates to ratings and rankings

### Step 5: Export Results
- Use the export buttons in the sidebar to save data
- CSV files are suitable for spreadsheet analysis
- JSON files preserve full data structure for programmatic use

## Project Structure

```
cs2-demo-analyzer/
├── backend/
│   ├── parser.py          # Demo file parsing and statistics extraction
│   └── rating.py          # Player rating calculation system
├── frontend/
│   └── app.py             # Streamlit web application
├── data/                  # Demo files directory
├── results/               # Exported statistics and reports
├── notebooks/             # Jupyter notebooks for analysis
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Configuration

### Rating Weights
The rating system uses the following default weights:
- K/D Ratio: 25%
- Headshot %: 20%
- ADR: 20%
- Multi-Kill Score: 15%
- Clutch Score: 20%

Weights can be adjusted in real-time through the Streamlit interface.

### Demo Parsing
The application uses `demoparser2` for efficient demo parsing:
- Supports all CS2 demo formats
- Extracts player, event, and tick data
- Optimized for performance with large demo files

## 📊 Technical Details

### Backend Architecture
- **parser.py**: Handles demo file I/O and statistical calculations
- **rating.py**: Implements weighted rating algorithm with normalization

### Frontend Features
- **Responsive Design**: Works on desktop and mobile devices
- **Interactive Charts**: Built with Plotly for rich visualizations
- **Real-time Updates**: Dynamic content based on user selections
- **Modern UI**: Clean, professional interface inspired by Leetify

### Data Processing
- **Efficient Parsing**: Optimized algorithms for large demo files
- **Memory Management**: Streaming processing for minimal RAM usage
- **Error Handling**: Robust error recovery and user feedback

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run the development server
streamlit run frontend/app.py

## 🙏 Acknowledgments

- **demoparser2** - For providing excellent demo parsing capabilities
- **Streamlit** - For the amazing web app framework
- **Plotly** - For interactive data visualizations


---

**Happy analyzing! 🎯**

**Note**: This project is not affiliated with Valve Corporation or Counter-Strike. All product names, logos, and brands are property of their respective owners.