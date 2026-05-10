# Análisis de Mortalidad en Colombia 2019

## Introducción

Aplicación web interactiva desarrollada con Python y Dash para explorar y visualizar los datos de mortalidad no fetal en Colombia correspondientes al año 2019, con base en los microdatos publicados por el DANE (Departamento Administrativo Nacional de Estadística).

## Objetivo

Transformar los microdatos de defunciones no fetales del DANE en representaciones visuales interactivas que permitan identificar patrones demográficos, geográficos y clínicos de la mortalidad en Colombia durante el año 2019.

## Estructura del proyecto

```
mortalidad_app/
├── app.py                  # Punto de entrada de la aplicación Dash
├── requirements.txt        # Dependencias del proyecto
├── render.yaml             # Configuración de despliegue en Render
├── README.md               # Este documento
└── data/
    ├── NoFetal2019.xlsx        # Microdatos de defunciones no fetales 2019
    ├── CodigosDeMuerte.xlsx    # Catálogo CIE-10 (causas de muerte)
    ├── Divipola.xlsx           # División político-administrativa de Colombia
    └── dept_centroids.json     # Coordenadas centroides de departamentos (generado)
```

## Requisitos

| Librería     | Versión  |
|-------------|---------|
| dash        | 2.18.2  |
| plotly      | 5.24.1  |
| pandas      | 2.2.3   |
| openpyxl    | 3.1.5   |
| gunicorn    | 23.0.0  |

## Instalación y ejecución local

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario>/mortalidad-colombia-2019.git
cd mortalidad-colombia-2019

# 2. Crear y activar entorno virtual
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python app.py
```

Abrir el navegador en `http://127.0.0.1:8050`

## Despliegue en Render

1. Hacer push del repositorio a GitHub (el repositorio debe ser público o conectado a Render).
2. Ir a [https://render.com](https://render.com) → **New → Blueprint**.
3. Conectar el repositorio; Render detecta automáticamente el archivo `render.yaml`.
4. Verificar que el campo **Branch** sea `main` y hacer clic en **Deploy Blueprint**.
5. Una vez desplegado, acceder a la URL pública generada (p. ej., `https://mortalidad-colombia-2019.onrender.com`).

> **Nota de memoria:** el plan gratuito de Render ofrece 512 MB de RAM. Para optimizar la carga, los datos se procesan en el arranque de la aplicación. Si el archivo `NoFetal2019.xlsx` supera la memoria disponible, se recomienda pre-procesar los datos y guardarlos en formato Parquet antes del despliegue.

## Software utilizado

- **Python 3.11** — lenguaje de programación
- **Dash 2.18** — framework para aplicaciones web analíticas
- **Plotly 5.24** — librería de visualización interactiva
- **Pandas 2.2** — manipulación y análisis de datos
- **Gunicorn** — servidor WSGI para producción

## Visualizaciones incluidas

| # | Visualización | Descripción |
|---|--------------|-------------|
| 1 | **Mapa de burbujas** | Distribución total de muertes por departamento en Colombia |
| 2 | **Gráfico de líneas** | Evolución mensual del total de muertes durante 2019 |
| 3 | **Gráfico de barras** | Top 5 ciudades con mayor número de homicidios por arma de fuego (código X95) |
| 4 | **Gráfico circular** | 10 municipios con el menor índice de mortalidad |
| 5 | **Tabla interactiva** | Top 10 causas de muerte según el código CIE-10 |
| 6 | **Barras apiladas** | Comparación de muertes por sexo en los 15 departamentos con mayor mortalidad |
| 7 | **Histograma** | Distribución de muertes por grupo de edad (GRUPO_EDAD1 del DANE) |

## Fuente de datos

- DANE — Estadísticas Vitales EEVV 2019  
  [https://microdatos.dane.gov.co/index.php/catalog/696](https://microdatos.dane.gov.co/index.php/catalog/696)
