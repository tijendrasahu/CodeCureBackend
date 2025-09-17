import sys
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def add_project_root_to_path():
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

