import pandas as pd
import json
import os
import shutil
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Configuración de Archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
API_DIR = os.path.join(DOCS_DIR, 'api')
DETAILS_DIR = os.path.join(API_DIR, 'details')
INDEX_DIR = os.path.join(API_DIR, 'index')

# Rutas de entrada
INPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), '')
FILE_LEVANTAR = os.path.join(INPUT_DIR, 'Levantar.xlsx')
FILE_TRAFOS = os.path.join(INPUT_DIR, 'Tranformadores.xlsx')
FILE_CLIENTES = os.path.join(INPUT_DIR, 'Clientes.xlsx')

def setup_directories():
    if os.path.exists(API_DIR):
        shutil.rmtree(API_DIR)
    os.makedirs(DETAILS_DIR, exist_ok=True)
    os.makedirs(INDEX_DIR, exist_ok=True)
    print(f"Directorios de salida preparados en {API_DIR}")

def clean_code(val):
    if pd.isna(val):
        return ""
    # Convert to string, remove decimal .0 if present
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

def process_data():
    setup_directories()

    print("=== PROCESANDO LEVANTAR.xlsx ===")
    try:
        # Levantar: Sheet 'BDD', column 'CODIGO_TRAFO'
        df_levantar = pd.read_excel(FILE_LEVANTAR, sheet_name='BDD', usecols=['CODIGO_TRAFO'])
        # Clean data
        codigos_levantar = set(df_levantar['CODIGO_TRAFO'].apply(clean_code).tolist())
        codigos_levantar.discard("") # Remove empty matches
        print(f"Códigos a levantar cargados: {len(codigos_levantar)}")
    except Exception as e:
        print(f"ERROR leyendo Levantar.xlsx: {e}")
        return

    print("=== PROCESANDO TRANFORMADORES.xlsx ===")
    try:
        df_trafos = pd.read_excel(FILE_TRAFOS, sheet_name='TRANSFORMADOR')
        # Ensure CODIGO_TRANSFORMADOR exists
        if 'CODIGO_TRANSFORMADOR' not in df_trafos.columns:
            print("ERROR: No se encontró la columna 'CODIGO_TRANSFORMADOR' en Tranformadores.xlsx")
            print("Columnas encontradas:", df_trafos.columns.tolist())
            return
            
        df_trafos['CODIGO_TRANSFORMADOR'] = df_trafos['CODIGO_TRANSFORMADOR'].apply(clean_code)
        
        # Add LEVANTAR status
        df_trafos['LEVANTAR_STATUS'] = df_trafos['CODIGO_TRANSFORMADOR'].apply(
            lambda x: 'LEVANTAR' if x in codigos_levantar else 'NO LEVANTAR'
        )
        print(f"Transformadores cargados: {len(df_trafos)}")
    except Exception as e:
        print(f"ERROR leyendo Tranformadores.xlsx: {e}")
        return

    print("=== PROCESANDO CLIENTES.xlsx (Esto puede tardar...) ===")
    try:
        # Load specific columns to save memory if possible, but we need many.
        # We will load both sheets.
        client_sheets = ['ACOSUM-MEDIDOR (1)', 'ACOSUM-MEDIDOR']
        df_list = []
        for sheet in client_sheets:
            print(f"  Leyendo hoja: {sheet}...")
            df = pd.read_excel(FILE_CLIENTES, sheet_name=sheet)
            df_list.append(df)
        
        df_clientes = pd.concat(df_list, ignore_index=True)
        
        # Normalize linking column
        if 'CODIGO_TRANSFORMADOR' not in df_clientes.columns:
             # Fallback if inconsistent naming
             if 'CODIGO_CT' in df_clientes.columns:
                 print("  Aviso: Usando 'CODIGO_CT' como llave de enlace.")
                 df_clientes.rename(columns={'CODIGO_CT': 'CODIGO_TRANSFORMADOR'}, inplace=True)
             else:
                 print("ERROR: No se encontró columna de enlace en Clientes (CODIGO_TRANSFORMADOR o CODIGO_CT)")
                 return

        df_clientes['CODIGO_TRANSFORMADOR'] = df_clientes['CODIGO_TRANSFORMADOR'].apply(clean_code)
        print(f"Total Clientes procesados: {len(df_clientes)}")
    except Exception as e:
        print(f"ERROR leyendo Clientes.xlsx: {e}")
        return

    print("=== GENERANDO JSONs ===")
    # Verify client columns exist
    required_client_cols = ['MATRÍCULA CT', 'NIU', 'NIS_RAD_1', 'NIC', 'MEDIDOR', 'DIRECCION_CLIENTE', 'NOMBRE_CLIENTE']
    # Check if they exist, specific handling for potentially garbled accents
    actual_cols = df_clientes.columns.tolist()
    # Flexible column matching could be added here if needed
    
    # Group clients
    # Optimize: Filter only needed columns before grouping
    cols_to_keep = ['CODIGO_TRANSFORMADOR'] + [c for c in required_client_cols if c in actual_cols]
    
    clientes_por_trafo = df_clientes[cols_to_keep].groupby('CODIGO_TRANSFORMADOR').apply(
        lambda x: x.fillna('').to_dict(orient='records')
    ).to_dict()

    search_index = {}
    
    # Process Transformers
    # Columns to save
    cols_trafo_save = ['CODIGO_TRANSFORMADOR', 'MATRÍCULA CT', 'MATRÍCULA_TRANSFORMADOR', 'MATRÍCULA_CENSO', 'DIRECCIÓN TRAFO', 'POTENCIA_NOMINAL', 'LEVANTAR_STATUS']
    # Filter to existing columns
    cols_trafo_save = [c for c in cols_trafo_save if c in df_trafos.columns or c == 'LEVANTAR_STATUS']

    count = 0
    for _, row in df_trafos.iterrows():
        cod_trafo = row['CODIGO_TRANSFORMADOR']
        if not cod_trafo: continue

        # Prepare data
        data = {col: str(row[col]) if not pd.isna(row[col]) else "" for col in cols_trafo_save}
        
        # Add clients
        clients = clientes_por_trafo.get(cod_trafo, [])
        data['CLIENTES'] = clients
        data['TOTAL_CLIENTES'] = len(clients)

        # Write JSON
        try:
            with open(os.path.join(DETAILS_DIR, f"{cod_trafo}.json"), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            # Handle invalid filenames
            pass

        # Update Index
        # Index keys: COIGO, MATRICULA CT, MATRICULA CENSO, MATRICULA TRANFORMADOR
        keys = []
        if 'CODIGO_TRANSFORMADOR' in row: keys.append(row['CODIGO_TRANSFORMADOR'])
        if 'MATRÍCULA CT' in row: keys.append(row['MATRÍCULA CT'])
        if 'MATRÍCULA_TRANSFORMADOR' in row: keys.append(row['MATRÍCULA_TRANSFORMADOR'])
        if 'MATRÍCULA_CENSO' in row: keys.append(row['MATRÍCULA_CENSO'])
        
        for k in keys:
            k_clean = clean_code(k)
            if k_clean:
                search_index[k_clean.upper()] = cod_trafo
        
        count += 1
        if count % 1000 == 0:
            print(f"  Procesados {count} transformadores...")

    # Save Index
    with open(os.path.join(INDEX_DIR, "search_index.json"), 'w', encoding='utf-8') as f:
        json.dump(search_index, f, ensure_ascii=False)

    print(f"\n--- PROCESO TERMINADO ---")
    print(f"Total transformadores: {count}")
    print(f"Entradas en índice: {len(search_index)}")

if __name__ == "__main__":
    process_data()
