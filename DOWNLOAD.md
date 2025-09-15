# 📥 Download Safety Report Analyzer

## 🌐 Web Version (Recommended)
**Use the web version** - No download required!
- Visit: [Your Vercel URL]
- Upload PDF files directly in your browser
- Works on any device with internet connection

## 🖥️ Desktop Version (For Offline Use)

### Windows Users
1. **Download the ZIP file** from GitHub
2. **Extract** the files to a folder
3. **Double-click `install.bat`** to install dependencies
4. **Double-click `run.bat`** to start the application

### Mac/Linux Users
1. **Download the ZIP file** from GitHub
2. **Extract** the files to a folder
3. **Open Terminal** in the folder
4. **Run**: `chmod +x install.sh run.sh`
5. **Run**: `./install.sh` to install dependencies
6. **Run**: `./run.sh` to start the application

### Manual Installation
```bash
# Clone or download the repository
git clone https://github.com/strecshazovskiOK/safetyAnalyzer.git
cd safetyAnalyzer

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python gui.py
```

## 📋 Requirements
- **Python 3.8+** installed on your system
- **OpenAI API Key** (set in `config.py` or environment variable)
- **Internet connection** for AI analysis

## 🔧 Setup API Key
1. Create a `config.py` file in the project folder
2. Add your OpenAI API key:
```python
API_KEY = "your-openai-api-key-here"
```

## 🚀 Features
- ✅ AI-powered safety report analysis
- ✅ Multiple analysis methods (Five Whys, Fishbone, Bowtie, Fault Tree)
- ✅ Auto-classification (Transport Canada standards)
- ✅ Multi-language support (English/French)
- ✅ Export to PDF/Excel
- ✅ Local database storage
- ✅ Similar case search

## 🆘 Troubleshooting
- **Python not found**: Install Python from https://python.org
- **Permission denied**: Run as administrator (Windows) or use `sudo` (Mac/Linux)
- **API errors**: Check your OpenAI API key in `config.py`
