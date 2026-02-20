import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_LEVANTAR = os.path.join(BASE_DIR, 'Levantar.xlsx')
FILE_TRAFOS = os.path.join(BASE_DIR, 'Tranformadores.xlsx')

TARGET_CODE = "65701527"

def clean_code(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

print(f"Checking for code: {TARGET_CODE}")

try:
    df_levantar = pd.read_excel(FILE_LEVANTAR, sheet_name='BDD', usecols=['CODIGO_TRAFO'])
    df_levantar['CODIGO_CLEAN'] = df_levantar['CODIGO_TRAFO'].apply(clean_code)
    
    found_in_levantar = df_levantar[df_levantar['CODIGO_CLEAN'] == TARGET_CODE]
    print(f"In Levantar.xlsx: {'YES' if not found_in_levantar.empty else 'NO'}")
    if not found_in_levantar.empty:
        print(f"  Raw value: {found_in_levantar.iloc[0]['CODIGO_TRAFO']}")
        print(f"  Type: {type(found_in_levantar.iloc[0]['CODIGO_TRAFO'])}")

except Exception as e:
    print(f"Error reading Levantar: {e}")

try:
    df_trafos = pd.read_excel(FILE_TRAFOS, sheet_name='TRANSFORMADOR')
    if 'CODIGO_TRANSFORMADOR' in df_trafos.columns:
        df_trafos['CODIGO_CLEAN'] = df_trafos['CODIGO_TRANSFORMADOR'].apply(clean_code)
        found_in_trafos = df_trafos[df_trafos['CODIGO_CLEAN'] == TARGET_CODE]
        print(f"In Tranformadores.xlsx: {'YES' if not found_in_trafos.empty else 'NO'}")
    else:
        print("Column CODIGO_TRANSFORMADOR not found in Trafos")

except Exception as e:
    print(f"Error reading Trafos: {e}")
