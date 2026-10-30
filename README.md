# ¿Cómo le fue? · Taquilla del cine en Estados Unidos (2003–2025)

App de consulta que acompaña el Proyecto Integrador (FCE-UBA).

## Estructura

| Archivo | Para qué sirve |
|---|---|
| `app.py` | La app (7 pantallas del diseño de Figma) |
| `data/*.parquet` | Datos que lee la app (generados con el script) |
| `preparar_datos.py` | Convierte los CSV de `datos_originales/` en los Parquet de `data/` |
| `requirements.txt` | Librerías para Streamlit Community Cloud |
| `.streamlit/config.toml` | Tema claro y opciones de la interfaz |

## Actualizar los datos

1. Copiar los tres CSV a `datos_originales/`.
2. `python preparar_datos.py`
3. Subir los Parquet nuevos de `data/` al repositorio.

## Probar en la computadora

```
pip install -r requirements.txt
streamlit run app.py
```

## Publicar gratis

1. Crear un repositorio público en GitHub y subir todo menos `datos_originales/`.
2. Entrar a share.streamlit.io con la cuenta de GitHub, elegir **Create app**, el repositorio y `app.py`.
3. Elegir un subdominio corto (por ejemplo `comolefue.streamlit.app`).
4. Generar el QR con esa dirección.

La app se duerme tras unas horas sin visitas: abrirla la mañana de la defensa.
