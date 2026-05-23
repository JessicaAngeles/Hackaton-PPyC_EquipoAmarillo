# 🚕 Salvando a "UrbanFlow AI" — Pipeline de Datos de Movilidad Masiva

![UrbanFlow AI Banner](https://img.shields.io/badge/Industry-AdTech-ff69b4) ![Data-Size](https://img.shields.io/badge/Data--Size-600M%20Rows%20%2F%2072%20Parquet%20Files-blue) ![Status](https://img.shields.io/badge/Status-Optimized-success)

## 🏢 Contexto de la Startup
**UrbanFlow AI** es una startup de *AdTech* (Tecnología Publicitaria) que revoluciona el mercado vendiendo espacios publicitarios dinámicos en pantallas digitales (*billboards*) distribuidas estratégicamente por toda la ciudad de Nueva York. 

Para poder cobrar tarifas *premium* a marcas globales, prometemos pautas publicitarias inteligentes basadas en el flujo vehicular real y predictivo de la ciudad. Para entrenar nuestro modelo predictivo de manera robusta, el equipo de negocio requiere procesar y consolidar la historia completa de movilidad de Nueva York de los últimos dos años (**2024 y 2025**).

---

## 🚨 El Problema de Negocio (La Crisis de Coca-Cola)
El prototipo inicial del pipeline cargaba los datos directamente en memoria RAM usando Pandas de forma ingenua (`pd.read_parquet()`). Si bien funcionaba para un solo mes de datos de *Yellow Taxis*, colapsa por **Out of Memory (OOM)** al intentar procesar el histórico completo.

Los ejecutivos han firmado una carta de intención comercial clave con **Coca-Cola**, pero para cerrar el contrato exigen ver los mapas de calor agregados y el análisis de flujo de toda la ciudad utilizando todas las plataformas de transporte:
* **Yellow Taxis**
* **Green Taxis**
* **High Volume For-Hire Vehicles (FHVHV)** — *Uber y Lyft*

Esto representa descargar, normalizar y procesar **72 archivos Parquet masivos** que en su conjunto suman aproximadamente **600 millones de viajes** en menos de 3 horas y media.

---

## 🎯 Objetivo del Proyecto
El objetivo principal de este proyecto es reescribir y optimizar la tubería de datos (*Data Pipeline*) desde cero. El sistema debe ser capaz de procesar años de historia de transporte de forma eficiente sin desbordar la memoria RAM de los servidores, utilizando procesamiento paralelo, lectura proyectada en disco y una arquitectura de agregación inteligente (**Map-Reduce**).

### Requerimientos Principales:
1. **Escalabilidad Masiva:** Soporte completo para los años 2024 y 2025 de las tres fuentes de datos (Yellow, Green, FHVHV).
2. **Estandarización y Homologación de Esquemas:** Resolver la inconsistencia de nombres en las columnas de fechas y zonas de origen/destino según el tipo de vehículo.
3. **Agrupación Global:** Consolidar los 600 millones de registros en un resumen agregado por hora y zona.
4. **Renderizado Visual:** Generar mapas de calor coropléticos interactivos que muestren el comportamiento y los flujos promedio de la ciudad.

---

## 🛠️ Arquitectura de Solución y Optimizaciones

Para evitar el colapso por memoria (**OOM**) y acelerar el procesamiento de horas a minutos, se implementaron tres pilares de la ingeniería de datos a gran escala:

### 1. Proyección de Columnas en Disco (Evitar el Asesino de RAM)
En lugar de cargar archivos completos que expandidos en RAM ocupan hasta 4 veces su tamaño en disco, la lectura de los archivos Parquet se realiza aplicando **Column Projection**. Solo se extraen del disco las columnas estrictamente necesarias para el análisis de flujo (`pickup_datetime`, `PULocationID`, `DOLocationID`).

### 2. Homologación Dinámica de Esquemas
Cada tipo de servicio registra los datos con nomenclaturas diferentes. El pipeline incorpora una capa de abstracción y limpieza que detecta el origen del archivo y estandariza los esquemas bajo las siguientes reglas de mapeo:

| Dataset Original | Columna Origen Temporal | Columna Destino Estandarizada | Columna Zona Origen | Columna Zona Destino |
| :--- | :--- | :--- | :--- | :--- |
| **Yellow Taxi** | `tpep_pickup_datetime` | `pickup_datetime` | `PULocationID` | `DOLocationID` |
| **Green Taxi** | `lpep_pickup_datetime` | `pickup_datetime` | `PULocationID` | `DOLocationID` |
| **FHVHV (Uber/Lyft)** | `pickup_datetime` | `pickup_datetime` | `PULocationID` | `DOLocationID` |

### 3. Estrategia "Divide y Vencerás" (Map-Reduce Local)
No se realiza un `groupby` global sobre los 600 millones de filas directamente. El pipeline procesa los datos mediante un flujo por etapas descentralizadas:
1. **Fase Map:** Se procesa cada archivo de forma independiente. Se extrae la hora de la fecha y se realiza una agregación local reduciendo millones de filas a unos pocos cientos de combinaciones únicas (`pickup_hour`, `PULocationID`, `DOLocationID`).
2. **Fase Free Memory:** Se escribe el resultado parcial, liberando la RAM inmediatamente antes de pasar al siguiente archivo.
3. **Fase Reduce:** Se consolidan únicamente los resúmenes agregados intermedios en la matriz final.

---

## 📂 Estructura del Proyecto

El repositorio se organiza de forma plana en la raíz con los siguientes componentes core:

```text
├── .gitignore           # Archivos y carpetas omitidos en Git (ej. datasets pesados)
├── README.md            # Documentación del proyecto (esta guía)
├── webscrapping.py      # Script encargado de automatizar la descarga de los 72 archivos de TLC
├── etl_process.py       # Lógica de extracción, homologación de esquemas y Map-Reduce
├── visor_gui.py         # Interfaz gráfica y renderizado del mapa de calor interactivo
├── main.py              # Orquestador principal que ejecuta el pipeline de inicio a fin
└── requirements.txt     # Dependencias del proyecto de Python

