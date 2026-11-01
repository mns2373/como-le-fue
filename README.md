# ¿Cómo le fue? · Taquilla del cine en Estados Unidos

Aplicación web para explorar la evolución de la taquilla cinematográfica de Estados Unidos y el desempeño comercial de sus películas, con datos diarios entre **2003 y 2025**.

**Autor:** Martín Nicolás Serafini · [GitHub](https://github.com/MartinSerafini) · [LinkedIn](https://www.linkedin.com/in/martin-nicolas-serafini-05224923b/)

**Fecha:** noviembre de 2026

La aplicación forma parte del Proyecto Integrador de la Licenciatura en Administración (Facultad de Ciencias Económicas, Universidad de Buenos Aires), que analiza la reconfiguración del mercado del cine en Estados Unidos.

## Qué permite hacer

- **Explorar por fecha.** Elegir un período y ver la recaudación total del mercado, de la película número uno y del Top 10 de cada día, agrupada por días, semanas, meses o años, con indicadores de concentración.
- **Explorar por película.** Buscar entre más de 3.400 títulos, filtrar por distribuidora, año, género y calificación, y ver la recaudación diaria y acumulada de cada película junto con su ficha.
- **Descargar gráficos.** Generar una imagen apaisada (16:9) del recorrido de cada película, con su puesto diario en el ranking y los fines de semana marcados.

## Datos y metodología

Los datos provienen de **Box Office Mojo** y se obtuvieron mediante **web scraping**, como parte del trabajo de investigación. El proceso de recolección y preparación, que no forma parte de este repositorio, incluyó:

- **Extracción automatizada** de páginas por fecha y por película con Python (requests y BeautifulSoup), con pausas aleatorias entre consultas, reutilización de sesiones, registro de errores por código de respuesta y puntos de control por tramos de años para retomar la descarga sin repetir trabajo.
- **Integración** de tres fuentes: la ficha de cada película (distribuidora, calificación, duración, géneros, estreno y salas), la recaudación diaria por película y la recaudación diaria del mercado con su ranking.
- **Validación y limpieza:** controles de continuidad de los días en cartel y de la recaudación acumulada, reconstrucción de fechas faltantes, eliminación de registros duplicados y exclusión de películas sin estreno en Estados Unidos.
- **Normalización** de géneros, calificaciones, días de la semana y feriados, y armado de las series temporales en formato Parquet.

Resultado: 3.424 películas, cerca de 239.000 registros de recaudación diaria por película y 8.395 días de recaudación del mercado.

Las cifras se expresan en dólares nominales, sin ajuste por inflación. Los datos pertenecen a su fuente original y se usan con fines académicos.

## Tecnologías

Python · pandas · Plotly · matplotlib · Streamlit · diseño de pantallas en Figma

## Contenido del repositorio

| Archivo o carpeta | Contenido |
|---|---|
| `app.py` | Aplicación: navegación, pantallas, búsqueda, filtros y gráficos interactivos |
| `grafico_descarga.py` | Generación de la imagen PNG 16:9 que se descarga desde el detalle de cada película |
| `preparar_datos.py` | Limpieza e integración que produjo los archivos de `data/` a partir de los datos recolectados (los datos de origen no se incluyen) |
| `data/` | Datos procesados que usa la aplicación: películas, recaudación diaria por película y recaudación del mercado |
| `assets/claqueta.png` | Imagen de la pantalla de inicio |
| `assets/fuentes/` | Fuente Inter para la imagen descargable, con su licencia (SIL Open Font License) |
| `.streamlit/config.toml` | Tema visual de la aplicación |
| `requirements.txt` | Librerías necesarias |
| `LICENSE` | Términos de uso |

## Derechos y uso

© 2026 Martín Nicolás Serafini. Todos los derechos reservados.

El código, el diseño y el procesamiento de los datos son obra del autor. Se puede consultar el repositorio y usar libremente la aplicación publicada. No se permite copiar, redistribuir, publicar ni presentar este trabajo, total o parcialmente, como propio sin autorización escrita del autor. Para cualquier otro uso, se puede contactar al autor por [LinkedIn](https://www.linkedin.com/in/martin-nicolas-serafini-05224923b/).

Los datos de taquilla provienen de Box Office Mojo y están sujetos a los términos de su fuente original. La fuente Inter se distribuye bajo su propia licencia.
