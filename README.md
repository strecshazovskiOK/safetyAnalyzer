# 🛡️ Safety Report Analyzer

A modern web application for aviation safety report analysis using AI-powered methods to process PDF safety reports and generate structured recommendations.

## ✨ Features

- **🌐 Web-Based**: Access from any device with a browser
- **🤖 AI-Powered Analysis**: Uses OpenAI GPT-4 for intelligent report analysis
- **📊 Multiple Analysis Methods**: Five Whys, Fishbone, Bowtie, and Fault Tree analysis
- **✈️ Aviation-Specific**: Aligned with ICAO and Transport Canada standards
- **🌍 Multi-Language Support**: English and French output
- **🏷️ Auto-Classification**: Automatic occurrence classification using Transport Canada CADORS/SMS standards
- **🔍 Similar Case Search**: Find similar reports using vector similarity search
- **💾 Database Storage**: SQLite database for storing and retrieving analysis results
- **🎨 Modern UI**: Clean, responsive design with dark theme

## 🚀 Quick Start

### 🌐 Live Web Application
**No installation required!** Simply visit the deployed application:
- **Visit**: [Your Vercel URL]
- **Upload PDF** files directly in your browser
- **Select analysis method** and language
- **Get instant AI-powered results**

### 🛠️ Local Development
**For developers who want to run locally:**

1. **Clone the repository:**
```bash
git clone https://github.com/strecshazovskiOK/safetyAnalyzer.git
cd safetyAnalyzer
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variable:**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

4. **Run the application:**
```bash
python app.py
```

5. **Open browser:** Visit `http://localhost:5000`

## 📖 How to Use

1. **Visit the web application** (Vercel URL)
2. **Upload a PDF** safety report file
3. **Select analysis method** (Five Whys, Fishbone, Bowtie, or Fault Tree)
4. **Choose output language** (English or French)
5. **Click "Run Analysis"** to generate the AI-powered report
6. **Use auto-classification** to categorize the incident
7. **View results** with structured recommendations

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

## 📦 Dependencies

- **Flask**: Web framework
- **OpenAI**: AI analysis engine
- **PyMuPDF**: PDF text extraction
- **NumPy**: Vector operations for similarity search
- **SQLite3**: Database storage (built-in)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source. Please ensure you have proper OpenAI API access and follow their usage policies.

## Support

For issues and questions, please open an issue in the GitHub repository.
