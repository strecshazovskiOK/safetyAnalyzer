# Safety Report Analyzer

A comprehensive aviation safety report analysis tool that uses AI-powered analysis methods to process PDF safety reports and generate structured recommendations.

## Features

- **Multiple Analysis Methods**: Five Whys, Fishbone, Bowtie, and Fault Tree analysis
- **AI-Powered Analysis**: Uses OpenAI GPT-4 for intelligent report analysis
- **Aviation-Specific**: Aligned with ICAO and Transport Canada standards
- **Multi-Language Support**: English and French output
- **Auto-Classification**: Automatic occurrence classification using Transport Canada CADORS/SMS standards
- **Similar Case Search**: Find similar reports using vector similarity search
- **Local Database**: SQLite database for storing and retrieving analysis results
- **Export Capabilities**: Export reports as PDF or Excel/CSV
- **Modern GUI**: Clean, dark-themed interface built with tkinter

## 🚀 Quick Start

### 🌐 Web Version (Recommended)
**No installation required!** Use the web version deployed on Vercel:
- Visit: [Your Vercel URL]
- Upload PDF files directly in your browser
- Works on any device with internet connection

### 🖥️ Desktop Version
**Download and run locally** for offline use:

**Windows:**
1. Download ZIP from GitHub
2. Extract files
3. Double-click `install.bat`
4. Double-click `run.bat`

**Mac/Linux:**
1. Download ZIP from GitHub
2. Extract files
3. Run: `chmod +x install.sh run.sh`
4. Run: `./install.sh`
5. Run: `./run.sh`

### 📋 Requirements
- Python 3.8+ installed
- OpenAI API key
- Internet connection for AI analysis

### 🔧 API Key Setup
Create `config.py` file:
```python
API_KEY = "your-openai-api-key-here"
```

📥 **For detailed download instructions, see [DOWNLOAD.md](DOWNLOAD.md)**

## Usage

1. Run the application:
```bash
python gui.py
```

2. Select a PDF safety report file
3. Choose your analysis method and output language
4. Click "Run Analysis" to generate the report
5. Use the feedback system to refine the analysis
6. Export the final report in your preferred format

## Analysis Methods

- **Five Whys**: Systematic root cause analysis through iterative questioning
- **Fishbone**: Cause-and-effect diagram analysis
- **Bowtie**: Risk assessment with preventive and mitigative barriers
- **Fault Tree**: Logical analysis of system failures

## Classification System

The tool automatically classifies incidents according to Transport Canada standards:
- **Occurrence Types**: Comprehensive list of aviation incident types
- **Severity Levels**: Minor, Moderate, Major, Critical
- **Probability Levels**: Rare, Unlikely, Possible, Likely, Frequent

## Database Features

- Local SQLite database for storing analysis results
- Vector similarity search for finding similar cases
- Version control for report updates
- Export capabilities for data analysis

## Dependencies

- **Core**: OpenAI API, PyMuPDF (PDF processing), NumPy
- **Optional**: ReportLab (PDF export), Pandas (Excel export)
- **Built-in**: tkinter (GUI), sqlite3 (database)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source. Please ensure you have proper OpenAI API access and follow their usage policies.

## Support

For issues and questions, please open an issue in the GitHub repository.
