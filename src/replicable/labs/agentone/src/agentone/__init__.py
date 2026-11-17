"""Load <lab>/.env once for every entry point (cli, loops, harnesses, evals). Real env vars win."""
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
