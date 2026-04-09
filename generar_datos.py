import pandas as pd
import json
import os
import shutil
import stat
import warnings
import time

# Suppress warnings
warnings.filterwarnings("ignore")

# Configuración de Archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
API_DIR = os.path.join(DOCS_DIR, 'api')
DETAILS_DIR = os.path.join(API_DIR, 'details')
INDEX_DIR = os.path.join(API_DIR, 'index')
MAP_DIR = os.path.join(API_DIR, 'map')

# Rutas de entrada
INPUT_DIR = BASE_DIR
FILE_LEVANTAR = os.path.join(INPUT_DIR, 'Levantar.xlsx')
FILE_TRAFOS = os.path.join(INPUT_DIR, 'Tranformadores.xlsx')
FILE_CLIENTES = os.path.join(INPUT_DIR, 'Clientes.xlsx')

def setup_directories():
    def remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if os.path.exists(API_DIR):
        print(f"Limpiando directorio {API_DIR}...")
        try:
            shutil.rmtree(API_DIR, onexc=remove_readonly)
        except PermissionError:
            print("AVISO: No se pudo eliminar el directorio completo (posiblemente archivos en uso).")
            print("Intentando limpiar archivos individuales...")
            # Fallback: intentar borrar lo que se pueda
            for root, dirs, files in os.walk(API_DIR, topdown=False):
                for name in files:
                    try:
                        p = os.path.join(root, name)
                        os.chmod(p, stat.S_IWRITE)
                        os.remove(p)
                    except: pass
                for name in dirs:
                    try: os.rmdir(os.path.join(root, name))
                    except: pass
    
    os.makedirs(DETAILS_DIR, exist_ok=True)
    os.makedirs(INDEX_DIR, exist_ok=True)
    os.makedirs(MAP_DIR, exist_ok=True)
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
    data_levantar = {}
    codigos_levantar = set()
    try:
        # Levantar: Sheet 'BDD', Columns for missing info fallback
        cols_levantar = ['CODIGO_TRAFO', 'MATRICULA_CT', 'MATRICULA_TRAFO', 'POTENCIA_NOMINAL_KVA']
        # Check if columns exist (flexible) - based on diagnosis they do exist
        df_levantar = pd.read_excel(FILE_LEVANTAR, sheet_name='BDD', usecols=cols_levantar)
        
        # Fill NaNs
        df_levantar = df_levantar.fillna('')
        
        for _, row in df_levantar.iterrows():
            code = clean_code(row['CODIGO_TRAFO'])
            if code:
                codigos_levantar.add(code)
                data_levantar[code] = {
                    'MATRICULA_CT': clean_code(row['MATRICULA_CT']),
                    'MATRICULA_TRAFO': clean_code(row['MATRICULA_TRAFO']),
                    'POTENCIA_NOMINAL_KVA': clean_code(row['POTENCIA_NOMINAL_KVA'])
                }

        print(f"Códigos a levantar cargados: {len(codigos_levantar)}")
    except Exception as e:
        print(f"ERROR leyendo Levantar.xlsx: {e}")
        return

    print("=== PROCESANDO TRANFORMADORES.xlsx ===")
    df_trafos = None
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
    actual_cols = df_clientes.columns.tolist()
    
    # Group clients
    cols_to_keep = ['CODIGO_TRANSFORMADOR'] + [c for c in required_client_cols if c in actual_cols]
    
    clientes_por_trafo = df_clientes[cols_to_keep].groupby('CODIGO_TRANSFORMADOR').apply(
        lambda x: x.fillna('').to_dict(orient='records')
    ).to_dict()

    search_index = {}
    processed_codes = set()
    
    # Process Transformers from Tranformadores.xlsx
    cols_trafo_save = ['CODIGO_TRANSFORMADOR', 'MATRÍCULA CT', 'MATRÍCULA_TRANSFORMADOR', 'MATRÍCULA_CENSO', 'DIRECCIÓN TRAFO', 'POTENCIA_NOMINAL', 'LEVANTAR_STATUS', 'LATITUD', 'LONGITUD', 'MODELO', 'TIPO CT', 'TIPO CONEXION', 'DEPARTAMENTO TRAFO']
    cols_trafo_save = [c for c in cols_trafo_save if c in df_trafos.columns or c in ['LEVANTAR_STATUS', 'LATITUD', 'LONGITUD', 'MODELO', 'TIPO CT', 'TIPO CONEXION', 'DEPARTAMENTO TRAFO']]


    count = 0
    print("  Generando desde Tranformadores.xlsx...")
    for _, row in df_trafos.iterrows():
        cod_trafo = row['CODIGO_TRANSFORMADOR']
        if not cod_trafo: continue
        
        processed_codes.add(cod_trafo)

        # Prepare data
        data = {col: str(row[col]) if not pd.isna(row[col]) else "" for col in cols_trafo_save}
        
        # Enrich with Levantar.xlsx data if fields are empty
        if cod_trafo in codigos_levantar:
            lev_info = data_levantar.get(cod_trafo, {})
            if not data.get('MATRÍCULA CT', '').strip():
                data['MATRÍCULA CT'] = lev_info.get('MATRICULA_CT', '')
            if not data.get('MATRÍCULA_TRANSFORMADOR', '').strip():
                data['MATRÍCULA_TRANSFORMADOR'] = lev_info.get('MATRICULA_TRAFO', '')
            if not data.get('POTENCIA_NOMINAL', '').strip():
                data['POTENCIA_NOMINAL'] = lev_info.get('POTENCIA_NOMINAL_KVA', '')
        
        # Add clients
        clients = clientes_por_trafo.get(cod_trafo, [])
        data['CLIENTES'] = clients
        data['TOTAL_CLIENTES'] = len(clients)

        # Write JSON
        try:
            with open(os.path.join(DETAILS_DIR, f"{cod_trafo}.json"), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass

        # Update Index
        keys = []
        if 'CODIGO_TRANSFORMADOR' in row: keys.append(row['CODIGO_TRANSFORMADOR'])
        if 'MATRÍCULA CT' in row: keys.append(row['MATRÍCULA CT'])
        if 'MATRÍCULA_TRANSFORMADOR' in row: keys.append(row['MATRÍCULA_TRANSFORMADOR'])
        if 'MATRÍCULA_CENSO' in row: keys.append(row['MATRÍCULA_CENSO'])
        
        for c in clients:
            if c.get('MEDIDOR'):
                keys.append(c['MEDIDOR'])
                # Add base medidor if it has a hyphen
                if '-' in c['MEDIDOR']:
                    keys.append(c['MEDIDOR'].split('-')[0])
            if c.get('NIC'): keys.append(c['NIC'])
        
        for k in keys:
            k_clean = clean_code(k)
            if k_clean:
                k_upper = k_clean.upper()
                if k_upper in search_index:
                    # Si ya existe, nos aseguramos que sea una lista de IDs únicos
                    current_val = search_index[k_upper]
                    if isinstance(current_val, list):
                        if cod_trafo not in current_val:
                            current_val.append(cod_trafo)
                    else:
                        if current_val != cod_trafo:
                            search_index[k_upper] = [current_val, cod_trafo]
                else:
                    search_index[k_upper] = cod_trafo
        
        count += 1
        if count % 5000 == 0:
            print(f"    Procesados {count}...")

    # Process Missing Transformers from Levantar.xlsx
    missing_codes = codigos_levantar - processed_codes
    print(f"  Procesando {len(missing_codes)} transformadores faltantes desde Levantar.xlsx...")
    
    for cod_trafo in missing_codes:
        info = data_levantar.get(cod_trafo, {})
        clients = clientes_por_trafo.get(cod_trafo, [])
        
        # Determine Address from clients if available
        direccion = ""
        if clients and len(clients) > 0:
             # Try to get address from first client
             direccion = clients[0].get('DIRECCION_CLIENTE', '')

        data = {
            'CODIGO_TRANSFORMADOR': cod_trafo,
            'MATRÍCULA CT': info.get('MATRICULA_CT', ''),
            'MATRÍCULA_TRANSFORMADOR': info.get('MATRICULA_TRAFO', ''),
            'MATRÍCULA_CENSO': '', # Not in Levantar column
            'DIRECCIÓN TRAFO': direccion,
            'POTENCIA_NOMINAL': info.get('POTENCIA_NOMINAL_KVA', ''),
            'LEVANTAR_STATUS': 'LEVANTAR', # By definition
            'LATITUD': '',
            'LONGITUD': '',
            'MODELO': '',
            'TIPO CT': '',
            'TIPO CONEXION': '',
            'DEPARTAMENTO TRAFO': '',
            'CLIENTES': clients,
            'TOTAL_CLIENTES': len(clients)
        }

        # Write JSON
        try:
            with open(os.path.join(DETAILS_DIR, f"{cod_trafo}.json"), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass
            
        # Update Index
        keys = [cod_trafo, info.get('MATRICULA_CT', ''), info.get('MATRICULA_TRAFO', '')]
        
        for c in clients:
            if c.get('MEDIDOR'):
                keys.append(c['MEDIDOR'])
                # Add base medidor if it has a hyphen
                if '-' in c['MEDIDOR']:
                    keys.append(c['MEDIDOR'].split('-')[0])
            if c.get('NIC'): keys.append(c['NIC'])
            
        for k in keys:
            k_clean = clean_code(k)
            if k_clean:
                k_upper = k_clean.upper()
                if k_upper in search_index:
                    current_val = search_index[k_upper]
                    if isinstance(current_val, list):
                        if cod_trafo not in current_val:
                            current_val.append(cod_trafo)
                    else:
                        if current_val != cod_trafo:
                            search_index[k_upper] = [current_val, cod_trafo]
                else:
                    search_index[k_upper] = cod_trafo
        
        count += 1

    # Save Index
    with open(os.path.join(INDEX_DIR, "search_index.json"), 'w', encoding='utf-8') as f:
        json.dump(search_index, f, ensure_ascii=False)

    print("=== GENERANDO ÍNDICE ESPACIAL (MAPA) ===")
    # Agrupar todos los transformadores con coordenadas en celdas geográficas
    # Usaremos una precisión de 0.01 grados (~1.1km) para las celdas
    spatial_index = {} # {(grid_lat, grid_lon): [list of trafos]}

    def get_trafo_map_data(df):
        for _, row in df.iterrows():
            lat = row.get('LATITUD')
            lon = row.get('LONGITUD')
            if pd.isna(lat) or pd.isna(lon): continue
            
            try:
                lat_f = float(str(lat).replace(',', '.'))
                lon_f = float(str(lon).replace(',', '.'))
                
                # Truncar a 2 decimales para la rejilla
                grid_lat = round(lat_f, 2)
                grid_lon = round(lon_f, 2)
                
                trafo_data = {
                    'id': clean_code(row['CODIGO_TRANSFORMADOR']),
                    'ct': clean_code(row.get('MATRÍCULA CT', '')),
                    'lat': lat_f,
                    'lon': lon_f,
                    'status': 'LEVANTAR' if row['CODIGO_TRANSFORMADOR'] in codigos_levantar else 'NO LEVANTAR'
                }
                
                key = (grid_lat, grid_lon)
                if key not in spatial_index:
                    spatial_index[key] = []
                spatial_index[key].append(trafo_data)
            except (ValueError, TypeError):
                continue

    get_trafo_map_data(df_trafos)
    
    # También procesar los faltantes de Levantar? 
    # (Usualmente no tienen coordenadas en Levantar.xlsx, pero por si acaso)
    # En este script, los faltantes de Levantar no tienen Lat/Lon mapeado.

    print(f"  Guardando {len(spatial_index)} celdas geográficas...")
    for (glat, glon), trafos in spatial_index.items():
        filename = f"tile_{glat}_{glon}.json"
        with open(os.path.join(MAP_DIR, filename), 'w', encoding='utf-8') as f:
            json.dump(trafos, f, ensure_ascii=False)

    print(f"\n--- PROCESO TERMINADO ---")
    print(f"Total transformadores (incluyendo faltantes): {count}")
    print(f"Entradas en índice: {len(search_index)}")

if __name__ == "__main__":
    process_data()
