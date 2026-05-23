import os
import time
import urllib.request
import zipfile
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import LogNorm
from multiprocessing import Pool, cpu_count
from functools import partial

# ==========================================
# 1. DESCARGA DEL SHAPEFILE DE ZONAS (Se mantiene igual)
# ==========================================
def obtener_shapefile_zonas():
    os.makedirs('taxi_zones', exist_ok=True)
    shapefile_path = 'taxi_zones/taxi_zones.shp'
    
    if not os.path.exists(shapefile_path):
        print("📥 Descargando Shapefile de zonas de Nueva York...")
        url = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
        zip_path = "taxi_zones/taxi_zones.zip"
        
        # Generamos una petición con cabecera de navegador real (Chrome en Windows)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        
        try:
            # Descarga del archivo usando bloques de bytes seguros
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                out_file.write(response.read())
                
            # Extracción del ZIP dentro de la carpeta designada
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall('./taxi_zones/')
            print("✅ Zonas descargadas y extraídas.")
        except Exception as e:
            print(f"❌ Error crítico al descargar el mapa geográfico: {e}")
            exit()
    
    gdf_zonas = gpd.read_file(shapefile_path)
    gdf_zonas = gdf_zonas.to_crs(epsg=3857)
    return gdf_zonas
# ==========================================
# 2. RENDERIZADO OPTIMIZADO POR HORA
# ==========================================
def renderizar_una_hora(hora, gdf_zonas, conteo_viajes, vmax_global):
    """Esta función pinta y guarda el mapa de una hora específica de forma aislada."""
    print(f"🎨 Dibujando mapa para la hora: {hora:02d}:00...")
    
    # 1. Filtrar los datos de esta hora específica
    datos_hora = conteo_viajes[conteo_viajes['hour'] == hora]
    
    # 2. Hacer el JOIN con el mapa usando las columnas correctas
    gdf_hora = gdf_zonas.merge(datos_hora, left_on='LocationID', right_on='LocationID', how='left')
    
    # 3. Configurar la figura de Matplotlib
    fig, ax = plt.subplots(figsize=(12, 12), dpi=120)
    
    # 4. Pintar la coropleta
    gdf_hora.plot(
        column='trip_count',
        ax=ax,
        cmap=plt.cm.hot,
        norm=LogNorm(vmin=1, vmax=vmax_global),
        alpha=0.8,
        edgecolor='black',
        linewidth=0.3,
        missing_kwds={'color': 'none'} # Zonas sin viajes quedan transparentes
    )
    
    # 5. Agregar el mapa base oscuro (CartoDB DarkMatter)
    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, crs=gdf_hora.crs.to_string(), attribution=False)
    except Exception as e:
        print(f"⚠️ Alerta en hora {hora:02d}: No se pudo descargar el mapa base de internet (usando fondo plano). Err: {e}")
    
    # 6. Encuadre estricto sobre Nueva York
    ax.set_xlim(-8250000, -8210000)
    ax.set_ylim(4960000, 4995000)
    ax.axis('off')
    
    # 7. Agregar etiqueta de tiempo elegante
    plt.text(0.05, 0.95, f'Hora: {hora:02d}:00', transform=ax.transAxes, 
             fontsize=24, color='white', fontweight='bold', 
             bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))
    
    # 8. Guardar el PNG en la carpeta output
    nombre_archivo = f"output/zonas_hora_{hora:02d}.png"
    plt.savefig(nombre_archivo, bbox_inches='tight', pad_inches=0, facecolor='black')
    plt.close(fig)
    return f"✅ Mapa {hora:02d} guardado."

# ==========================================
# 3. ORQUESTADOR DE VISUALIZACIÓN
# ==========================================
if __name__ == '__main__':
    os.makedirs('output', exist_ok=True)
    start_total = time.time()
    
    # 1. Cargar el mapa de Nueva York
    gdf_zonas = obtener_shapefile_zonas()
    
    # 2. Cargar el CSV ligero generado por la Pareja 2
    ruta_csv = "output/conteo_viajes_global_2024_2025.csv"
    if not os.path.exists(ruta_csv):
        print(f"❌ Error: No se encuentra el archivo {ruta_csv}. La Pareja 2 debe ejecutar su pipeline primero.")
        exit()
        
    print("📈 Cargando datos consolidados de viajes...")
    conteo_viajes = pd.read_csv(ruta_csv)
    
    # 3. Calcular el límite máximo de la escala de colores (consistente para las 24 horas)
    vmax_global = conteo_viajes['trip_count'].quantile(0.99)
    if vmax_global < 2: vmax_global = 10
    
    print(f"🌍 Preparando renderizado paralelo en {cpu_count()} núcleos...")
    
    # 4. PARALELIZACIÓN: Configuramos la función para que acepte los parámetros fijos
    funcion_parcial = partial(renderizar_una_hora, gdf_zonas=gdf_zonas, conteo_viajes=conteo_viajes, vmax_global=vmax_global)
    
    # Lanzamos el Pool para procesar las 24 horas concurrentemente
    horas = list(range(24))
    with Pool(processes=cpu_count()) as pool:
        resultados = pool.map(funcion_parcial, horas)
        
    print("\n" + "\n".join(resultados))
    print(f"⏱️ TIEMPO TOTAL DE MAPEO: {time.time() - start_total:.2f} segundos")
    print("🎉 ¡Todos los mapas de calor dinámicos para Coca-Cola han sido generados en 'output/'!")