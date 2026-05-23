"""Runtime configuration for Grand Sumo."""
import os
from pathlib import Path

# Default vault path — users can override via env var or the GUI
DEFAULT_VAULT_PATH = Path(os.environ.get(
    "GRAND_SUMO_VAULT",
    r"C:\Users\jacka\OneDrive\Documents\GitHub\grand-sumo\data"
))

# Current basho in YYYYMM format
CURRENT_BASHO: int = 202605
