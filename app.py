"""
¿Cómo le fue? · Taquilla del cine en Estados Unidos (2003–2025)  ·  versión 2

Ejecutar localmente:   streamlit run app.py
Datos: ./data/*.parquet (generados con preparar_datos.py y preparar_datos_tmdb.py)
"""
import base64
import html
import importlib
import traceback
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import grafico_descarga
import informes


def recargar_si_cambiaron(*modulos):
    """Streamlit relee app.py en cada actualización, pero no los módulos auxiliares.
    Si informes.py o grafico_descarga.py cambiaron en disco, se vuelven a cargar
    (así no hace falta reiniciar la app en Streamlit Cloud)."""
    for modulo in modulos:
        try:
            modificado = Path(modulo.__file__).stat().st_mtime
            if getattr(modulo, "_cargado_en", None) != modificado:
                importlib.reload(modulo)
                modulo._cargado_en = modificado
        except Exception:
            traceback.print_exc()


recargar_si_cambiaron(informes, grafico_descarga)

# =============================================================================
# Configuración general (lo único que suele hacer falta tocar)
# =============================================================================
AUTOR = "Martín Nicolás Serafini"
# Versión para la defensa: False (sin enlaces personales). Versión para publicar: True.
MOSTRAR_CONTACTO = True
LINKEDIN = "https://www.linkedin.com/in/martin-nicolas-serafini-05224923b/"
SUBTITULO = "Taquilla del cine en Estados Unidos · 2003–2025"
POR_PAGINA = 20                      # resultados que se suman con "Mostrar más"
COLOR_DIARIA = "#2F80D0"
COLOR_ACUMULADA = "#1F8F5C"
COLOR_BARRAS = "#2F80D0"
BASE = Path(__file__).parent
DATA = BASE / "data"
LOGO_TMDB = BASE / "assets" / "tmdb_logo.svg"     # logo oficial (ver README)
SIN = "Sin datos."

st.set_page_config(page_title="¿Cómo le fue?", page_icon="🎬", layout="centered",
                   initial_sidebar_state="collapsed")


# =============================================================================
# Datos
# =============================================================================
def leer(nombre, columnas_vacias=()):
    """Lee un Parquet de ./data; si falta, devuelve una tabla vacía para que la app no se rompa."""
    ruta = DATA / nombre
    if ruta.exists():
        return pd.read_parquet(ruta)
    return pd.DataFrame(columns=list(columnas_vacias))


@st.cache_data(show_spinner=False)
def cargar_datos():
    pel = pd.read_parquet(DATA / "peliculas.parquet")
    pel["generos"] = pel["generos"].map(list)
    pel = pel.set_index("id", drop=False)
    dia = pd.read_parquet(DATA / "diaria.parquet")
    merc = pd.read_parquet(DATA / "mercado.parquet")
    fichas = leer("fichas.parquet", ["id"]).set_index("id", drop=False)
    lanz = leer("lanzamientos.parquet", ["id", "tipo", "fecha", "detalle"])
    cred = leer("creditos.parquet", ["id", "bio_id", "nombre", "grupo", "rol", "personaje", "orden"])
    per = leer("personas.parquet", ["bio_id", "nombre", "nombre_norm", "roles", "n_peliculas", "popularidad"])
    per = per.set_index("bio_id", drop=False)
    return pel, dia, merc, fichas, lanz, cred, per


@st.cache_data(show_spinner=False)
def fuente_logo():
    """Oleo Script incluida en la app: no depende de Google Fonts."""
    ruta = BASE / "assets" / "fuentes" / "OleoScript-Bold.ttf"
    if not ruta.exists():
        return ""
    b64 = base64.b64encode(ruta.read_bytes()).decode()
    return ("@font-face { font-family: 'Oleo Script'; font-weight: 700; font-display: swap; "
            f"src: url(data:font/ttf;base64,{b64}) format('truetype'); }}")


def normalizar(texto) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower().strip()


def vacio(v):
    if v is None:
        return True
    if isinstance(v, (list, tuple, np.ndarray)):
        return len(v) == 0
    try:
        return bool(pd.isna(v)) or (isinstance(v, str) and not v.strip())
    except (TypeError, ValueError):
        return False


def campo(tabla, clave, columna):
    """Valor de una celda o None si falta la fila, la columna o el dato."""
    try:
        v = tabla.at[clave, columna]
    except (KeyError, ValueError):
        return None
    return None if vacio(v) else v


# =============================================================================
# Formatos (convención argentina: punto de miles, coma decimal)
# =============================================================================
def num(x, dec=0):
    if vacio(x):
        return SIN
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def millones(x):
    if vacio(x):
        return SIN
    m = x / 1e6
    return num(m, 0 if m >= 1000 else 1)


def fecha(f):
    return SIN if vacio(f) else pd.Timestamp(f).strftime("%d/%m/%Y")


def txt(x, sufijo=""):
    return SIN if vacio(x) else f"{x}{sufijo}"


def e(x):
    return html.escape(str(x))


def edad(nacimiento, hasta=None):
    if vacio(nacimiento):
        return None
    n, h = pd.Timestamp(nacimiento), pd.Timestamp(hasta) if hasta is not None else pd.Timestamp(informes.hoy())
    return h.year - n.year - ((h.month, h.day) < (n.month, n.day))


def duracion(minutos):
    if vacio(minutos):
        return SIN
    m = int(minutos)
    return f"{m // 60} h {m % 60:02d} min"


# =============================================================================
# Estilos
# =============================================================================
ICONOS = {
    "calendario": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/></svg>',
    "pelicula": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.2"/><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/></svg>',
    "persona": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.9-3.6 3.5-5.5 6.5-5.5s5.6 1.9 6.5 5.5"/><circle cx="17" cy="9" r="2.6"/><path d="M16 14.6c2.6.1 4.6 1.9 5.4 4.9"/></svg>',
    "info": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
}
SVG_AFICHE = ('<svg viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="1.4"><rect x="2" y="2" width="20" '
              'height="20" rx="2.2"/><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/></svg>')
SVG_PERSONA = ('<svg viewBox="0 0 24 24" fill="none" stroke="#a0a0a0" stroke-width="1.5"><circle cx="12" cy="8" r="4"/>'
               '<path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>')

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
__FUENTE_LOGO__

.stApp, .stApp p, .stApp div, .stApp label, .stApp input, .stApp button, .stApp li, .stApp h4 {
  font-family: 'Inter', system-ui, sans-serif;
}
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
.stMainBlockContainer, .block-container { max-width: 460px; padding-top: 0.6rem !important;
  padding-left: 1rem !important; padding-right: 1rem !important; }
[data-testid="stVerticalBlock"] { gap: 0.7rem; }

/* Marca */
.stApp .logo { font-family: 'Oleo Script', cursive !important; font-weight: 700 !important; line-height: 1.1; color: #111;
  padding: 0 0.3rem; }
.logo-grande { font-size: 2.6rem; text-align: center; margin-top: 0.8rem; }
.subtitulo { text-align: center; font-weight: 600; font-size: 0.78rem; line-height: 1.35; margin: 0.3rem 0 0;
  text-wrap: balance; }
html, body, .stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] { overflow-x: hidden !important; max-width: 100vw; }
.stApp .logo-grande { font-size: clamp(2rem, 10vw, 2.6rem); max-width: 100%; }
.separador { border: 0 !important; border-top: 1px solid #e4e4e4 !important; margin: 0.5rem -1rem !important; }

/* Barra superior: volver + logo */
.st-key-barra, .st-key-cab_det { justify-content: space-between !important; align-items: center !important; flex-wrap: nowrap !important; gap: 0.4rem !important; }
.st-key-barra [data-testid="stElementContainer"] { width: auto !important; }
.st-key-barra button { padding: 0; min-height: 0; color: #111; }
.st-key-barra button p { font-size: 0.78rem !important; font-weight: 600; white-space: nowrap; }
.st-key-logo button { padding: 0; min-height: 0; }
.st-key-logo { flex: 0 0 auto; margin-right: 0.35rem; }
.st-key-logo button p { font-family: 'Oleo Script', cursive !important; font-size: 1.15rem !important;
  font-weight: 700 !important; color: #111; white-space: nowrap; overflow: visible;
  padding-right: 0.25rem; line-height: 1.2; }

/* Encabezados de pantalla */
.stMarkdown p.titulo-pantalla { text-align: center; font-size: 1.6rem; font-weight: 700; line-height: 1.15; margin: 0; }
.stMarkdown p.bajada { text-align: center; font-size: 0.82rem; font-weight: 600; margin: 0.2rem 0 0; line-height: 1.3; }
.stMarkdown p.titulo-peli { font-size: 1.4rem; font-weight: 700; line-height: 1.15; margin: 0; }
.stMarkdown p.anio-peli { font-size: 0.84rem; font-weight: 600; margin: 0.15rem 0 0; }
.stMarkdown p.seccion { font-weight: 700; font-size: 0.98rem; margin: 0; line-height: 1.3; }
.stMarkdown p.seccion-sub { font-size: 0.74rem; font-weight: 600; color: #333; margin: 0; }
.stMarkdown p.sub-grafico { white-space: nowrap; margin-top: -1rem; }
.stMarkdown p.etiqueta, .etiqueta { font-size: 0.78rem; font-weight: 700; letter-spacing: 0.02em; margin: 0; }
[data-testid="stWidgetLabel"] p { font-size: 0.78rem !important; font-weight: 700; }

/* Tarjetas cliqueables: el botón invisible cubre toda la tarjeta */
[class*="st-key-card_"] { position: relative; gap: 0 !important; }
[class*="st-key-card_"] [data-testid="stElementContainer"]:has(.stButton) {
  position: absolute !important; inset: 0; z-index: 5; margin: 0;
  width: 100% !important; height: 100% !important;
}
[class*="st-key-card_"] .stButton, [class*="st-key-card_"] .stButton button {
  width: 100%; height: 100%; opacity: 0; cursor: pointer;
}
[class*="st-key-card_"]:hover .tarjeta { background: #f6f6f6; }
.tarjeta { border: 1px solid #e2e2e2; border-radius: 12px; background: #fff;
  padding: 0.85rem 0.9rem; transition: background .15s; }
.menu { display: flex; align-items: center; gap: 0.7rem; min-height: 4.3rem; }
.menu svg { width: 40px; height: 40px; flex: none; }
.menu-tit { font-weight: 700; font-size: 1.05rem; line-height: 1.2; }
.menu-sub { font-weight: 600; font-size: 0.84rem; line-height: 1.3; }

/* Resultados */
.res-tit { font-weight: 700; font-size: 1.05rem; line-height: 1.2; margin-bottom: 0.25rem; }
.res-linea { font-size: 0.85rem; color: #222; line-height: 1.45; }
.res-taq { display: flex; justify-content: space-between; align-items: baseline; gap: .5rem;
  font-size: 0.86rem; margin-top: 0.15rem; }
.res-taq span { font-size: 0.8rem; color: #444; }
.res-taq b { font-weight: 700; }
.encab-res { display: flex; justify-content: space-between; align-items: baseline; }
.encab-res span { font-size: 0.74rem; color: #444; }
.st-key-lista { border: 1px solid #e2e2e2; border-radius: 12px; padding: 0.5rem; }
.st-key-lista [data-testid="stVerticalBlock"] { gap: 0.45rem; }
.rk { display: flex; gap: .7rem; align-items: flex-start; }
.rk-pos { min-width: 1.9rem; height: 1.9rem; border-radius: 50%; background: #111; color: #fff; font-weight: 700;
  font-size: .9rem; display: flex; align-items: center; justify-content: center; margin-top: .1rem; }
.rk-cuerpo { flex: 1; min-width: 0; }
.st-key-fechas { gap: .6rem; }
.st-key-fechas > div { flex: 1 1 0; min-width: 0; }
.st-key-fechas label p { font-size: .75rem; }
.pr-card { display: flex; gap: .75rem; align-items: center; }
.pr-foto { width: 52px; height: 52px; border-radius: 50%; background: #eee; display: flex; align-items: center;
  justify-content: center; flex: none; overflow: hidden; }
.pr-foto img { width: 100%; height: 100%; object-fit: cover; }
.pr-foto svg { width: 30px; height: 30px; }

/* Indicadores */
.kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 0.55rem; }
.kpi { border: 1px solid #e2e2e2; border-radius: 10px; padding: 0.5rem 0.7rem; }
.kpi-tit { font-size: 0.72rem; font-weight: 600; }
.kpi-val { font-size: 1.15rem; font-weight: 700; line-height: 1.35; }
.kpi-val.sin { color: #888; font-weight: 600; }
.kpi-pie { font-size: 0.7rem; color: #444; }

/* Ficha */
.dato { border: 1px solid #e2e2e2; border-radius: 10px; padding: 0.4rem 0.75rem; margin-bottom: 0.45rem; }
.dato-tit { font-size: 0.72rem; font-weight: 600; }
.dato-val { font-size: 1.02rem; font-weight: 700; }
.dato-val small { font-size: .75rem; color: #666; font-weight: 600; }

/* Afiche o foto + indicadores; ampliación a pantalla completa */
.cab { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; align-items: stretch; margin-top: 0.2rem; }
.afiche { aspect-ratio: 2 / 3; border: 1px solid #e2e2e2; border-radius: 10px; background: #f3f3f3; overflow: hidden;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .3rem;
  color: #2F6FB0 !important; font-weight: 600; font-size: .8rem; text-align: center; text-decoration: none !important; }
.afiche img { width: 100%; height: 100%; object-fit: cover; display: block; }
.afiche svg { width: 38px; height: 38px; } .afiche small { font-weight: 400; font-size: .68rem; color: #999; }
a.afiche { cursor: zoom-in; }
.cab-kpis { display: flex; flex-direction: column; justify-content: space-between; gap: .45rem; }
.cab-kpis .kpi { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.ampliada { display: none; position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,.92);
  align-items: center; justify-content: center; flex-direction: column; gap: .8rem; cursor: zoom-out;
  text-decoration: none !important; }
.ampliada:target { display: flex; }
.ampliada img { max-width: 94vw; max-height: 86dvh; object-fit: contain; border-radius: 6px; background: #fff; }
.ampliada span { color: #ddd; font-size: .8rem; }

/* Pantallas de información */
.sec { font-weight: 700; font-size: 1rem; margin: 1.1rem 0 .45rem; display: flex; align-items: center; gap: .45rem; }
.tag { font-size: .62rem; font-weight: 700; border: 1px solid #bbb; border-radius: 4px; padding: 0 .3rem; color: #666; }
.cuenta { font-size: .72rem; font-weight: 600; color: #666; background: #f0f0f0; border-radius: 9px; padding: 0 .45rem; }
.texto { font-size: .9rem; line-height: 1.5; margin: 0; }
.sin-dato { border: 1px dashed #ccc; border-radius: 10px; padding: 1.1rem; text-align: center; color: #777;
  font-size: .9rem; font-weight: 600; background: #fafafa; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: .45rem; }
.grid .dato { margin: 0; } .grid .dato.ancho { grid-column: 1 / -1; }
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: .45rem; }
.grid3 .dato { margin: 0; padding: .4rem .55rem; } .grid3 .dato.ancho { grid-column: 1 / -1; }
.grid3 .dato-val { font-size: .95rem; white-space: nowrap; }
.pie-dato { font-size: .7rem; color: #555; }
.nota { font-size: .72rem; color: #666; margin: .35rem 0 0; }
.sub { font-size: .78rem; font-weight: 600; color: #333; margin: .8rem 0 0; }
.destacado { border: 1px solid #e2e2e2; border-left: 4px solid #1F8F5C; border-radius: 10px; padding: .55rem .8rem;
  font-size: .92rem; margin-bottom: .5rem; } .destacado small { color: #555; font-size: .74rem; }
.tabla { width: 100%; border-collapse: collapse; font-size: .8rem; }
.tabla th { text-align: left; font-size: .7rem; color: #666; font-weight: 700; border-bottom: 1px solid #ddd; padding: .3rem .25rem; }
.tabla td { border-bottom: 1px solid #f0f0f0; padding: .35rem .25rem; vertical-align: top; }
.tabla td:nth-child(2) { white-space: nowrap; }
.links { display: grid; gap: .4rem; }
.links a { background: #3a3a3a; color: #fff !important; text-decoration: none !important; border-radius: 10px;
  font-size: .76rem; font-weight: 600; text-align: center; padding: .7rem .2rem; }
.links a:hover { background: #111; }
.st-key-cab_titulo { justify-content: space-between !important; flex-wrap: nowrap !important; align-items: center !important; }
.st-key-cab_titulo > div:first-child { flex: 1 1 auto; min-width: 0; }
.st-key-cab_titulo button { padding: 0 .15rem; min-height: 0; }
.st-key-cab_titulo button span { font-size: 1.45rem; }
.st-key-cab_titulo [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-saga { flex-wrap: wrap !important; gap: .35rem !important; }
.st-key-saga button { min-height: 0; padding: .15rem .6rem; border-radius: 14px; }
.st-key-saga button p { font-size: .78rem; }
.st-key-saga button:disabled { background: #3a3a3a; color: #fff; border-color: #3a3a3a; opacity: 1; }

/* Listas de nombres o títulos (equipo, elenco, filmografía) */
.rol { font-size: .84rem; color: #444; }
[class*="st-key-fila_"] { flex-wrap: nowrap !important; justify-content: space-between !important; gap: .6rem !important;
  border-bottom: 1px solid #f2f2f2; padding: .1rem 0; }
[class*="st-key-fila_"] > div { width: auto !important; min-width: 0; }
[class*="st-key-fila_"] .stMarkdown { text-align: right; }
[class*="st-key-fila_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-equipo [data-testid="stVerticalBlock"], .st-key-elenco [data-testid="stVerticalBlock"],
.st-key-filmo [data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-equipo button, .st-key-elenco button, .st-key-filmo button { padding: .2rem 0; min-height: 0;
  justify-content: flex-start; text-align: left; }
.st-key-equipo button p, .st-key-elenco button p, .st-key-filmo button p { font-size: .9rem; font-weight: 600;
  text-decoration: underline; text-decoration-color: #bbb; text-underline-offset: 3px; }
.nombre-fijo { font-size: .9rem; font-weight: 600; padding: .2rem 0; display: inline-block; }
[class*="st-key-film_"] { flex-wrap: nowrap !important; gap: .5rem !important; border-bottom: 1px solid #f2f2f2;
  padding: .3rem 0; align-items: flex-start !important; }
[class*="st-key-film_"] > div { width: auto !important; min-width: 0; }
[class*="st-key-film_"] > div:first-child { flex: 0 0 2.4rem; }
[class*="st-key-film_"] > div:last-child { flex: 1 1 auto; }
[class*="st-key-film_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[class*="st-key-fcol"] { gap: 0 !important; }
.f-anio { font-weight: 700; color: #555; font-size: .8rem; position: relative; top: .25rem; }
.f-rol { font-size: .8rem; line-height: 1.3; display: block; color: #555; }
.st-key-ver_mas button { padding: 0; min-height: 0; } .st-key-ver_mas button p { font-size: .85rem; text-decoration: underline; }

/* Botones negros */
.stButton button[kind="primary"], .stLinkButton a[kind="primary"] {
  background: #3a3a3a; border-color: #3a3a3a; border-radius: 12px; min-height: 3.1rem;
  font-weight: 600; color: #fff;
}
.stButton button[kind="primary"]:hover, .stLinkButton a[kind="primary"]:hover { background: #111; border-color: #111; }

/* Gráfico del detalle */
.st-key-acciones_det { flex: 0 0 auto !important; width: auto !important; gap: 1.6rem !important;
  margin-left: auto !important; margin-right: -0.3rem; transform: translateY(4px);
  flex-wrap: nowrap !important; align-items: center !important; }
.st-key-cab_det > [data-testid="stElementContainer"]:first-child { flex: 1 1 auto !important; min-width: 0; }
.st-key-cab_det button { padding: 0 0.15rem; min-height: 0; }
.st-key-cab_det button span { font-size: 1.45rem; }
.st-key-cab_busq { justify-content: space-between !important; align-items: center !important; flex-wrap: nowrap !important; }
.st-key-cab_busq button { padding: 0 0.15rem; min-height: 0; } .st-key-cab_busq button span { font-size: 1.45rem; }
[class*="st-key-cab_"] [data-testid="stMarkdownContainer"], .st-key-barra [data-testid="stMarkdownContainer"] {
  margin-bottom: 0 !important; }

/* Texto de "Acerca de" */
.acerca h4 { font-size: 1rem; font-weight: 700; margin: 1rem 0 0.3rem; }
.acerca p, .acerca li { font-size: 0.9rem; line-height: 1.5; margin: 0 0 0.3rem; }
.acerca .nota-fuente { font-size: .82rem; color: #444; background: #f7f7f7; border-radius: 8px; padding: .5rem .7rem; margin-top: .4rem; }
.acerca .atrib { display: flex; gap: .7rem; align-items: center; border: 1px solid #e2e2e2; border-radius: 10px;
  padding: .5rem .7rem; margin: .45rem 0; }
.acerca .atrib p { margin: 0; font-size: .82rem; }
.acerca .atrib img { width: 70px; flex: none; }
.acerca a.contacto { display: flex; width: fit-content; align-items: center; gap: 0.5rem; margin: 0.8rem auto 0.4rem;
  padding: 0.55rem 0.9rem; border: 1px solid #e2e2e2; border-radius: 12px; color: #111 !important;
  text-decoration: none !important; font-size: 0.9rem; font-weight: 600; }
.acerca a.contacto:hover { background: #f6f6f6; }
.acerca a.contacto svg { width: 20px; height: 20px; flex: none; }
.acerca a.contacto svg.flecha { width: 16px; height: 16px; color: #666; }

/* Pie fijo al fondo de la pantalla */
.stMainBlockContainer, .block-container { padding-bottom: 3.2rem !important; }
.pie { position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: min(460px, 100%);
  box-sizing: border-box; padding-left: 1rem !important; padding-right: 6rem !important; text-align: left !important;
  background: #fff; border-top: 1px solid #e4e4e4; padding: 0.45rem 0 0.6rem; z-index: 50;
  font-size: 0.68rem; color: #888; font-weight: 500; }

/* Imagen del inicio */
.st-key-imagen_inicio { align-items: center; }
.st-key-imagen_inicio img { max-width: 230px; margin: 0 auto; display: block; }
div[data-testid="stElementContainer"]:has(> .stHtml script):not(:has(style)) { display: none; }

/* Ajustes sobre los estilos propios de Streamlit */
.stApp p.etiqueta.campo { margin-bottom: .45rem; }
.stApp p.texto { font-size: .9rem; line-height: 1.5; margin: 0; }
.stApp p.nota { font-size: .72rem; color: #666; margin: .35rem 0 0; line-height: 1.4; }
.stApp p.sub { font-size: .78rem; font-weight: 600; color: #333; margin: .8rem 0 0; }
.stApp table.tabla { border: 0; margin: 0; }
.stApp table.tabla th, .stApp table.tabla td { border: 0; background: none; }
.stApp table.tabla th { border-bottom: 1px solid #ddd; }
.stApp table.tabla td { border-bottom: 1px solid #f0f0f0; }
[class*="st-key-fila_"] p { margin: 0 !important; line-height: 1.3; }
[class*="st-key-fila_"] { align-items: center !important; min-height: 2.2rem; }
[class*="st-key-fila_"] [data-testid="stElementContainer"] { display: flex; align-items: center; }
</style>
"""


def md(contenido: str):
    st.markdown(contenido, unsafe_allow_html=True)


# =============================================================================
# Navegación (con historial: el botón superior vuelve a la pantalla anterior)
# =============================================================================
TODOS = {"f_dist": "Todas las distribuidoras", "f_anio": "Todos los años",
         "f_genero": "Todos los géneros", "f_mpaa": "Todas las calificaciones"}
TODOS_ROLES = "Todos los roles"
ROLES = ["Actuación", "Dirección", "Guion", "Producción", "Música", "Fotografía", "Montaje", "Diseño de producción"]
ESTADO_INICIAL = {
    "pantalla": "inicio", "pel_id": None, "bio_id": None, "historia": [], "ultima": None,
    "limite": POR_PAGINA, "limite_pr": POR_PAGINA, "limite_rk": POR_PAGINA,
    "desde": None, "hasta": None, "busqueda": "", "busca_persona": "", "rol_persona": TODOS_ROLES,
    "elenco_completo": False, "bio_completa": False, "trailer_idioma": "Inglés", **TODOS,
}
PERSISTENTES = ["desde", "hasta", "busqueda", "busca_persona", "rol_persona", *TODOS]
VOLVER = {"inicio": "Volver al inicio", "por_pelicula": "Volver a explorar por película",
          "por_persona": "Volver a explorar por persona", "por_fecha": "Volver al ranking",
          "detalle": "Volver al detalle de la película", "info": "Volver a la película",
          "persona": "Volver a la persona", "acerca": "Volver a Acerca de"}


def limpiar_busqueda():
    """Vacía la búsqueda y deja todos los filtros en Todos/as."""
    st.session_state.busqueda = ""
    for clave, todos in TODOS.items():
        st.session_state[clave] = todos
    st.session_state.limite = POR_PAGINA


def ir(pantalla, **extra):
    """Avanza a otra pantalla y guarda la actual en el historial."""
    ss = st.session_state
    if pantalla == "inicio":
        ss.historia = []
    else:
        ss.historia = (ss.historia + [{"pantalla": ss.pantalla, "pel_id": ss.pel_id, "bio_id": ss.bio_id}])[-40:]
    if pantalla == "por_pelicula" and ss.pantalla == "inicio":
        limpiar_busqueda()
    if "pel_id" in extra and extra["pel_id"] != ss.pel_id:
        ss.elenco_completo = False
        ss.trailer_idioma = "Inglés"
    if "bio_id" in extra and extra["bio_id"] != ss.bio_id:
        ss.bio_completa = False
    ss.pantalla = pantalla
    ss.update(extra)


def volver():
    ss = st.session_state
    if not ss.historia:
        ss.pantalla = "inicio"
        return
    anterior = ss.historia.pop()
    if anterior.get("pel_id") != ss.pel_id:
        ss.elenco_completo = False
    ss.update(anterior)


def volver_arriba():
    """Sube al principio de la página cuando cambia la pantalla."""
    ss = st.session_state
    actual = f"{ss.pantalla}|{ss.pel_id}|{ss.bio_id}"
    if ss.ultima != actual:
        ss.ultima = actual
        st.html(f"<script>/*{actual}*/"
                "const m=document.querySelector('[data-testid=\"stMain\"]');"
                "if(m){m.scrollTo(0,0);} window.scrollTo(0,0);"
                "if(location.hash){history.replaceState(null,'',location.pathname+location.search);}</script>",
                unsafe_allow_javascript=True)


def barra_superior():
    ss = st.session_state
    anterior = ss.historia[-1]["pantalla"] if ss.historia else "inicio"
    with st.container(horizontal=True, key="barra"):
        st.button(VOLVER.get(anterior, "Volver"), icon=":material/undo:", type="tertiary", on_click=volver)
        st.button("¿Cómo le fue?", key="logo", type="tertiary", help="Ir al menú principal",
                  on_click=ir, args=("inicio",))
    md('<hr class="separador">')


def encabezado(titulo, bajada):
    md(f'<p class="titulo-pantalla">{e(titulo)}</p><p class="bajada">{e(bajada)}</p><hr class="separador">')


def pie():
    md(f'<div class="pie">Desarrollado por {e(AUTOR)}</div>')


def tarjeta(clave, contenido_html, etiqueta, on_click, args=(), kwargs=None):
    with st.container(key=f"card_{clave}"):
        md(f'<div class="tarjeta">{contenido_html}</div>')
        st.button(etiqueta, key=f"btn_{clave}", on_click=on_click, args=args, kwargs=kwargs or {},
                  width="stretch")


def kpis(items):
    celdas = "".join(
        f'<div class="kpi"><div class="kpi-tit">{e(t)}</div>'
        f'<div class="kpi-val{" sin" if v == SIN else ""}">{e(v)}</div><div class="kpi-pie">{e(p)}</div></div>'
        for t, v, p in items)
    md(f'<div class="kpis">{celdas}</div>')


def kpi_html(titulo, valor, pie_=""):
    sin = valor == SIN
    return (f'<div class="kpi"><div class="kpi-tit">{e(titulo)}</div>'
            f'<div class="kpi-val{" sin" if sin else ""}">{e(valor)}</div>'
            f'<div class="kpi-pie">{e(pie_) if pie_ and not sin else "&nbsp;"}</div></div>')


def caja(titulo, valor, pie_="", ancho=False):
    return (f'<div class="dato{" ancho" if ancho else ""}"><div class="dato-tit">{e(titulo)}</div>'
            f'<div class="dato-val">{valor}</div>{f"<div class=pie-dato>{e(pie_)}</div>" if pie_ else ""}</div>')


def imagen_ampliable(chica, grande, ancla, texto_vacio, svg):
    """Afiche o foto que, al tocarla, se abre en alta resolución a pantalla completa."""
    if vacio(chica):
        return f'<div class="afiche">{svg}<span style="color:#888">{e(texto_vacio)}</span></div>'
    grande = chica if vacio(grande) else grande
    return (f'<a id="{ancla}" class="ampliada" href="#cerrar" aria-label="Cerrar">'
            f'<img src="{e(grande)}" alt="" loading="lazy"><span>Tocá para volver</span></a>'
            f'<a class="afiche" href="#{ancla}" aria-label="Ampliar"><img src="{e(chica)}" alt=""></a>')


def estilo_grafico(fig, alto, rango_dias, eje_y="Millones de USD"):
    if rango_dias > 730:
        formato = "%Y"
    elif rango_dias > 90:
        formato = "%m/%Y"
    else:
        formato = "%d/%m"
    fig.update_layout(
        height=alto, margin=dict(l=4, r=4, t=8, b=4), separators=",.",
        paper_bgcolor="white", plot_bgcolor="white", dragmode=False,
        hovermode="x unified", showlegend=False,
        font=dict(family="Inter, sans-serif", size=11, color="#333"),
        hoverlabel=dict(bgcolor="white", font_size=12, font_color="#222", bordercolor="#ccc"),
    )
    fig.update_xaxes(tickformat=formato, hoverformat="%d/%m/%Y", showgrid=False,
                     linecolor="#999", ticks="outside", tickcolor="#999")
    fig.update_yaxes(title_text=eje_y, title_font_size=10, gridcolor="#eeeeee",
                     zeroline=False, rangemode="tozero", exponentformat="none", separatethousands=True)
    return fig


CONFIG_GRAFICO = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


# =============================================================================
# Inicio
# =============================================================================
def pantalla_inicio():
    md(f'<div class="logo logo-grande">¿Cómo le fue?</div><p class="subtitulo">{e(SUBTITULO)}</p>'
       '<hr class="separador">')
    st.write("")
    opciones = [
        ("peli", "pelicula", "Explorar por película", "Buscá títulos", "por_pelicula"),
        ("persona", "persona", "Explorar por persona", "Actores, directores y equipo técnico", "por_persona"),
        ("fecha", "calendario", "Explorar por fecha", "Las más taquilleras de un período", "por_fecha"),
        ("acerca", "info", "Acerca de este proyecto", "Investigación, fuentes y metodología", "acerca"),
    ]
    for clave, icono, titulo, sub, destino in opciones:
        tarjeta(clave, f'<div class="menu">{ICONOS[icono]}<div><div class="menu-tit">{titulo}</div>'
                       f'<div class="menu-sub">{sub}</div></div></div>',
                titulo, ir, args=(destino,))
        st.write("")
    imagen = BASE / "assets" / "claqueta.png"
    if imagen.exists():
        with st.container(key="imagen_inicio"):
            st.image(str(imagen), width=230)
    pie()


# =============================================================================
# Explorar por fecha: ranking de películas del período
# =============================================================================
def mas(clave):
    st.session_state[clave] += POR_PAGINA


def reiniciar(clave):
    st.session_state[clave] = POR_PAGINA


def pantalla_por_fecha(pel, dia, merc):
    barra_superior()
    encabezado("Explorar por fecha", "Las películas más taquilleras de un período")
    fmin, fmax = merc["fecha"].min().date(), merc["fecha"].max().date()
    if st.session_state.desde is None:        # por defecto: el último mes con datos
        st.session_state.desde, st.session_state.hasta = fmax.replace(day=1), fmax
    md('<p class="etiqueta">PERÍODO</p>')
    with st.container(horizontal=True, key="fechas"):
        st.date_input("Desde", key="desde", min_value=fmin, max_value=fmax, format="DD/MM/YYYY",
                      on_change=reiniciar, args=("limite_rk",))
        st.date_input("Hasta", key="hasta", min_value=fmin, max_value=fmax, format="DD/MM/YYYY",
                      on_change=reiniciar, args=("limite_rk",))
    desde, hasta = st.session_state.desde, st.session_state.hasta
    if desde is None or hasta is None:
        st.info("Elegí las dos fechas del período.")
        pie()
        return
    if desde > hasta:
        st.warning("La fecha desde no puede ser posterior a la fecha hasta.")
        pie()
        return
    d0, d1 = pd.Timestamp(desde), pd.Timestamp(hasta)
    tramo = dia[(dia["fecha"] >= d0) & (dia["fecha"] <= d1)]
    total = merc.loc[(merc["fecha"] >= d0) & (merc["fecha"] <= d1), "total"].sum()
    g = (tramo.groupby("id")["recaudacion"].sum().rename("rec").to_frame()
         .join(pel[["titulo", "anio", "distribuidora"]], how="inner").sort_values("rec", ascending=False))
    ndias = (d1 - d0).days + 1
    kpis([("Recaudación del mercado", millones(total) if total else SIN, "Millones de USD"),
          ("Películas", num(len(g)), f"{num(ndias)} {'día' if ndias == 1 else 'días'} de cartelera")])
    st.write("")
    md('<div class="encab-res"><p class="etiqueta">RANKING</p><span>Orden: Recaudación en el período</span></div>')
    with st.container(height=470, key="lista"):
        if g.empty:
            st.caption(SIN)
        for pos, (pid, r) in enumerate(g.head(st.session_state.limite_rk).iterrows(), start=1):
            contenido = (
                f'<div class="rk"><div class="rk-pos">{pos}</div><div class="rk-cuerpo">'
                f'<div class="res-tit">{e(r["titulo"])}</div>'
                f'<div class="res-linea">{r["anio"]} - {e(txt(r["distribuidora"]))}</div>'
                f'<div class="res-taq"><div><b>En el período:</b>&nbsp;&nbsp;<b>{millones(r["rec"])}</b></div>'
                '<span>Millones de USD</span></div></div></div>')
            tarjeta(f"rk{pid}", contenido, r["titulo"], ir, args=("detalle",), kwargs={"pel_id": int(pid)})
        if len(g) > st.session_state.limite_rk:
            st.button(f"Mostrar más ({num(len(g) - st.session_state.limite_rk)} restantes)",
                      on_click=mas, args=("limite_rk",), width="stretch")
    pie()


# =============================================================================
# Explorar por película
# =============================================================================
ORDEN_MPAA = ["G", "PG", "PG-13", "R", "NC-17", "Sin calificación"]


def mascara(pel, clave, valor):
    if clave == "f_dist":
        return pel["distribuidora"].eq(valor).to_numpy(dtype=bool)
    if clave == "f_anio":
        return pel["anio"].eq(int(valor)).to_numpy(dtype=bool)
    if clave == "f_genero":
        return pel["generos"].map(lambda gs: valor in gs).to_numpy(dtype=bool)
    return pel["mpaa"].eq(valor).to_numpy(dtype=bool)


def valores_disponibles(sub, clave):
    if clave == "f_dist":
        return sorted(sub["distribuidora"].dropna().unique(), key=normalizar)
    if clave == "f_anio":
        return [int(a) for a in sorted(sub["anio"].unique(), reverse=True)]
    if clave == "f_genero":
        return sorted({g for lista in sub["generos"] for g in lista}, key=normalizar)
    presentes = set(sub["mpaa"].dropna())
    return [m for m in ORDEN_MPAA if m in presentes]


def calcular_busqueda(pel):
    """Opciones de cada filtro según la búsqueda y los demás filtros, y películas resultantes."""
    q = normalizar(st.session_state.busqueda)
    base = pel["titulo_norm"].str.contains(q, regex=False).to_numpy(dtype=bool) if q else \
        np.ones(len(pel), dtype=bool)
    masks = {}
    for _ in range(len(TODOS)):          # descarta selecciones que dejaron de ser posibles
        activos = {c: st.session_state[c] for c in TODOS if st.session_state[c] != TODOS[c]}
        masks = {c: mascara(pel, c, v) for c, v in activos.items()}
        opciones, cambio = {}, False
        for c in TODOS:
            m = base.copy()
            for otra, mk in masks.items():
                if otra != c:
                    m &= mk
            opciones[c] = [TODOS[c]] + valores_disponibles(pel[m], c)
            if st.session_state[c] not in opciones[c]:
                st.session_state[c] = TODOS[c]
                cambio = True
        if not cambio:
            break
    final = base.copy()
    for mk in masks.values():
        final &= mk
    res = pel[final].sort_values("taquilla", ascending=False)
    return opciones, res


def pantalla_por_pelicula(pel):
    barra_superior()
    encabezado("Explorar por película", "Buscá una película y explorá su desempeño en taquilla")
    try:
        opciones, res = calcular_busqueda(pel)
        error = False
    except Exception:                   # se registra en los logs y se ofrece reiniciar
        traceback.print_exc()
        opciones = {c: [TODOS[c]] + valores_disponibles(pel, c) for c in TODOS}
        for c in TODOS:
            if st.session_state[c] not in opciones[c]:
                st.session_state[c] = TODOS[c]
        res, error = pel.iloc[0:0], True

    with st.container(horizontal=True, vertical_alignment="center", key="cab_busq"):
        md('<p class="etiqueta">BUSCAR PELÍCULA</p>')
        st.button("", icon=":material/cleaning_services:", type="tertiary", key="escoba",
                  help="Borrar búsqueda y filtros", on_click=limpiar_busqueda)
    st.text_input("Buscar película", key="busqueda", placeholder="Buscar por título...",
                  icon=":material/search:", on_change=reiniciar, args=("limite",), label_visibility="collapsed")
    md('<p class="etiqueta">FILTROS</p>')
    for clave in TODOS:
        st.selectbox(TODOS[clave], opciones[clave], key=clave, label_visibility="collapsed",
                     on_change=reiniciar, args=("limite",))

    n = len(res)
    md(f'<div class="encab-res"><p class="etiqueta">RESULTADOS</p>'
       f'<span>{num(n)} {"película" if n == 1 else "películas"} · Orden: Recaudación</span></div>')
    with st.container(height=430, key="lista"):
        if error:
            st.error("Ocurrió un error en la búsqueda. Reiniciá la búsqueda para volver a empezar.")
            st.button("Reiniciar búsqueda", icon=":material/restart_alt:", on_click=limpiar_busqueda,
                      width="stretch")
        elif n == 0:
            st.caption("No se encontraron películas con esa combinación.")
        for _, f in res.head(st.session_state.limite).iterrows():
            contenido = (
                f'<div class="res-tit">{e(f["titulo"])}</div>'
                f'<div class="res-linea">{f["anio"]} - {e(txt(f["distribuidora"]))}</div>'
                f'<div class="res-linea">Calificación: {e(txt(f["mpaa"]))}</div>'
                f'<div class="res-taq"><div><b>Taquilla:</b>&nbsp;&nbsp;<b>{millones(f["taquilla"])}</b></div>'
                f'<span>Millones de USD</span></div>')
            tarjeta(f"res{f['id']}", contenido, f["titulo"], ir, args=("detalle",),
                    kwargs={"pel_id": int(f["id"])})
        if n > st.session_state.limite:
            st.button(f"Mostrar más ({num(n - st.session_state.limite)} restantes)",
                      on_click=mas, args=("limite",), width="stretch")
    pie()


# =============================================================================
# Detalle de la película
# =============================================================================
def pantalla_detalle(pel, dia, fichas):
    barra_superior()
    f = pel.loc[st.session_state.pel_id]
    pid = int(f["id"])
    md(f'<p class="titulo-peli">{e(f["titulo"])}</p><p class="anio-peli">{f["anio"]}</p>'
       '<hr class="separador">')
    afiche = imagen_ampliable(campo(fichas, pid, "afiche"), campo(fichas, pid, "afiche_grande"),
                              "afiche-grande", "Sin afiche", SVG_AFICHE)
    md(f'<div class="cab">{afiche}<div class="cab-kpis">'
       f'{kpi_html("Total taquilla", millones(f["taquilla"]), "Millones de USD")}'
       f'{kpi_html("Recaudación apertura", millones(f["apertura"]), "Millones de USD")}'
       f'{kpi_html("Presupuesto", millones(campo(fichas, pid, "presupuesto")), "Millones de USD")}'
       '</div></div><hr class="separador">')

    serie = dia[dia["id"] == pid]
    with st.container(horizontal=True, vertical_alignment="center", key="cab_det"):
        md('<p class="seccion">Evolución de la taquilla</p>')
        with st.container(horizontal=True, vertical_alignment="center", key="acciones_det"):
            if not serie.empty:
                fila = f.to_dict()
                st.download_button(
                    "", data=lambda: grafico_descarga.generar_png(fila, serie),
                    file_name=grafico_descarga.nombre_archivo(fila), mime="image/png",
                    icon=":material/download:", type="tertiary", key="btn_descarga",
                    help="Descargar el gráfico como imagen (PNG 16:9)", on_click="ignore")
            st.button("", icon=":material/info:", type="tertiary", help="Más datos de la película",
                      key="btn_info", on_click=ir, args=("info",))
    md('<p class="seccion-sub sub-grafico">Diaria y acumulada en USD (sin ajuste por inflación)</p>')

    if serie.empty:
        st.info("Sin datos de recaudación diaria para esta película.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=serie["fecha"], y=serie["recaudacion"] / 1e6, name="Diaria",
            marker=dict(color=COLOR_DIARIA, line_width=0),
            customdata=serie[["dia", "puesto", "salas"]],
            hovertemplate=("Diaria: %{y:,.2f} M<br>Día %{customdata[0]} en cartel · "
                           "puesto %{customdata[1]} · %{customdata[2]:,} salas<extra></extra>")))
        fig.add_trace(go.Scatter(
            x=serie["fecha"], y=serie["acumulado"] / 1e6, name="Acumulada", yaxis="y2",
            mode="lines", line=dict(color=COLOR_ACUMULADA, width=2),
            hovertemplate="Acumulada: %{y:,.1f} M<extra></extra>"))
        rango = (serie["fecha"].max() - serie["fecha"].min()).days
        estilo_grafico(fig, 340, rango, eje_y="Diaria (millones de USD)")
        fig.update_layout(
            showlegend=True, legend=dict(orientation="h", y=1.08, x=0, font_size=11),
            margin=dict(t=30), bargap=0.15,
            yaxis2=dict(title_text="Acumulada (millones de USD)", title_font_size=10, overlaying="y",
                        side="right", rangemode="tozero", showgrid=False, zeroline=False,
                        tickmode="auto", nticks=5, exponentformat="none", separatethousands=True))
        st.plotly_chart(fig, config=CONFIG_GRAFICO, width="stretch")
    pie()


# =============================================================================
# Información extra de la película
# =============================================================================
def lista_personas(clave, filas, texto_vacio=SIN):
    """Nombres que llevan a la ficha de cada persona, con su rol o personaje a la derecha."""
    if not filas:
        md(f'<p class="texto" style="color:#777">{texto_vacio}</p>')
        return
    per = cargar_datos()[6]
    with st.container(key=clave):
        for i, (nombre, bio_id, detalle) in enumerate(filas):
            with st.container(horizontal=True, vertical_alignment="center", key=f"fila_{clave}{i}"):
                if bio_id in per.index:
                    st.button(nombre, key=f"{clave}_b{i}", type="tertiary", icon=":material/person:",
                              on_click=ir, args=("persona",), kwargs={"bio_id": bio_id})
                else:
                    md(f'<span class="nombre-fijo">{e(nombre)}</span>')
                md(f'<span class="rol">{e(detalle or "")}</span>')


def ventana_exclusividad(estreno, ficha):
    """Días entre el estreno en cines y la primera salida digital o en DVD / Blu-ray."""
    if vacio(estreno) or ficha is None:
        return None
    est = pd.Timestamp(estreno)
    candidatas = [(ficha.get("fecha_digital"), "digital"), (ficha.get("fecha_fisico"), "en DVD / Blu-ray")]
    candidatas = [(pd.Timestamp(d), m) for d, m in candidatas if not vacio(d) and pd.Timestamp(d) >= est]
    if not candidatas:
        return None
    salida, medio = min(candidatas)
    return (salida - est).days, est, salida, medio


def descargar_resumen_pelicula(pid):
    pel, dia, merc, fichas, lanz, cred, per = cargar_datos()
    return informes.resumen_pelicula(pid, pel, fichas, lanz, cred)


def descargar_resumen_persona(bio_id):
    pel, dia, merc, fichas, lanz, cred, per = cargar_datos()
    return informes.resumen_trayectoria(bio_id, pel, fichas, cred, per)


def ir_saga(pid):
    st.session_state.saga_eleccion = None
    ir("detalle", pel_id=pid)


def pantalla_info(pel, fichas, lanz, cred):
    barra_superior()
    f = pel.loc[st.session_state.pel_id]
    pid = int(f["id"])
    x = fichas.loc[pid].to_dict() if pid in fichas.index else {}
    def v(col):
        return None if vacio(x.get(col)) else x.get(col)

    with st.container(horizontal=True, vertical_alignment="center", key="cab_titulo"):
        md(f'<p class="titulo-peli">{e(f["titulo"])}</p><p class="anio-peli">{f["anio"]}</p>')
        st.download_button("", data=lambda: descargar_resumen_pelicula(pid),
                           file_name=informes.nombre_resumen_pelicula(f["titulo"], f["anio"]), mime="image/jpeg",
                           icon=":material/download:", type="tertiary", key="desc_resumen",
                           help="Descargar el resumen de la película (JPG, A4)", on_click="ignore")
    md('<hr class="separador">')

    # Sinopsis
    etiqueta = '<span class="tag">EN</span>' if v("sinopsis") and x.get("sinopsis_en") else ""
    md(f'<div class="sec">Sinopsis {etiqueta}</div><p class="texto">{e(v("sinopsis") or SIN)}</p>')

    # Tráiler
    md('<div class="sec">Tráiler</div>')
    trailers = {k: v(c) for k, c in (("Inglés", "trailer"), ("Español", "trailer_es")) if v(c)}
    if not trailers:
        md('<div class="sin-dato">Sin tráiler</div>')
    else:
        idioma = st.session_state.trailer_idioma if st.session_state.trailer_idioma in trailers else next(iter(trailers))
        try:
            st.video(trailers[idioma])
        except Exception:
            md('<div class="sin-dato">Sin tráiler</div>')
        if len(trailers) > 1:
            st.pills("Idioma del tráiler", list(trailers), key="trailer_idioma", label_visibility="collapsed")

    # Ficha
    generos = ", ".join(f["generos"]) if len(f["generos"]) else SIN
    md('<div class="sec">Ficha</div><div class="grid3">'
       + caja("Distribuidora", e(txt(f["distribuidora"])), ancho=True)
       + caja("Estreno", fecha(f["fecha_estreno"])) + caja("Calificación", e(txt(f["mpaa"])))
       + caja("Duración", duracion(f["duracion_min"]))
       + caja("Género", e(generos), ancho=True) + "</div>")
    if v("saga") and not vacio(x.get("saga_id")):
        saga = fichas.loc[fichas["saga_id"] == x["saga_id"], ["id"]].reset_index(drop=True).join(pel[["titulo", "anio"]], on="id", how="inner")
        saga = saga.sort_values(["anio", "titulo"])
        md(f'<div class="dato" style="margin:.45rem 0 0"><div class="dato-tit">Saga</div><div class="dato-val">{e(v("saga"))}</div>'
           f'<div class="pie-dato">{len(saga)} {"película" if len(saga) == 1 else "películas"} en la app'
           f'{" · tocá una para ver su detalle" if len(saga) > 1 else ""}</div></div>')
        if len(saga) > 1:
            with st.container(horizontal=True, key="saga"):
                for sid, t, a in saga[["id", "titulo", "anio"]].itertuples(index=False):
                    st.button(f"{t} · {a}", key=f"saga_{sid}", disabled=int(sid) == pid,
                              on_click=ir_saga, args=(int(sid),))

    # Origen
    origen = []
    if v("titulo_original") and v("titulo_original") != f["titulo"]:
        origen.append(("Título original", v("titulo_original"), False))
    origen += [("Idioma original", v("idioma_original") or SIN, False), ("Idiomas hablados", v("idiomas") or SIN, False),
               ("País de origen", v("pais_origen") or SIN, False), ("Países de producción", v("paises_produccion") or SIN, False),
               ("Productoras", v("productoras") or SIN, True)]
    md('<div class="sec">Origen</div><div class="grid">' + "".join(caja(t, e(val), ancho=a) for t, val, a in origen) + "</div>")

    # Desempeño
    mundial = v("mundial")
    pct = f" · EE. UU.: {num(100 * f['taquilla'] / mundial, 1)} %" if mundial and not vacio(f["taquilla"]) else ""
    md('<div class="sec">Desempeño en Estados Unidos</div><div class="grid">'
       + caja("Días en cartel", SIN if vacio(f["dias_cartel"]) else f"{num(f['dias_cartel'])} días")
       + caja("Mejor puesto diario", SIN if vacio(f["mejor_puesto"]) else f"N.º {int(f['mejor_puesto'])}")
       + caja("Máximo de cines", SIN if vacio(f["salas_max"]) else f"{num(f['salas_max'])} cines")
       + caja("Fin de semana de estreno", SIN if vacio(f["apertura"]) else f"{millones(f['apertura'])} M")
       + '</div><div class="sec">Contexto mundial</div><div class="grid">'
       + caja("Recaudación mundial", SIN if not mundial else f"{millones(mundial)} M", pct.strip(" ·"))
       + caja("Ranking anual mundial", SIN if vacio(f["ranking_anual"]) else f"N.º {f['ranking_anual']} de {f['anio']}")
       + '</div><p class="nota">Recaudaciones en millones de USD nominales.</p>')

    # Recepción
    critica, publico = v("critica"), v("publico")
    md('<div class="sec">Recepción</div><div class="grid">'
       + caja("Crítica (Metascore)", SIN if critica is None else f"{int(critica)} <small>/ 100</small>",
              "" if v("n_criticas") is None else f"{num(v('n_criticas'))} críticas")
       + caja("Público (IMDb)", SIN if publico is None else f"{num(publico, 1)} <small>/ 10</small>",
              "" if v("votos_total") is None else f"{num(v('votos_total'))} votos") + "</div>")
    votos = [0 if vacio(x.get(f"votos_{i}")) else float(x[f"votos_{i}"]) for i in range(1, 11)]
    total_votos = sum(votos)
    if total_votos > 0:
        md('<p class="sub">Votos del público por puntaje</p>')
        fig = go.Figure(go.Bar(
            x=[str(i) for i in range(1, 11)], y=[val / 1e3 for val in votos], marker_color=COLOR_BARRAS,
            marker_line_width=0, text=[f"{100 * val / total_votos:.0f} %" for val in votos], textposition="outside",
            textfont=dict(size=10, color="#555"), cliponaxis=False,
            hovertemplate="%{x} estrellas: %{y:,.1f} mil votos<extra></extra>"))
        fig.update_layout(height=200, margin=dict(l=4, r=4, t=18, b=4), paper_bgcolor="white", plot_bgcolor="white",
                          bargap=0.25, font=dict(family="Inter, sans-serif", size=11, color="#333"), separators=",.",
                          dragmode=False)
        fig.update_xaxes(title_text="Estrellas", title_font_size=10, type="category", linecolor="#999", fixedrange=True)
        fig.update_yaxes(title_text="Miles de votos", title_font_size=10, gridcolor="#eee", rangemode="tozero",
                         fixedrange=True)
        st.plotly_chart(fig, config=CONFIG_GRAFICO, width="stretch")

    # Recorrido
    md('<div class="sec">Recorrido</div>')
    vent = ventana_exclusividad(f["fecha_estreno"], x)
    if vent:
        dias_v, est, salida, medio = vent
        md(f'<div class="destacado"><b>{num(dias_v)} días</b> de exclusividad en cines<br><small>Del estreno '
           f'({fecha(est)}) a la primera salida {medio} ({fecha(salida)})</small></div>')
    rec = lanz[lanz["id"] == pid].sort_values("fecha")
    if rec.empty:
        md(f'<p class="texto" style="color:#777">{SIN}</p>')
    else:
        filas = "".join(f'<tr><td>{e(r.tipo)}</td><td>{fecha(r.fecha)}</td><td>{e(r.detalle or "")}</td></tr>'
                        for r in rec.itertuples())
        md(f'<table class="tabla"><thead><tr><th>Tipo</th><th>Fecha</th><th>Detalle</th></tr></thead>'
           f'<tbody>{filas}</tbody></table>')

    # Equipo y elenco
    c = cred[cred["id"] == pid]
    eq = c[c["grupo"] == "Equipo"].sort_values("orden")
    eq = [(n, b, " · ".join(dict.fromkeys(g["rol"]))) for (n, b), g in eq.groupby(["nombre", "bio_id"], sort=False)]
    md('<div class="sec">Equipo</div>')
    lista_personas("equipo", eq)
    el = c[c["grupo"] == "Elenco"].sort_values("orden")
    md(f'<div class="sec">Elenco {f"<span class=cuenta>{len(el)}</span>" if len(el) else ""}</div>')
    mostrar = el if st.session_state.elenco_completo else el.head(8)
    lista_personas("elenco", [(r.nombre, r.bio_id, r.personaje) for r in mostrar.itertuples()])
    if len(el) > 8:
        if st.session_state.elenco_completo:
            st.button("Ver menos", width="stretch", key="elenco_menos",
                      on_click=lambda: st.session_state.update(elenco_completo=False))
        else:
            st.button(f"Ver el elenco completo ({len(el)})", width="stretch", key="elenco_mas",
                      on_click=lambda: st.session_state.update(elenco_completo=True))

    # Más información
    links = [(t, u) for t, u in (("Box Office Mojo", f.get("link")), ("IMDb", v("link_imdb")), ("TMDB", v("link_tmdb")))
             if not vacio(u)]
    if links:
        md(f'<div class="sec">Más información</div><div class="links" style="grid-template-columns:repeat({len(links)},1fr)">'
           + "".join(f'<a href="{e(u)}" target="_blank" rel="noopener noreferrer">{t} ↗</a>' for t, u in links) + "</div>")
    pie()


# =============================================================================
# Personas
# =============================================================================
def roles_resumidos(roles):
    rs = [] if vacio(roles) else str(roles).split("|")
    partes = (["Actuación"] if "Actuación" in rs else []) + (["Equipo técnico"] if any(r != "Actuación" for r in rs) else [])
    return " · ".join(partes) or SIN


@st.cache_data(show_spinner=False)
def peliculas_por_rol():
    """Cantidad de películas de cada persona en cada rol (sin reestrenos)."""
    pel, _, _, _, _, cred, _ = cargar_datos()
    reestrenos = set(pel.loc[pel["titulo"].str.contains(informes.REESTRENO, na=False), "id"])
    c = cred[~cred["id"].isin(reestrenos)]
    return c.groupby(["bio_id", "rol"])["id"].nunique().unstack(fill_value=0)


def pantalla_por_persona(per):
    barra_superior()
    encabezado("Explorar por persona", "Buscá actores, directores y equipo técnico")
    md('<div style="height:.5rem"></div><p class="etiqueta campo">BUSCAR PERSONA</p>')
    st.text_input("Buscar persona", key="busca_persona", placeholder="Buscar por nombre...",
                  icon=":material/search:", label_visibility="collapsed", on_change=reiniciar, args=("limite_pr",))
    md('<div style="height:.3rem"></div><p class="etiqueta campo">FILTROS</p>')
    st.selectbox("Rol", [TODOS_ROLES] + ROLES, key="rol_persona", label_visibility="collapsed",
                 on_change=reiniciar, args=("limite_pr",))
    try:
        b = per
        q = normalizar(st.session_state.busca_persona)
        if q:
            b = b[b["nombre_norm"].str.contains(q, regex=False, na=False)]
        rol = st.session_state.rol_persona
        if rol != TODOS_ROLES:
            # Con un rol elegido, se cuentan y ordenan solo las películas en ese rol
            por_rol = peliculas_por_rol()
            cuenta = por_rol[rol] if rol in por_rol.columns else pd.Series(dtype=int)
            b = b.assign(n_peliculas=b["bio_id"].map(cuenta).fillna(0).astype(int))
            b = b[b["n_peliculas"] > 0].sort_values(["n_peliculas", "popularidad"], ascending=False)
    except Exception:
        traceback.print_exc()
        b = per.iloc[0:0]
    md(f'<div class="encab-res"><p class="etiqueta">RESULTADOS</p>'
       f'<span>{num(len(b))} {"persona" if len(b) == 1 else "personas"} · Orden: Más películas</span></div>')
    with st.container(height=540, key="lista"):
        if b.empty:
            st.caption("No se encontraron personas con esa búsqueda.")
        for r in b.head(st.session_state.limite_pr).itertuples():
            foto = f'<img src="{e(r.foto)}" alt="" loading="lazy">' if not vacio(getattr(r, "foto", None)) else SVG_PERSONA
            n = int(r.n_peliculas)
            cantidad = f'{n} {"película" if n == 1 else "películas"}'
            cantidad = f"{cantidad} en la app" if st.session_state.rol_persona == TODOS_ROLES else \
                f"{st.session_state.rol_persona}: {cantidad}"
            contenido = (f'<div class="pr-card"><div class="pr-foto">{foto}</div><div>'
                         f'<div class="res-tit">{e(r.nombre)}</div><div class="res-linea">{e(roles_resumidos(r.roles))}</div>'
                         f'<div class="res-linea">{e(cantidad)}</div></div></div>')
            tarjeta(f"pr{r.bio_id}", contenido, r.nombre, ir, args=("persona",), kwargs={"bio_id": r.bio_id})
        if len(b) > st.session_state.limite_pr:
            st.button(f"Mostrar más ({num(len(b) - st.session_state.limite_pr)} restantes)",
                      on_click=mas, args=("limite_pr",), width="stretch")
    pie()


def filmografia(bio_id, pel, cred):
    """Películas de la persona en la app (sin reestrenos), en orden cronológico."""
    c = cred[(cred["bio_id"] == bio_id)].merge(pel[["id", "titulo", "anio", "taquilla"]].reset_index(drop=True), on="id")
    c = c[~c["titulo"].str.contains(informes.REESTRENO, na=False)]
    if c.empty:
        return c
    orden = {r: i for i, r in enumerate(ROLES)}
    filas = []
    for (pid, titulo, anio, taq), g in c.groupby(["id", "titulo", "anio", "taquilla"], dropna=False, sort=False):
        roles = sorted(dict.fromkeys(g["rol"]), key=lambda r: orden.get(r, 99))
        personaje = g.loc[g["rol"] == "Actuación", "personaje"].dropna()
        filas.append({"id": pid, "titulo": titulo, "anio": anio, "taquilla": taq, "rol": " · ".join(roles),
                      "personaje": personaje.iloc[0] if len(personaje) else None})
    return pd.DataFrame(filas).sort_values(["anio", "titulo"])


def pantalla_persona(pel, cred, per):
    barra_superior()
    bio_id = st.session_state.bio_id
    if bio_id not in per.index:
        st.info("No hay datos de esta persona.")
        pie()
        return
    b = per.loc[bio_id]
    with st.container(horizontal=True, vertical_alignment="center", key="cab_titulo"):
        md(f'<p class="titulo-peli">{e(b["nombre"])}</p><p class="anio-peli">{e(b.get("lugar")) if not vacio(b.get("lugar")) else "&nbsp;"}</p>')
        st.download_button("", data=lambda: descargar_resumen_persona(bio_id),
                           file_name=informes.nombre_resumen_persona(b["nombre"]), mime="image/jpeg",
                           icon=":material/download:", type="tertiary", key="desc_persona",
                           help="Descargar el resumen de trayectoria (JPG, A4)", on_click="ignore")
    md('<hr class="separador">')

    nac, fal = b.get("nacimiento"), b.get("fallecimiento")
    tarjetas = [("Nacimiento", fecha(nac))]
    if not vacio(fal):
        tarjetas.append(("Fallecimiento", fecha(fal)))
        a = edad(nac, fal)
        tarjetas.append(("Edad", SIN if a is None else f"Falleció a los {a} años"))
    else:
        a = edad(nac)
        tarjetas.append(("Edad", SIN if a is None else f"{a} años"))
    film = filmografia(bio_id, pel, cred)
    foto = imagen_ampliable(b.get("foto"), b.get("foto_grande"), "foto-grande", "Sin foto", SVG_PERSONA)
    md(f'<div class="cab">{foto}<div class="cab-kpis">' + "".join(kpi_html(t, val) for t, val in tarjetas) + '</div></div>')
    top = b.get("top_pct")
    anios = f"{int(film['anio'].min())}–{int(film['anio'].max())}" if len(film) else ""
    md('<div class="grid" style="margin-top:.45rem">'
       + caja("Popularidad (TMDB)", SIN if vacio(top) else f"Top {int(top)} %", "" if vacio(top) else "entre las personas de la app")
       + caja("Películas en la app", str(len(film)), anios) + '</div><hr class="separador">')

    bio = b.get("biografia")
    if not vacio(bio):
        etiqueta = '<span class="tag">EN</span>' if b.get("biografia_en") else ""
        texto = str(bio)
        corto = not st.session_state.bio_completa and len(texto) > 520
        md(f'<div class="sec">Biografía {etiqueta}</div>'
           f'<p class="texto">{e(texto[:520].rsplit(" ", 1)[0] + "…" if corto else texto)}</p>')
        if len(texto) > 520:
            with st.container(key="ver_mas"):
                st.button("Ver menos" if st.session_state.bio_completa else "Ver más", type="tertiary",
                          on_click=lambda: st.session_state.update(bio_completa=not st.session_state.bio_completa))
        md('<hr class="separador">')

    md(f'<div class="sec">Películas en la app <span class="cuenta">{len(film)}</span></div>')
    if film.empty:
        md(f'<p class="texto" style="color:#777">{SIN}</p>')
    else:
        with st.container(key="filmo"):
            for i, r in enumerate(film.itertuples()):
                rol = r.rol + (f" ({r.personaje})" if not vacio(r.personaje) else "")
                with st.container(horizontal=True, vertical_alignment="center", key=f"film_{i}"):
                    md(f'<span class="f-anio">{r.anio}</span>')
                    with st.container(key=f"fcol{i}"):
                        st.button(r.titulo, key=f"pf{i}", type="tertiary", on_click=ir, args=("detalle",),
                                  kwargs={"pel_id": int(r.id)})
                        md(f'<span class="f-rol">{e(rol)}</span>')
        md('<p class="nota">En orden cronológico. No se incluyen los reestrenos.</p>')

    links = []
    if not vacio(b.get("sitio_web")):
        links.append(("Sitio web", b["sitio_web"]))
    if not vacio(b.get("imdb")):
        links.append(("IMDb", f"https://www.imdb.com/name/{b['imdb']}/"))
    if not vacio(b.get("tmdb")):
        links.append(("TMDB", f"https://www.themoviedb.org/person/{int(b['tmdb'])}"))
    if links:
        md(f'<div class="sec">Más información</div><div class="links" style="grid-template-columns:repeat({len(links)},1fr)">'
           + "".join(f'<a href="{e(u)}" target="_blank" rel="noopener noreferrer">{t} ↗</a>' for t, u in links) + "</div>")
    pie()


# =============================================================================
# Acerca de
# =============================================================================
@st.cache_data(show_spinner=False)
def logo_tmdb():
    if not LOGO_TMDB.exists():
        return ""
    return f'<img src="data:image/svg+xml;base64,{base64.b64encode(LOGO_TMDB.read_bytes()).decode()}" alt="TMDB">'


def pantalla_acerca():
    barra_superior()
    encabezado("Acerca de este proyecto", SUBTITULO)
    md(f"""<div class="acerca">
<h4>1. El proyecto</h4>
<p>Una herramienta exploratoria para analizar la evolución de la taquilla cinematográfica estadounidense, el desempeño
comercial de sus películas y la trayectoria de las personas que las hicieron.</p>
<h4>2. Fuentes de datos</h4>
<ul>
<li><b>Box Office Mojo</b> (IMDbPro): recaudación diaria y total, rankings, distribuidoras, cines, fechas de estreno y equipo técnico. Es la fuente principal.</li>
<li><b>IMDb</b>: elenco y puntajes del público y de la crítica (Metascore).</li>
<li><b>TMDB</b> (The Movie Database): sinopsis, afiches, fotos, biografías, presupuesto, sagas, idiomas, países, productoras, fechas de lanzamiento fuera de los cines y tráileres. Solo completa lo que Box Office Mojo no tiene.</li>
</ul>
<p class="nota-fuente"><b>Notas sobre los datos.</b> El presupuesto es una cifra mundial cargada por usuarios de TMDB: no es
comparable con la recaudación en Estados Unidos. Las sinopsis y biografías se muestran en español cuando existen; si no, en
inglés (marcadas con EN). Los tráileres son videos de YouTube y pueden dejar de estar disponibles.</p>
<h4>3. Cómo se construyeron los datos</h4>
<ul>
<li>Extracción de información mediante técnicas de web scraping y consultas a la API de TMDB.</li>
<li>Vinculación de cada película y cada persona entre las fuentes (por título, año, fechas y créditos), conservando siempre el valor de Box Office Mojo cuando hay diferencias.</li>
<li>Normalización, revisión de inconsistencias y preparación de series temporales.</li>
</ul>
<h4>4. Cómo interpretar los indicadores</h4>
<ul>
<li>Las recaudaciones se expresan en dólares nominales, sin ajuste por inflación.</li>
<li>La recaudación en el período suma lo que recaudó cada película entre las fechas elegidas.</li>
<li>La recaudación de apertura corresponde al primer fin de semana en cines.</li>
<li>El mejor puesto diario es la mejor posición que alcanzó la película en el ranking de un día, y el máximo de cines, la mayor cantidad de cines en que se exhibió un mismo día.</li>
<li>El ranking anual ubica a la película entre las más taquilleras del mundo en su año de estreno.</li>
<li>La ventana de exclusividad son los días entre el estreno en cines y la primera salida digital (o en DVD / Blu-ray).</li>
<li>La popularidad de una persona indica su posición entre todas las personas de la app según el índice de TMDB.</li>
</ul>
<h4>5. Alcances y limitaciones</h4>
<p>La cobertura depende de las fuentes y de los registros disponibles. Algunas películas no tienen serie de recaudación
diaria o les faltan datos de su ficha; en esos casos la app lo indica con «{SIN}». Los reestrenos no se cuentan en las
filmografías.</p>
<h4>6. Autor</h4>
<p>Martín Nicolás Serafini, a cargo del diseño y desarrollo de la aplicación y de la recopilación y el procesamiento de los
datos. La aplicación acompaña su Proyecto Integrador sobre la reconfiguración del mercado del cine en Estados Unidos
(Licenciatura en Administración, Facultad de Ciencias Económicas, Universidad de Buenos Aires).</p>
<h4>7. Créditos y atribuciones</h4>
<div class="atrib">{logo_tmdb()}<p>This product uses the TMDB API but is not endorsed or certified by TMDB.</p></div>
<div class="atrib"><p>Information courtesy of IMDb (<a href="https://www.imdb.com" target="_blank" rel="noopener noreferrer">https://www.imdb.com</a>). Used with permission.</p></div>
<div class="atrib"><p>Datos de taquilla: Box Office Mojo by IMDbPro (<a href="https://www.boxofficemojo.com" target="_blank" rel="noopener noreferrer">boxofficemojo.com</a>).</p></div>
</div>""")
    if MOSTRAR_CONTACTO and LINKEDIN:
        md(f'''<div class="acerca"><a class="contacto" href="{LINKEDIN}"
   target="_blank" rel="noopener noreferrer">
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
 stroke-linejoin="round"><path d="M4 4h16v16H4z"/><path d="M8 11v5M8 8v.01M12 16v-5M12 13a2 2 0 0 1 4 0v3"/></svg>
<span>Contactar vía LinkedIn</span>
<svg class="flecha" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
 stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M9 7h8v8"/></svg>
</a>
</div>''')
    pie()


# =============================================================================
# Principal
# =============================================================================
def main():
    md(CSS.replace("__FUENTE_LOGO__", fuente_logo()))
    ss = st.session_state
    for clave, valor in ESTADO_INICIAL.items():
        ss.setdefault(clave, valor.copy() if isinstance(valor, list) else valor)
    for clave in PERSISTENTES:       # evita que Streamlit borre los valores al cambiar de pantalla
        ss[clave] = ss[clave]

    pel, dia, merc, fichas, lanz, cred, per = cargar_datos()
    pantalla = ss.pantalla
    if pantalla in ("detalle", "info") and ss.pel_id not in pel.index:
        pantalla = ss.pantalla = "por_pelicula"
    if pantalla == "persona" and ss.bio_id not in per.index:
        pantalla = ss.pantalla = "por_persona"
    volver_arriba()

    pantallas = {
        "inicio": pantalla_inicio,
        "por_fecha": lambda: pantalla_por_fecha(pel, dia, merc),
        "por_pelicula": lambda: pantalla_por_pelicula(pel),
        "detalle": lambda: pantalla_detalle(pel, dia, fichas),
        "info": lambda: pantalla_info(pel, fichas, lanz, cred),
        "por_persona": lambda: pantalla_por_persona(per),
        "persona": lambda: pantalla_persona(pel, cred, per),
        "acerca": pantalla_acerca,
    }
    try:
        pantallas.get(pantalla, pantalla_inicio)()
    except Exception:                 # cualquier dato inesperado: se registra y se ofrece volver
        traceback.print_exc()
        st.error("No se pudo mostrar esta pantalla.")
        st.button("Volver al inicio", icon=":material/home:", on_click=ir, args=("inicio",), width="stretch")


main()
