import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_LEVANTAR = os.path.join(BASE_DIR, 'Levantar.xlsx')

try:
    df = pd.read_excel(FILE_LEVANTAR, sheet_name='BDD')
    print("Columns in Levantar.xlsx (BDD):")
    for col in df.columns:
        print(f" - {col}")
except Exception as e:
    print(f"Error reading file: {e}")
