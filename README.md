# ¿Cómo le fue? · Taquilla del cine en Estados Unidos

Aplicación web para explorar el desempeño comercial de las películas estrenadas en Estados Unidos entre **2003 y 2025**, y la trayectoria de las personas que las hicieron.

**Autor:** Martín Nicolás Serafini
**Versión:** 2.1 · noviembre de 2026

La aplicación nació como parte del Proyecto Integrador de la Licenciatura en Administración (Facultad de Ciencias Económicas, Universidad de Buenos Aires), que analiza la reconfiguración del mercado del cine en Estados Unidos.

## Qué permite hacer

- **Explorar por película.** Buscar entre más de 3.400 títulos y filtrar por distribuidora, año, género y calificación. Cada película muestra su afiche (se amplía a pantalla completa al tocarlo), la taquilla total, la de apertura, el presupuesto y la recaudación diaria y acumulada.
- **Ver la información completa de una película:** sinopsis, tráiler, ficha, saga, origen, desempeño en Estados Unidos y en el mundo, recepción de la crítica y del público, recorrido (cines, digital, DVD / Blu-ray, TV) con la ventana de exclusividad en cines, equipo técnico y elenco.
- **Explorar por persona.** Buscar actores, directores y equipo técnico y ver sus datos, biografía y filmografía en la app, con enlaces entre películas y personas.
- **Explorar por fecha.** Elegir un período y ver el ranking de las películas que más recaudaron en esas fechas.
- **Descargar** el gráfico de cada película (PNG 16:9) y dos resúmenes en formato A4 (JPG): el *Resumen de la película* y el *Resumen de trayectoria* de cada persona.

Si falta un dato, la aplicación lo indica con «Sin datos.» (o «Sin tráiler») y sigue funcionando.

## Datos y metodología

| Fuente | Qué aporta |
|---|---|
| **Box Office Mojo** (IMDbPro) | Recaudación diaria y total, rankings, distribuidoras, cines, fechas de estreno y equipo técnico. Es la fuente principal. |
| **IMDb** | Elenco y puntajes del público y de la crítica (Metascore). |
| **TMDB** (The Movie Database) | Sinopsis, afiches, fotos, biografías, presupuesto, sagas, idiomas, países, productoras, fechas de lanzamiento fuera de los cines y tráileres. |

El proceso de recolección y preparación, que no forma parte de este repositorio, incluyó:

- **Extracción** de páginas por fecha, por película y por persona con Python, y consultas a la API de TMDB.
- **Vinculación** de cada película y cada persona entre las fuentes (por título, año, fechas y créditos), conservando el valor de Box Office Mojo cuando hay diferencias.
- **Validación y limpieza:** continuidad de los días en cartel y de la recaudación acumulada, reconstrucción de fechas faltantes, eliminación de duplicados y exclusión de películas sin estreno en Estados Unidos.
- **Normalización** de géneros, calificaciones, idiomas, países y lugares de nacimiento, y armado de las series temporales en formato Parquet.

Las cifras se expresan en dólares nominales, sin ajuste por inflación. El presupuesto es el informado en TMDB (cifra mundial). Los reestrenos no se cuentan en las filmografías.

## Tecnologías

Python · pandas · Plotly · matplotlib · Pillow · Streamlit · diseño de pantallas en Figma

## Contenido del repositorio

| Archivo o carpeta | Contenido |
|---|---|
| `app.py` | Aplicación: navegación con historial, pantallas, búsquedas, filtros y gráficos interactivos |
| `informes.py` | Resúmenes A4 descargables (película y trayectoria), dibujados con Pillow y matplotlib |
| `grafico_descarga.py` | Imagen PNG 16:9 del recorrido de cada película |
| `preparar_datos.py` | Integración de los datos de Box Office Mojo (genera `peliculas`, `diaria` y `mercado`) |
| `preparar_datos_tmdb.py` | Integración de los datos de TMDB e IMDb (genera `fichas`, `lanzamientos`, `creditos` y `personas`) |
| `data/` | Datos procesados que usa la aplicación (Parquet) |
| `assets/claqueta.png` | Imagen de la pantalla de inicio |
| `assets/fuentes/` | Fuentes Inter y Oleo Script, con sus licencias (SIL Open Font License) |
| `.streamlit/config.toml` | Tema visual |
| `requirements.txt` | Librerías necesarias |
| `LICENSE` | Términos de uso |

### Actualizar los datos

```
python preparar_datos.py
python preparar_datos_tmdb.py
```

Los archivos de origen (`datos_originales/` y `datos_tmdb/`) no se suben al repositorio.

### Logo de TMDB

Las condiciones de uso de TMDB piden mostrar su logo oficial en la sección de créditos. Descargá uno de los logos de [themoviedb.org/about/logos-attribution](https://www.themoviedb.org/about/logos-attribution) y guardalo como `assets/tmdb_logo.svg`. Si el archivo no está, «Acerca de» muestra solo el texto de atribución.

### Credenciales

La credencial de la API de TMDB se usa solo para recolectar los datos, no para ejecutar la aplicación. Va en el archivo `.env`, que está excluido en `.gitignore` y **no debe subirse al repositorio**.

## Créditos y atribuciones

This product uses the TMDB API but is not endorsed or certified by TMDB.

Information courtesy of IMDb (https://www.imdb.com). Used with permission.

Datos de taquilla: Box Office Mojo by IMDbPro (https://www.boxofficemojo.com).

## Derechos y uso

© 2026 Martín Nicolás Serafini. Todos los derechos reservados.

El código, el diseño y el procesamiento de los datos son obra del autor. Se puede consultar el repositorio y usar libremente la aplicación publicada. No se permite copiar, redistribuir, publicar ni presentar este trabajo, total o parcialmente, como propio sin autorización escrita del autor. Cualquier otro uso requiere autorización del autor.

Los datos pertenecen a sus fuentes originales (Box Office Mojo, IMDb y TMDB) y están sujetos a sus términos. Las fuentes Inter y Oleo Script se distribuyen bajo sus propias licencias.
