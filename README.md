# Visor de Partidos - Edición Definitiva

## Descripción
Aplicación Streamlit que permite visualizar próximos partidos y resultados finalizados con funcionalidades de análisis detallado.

## Funcionalidades
- Visualización de próximos partidos y resultados finalizados
- Filtrado por hándicap y línea de goles
- Vista previa detallada de partidos
- Análisis completo de partidos (en desarrollo)

## Despliegue en Streamlit Cloud

Para desplegar esta aplicación en Streamlit Cloud:

1. Crea un repositorio público en GitHub con los siguientes archivos:
   - `streamlit_app_final.py` (archivo principal de la aplicación)
   - `requirements.txt` (archivo con las dependencias)
   - Carpeta `Descarga_Todo` con los módulos necesarios
   - Archivo `data.json` con los datos iniciales
   - Carpeta `.streamlit` con `config.toml`

2. Ve a https://streamlit.io/cloud

3. Conecta tu cuenta de GitHub

4. Selecciona el repositorio donde subiste los archivos

5. Configura el nombre del archivo principal como: `streamlit_app_final.py`

6. Haz clic en "Deploy" y espera a que se complete la instalación de dependencias

## Estructura del proyecto
```
├── streamlit_app_final.py    # Archivo principal de la aplicación
├── requirements.txt          # Dependencias necesarias
├── data.json                 # Archivo con datos de partidos
├── Descarga_Todo/            # Carpeta con módulos auxiliares
│   ├── estudio_scraper.py    # Módulo para scraping de datos
│   └── ejemplo_html.txt      # Plantilla para vistas previas
├── .streamlit/
│   └── config.toml           # Configuración para Streamlit Cloud
└── README.md                 # Documentación (este archivo)
```

## Solución de problemas comunes

### Si la aplicación falla en Streamlit Cloud
1. Asegúrate de que todos los archivos necesarios estén en el repositorio
2. Verifica que las rutas de los archivos dentro del código sean relativas al directorio principal
3. Comprueba que todas las dependencias estén listadas en `requirements.txt`

### Si los módulos no se importan correctamente
- Asegúrate de que la estructura de carpetas se mantenga tal como se muestra en el esquema de arriba
- Comprueba que las rutas en los `sys.path.append()` coincidan con la estructura real

## Notas
- Esta aplicación depende de archivos externos como `data.json` y módulos en la carpeta `Descarga_Todo`
- Asegúrate de incluir todos los archivos necesarios en el repositorio para que funcione correctamente en la nube