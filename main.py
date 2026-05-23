import os
import glob
import time
import urllib.request
import zipfile
from multiprocessing import Pool, cpu_count
from functools import partial
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import LogNorm
from tqdm import tqdm

# ==========================================
# CONFIGURACIONES Y ESQUEMAS (TLC NYC)
# ==========================================
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

# ==========================================
# FUNCIONES DE LA FASE 1: PROCESAMIENTO PARQUET
# ==========================================
def procesar_un_archivo(file_path):
    """Función aislada para procesar un archivo Parquet en un núcleo de CPU."""
    import pyarrow.parquet as pq  # Importación local segura para multiprocesamiento
    tipo = identificar_tipo_vehiculo(file_path)
    if not tipo:
        return None
        
    mapeo = SCHEMA_MAPPING[tipo]
    columnas_requeridas = [mapeo['pickup_col'], mapeo['zone_col']]
    
    try:
        # Lectura selectiva desde disco
        table = pq.read_table(file_path, columns=columnas_requeridas)
        df = table.to_pandas()
        
        # Homologar nombres
        df = df.rename(columns={
            mapeo['pickup_col']: 'pickup_datetime',
            mapeo['zone_col']: 'LocationID'
        })
        
        # Procesar fechas y extraer hora
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
        df['hour'] = df['pickup_datetime'].dt.hour
        df['trip_count'] = 1
        
        # Reducción local inmediata
        resumen_mensual = df.groupby(['hour', 'LocationID'], as_index=False)['trip_count'].sum()
        return resumen_mensual
        
    except Exception as e:
        print(f"\n❌ Error procesando {os.path.basename(file_path)}: {e}")
        return None

# ==========================================
# FUNCIONES DE LA FASE 2: DESCARGA Y MAPEO
# ==========================================
def obtener_shapefile_zonas():
    # Ruta directa al archivo que ya descargaste y extrajiste manualmente
    shapefile_path = 'taxi_zones/taxi_zones.shp'
    
    if not os.path.exists(shapefile_path):
        print("❌ Error: No encontré 'taxi_zones/taxi_zones.shp'.")
        print("Asegúrate de haber descomprimido el ZIP manualmente dentro de esa carpeta.")
        exit()
        
    print("✅ Archivo geográfico encontrado localmente. Cargando mapa...")
    gdf_zonas = gpd.read_file(shapefile_path)
    gdf_zonas = gdf_zonas.to_crs(epsg=3857) # Coordenadas Web Mercator
    return gdf_zonas

def renderizar_una_hora(hora, gdf_zonas, conteo_viajes, vmax_global):
    """Pinta y guarda el mapa de una hora específica en un núcleo de CPU."""
    print(f"🎨 Dibujando mapa para la hora: {hora:02d}:00...")
    
    datos_hora = conteo_viajes[conteo_viajes['hour'] == hora]
    gdf_hora = gdf_zonas.merge(datos_hora, left_on='LocationID', right_on='LocationID', how='left')
    
    fig, ax = plt.subplots(figsize=(12, 12), dpi=120)
    
    gdf_hora.plot(
        column='trip_count',
        ax=ax,
        cmap=plt.cm.hot,
        norm=LogNorm(vmin=1, vmax=vmax_global),
        alpha=0.8,
        edgecolor='black',
        linewidth=0.3,
        missing_kwds={'color': 'none'}
    )
    
    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, crs=gdf_hora.crs.to_string(), attribution=False)
    except Exception as e:
        pass # Si falla internet en un nodo, continúa con fondo plano oscuro
    
    ax.set_xlim(-8250000, -8210000)
    ax.set_ylim(4960000, 4995000)
    ax.axis('off')
    
    plt.text(0.05, 0.95, f'Hora: {hora:02d}:00', transform=ax.transAxes, 
             fontsize=24, color='white', fontweight='bold', 
             bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))
    
    nombre_archivo = f"output/zonas_hora_{hora:02d}.png"
    plt.savefig(nombre_archivo, bbox_inches='tight', pad_inches=0, facecolor='black')
    plt.close(fig)
    return f"✅ Mapa {hora:02d}:00 guardado."

# ==========================================
# PIPELINE PRINCIPAL UNIFICADO
# ==========================================
# ==========================================
# PIPELINE PRINCIPAL UNIFICADO
# ==========================================
if __name__ == '__main__':
    start_total = time.time()
    os.makedirs('output', exist_ok=True)
    nucleos = cpu_count()
    
    print(f"🚀 Sistema Inicializado. Detectados {nucleos} núcleos de CPU.")
    print("--------------------------------------------------")
    
    # ----------------------------------------------
    # 🌐 FASE 0: EXTRACCIÓN Y WEB SCRAPING AUTÓNOMO
    # ----------------------------------------------
    print("🌐 [FASE 0] Iniciando extracción y descarga automática desde la TLC...")
    try:
        # Importamos el script de scraping de tus compañeros de forma dinámica
        import webscrapping
        
        # Ejecutamos su función principal (descargará los datos en 'input/' usando sus 4 hilos)
        webscrapping.main()
        print("✅ Fase 0: Descargas e inspección web finalizadas con éxito.")
    except Exception as e:
        print(f"⚠️ Alerta en Fase 0: Ocurrió un detalle durante el scraping: {e}")
        print("Intentando continuar con los archivos locales disponibles en 'input/'...")
        
    print("--------------------------------------------------")
    
    # ----------------------------------------------
    # FASE 1: PROCESAMIENTO MAP-REDUCE PARALELO (Pareja 2)
    # ----------------------------------------------
    archivos_parquet = glob.glob("input/*.parquet")
    if not archivos_parquet:
        print("❌ Error: No se encontraron archivos .parquet en la carpeta 'input/'.")
        exit()
        
    print(f"📦 [FASE 1] Procesando en paralelo {len(archivos_parquet)} archivos masivos...")
    # ... (Todo el resto de tu código de procesamiento y Fase 2 se queda exactamente igual)