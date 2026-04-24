"""Create database tables from models. Run once after creating the Postgres database."""
import sys
from pathlib import Path

# Ensure backend is on path when run as script (e.g. python scripts/init_db.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db

if __name__ == "__main__":
    init_db()
    print("Tables created.")
