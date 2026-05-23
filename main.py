import os
import glob
import time
from multiprocessing import Pool, cpu_count
import pandas as pd
import pyarrow.parquet as pq
from tqdm import tqdm

# Diccionario para mapear los nombres de las columnas de la TLC de Nueva York
SCHEMA_MAPPING = {
    'yellow': {'pickup_col': 'tpep_pickup_datetime', 'zone_col': 'PULocationID'},
    'green': {'pickup_col': 'lpep_pickup_datetime', 'zone_col': 'PULocationID'},
    'fhvhv': {'pickup_col': 'pickup_datetime', 'zone_col': 'PULocationID'}
}

def identificar_tipo_vehiculo(file_path):
    filename = os.path.basename(file_path).lower()
    if 'yellow' in filename: return 'yellow'
    if 'green' in filename: return 'green'
    if 'fhvhv' in filename: return 'fhvhv'
    return None

def procesar_un_archivo(file_path):
    """Esta función la ejecuta un núcleo de CPU independiente por cada archivo."""
    tipo = identificar_tipo_vehiculo(file_path)
    if not tipo:
        return None
        
    mapeo = SCHEMA_MAPPING[tipo]
    columnas_requeridas = [mapeo['pickup_col'], mapeo['zone_col']]
    
    try:
        # Lectura selectiva desde disco (Solo extrae las columnas necesarias)
        table = pq.read_table(file_path, columns=columnas_requeridas)
        df = table.to_pandas()
        
        # Homologar nombres de columnas
        df = df.rename(columns={
            mapeo['pickup_col']: 'pickup_datetime',
            mapeo['zone_col']: 'LocationID'
        })
        
        # Extraer únicamente la hora del viaje (0-23)
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
        df['hour'] = df['pickup_datetime'].dt.hour
        df['trip_count'] = 1
        
        # Reducción local inmediata para no saturar la RAM
        resumen_mensual = df.groupby(['hour', 'LocationID'], as_index=False)['trip_count'].sum()
        return resumen_mensual
        
    except Exception as e:
        print(f"\n❌ Error procesando {os.path.basename(file_path)}: {e}")
        return None

if __name__ == '__main__':
    start_time = time.time()
    
    # 🌟 CORRECCIÓN DE RUTA: Buscamos en tu carpeta real llamada 'input'
    archivos_parquet = glob.glob("input/*.parquet")
    
    if not archivos_parquet:
        print("❌ No se encontraron archivos .parquet en la carpeta 'input/'.")
        print("Verifica que tus archivos estén guardados exactamente dentro de la carpeta 'input'.")
        exit()
        
    # Determinar cuántos núcleos de CPU podemos explotar en tu máquina
    nucleos = cpu_count()
    print(f"🚀 Detectados {nucleos} núcleos de CPU.")
    print(f"📦 Iniciando procesamiento en paralelo de {len(archivos_parquet)} archivos...")
    
    # Lanzar el Pool de multiprocesamiento con una barra de progreso visual
    with Pool(processes=nucleos) as pool:
        resultados = list(tqdm(
            pool.imap_unordered(procesar_un_archivo, archivos_parquet),
            total=len(archivos_parquet),
            desc="Procesando archivos"
        ))
    
    # Filtrar posibles resultados nulos por archivos corruptos
    resultados_validos = [r for r in resultados if r is not None]
    
    if not resultados_validos:
        print("❌ No se pudo procesar ningún archivo con éxito.")
        exit()
        
    print("\n🔄 Combinando y ejecutando el Reduce Global de todos los meses...")
    df_unificado = pd.concat(resultados_validos, ignore_index=True)
    
    # Agrupación final combinada de todo el histórico de datos
    df_final = df_unificado.groupby(['hour', 'LocationID'], as_index=False)['trip_count'].sum()
    
    # Guardar el CSV optimizado listo para que la Pareja 3 dibuje los mapas
    os.makedirs('output', exist_ok=True)
    ruta_salida = "output/conteo_viajes_global_2024_2025.csv"
    df_final.to_csv(ruta_salida, index=False)
    
    print(f"\n🎉 ¡Tubería completada exitosamente en {time.time() - start_time:.2f} segundos!")
    print(f"📁 Archivo consolidado guardado en: {ruta_salida}")
    print(f"📊 Filas totales enviadas al equipo de mapas: {len(df_final)}")