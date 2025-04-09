
# Automated Trading System - Exiting Option Positions

## Overview

The system automates options trading through the Alpaca API. Existing positions will be exited at predefined profit levels leaving a certain portion as runners.


![Python Version](https://img.shields.io/badge/Python-3.12%2B-green)
<!-- ![License](https://img.shields.io/badge/License-MIT-yellow) -->

## 📦 Prerequisites

- Python 3.12+
- pip (Python Package Manager)
- Virtual Environment (recommended)

## 🔧 Installation

1.Clone the repository in a desired folder (or alternatively download from the same URL):

```bash
git clone https://github.com/rvanhezel/alpaca_closing_option_positions.git
cd alpaca_closing_option_positions
```

2.Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3.Install dependencies:

```bash
pip install -r requirements.txt
```

4.Set up environment variables for Alpaca:

```bash
# Create a .env file in the project root directory with:
ALPACA_KEY = your_alpaca_key
ALPACA_SECRET = your_alpaca_secret_key
```

## 🎬 Running the Application

```bash
# Run the app
python main.py
```
