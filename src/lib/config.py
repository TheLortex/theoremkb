import os, sys
from sqlalchemy import create_engine

HOME = os.getenv("HOME")
USER = os.getenv("USER")

if USER == "lpluvina":
    base = f"{HOME}"
elif USER == "lucas":
    base = f"{HOME}/stage"
else:
    print("config/__init__.py: error: set-up your user here.", file=sys.stderr)
    exit(1)

# databases/datasets
DATA_PATH = f"{HOME}/stage/tkb-data"

SQL_ENGINE = create_engine(f"sqlite:///{DATA_PATH}/tkb.sqlite")#, echo=True)

REBUILD_FEATURES = False
