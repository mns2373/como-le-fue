"""
¿Cómo le fue? · Taquilla del cine en Estados Unidos (2003–2025)

App de consulta para la defensa del Proyecto Integrador.
Ejecutar localmente:   streamlit run app.py
Datos: ./data/*.parquet (generados con preparar_datos.py)
"""
import html
import traceback
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# Configuración general (lo único que suele hacer falta tocar)
# =============================================================================
AUTOR = "Martín Nicolás Serafini"
SUBTITULO = "Taquilla del cine en Estados Unidos · 2003–2025"
POR_PAGINA = 20                      # resultados que se suman con "Mostrar más"
COLORES = {                          # series del gráfico (validadas para daltonismo)
    "Mercado total": "#2F80D0",
    "Top 1": "#D6453D",
    "Top 10": "#1F8F5C",
}
COLOR_DIARIA = "#2F80D0"
COLOR_ACUMULADA = "#1F8F5C"
DATA = Path(__file__).parent / "data"

st.set_page_config(page_title="¿Cómo le fue?", page_icon="🎬", layout="centered",
                   initial_sidebar_state="collapsed")


# =============================================================================
# Datos
# =============================================================================
@st.cache_data(show_spinner=False)
def cargar_datos():
    pel = pd.read_parquet(DATA / "peliculas.parquet")
    pel["generos"] = pel["generos"].map(list)
    dia = pd.read_parquet(DATA / "diaria.parquet")
    merc = pd.read_parquet(DATA / "mercado.parquet")
    return pel, dia, merc


def normalizar(texto) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower().strip()


# =============================================================================
# Formatos (convención argentina: punto de miles, coma decimal)
# =============================================================================
def num(x, dec=0):
    if x is None or pd.isna(x):
        return "Sin dato"
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def millones(x):
    if x is None or pd.isna(x):
        return "Sin dato"
    m = x / 1e6
    return num(m, 0 if m >= 1000 else 1)


def fecha(f):
    return "Sin dato" if f is None or pd.isna(f) else pd.Timestamp(f).strftime("%d/%m/%Y")


def txt(x, sufijo=""):
    return "Sin dato" if x is None or (not isinstance(x, list) and pd.isna(x)) else f"{x}{sufijo}"


def e(x):
    return html.escape(str(x))


# =============================================================================
# Estilos
# =============================================================================
ICONOS = {
    "calendario": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/></svg>',
    "pelicula": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.2"/><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/></svg>',
    "info": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lobster&display=swap');

.stApp, .stApp p, .stApp div, .stApp label, .stApp input, .stApp button, .stApp li {
  font-family: 'Inter', system-ui, sans-serif;
}
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
.stMainBlockContainer, .block-container { max-width: 460px; padding-top: 0.6rem !important;
  padding-left: 1rem !important; padding-right: 1rem !important; }
[data-testid="stVerticalBlock"] { gap: 0.7rem; }

/* Marca */
.logo { font-family: 'Lobster', cursive; font-style: italic; line-height: 1; color: #111; }
.logo-grande { font-size: 2.6rem; text-align: center; margin-top: 0.8rem; }
.logo-chico { font-size: 1.15rem; white-space: nowrap; }
.subtitulo { text-align: center; font-weight: 600; font-size: 0.7rem; white-space: nowrap; margin: 0.3rem 0 0; }
.separador { border: 0 !important; border-top: 1px solid #e4e4e4 !important; margin: 0.5rem -1rem !important; }

/* Barra superior: volver + logo */
.st-key-barra, .st-key-cab_det { justify-content: space-between !important; align-items: center !important; flex-wrap: nowrap !important; gap: 0.4rem !important; }
.st-key-barra [data-testid="stElementContainer"] { width: auto !important; }
.st-key-barra button { padding: 0; min-height: 0; color: #111; }
.st-key-barra button p { font-size: 0.78rem !important; font-weight: 600; white-space: nowrap; }

/* Encabezados de pantalla */
.stMarkdown p.titulo-pantalla { text-align: center; font-size: 1.6rem; font-weight: 700; line-height: 1.15; margin: 0; }
.stMarkdown p.bajada { text-align: center; font-size: 0.82rem; font-weight: 600; margin: 0.2rem 0 0; line-height: 1.3; }
.stMarkdown p.titulo-peli { font-size: 1.4rem; font-weight: 700; line-height: 1.15; margin: 0; }
.stMarkdown p.anio-peli { font-size: 0.84rem; font-weight: 600; margin: 0.15rem 0 0; }
.stMarkdown p.seccion { font-weight: 700; font-size: 0.98rem; margin: 0; line-height: 1.3; }
.stMarkdown p.seccion-sub { font-size: 0.74rem; font-weight: 600; color: #333; margin: 0; }
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

/* Resultados de búsqueda */
.res-tit { font-weight: 700; font-size: 1.05rem; line-height: 1.2; margin-bottom: 0.25rem; }
.res-linea { font-size: 0.85rem; color: #222; line-height: 1.45; }
.res-taq { display: flex; justify-content: space-between; align-items: baseline; gap: .5rem;
  font-size: 0.86rem; margin-top: 0.15rem; }
.res-taq span { font-size: 0.8rem; color: #444; }
[class*="st-key-card_res"] { margin-bottom: 0.45rem; }
.res-taq b { font-weight: 700; }
.encab-res { display: flex; justify-content: space-between; align-items: baseline; }
.encab-res span { font-size: 0.74rem; color: #444; }
.st-key-lista { border: 1px solid #e2e2e2; border-radius: 12px; padding: 0.5rem; }
.st-key-lista [data-testid="stVerticalBlock"] { gap: 0.45rem; }

/* Indicadores */
.kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 0.55rem; }
.kpi { border: 1px solid #e2e2e2; border-radius: 10px; padding: 0.5rem 0.7rem; }
.kpi-tit { font-size: 0.72rem; font-weight: 600; }
.kpi-val { font-size: 1.15rem; font-weight: 700; line-height: 1.35; }
.kpi-pie { font-size: 0.7rem; color: #444; }

/* Ficha */
.dato { border: 1px solid #e2e2e2; border-radius: 10px; padding: 0.4rem 0.75rem; margin-bottom: 0.45rem; }
.dato-tit { font-size: 0.72rem; font-weight: 600; }
.dato-val { font-size: 1.02rem; font-weight: 700; }

/* Recuadro del período */
.periodo { border: 1px solid #e2e2e2; border-radius: 12px; padding: 0.8rem 1rem; }
.periodo-val { font-size: 1.25rem; font-weight: 700; margin: 0.25rem 0; }
.periodo-pie { font-size: 0.84rem; color: #333; }

/* Botones negros */
.stButton button[kind="primary"], .stLinkButton a[kind="primary"] {
  background: #3a3a3a; border-color: #3a3a3a; border-radius: 12px; min-height: 3.1rem;
  font-weight: 600; color: #fff;
}
.stButton button[kind="primary"]:hover, .stLinkButton a[kind="primary"]:hover { background: #111; border-color: #111; }
.stButton button[kind="primary"] p, .stLinkButton a[kind="primary"] p { font-weight: 600; font-size: 0.95rem; }

/* Chips de series: punto de color antes de cada etiqueta */
.st-key-series button { font-size: 0.78rem; }
.st-key-series button::before { content: ""; width: 9px; height: 9px; border-radius: 50%;
  display: inline-block; margin-right: 6px; background: var(--chip); }
.st-key-series button:nth-of-type(1) { --chip: #2F80D0; }
.st-key-series button:nth-of-type(2) { --chip: #D6453D; }
.st-key-series button:nth-of-type(3) { --chip: #1F8F5C; }

/* Texto de "Acerca de" */
.acerca h4 { font-size: 1rem; font-weight: 700; margin: 1rem 0 0.3rem; }
.acerca p, .acerca li { font-size: 0.9rem; line-height: 1.5; margin: 0 0 0.3rem; }

/* Pie fijo al fondo de la pantalla */
.stMainBlockContainer, .block-container { padding-bottom: 3.2rem !important; }
.pie { position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: min(460px, 100%);
  background: #fff; border-top: 1px solid #e4e4e4; padding: 0.45rem 0 0.6rem; z-index: 50;
  text-align: center; font-size: 0.68rem; color: #888; font-weight: 500; }

/* Logo de la barra: vuelve al menú principal */
.st-key-logo button { padding: 0; min-height: 0; }
.st-key-logo button p { font-family: 'Lobster', cursive !important; font-size: 1.15rem !important;
  font-style: italic; font-weight: 400 !important; color: #111; white-space: nowrap; }

/* Encabezados con botones a la derecha (zoom, información, escoba) */
.st-key-cab_fecha, .st-key-cab_busq { justify-content: space-between !important;
  align-items: center !important; flex-wrap: nowrap !important; }
.st-key-zoom { gap: 0.15rem !important; align-items: center !important; flex-wrap: nowrap !important;
  width: auto !important; }
.st-key-zoom button, .st-key-cab_busq button, .st-key-cab_det button { padding: 0 0.15rem; min-height: 0; }
.st-key-zoom button span, .st-key-cab_busq button span { font-size: 1.45rem; }
[class*="st-key-cab_"] [data-testid="stMarkdownContainer"],
.st-key-zoom [data-testid="stMarkdownContainer"], .st-key-barra [data-testid="stMarkdownContainer"] {
  margin-bottom: 0 !important; }
.zoom-nivel { font-size: 0.72rem; font-weight: 600; color: #444; min-width: 3.6rem; text-align: center;
  line-height: 1; margin-top: -6px; }
.st-key-series { margin-top: 0.35rem; }

/* Imagen del inicio */
.st-key-imagen_inicio { align-items: center; }
.st-key-imagen_inicio img { max-width: 230px; margin: 0 auto; display: block; }
div[data-testid="stElementContainer"]:has(> .stHtml script):not(:has(style)) { display: none; }
</style>
"""


def md(contenido: str):
    st.markdown(contenido, unsafe_allow_html=True)


# =============================================================================
# Navegación
# =============================================================================
TODOS = {"f_dist": "Todas las distribuidoras", "f_anio": "Todos los años",
         "f_genero": "Todos los géneros", "f_mpaa": "Todas las calificaciones"}
ESCALAS = ["Días", "Semanas", "Meses", "Años"]
ESTADO_INICIAL = {
    "pantalla": "inicio", "pel_id": None, "limite": POR_PAGINA, "ultima": None,
    "desde": None, "hasta": None, "series": list(COLORES), "escala": None,
    "busqueda": "", "error_busqueda": False, **TODOS,
}
PERSISTENTES = ["desde", "hasta", "series", "busqueda", *TODOS]


def limpiar_busqueda():
    """Vacía la búsqueda y deja todos los filtros en Todos/as."""
    st.session_state.busqueda = ""
    for clave, todos in TODOS.items():
        st.session_state[clave] = todos
    st.session_state.limite = POR_PAGINA
    st.session_state.error_busqueda = False


def ir(pantalla, **extra):
    st.session_state.pantalla = pantalla
    st.session_state.update(extra)
    if pantalla == "por_pelicula":        # cada vez que se entra, la búsqueda arranca limpia
        limpiar_busqueda()


def volver_arriba():
    """Sube al principio de la página cuando cambia la pantalla."""
    if st.session_state.ultima != st.session_state.pantalla:
        st.session_state.ultima = st.session_state.pantalla
        st.html(f"<script>/*{st.session_state.pantalla}*/"
                "const m=document.querySelector('[data-testid=\"stMain\"]');"
                "if(m){m.scrollTo(0,0);} window.scrollTo(0,0);</script>",
                unsafe_allow_javascript=True)


def barra_superior(texto, destino):
    with st.container(horizontal=True, key="barra"):
        st.button(texto, icon=":material/undo:", type="tertiary", on_click=ir, args=(destino,))
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
        f'<div class="kpi-val">{e(v)}</div><div class="kpi-pie">{e(p)}</div></div>'
        for t, v, p in items)
    md(f'<div class="kpis">{celdas}</div>')


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
                     zeroline=False, rangemode="tozero")
    return fig


CONFIG_GRAFICO = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


# =============================================================================
# Pantallas
# =============================================================================
def pantalla_inicio():
    md(f'<div class="logo logo-grande">¿Cómo le fue?</div><p class="subtitulo">{e(SUBTITULO)}</p>'
       '<hr class="separador">')
    st.write("")
    opciones = [
        ("fecha", "calendario", "Explorar por fecha", "La evolución de la recaudación", "por_fecha"),
        ("peli", "pelicula", "Explorar por película", "Buscá títulos", "por_pelicula"),
        ("acerca", "info", "Acerca de este proyecto", "Investigación, fuentes y metodología", "acerca"),
    ]
    for clave, icono, titulo, sub, destino in opciones:
        tarjeta(clave, f'<div class="menu">{ICONOS[icono]}<div><div class="menu-tit">{titulo}</div>'
                       f'<div class="menu-sub">{sub}</div></div></div>',
                titulo, ir, args=(destino,))
        st.write("")
    imagen = Path(__file__).parent / "assets" / "claqueta.png"
    if imagen.exists():
        with st.container(key="imagen_inicio"):
            st.image(str(imagen), width=230)
    pie()


def pantalla_por_fecha(merc):
    barra_superior("Volver al inicio", "inicio")
    encabezado("Explorar por fecha", "Elegí el período que querés analizar")
    fmin, fmax = merc["fecha"].min().date(), merc["fecha"].max().date()
    if st.session_state.desde is None:
        st.session_state.desde, st.session_state.hasta = fmin, fmax
    st.write("")
    st.date_input("FECHA DESDE", key="desde", min_value=fmin, max_value=fmax, format="DD/MM/YYYY")
    st.date_input("FECHA HASTA", key="hasta", min_value=fmin, max_value=fmax, format="DD/MM/YYYY")
    desde, hasta = st.session_state.desde, st.session_state.hasta
    st.write("")
    md(f'<div class="periodo"><div class="etiqueta">PERÍODO SELECCIONADO</div>'
       f'<div class="periodo-val">{fecha(desde)} – {fecha(hasta)}</div>'
       f'<div class="periodo-pie">Podés cambiar ambas fechas</div></div>')
    invertido = desde > hasta
    if invertido:
        st.warning("La fecha desde no puede ser posterior a la fecha hasta.")
    st.write("")
    st.button("Ver evolución de la taquilla", icon=":material/arrow_forward:", icon_position="right",
              type="primary", width="stretch", disabled=invertido,
              on_click=ir, args=("resultados_fecha",), kwargs={"escala": None})
    pie()


# ---------- Resultados por fecha ----------
ADJETIVO = {"Días": "diaria", "Semanas": "semanal", "Meses": "mensual", "Años": "anual"}
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def escala_sugerida(dias):
    """Escala inicial según la extensión del período (después se cambia con la lupa)."""
    if dias <= 183:
        return "Días"
    if dias <= 3 * 365:
        return "Semanas"
    if dias <= 10 * 365:
        return "Meses"
    return "Años"


def cambiar_escala(paso):
    i = ESCALAS.index(st.session_state.escala) + paso
    st.session_state.escala = ESCALAS[max(0, min(i, len(ESCALAS) - 1))]


def agrupar(tramo, escala):
    """Suma la recaudación por día, semana (viernes a jueves), mes o año y arma el texto del recuadro."""
    t = tramo.copy()
    if "dia_semana" not in t:           # por si data/mercado.parquet es de una versión anterior
        t["dia_semana"] = t["fecha"].dt.weekday.map(dict(enumerate(DIAS)))
    if "evento" not in t:
        t["evento"] = ""
    t["evento"] = t["evento"].fillna("")
    if escala == "Días":
        t["x"] = t["fecha"]
        t["detalle"] = t["dia_semana"] + t["evento"].map(lambda v: f"<br>Feriado / evento: {v}" if v else "")
        return t
    if escala == "Semanas":     # semana de taquilla: de viernes a jueves
        t["x"] = t["fecha"] - pd.to_timedelta((t["fecha"].dt.weekday - 4) % 7, unit="D")
    elif escala == "Meses":
        t["x"] = t["fecha"].dt.to_period("M").dt.start_time
    else:
        t["x"] = t["fecha"].dt.to_period("Y").dt.start_time
    g = t.groupby("x").agg(total=("total", "sum"), top1=("top1", "sum"), top10=("top10", "sum"),
                           ini=("fecha", "min"), fin=("fecha", "max"), dias=("fecha", "size"),
                           eventos=("evento", lambda v: " · ".join(dict.fromkeys(x for x in v if x))))
    g = g.reset_index()

    def texto(r):
        if escala == "Semanas":
            base = f"Semana del {r.ini:%d/%m} al {r.fin:%d/%m/%Y}"
            completo = r.dias == 7
        elif escala == "Meses":
            base = f"{MESES[r.x.month - 1].capitalize()} de {r.x.year}"
            completo = r.dias == r.x.days_in_month
        else:
            base = f"Año {r.x.year}"
            completo = r.dias >= 365
        if not completo:
            base += f" (parcial, {r.dias} días)"
        if escala == "Semanas" and r.eventos:
            base += f"<br>Feriado / evento: {r.eventos}"
        return base

    g["detalle"] = g.apply(texto, axis=1)
    return g


def pantalla_resultados_fecha(merc):
    barra_superior("Volver a explorar por fecha", "por_fecha")
    desde, hasta = st.session_state.desde, st.session_state.hasta
    encabezado("Resultados por fecha", f"Estados Unidos · {fecha(desde)}–{fecha(hasta)}")
    tramo = merc[(merc["fecha"] >= pd.Timestamp(desde)) & (merc["fecha"] <= pd.Timestamp(hasta))]
    if st.session_state.escala is None:
        st.session_state.escala = escala_sugerida((hasta - desde).days)
    escala = st.session_state.escala
    i = ESCALAS.index(escala)

    with st.container(horizontal=True, vertical_alignment="center", key="cab_fecha"):
        md(f'<p class="seccion">Recaudación {ADJETIVO[escala]}</p>'
           '<p class="seccion-sub">Recaudación total del mercado</p>')
        with st.container(horizontal=True, vertical_alignment="center", key="zoom"):
            st.button("", icon=":material/zoom_out:", type="tertiary", key="zoom_menos",
                      help="Alejar: agrupar en períodos más largos", disabled=i == len(ESCALAS) - 1,
                      on_click=cambiar_escala, args=(1,))
            md(f'<div class="zoom-nivel">{escala}</div>')
            st.button("", icon=":material/zoom_in:", type="tertiary", key="zoom_mas",
                      help="Acercar: agrupar en períodos más cortos", disabled=i == 0,
                      on_click=cambiar_escala, args=(-1,))

    elegidas = st.session_state.series or []
    columnas = {"Mercado total": "total", "Top 1": "top1", "Top 10": "top10"}
    if not elegidas:
        st.info("Elegí al menos una serie para graficar.")
    else:
        g = agrupar(tramo, escala)
        traza = go.Scatter
        modo = "lines" if len(g) > 60 else "lines+markers"
        fig = go.Figure()
        # Traza invisible: agrega día de la semana, feriado o período debajo de la fecha del recuadro
        fig.add_trace(go.Scatter(x=g["x"], y=[0] * len(g), yaxis="y2", mode="markers",
                                 marker=dict(color="rgba(0,0,0,0)", size=1), customdata=g["detalle"],
                                 hovertemplate="%{customdata}<extra></extra>", showlegend=False))
        for nombre in ["Mercado total", "Top 10", "Top 1"]:   # el total queda detrás
            if nombre not in elegidas:
                continue
            extra = dict(hovertemplate=f"%{{y:,.1f}} M<extra>{nombre}</extra>")
            if nombre == "Top 1" and escala == "Días":
                extra = dict(customdata=g["pelicula_1"],
                             hovertemplate="%{y:,.1f} M · %{customdata}<extra>Top 1</extra>")
            fig.add_trace(traza(x=g["x"], y=g[columnas[nombre]] / 1e6, name=nombre, mode=modo,
                                line=dict(color=COLORES[nombre], width=1.8),
                                marker=dict(size=6, color=COLORES[nombre]), **extra))
        estilo_grafico(fig, 360, (hasta - desde).days)
        formato_hover = {"Días": "%d/%m/%Y", "Semanas": "%d/%m/%Y", "Meses": "%m/%Y", "Años": "%Y"}[escala]
        fig.update_xaxes(hoverformat=formato_hover)
        fig.update_layout(yaxis2=dict(overlaying="y", visible=False, range=[0, 1], fixedrange=True))
        st.plotly_chart(fig, config=CONFIG_GRAFICO, width="stretch")

    md('<p class="seccion">Comparar recaudación</p>')
    st.pills("Series", list(COLORES), selection_mode="multi", key="series", label_visibility="collapsed")

    total = tramo["total"].sum()
    md('<hr class="separador"><p class="seccion">Indicadores del período</p>')
    kpis([
        ("Total taquilla", millones(total), "Millones de USD"),
        ("Días acumulados", num(len(tramo)), "Días en el período"),
        ("% Top 1", f"{num(100 * tramo['top1'].sum() / total, 1)} %" if total else "Sin dato", "Sobre el total"),
        ("% Top 10", f"{num(100 * tramo['top10'].sum() / total, 1)} %" if total else "Sin dato", "Sobre el total"),
    ])
    pie()


# ---------- Explorar por película ----------
ORDEN_MPAA = ["G", "PG", "PG-13", "R", "NC-17", "Sin calificación"]


def mas_resultados():
    st.session_state.limite += POR_PAGINA


def reiniciar_limite():
    st.session_state.limite = POR_PAGINA


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
    barra_superior("Volver al inicio", "inicio")
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
                  icon=":material/search:", on_change=reiniciar_limite, label_visibility="collapsed")
    md('<p class="etiqueta">FILTROS</p>')
    for clave in TODOS:
        st.selectbox(TODOS[clave], opciones[clave], key=clave, label_visibility="collapsed",
                     on_change=reiniciar_limite)

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
                      on_click=mas_resultados, width="stretch")
    pie()


def pantalla_detalle(pel, dia):
    barra_superior("Volver a explorar por película", "por_pelicula")
    f = pel.loc[st.session_state.pel_id]
    md(f'<p class="titulo-peli">{e(f["titulo"])}</p><p class="anio-peli">{f["anio"]}</p>'
       '<hr class="separador">')
    with st.container(horizontal=True, vertical_alignment="center", key="cab_det"):
        md('<p class="seccion">Evolución de la taquilla</p>'
           '<p class="seccion-sub">Recaudación diaria y acumulada</p>')
        st.button("", icon=":material/info:", type="tertiary", help="Más datos de la película",
                  key="btn_info", on_click=ir, args=("info",))

    serie = dia[dia["id"] == f["id"]]
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
                        tickmode="auto", nticks=5))
        st.plotly_chart(fig, config=CONFIG_GRAFICO, width="stretch")

    md('<hr class="separador"><p class="seccion">¿Cómo le fue?</p>')
    kpis([("Total taquilla", millones(f["taquilla"]), "Millones de USD"),
          ("Recaudación apertura", millones(f["apertura"]), "Millones de USD")])
    pie()


def pantalla_info(pel):
    barra_superior("Volver al detalle de la película", "detalle")
    f = pel.loc[st.session_state.pel_id]
    md(f'<p class="titulo-peli">{e(f["titulo"])}</p><p class="anio-peli">{f["anio"]}</p>'
       '<hr class="separador">')
    dur = f["duracion_min"]
    datos = [
        ("Distribuidora", txt(f["distribuidora"])),
        ("Fecha de lanzamiento", fecha(f["fecha_estreno"])),
        ("Género", ", ".join(f["generos"]) if len(f["generos"]) else "Sin dato"),
        ("Calificación", txt(f["mpaa"])),
        ("Duración", "Sin dato" if pd.isna(dur) else f"{int(dur)} minutos ({int(dur) // 60} h {int(dur) % 60:02d} min)"),
        ("Días en cartel", "Sin dato" if pd.isna(f["dias_cartel"]) else f"{num(f['dias_cartel'])} días"),
        ("Mejor puesto en la taquilla diaria", "Sin dato" if pd.isna(f["mejor_puesto"]) else f"N.º {int(f['mejor_puesto'])}"),
        ("Ranking anual mundial", f"N.º {f['ranking_anual']} de {f['anio']}"),
        ("Máxima cantidad de cines donde se exhibió", "Sin dato" if pd.isna(f["salas_max"]) else f"{num(f['salas_max'])} cines"),
    ]
    md("".join(f'<div class="dato"><div class="dato-tit">{e(t)}</div><div class="dato-val">{e(v)}</div></div>'
               for t, v in datos))
    st.link_button("Visitar Box Office Mojo", f["link"], icon=":material/arrow_forward:",
                   icon_position="right", type="primary", width="stretch")
    pie()


def pantalla_acerca():
    barra_superior("Volver al menú principal", "inicio")
    encabezado("Acerca de este proyecto", SUBTITULO)
    md("""
<div class="acerca">
<h4>1. El proyecto</h4>
<p>Una herramienta exploratoria para analizar la evolución de la taquilla cinematográfica
estadounidense y el desempeño comercial de sus películas. Acompaña el Proyecto Integrador
sobre la reconfiguración del mercado del cine en Estados Unidos (Licenciatura en
Administración, Facultad de Ciencias Económicas, Universidad de Buenos Aires).</p>
<h4>2. Fuentes de datos</h4>
<p>Box Office Mojo: recaudación diaria, rankings y atributos de las películas.</p>
<h4>3. Cómo se construyeron los datos</h4>
<ul>
<li>Extracción de información mediante técnicas de web scraping.</li>
<li>Integración de registros de taquilla, fechas y atributos de las películas.</li>
<li>Normalización, revisión de inconsistencias y preparación de series temporales.</li>
</ul>
<h4>4. Cómo interpretar los indicadores</h4>
<ul>
<li>Las recaudaciones se expresan en dólares nominales, sin ajuste por inflación.</li>
<li>Top 1 y Top 10 suman lo recaudado cada día por la película más vista y por las diez más vistas.</li>
<li>El mejor puesto diario es la mejor posición que alcanzó la película en el ranking de un día.</li>
<li>El ranking anual ubica a la película entre las más taquilleras del mundo en su año de estreno.</li>
<li>La recaudación de apertura corresponde al primer fin de semana en cines.</li>
</ul>
<h4>5. Alcances y limitaciones</h4>
<p>La cobertura depende de las fuentes y de los registros disponibles. Algunas películas no tienen
serie de recaudación diaria o les faltan datos de su ficha. Las diferencias entre fuentes y los
criterios de procesamiento pueden afectar las comparaciones.</p>
</div>""")
    pie()


# =============================================================================
# Principal
# =============================================================================
def main():
    md(CSS)
    for clave, valor in ESTADO_INICIAL.items():
        st.session_state.setdefault(clave, valor)
    for clave in PERSISTENTES:       # evita que Streamlit borre los valores al cambiar de pantalla
        st.session_state[clave] = st.session_state[clave]

    pel, dia, merc = cargar_datos()
    pantalla = st.session_state.pantalla
    if pantalla in ("detalle", "info") and st.session_state.pel_id is None:
        pantalla = st.session_state.pantalla = "por_pelicula"
    if pantalla == "resultados_fecha" and st.session_state.desde is None:
        pantalla = st.session_state.pantalla = "por_fecha"
    volver_arriba()

    {
        "inicio": pantalla_inicio,
        "por_fecha": lambda: pantalla_por_fecha(merc),
        "resultados_fecha": lambda: pantalla_resultados_fecha(merc),
        "por_pelicula": lambda: pantalla_por_pelicula(pel),
        "detalle": lambda: pantalla_detalle(pel, dia),
        "info": lambda: pantalla_info(pel),
        "acerca": pantalla_acerca,
    }[pantalla]()


main()
