"""Run with: python -m streamlit run app.py"""
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))

from ui import main

main()
