import os
import requests
import threading
from bs4 import BeautifulSoup
import queue

# ================= CONFIGURACIÓN =================
URL = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"
FOLDER_DESTINO = "input"
HTML_FILE = os.path.join(FOLDER_DESTINO, "tlc_page.html")
HEADERS = {"User-Agent": "MiProyectoTLC/1.0"}

# Cantidad de descargas simultáneas (recomendado: entre 3 y 5 para no saturar el servidor)
NUM_HILOS = 4 

# Asegurarse de que la carpeta "input" exista
os.makedirs(FOLDER_DESTINO, exist_ok=True)

# Creamos una cola (queue) para administrar las descargas y un 'candado' (lock) 
# para que los mensajes en la consola (print) no se sobrepongan al escribirse al mismo tiempo.
cola_descargas = queue.Queue()
print_lock = threading.Lock()

# ================= FUNCIÓN DEL TRABAJADOR (WORKER) =================
def descargar_archivo():
    """Función que ejecutará cada hilo. Toma URLs de la cola y las descarga."""
    while True:
        # Obtenemos la siguiente URL de la fila
        url_parquet = cola_descargas.get()
        
        # Si recibimos un 'None', significa que ya no hay más trabajo y debemos cerrar el hilo
        if url_parquet is None:
            break
            
        filename = os.path.basename(url_parquet)
        filepath = os.path.join(FOLDER_DESTINO, filename)
        
        # Verificamos si el archivo ya existe
        if os.path.exists(filepath):
            with print_lock:
                print(f"[Omitido] El archivo {filename} ya existe.")
        else:
            with print_lock:
                print(f"[Iniciando] Descargando {filename}...")
            
            try:
                # Descarga real del archivo
                response = requests.get(url_parquet, headers=HEADERS, stream=True)
                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    with print_lock:
                        print(f"[Éxito] -> {filename} guardado.")
                else:
                    with print_lock:
                        print(f"[Error] -> Código {response.status_code} al descargar {filename}")
            except Exception as e:
                with print_lock:
                    print(f"[Fallo] -> Error en {filename}: {e}")
        
        # Le indicamos a la cola que hemos terminado con esta tarea
        cola_descargas.task_done()


# ================= SCRIPT PRINCIPAL =================
def main():
    html_content = None

    # 1. Intentamos leer el archivo HTML en caché o descargarlo
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            print("Leyendo archivo HTML local...")
            html_content = f.read()
    except FileNotFoundError:
        print("Consultando la página web principal...")
        response = requests.get(URL, headers=HEADERS)
        if response.status_code == 200:
            html_content = response.text
            with open(HTML_FILE, "w", encoding="utf-8") as f:
                f.write(html_content)
        else:
            print(f"Error al consultar la página: {response.status_code}")
            return

    # 2. Extraer las URLs
    parquet_urls = []
    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        contenedores_ids = ["faq2024", "faq2025"]
        
        for container_id in contenedores_ids:
            container = soup.find(id=container_id)
            if container:
                for a_tag in container.find_all("a"):
                    href = a_tag.get("href")
                    if href:
                        clean_href = href.strip() 
                        
                        if clean_href.endswith(".parquet"):
                            # Filtro de exclusión solicitado
                            if "fhvhv_tripdata_2024-01.parquet" in clean_href:
                                print(f"-> Excluyendo de la lista: {os.path.basename(clean_href)}")
                                continue
                                
                            parquet_urls.append(clean_href)

        # 3. Llenar la cola y lanzar los hilos
        total_archivos = len(parquet_urls)
        if total_archivos > 0:
            print(f"\nSe encontraron {total_archivos} archivos. Iniciando descarga en {NUM_HILOS} hilos...\n")
            
            # Colocamos todas las URLs en la fila
            for url in parquet_urls:
                cola_descargas.put(url)
                
            # Creamos e iniciamos los hilos trabajadores
            hilos = []
            for i in range(NUM_HILOS):
                hilo = threading.Thread(target=descargar_archivo)
                hilo.start()
                hilos.append(hilo)
                
            # blockeamos el programa principal hasta que la cola esté vacía (todas las tareas listas)
            cola_descargas.join()
            
            # Detenemos los hilos enviando un 'None' por cada hilo activo
            for i in range(NUM_HILOS):
                cola_descargas.put(None)
                
            # Esperamos a que todos los hilos se cierren correctamente
            for hilo in hilos:
                hilo.join()
                
            print("\n=== Todas las descargas han finalizado ===")
        else:
            print("No se encontraron enlaces a descargar.")

if __name__ == "__main__":
    main()