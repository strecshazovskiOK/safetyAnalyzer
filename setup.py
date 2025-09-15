from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="safety-analyzer",
    version="1.0.0",
    author="Safety Analyzer Team",
    author_email="contact@example.com",
    description="AI-powered aviation safety report analysis tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/strecshazovskiOK/safetyAnalyzer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Aviation Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=0.28.0",
        "PyMuPDF>=1.23.0",
        "numpy>=1.24.0",
        "reportlab>=4.0.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "safety-analyzer=gui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt"],
    },
)
