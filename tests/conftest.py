import sys
import os
import pytest
from dotenv import load_dotenv

# --- YEH LINE ADD KI GAYI HAI (THIS IS THE FIX) ---
# .env file se saari keys ko load karta hai, taaki tests unhein istemaal kar sakein
load_dotenv()

@pytest.fixture(scope="session", autouse=True)
def add_project_root_to_path():
    """Fixture to add the project root to the Python path."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

