import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class VisorMapasNYC:
    def __init__(self, root):
        self.root = root
        self.root.title("UrbanFlow AI - Visor Dinámico de Tráfico NYC")
        self.root.geometry("750x850")
        self.root.configure(bg="#121212")  # Fondo oscuro elegante para hacer match con el mapa base
        
        # Ruta de la carpeta de mapas
        self.output_dir = "output"
        
        # 1. Título de la Aplicación
        self.title_label = tk.Label(
            root, 
            text="ANÁLISIS DINÁMICO DE FLUJOS (TLC NYC)", 
            font=("Helvetica", 16, "bold"), 
            fg="#FFFFFF", 
            bg="#121212",
            pady=10
        )
        self.title_label.pack()

        # 2. Contenedor para la Imagen del Mapa
        self.map_label = tk.Label(root, bg="#000000", bd=2, relief="groove")
        self.map_label.pack(padx=20, pady=10, fill="both", expand=True)
        
        # 3. Etiqueta de la Hora Actual
        self.time_label = tk.Label(
            root, 
            text="Hora Seleccionada: 00:00 h", 
            font=("Helvetica", 14, "bold"), 
            fg="#FF4500",  # Color naranja/fuego que hace match con la coropleta
            bg="#121212"
        )
        self.time_label.pack(pady=5)
        
        # 4. Control Deslizante (Slider / Scale) para las 24 horas
        self.style = ttk.Style()
        self.style.configure("TScale", background="#121212")
        
        self.slider = ttk.Scale(
            root, 
            from_=0, 
            to=23, 
            orient="horizontal", 
            command=self.actualizar_mapa,
            style="TScale"
        )
        self.slider.pack(fill="x", padx=50, pady=15)
        
        # 5. Pie de página técnico
        self.footer = tk.Label(
            root,
            text="Desarrollado con Arquitectura Multiprocesamiento (Map-Reduce Paralelo)",
            font=("Helvetica", 9, "italic"),
            fg="#666666",
            bg="#121212"
        )
        self.footer.pack(pady=5)
        
        # Inicializar mostrando la hora 00
        self.actualizar_mapa(0)

    def actualizar_mapa(self, valor):
        # Convertir el valor flotante del slider a entero (0 - 23)
        hora = int(float(valor))
        
        # Actualizar el texto de la hora
        self.time_label.config(text=f"Hora Seleccionada: {hora:02d}:00 h")
        
        # Construir la ruta de la imagen correspondiente
        img_name = f"zonas_hora_{hora:02d}.png"
        img_path = os.path.join(self.output_dir, img_name)
        
        if os.path.exists(img_path):
            try:
                # Abrir y redimensionar la imagen para que se ajuste perfectamente al formulario
                img = Image.open(img_path)
                img = img.resize((650, 650), Image.Resampling.LANCZOS)
                
                # Convertir al formato que Tkinter entiende
                self.photo = ImageTk.PhotoImage(img)
                
                # Inyectar la imagen en el contenedor
                self.map_label.config(image=self.photo)
            except Exception as e:
                self.time_label.config(text=f"❌ Error al cargar imagen: {e}")
        else:
            # Por si mueven el slider antes de correr el main.py
            self.map_label.config(image='')
            self.time_label.config(text=f"⚠️ Archivo '{img_name}' no encontrado en 'output/'")

if __name__ == "__main__":
    # Crear la ventana raíz de Windows
    root = tk.Tk()
    app = VisorMapasNYC(root)
    # Mantener la ventana activa e interactiva
    root.mainloop()