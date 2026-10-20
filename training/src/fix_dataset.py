
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "training" / "data" / "intents.csv"

# Thu doc file voi UTF-8 truoc
try:
    df = pd.read_csv(DATA_PATH, encoding="utf-8")
except UnicodeDecodeError:
    df = pd.read_csv(DATA_PATH, encoding="cp1252")

print("Cac cot:", df.columns.tolist())
print("Tong so dong:", len(df))
print("\nVi du du lieu:")
print(df.head(5).to_string(index=False))
