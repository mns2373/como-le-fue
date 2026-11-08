"""
Resúmenes descargables en formato A4 (JPG, 300 ppp, fondo blanco):
    - "Resumen de la película"
    - "Resumen de trayectoria" de una persona

Se dibujan con Pillow (y matplotlib para los gráficos), sin navegador, para que funcionen
en Streamlit Community Cloud. Si falta un dato se muestra "Sin datos."; si no se puede
descargar el afiche o la foto, se deja un recuadro gris.
"""
import io
import re
import unicodedata
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FUENTES = Path(__file__).parent / "assets" / "fuentes"
S = 2                                    # 1240 x 1754 px de diseño -> 2480 x 3508 px (A4 a 300 ppp)
ANCHO, ALTO = 1240, 1754
SIN = "Sin datos."
NEGRO, GRIS, GRIS_CLARO, BORDE, FONDO_LAT = "#111111", "#555555", "#888888", "#DDDDDD", "#F5F5F5"
AZUL, VERDE = "#2F80D0", "#1F8F5C"
SUBTITULO = "Taquilla del cine en Estados Unidos · 2003–2025"
AUTOR = "Martín Nicolás Serafini"
REESTRENO = re.compile(r"(?i)re-?release|anniversary|\b3d\b release|remaster")
ATRIB_TMDB = "This product uses the TMDB API but is not endorsed or certified by TMDB."
ATRIB_IMDB = "Information courtesy of IMDb (https://www.imdb.com). Used with permission."

for _f in ("Inter-Regular.otf", "Inter-Bold.otf"):
    if (FUENTES / _f).exists():
        font_manager.fontManager.addfont(str(FUENTES / _f))


# =============================================================================
# Utilidades
# =============================================================================
def hoy():
    """Fecha de Buenos Aires (el servidor suele estar en UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
    except Exception:
        return date.today()


def vacio(v):
    if v is None:
        return True
    try:
        return bool(pd.isna(v)) or (isinstance(v, str) and not v.strip())
    except (TypeError, ValueError):
        return False


def n(x, d=0):
    return SIN if vacio(x) else f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def m(x):
    return SIN if vacio(x) else f"{n(x / 1e6, 1)} M"


def fa(v):
    return SIN if vacio(v) else pd.Timestamp(v).strftime("%d/%m/%Y")


def slug(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_") or "resumen"


def nombre_resumen_pelicula(titulo, anio):
    return f"resumen_{slug(titulo)}_{anio}.jpg"


def nombre_resumen_persona(nombre):
    return f"resumen_trayectoria_{slug(nombre)}.jpg"


def P(v):
    return int(round(v * S))


@lru_cache(maxsize=64)
def fuente(tam, negrita=False, logo=False):
    archivo = "OleoScript-Bold.ttf" if logo else ("Inter-Bold.otf" if negrita else "Inter-Regular.otf")
    try:
        return ImageFont.truetype(str(FUENTES / archivo), P(tam))
    except OSError:
        return ImageFont.load_default(P(tam))


def descargar_imagen(url):
    if vacio(url):
        return None
    try:
        import requests
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


class Hoja:
    """Lienzo A4 con coordenadas en px de diseño (1240 x 1754)."""

    def __init__(self):
        self.img = Image.new("RGB", (P(ANCHO), P(ALTO)), "white")
        self.d = ImageDraw.Draw(self.img)

    # --- texto ---
    def ancho(self, texto, tam, negrita=False):
        return self.d.textlength(str(texto), font=fuente(tam, negrita)) / S

    def texto(self, x, y, texto, tam, negrita=False, color=NEGRO, ancla="la", logo=False):
        self.d.text((P(x), P(y)), str(texto), font=fuente(tam, negrita, logo), fill=color, anchor=ancla)

    def espaciado(self, x, y, texto, tam=14.5, color="#333333", sep=1.4):
        """Título de sección en mayúsculas con espaciado entre letras."""
        for c in texto.upper():
            self.texto(x, y, c, tam, True, color)
            x += self.ancho(c, tam, True) + sep

    def cortar(self, texto, tam, ancho, negrita=False, max_lineas=None):
        """Divide en líneas que entran en el ancho; la última se recorta con '…' si sobra texto."""
        palabras, lineas, actual = str(texto).split(), [], ""
        for p in palabras:
            prueba = f"{actual} {p}".strip()
            if self.ancho(prueba, tam, negrita) <= ancho or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = p
        if actual:
            lineas.append(actual)
        if max_lineas and len(lineas) > max_lineas:
            lineas = lineas[:max_lineas]
            ultima = lineas[-1]
            while ultima and self.ancho(ultima + "…", tam, negrita) > ancho:
                ultima = ultima[:-1]
            lineas[-1] = ultima.rstrip(" ,.;:") + "…"
        return lineas or [""]

    def parrafo(self, x, y, texto, tam, ancho, interlinea, negrita=False, color=NEGRO, max_lineas=None):
        lineas = self.cortar(texto, tam, ancho, negrita, max_lineas)
        for i, linea in enumerate(lineas):
            self.texto(x, y + i * interlinea, linea, tam, negrita, color)
        return y + len(lineas) * interlinea

    # --- formas ---
    def rect(self, x, y, w, h, radio=8, borde=BORDE, relleno="white", grosor=1):
        self.d.rounded_rectangle((P(x), P(y), P(x + w), P(y + h)), radius=P(radio), fill=relleno,
                                 outline=borde, width=max(1, P(grosor)))

    def linea(self, x1, y1, x2, y2, color=BORDE, grosor=1):
        self.d.line((P(x1), P(y1), P(x2), P(y2)), fill=color, width=max(1, P(grosor)))

    def pegar(self, imagen, x, y, w, h, cubrir=True):
        """Pega una imagen ajustada al recuadro (recortando para cubrirlo) con esquinas redondeadas."""
        W, H = P(w), P(h)
        iw, ih = imagen.size
        escala = max(W / iw, H / ih) if cubrir else min(W / iw, H / ih)
        im = imagen.resize((max(1, int(iw * escala)), max(1, int(ih * escala))), Image.LANCZOS)
        cx, cy = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((max(0, cx), max(0, cy), max(0, cx) + W, max(0, cy) + H)) if cubrir else im
        mascara = Image.new("L", im.size, 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=P(10), fill=255)
        self.img.paste(im, (P(x) + (W - im.width) // 2, P(y) + (H - im.height) // 2), mascara)

    # --- bloques ---
    def caja(self, x, y, w, titulo, valor, pie="", fuerte=False, tam_valor=20, sufijo="", max_lineas=3):
        """Recuadro con título, valor (y sufijo chico) y pie. Devuelve la altura usada."""
        lineas = self.cortar(valor, tam_valor, w - 28, True, max_lineas)
        h = 14 + 17 + len(lineas) * (tam_valor + 5) + (17 if pie else 0) + 10
        self.rect(x, y, w, h, borde=NEGRO if fuerte else BORDE, grosor=1.2 if fuerte else 1)
        self.texto(x + 14, y + 13, titulo, 12.5, False, "#333333")
        yy = y + 31
        for i, linea in enumerate(lineas):
            color = GRIS_CLARO if linea == SIN else NEGRO
            self.texto(x + 14, yy, linea, tam_valor, True, color)
            if sufijo and i == len(lineas) - 1 and linea != SIN:
                self.texto(x + 18 + self.ancho(linea, tam_valor, True), yy + tam_valor * 0.33, sufijo, 13, True, GRIS)
            yy += tam_valor + 5
        if pie:
            self.texto(x + 14, yy + 2, pie, 12, False, GRIS)
        return h

    def tabla(self, x, y, columnas, filas, limite_y, tam=14, alto_fila=27, encabezado=True, dibujar=True):
        """columnas: [(título, ancho, alineación, negrita)]. Corta las filas que no entran.
        Devuelve (y final, filas dibujadas)."""
        if encabezado and not dibujar:
            y += 34
        elif encabezado:
            cx = x
            for titulo, w, alin, _ in columnas:
                lineas = titulo.split("\n")
                for i, l in enumerate(lineas):
                    yy = y + i * 14 + (0 if len(lineas) > 1 else 7)
                    if alin == "r":
                        self.texto(cx + w - 6, yy, l, 12, False, GRIS, ancla="ra")
                    else:
                        self.texto(cx + 6, yy, l, 12, False, GRIS)
                cx += w
            y += 34
            self.linea(x, y, x + sum(c[1] for c in columnas), y, "#CCCCCC")
        dibujadas = 0
        for fila in filas:
            partes = [self.cortar(v, tam, w - 12, neg, 2) for v, (_, w, _, neg) in zip(fila, columnas)]
            h = max(alto_fila, 9 + max(len(p) for p in partes) * (tam + 3) + 6)
            if y + h > limite_y:
                break
            if not dibujar:
                y += h
                dibujadas += 1
                continue
            cx = x
            for lineas, (_, w, alin, neg) in zip(partes, columnas):
                for i, l in enumerate(lineas):
                    yy = y + 8 + i * (tam + 3)
                    color = GRIS_CLARO if l == SIN else NEGRO
                    if alin == "r":
                        self.texto(cx + w - 6, yy, l, tam, neg, color, ancla="ra")
                    else:
                        self.texto(cx + 6, yy, l, tam, neg, color)
                cx += w
            y += h
            self.linea(x, y, x + sum(c[1] for c in columnas), y, "#EEEEEE")
            dibujadas += 1
        return y, dibujadas

    def encabezado(self, tipo):
        self.texto(72, 112, "¿Cómo le fue?", 44, logo=True, ancla="ls")
        self.texto(1168, 86, tipo, 17, True, ancla="rs")
        self.texto(1168, 106, SUBTITULO, 15, False, GRIS, ancla="rs")
        self.linea(72, 123, 1168, 123, NEGRO, 2)

    def pie(self, fuentes):
        self.linea(72, 1652, 1168, 1652, "#BBBBBB")
        y = 1668
        lineas = self.cortar(f"Fuentes: {fuentes}", 12.5, 740)
        for i, l in enumerate(lineas[:5]):
            if i == 0:
                self.texto(72, y, "Fuentes:", 12.5, True, "#333333")
                self.texto(72 + self.ancho("Fuentes: ", 12.5, True), y, l[len("Fuentes: "):], 12.5, False, "#333333")
            else:
                self.texto(72, y, l, 12.5, False, "#333333")
            y += 18
        resto = f" · Desarrollado por {AUTOR}"
        x = 1168 - self.ancho(resto, 13)
        self.texto(x, 1686, resto, 13, False, GRIS, ancla="ls")
        self.texto(x - 4, 1686, "¿Cómo le fue?", 16, ancla="rs", logo=True)
        self.texto(1168, 1704, f"Generado el {hoy():%d/%m/%Y}", 12.5, False, GRIS, ancla="ra")

    def lateral(self, imagen, texto_vacio):
        self.rect(72, 150, 330, 1494, radio=12, borde=FONDO_LAT, relleno=FONDO_LAT)
        if imagen is not None:
            self.pegar(imagen, 90, 168, 294, 440)
        else:
            self.rect(90, 168, 294, 440, radio=10, borde="#E6E6E6", relleno="#EEEEEE")
            self.texto(237, 388, texto_vacio, 15, False, GRIS_CLARO, ancla="mm")
        return 632

    def jpg(self):
        salida = io.BytesIO()
        self.img.save(salida, "JPEG", quality=88, optimize=True, dpi=(300, 300))
        return salida.getvalue()


def grafico_a_imagen(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100 * S, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def estilo_ejes(ax):
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#BBBBBB")
    ax.tick_params(colors="#555555", labelsize=8.5, length=0)


def formato_ar(v, _=None):
    return f"{v:,.0f}".replace(",", ".")


# =============================================================================
# Resumen de la película
# =============================================================================
def histograma_votos(votos, w, h):
    total = sum(votos)
    fig, ax = plt.subplots(figsize=(w / 100, h / 100))
    plt.rcParams["font.family"] = "Inter"
    x = np.arange(1, 11)
    barras = ax.bar(x, votos, color=AZUL, width=0.72)
    for b, v in zip(barras, votos):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{100 * v / total:.0f} %", ha="center",
                va="bottom", fontsize=7.5, color="#555555")
    ax.set_xticks(x)
    ax.set_yticks([])
    estilo_ejes(ax)
    ax.set_xlabel("Estrellas (1 a 10) · % de votos del público", fontsize=8, color="#555555")
    ax.set_ylim(0, max(votos) * 1.18)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=0.2)
    return grafico_a_imagen(fig)


def resumen_pelicula(pid, pel, fichas, lanz, cred):
    f = pel.loc[pid]
    x = fichas.loc[pid].to_dict() if pid in fichas.index else {}
    def v(col):
        return None if vacio(x.get(col)) else x.get(col)

    h = Hoja()
    h.encabezado("Resumen de la película")
    h.lateral(descargar_imagen(v("afiche_grande") or v("afiche")), "Afiche no disponible")

    # ----- Columna lateral: ficha y origen -----
    X, W = 90, 294
    y = 632
    h.espaciado(X, y, "Ficha")
    y += 26
    y += h.caja(X, y, W, "Distribuidora", f["distribuidora"] if not vacio(f["distribuidora"]) else SIN) + 10
    y += h.caja(X, y, W, "Presupuesto", m(v("presupuesto")), "Según TMDB (mundial)" if v("presupuesto") else "") + 10
    w2 = (W - 10) / 2
    a = h.caja(X, y, w2, "Estreno en EE. UU.", fa(f["fecha_estreno"]))
    b = h.caja(X + w2 + 10, y, w2, "Calificación", f["mpaa"] if not vacio(f["mpaa"]) else SIN)
    y += max(a, b) + 10
    dur = None if vacio(f["duracion_min"]) else int(f["duracion_min"])
    y += h.caja(X, y, W, "Duración", SIN if dur is None else f"{dur // 60} h {dur % 60:02d} min") + 10
    generos = list(f["generos"]) if not vacio(f["generos"]) and len(f["generos"]) else []
    y += h.caja(X, y, W, "Género", ", ".join(generos[:5]) if generos else SIN) + 10
    if v("saga"):
        y += h.caja(X, y, W, "Saga", v("saga")) + 10
    y += 14
    h.espaciado(X, y, "Origen")
    y += 26
    for titulo, valor in (("Idiomas", v("idiomas")), ("Países de producción", v("paises_produccion")),
                          ("Productoras", v("productoras"))):
        if y > 1560:
            break
        if titulo == "Productoras" and valor:
            partes = [p.strip() for p in valor.split(",")]
            valor = ", ".join(partes[:4]) + (f" y {len(partes) - 4} más" if len(partes) > 4 else "")
        y += h.caja(X, y, W, titulo, valor or SIN, tam_valor=17 if titulo == "Productoras" else 19,
                    max_lineas=3) + 10

    # ----- Columna principal -----
    X, W = 438, 730
    lineas = h.cortar(f["titulo"], 44, W, True, 2)
    y = 150
    for linea in lineas:
        h.texto(X, y, linea, 44, True)
        y += 52
    h.texto(X, y + 2, str(f["anio"]), 22, False, GRIS)
    y += 42
    sinopsis = v("sinopsis") or "Sin sinopsis."
    y = h.parrafo(X, y, sinopsis, 15, W, 24, color="#222222", max_lineas=5) + 22

    h.espaciado(X, y, "Desempeño en Estados Unidos")
    y += 26
    w2 = (W - 10) / 2
    dias = SIN if vacio(f["dias_cartel"]) else f"{n(f['dias_cartel'])} días"
    puesto = SIN if vacio(f["mejor_puesto"]) else f"N.º {int(f['mejor_puesto'])}"
    for (t1, v1), (t2, v2) in ((("Recaudación total", m(f["taquilla"])), ("Fin de semana de estreno", m(f["apertura"]))),
                               (("Días en cartel", dias), ("Mejor puesto diario", puesto))):
        a = h.caja(X, y, w2, t1, v1, fuerte=True, tam_valor=24)
        h.caja(X + w2 + 10, y, w2, t2, v2, fuerte=True, tam_valor=24)
        y += a + 10
    y += 14
    h.espaciado(X, y, "Contexto mundial")
    y += 26
    mundial = v("mundial")
    pct = f"EE. UU.: {n(100 * f['taquilla'] / mundial, 1)} % del total" if mundial and not vacio(f["taquilla"]) else ""
    rk = SIN if vacio(f["ranking_anual"]) else f"N.º {f['ranking_anual']} de {f['anio']}"
    a = h.caja(X, y, w2, "Recaudación mundial", m(mundial), pct, tam_valor=24)
    b = h.caja(X + w2 + 10, y, w2, "Ranking anual mundial", rk, tam_valor=24)
    y += max(a, b) + 24

    # Recepción
    h.espaciado(X, y, "Recepción")
    y += 26
    critica, publico = v("critica"), v("publico")
    a = h.caja(X, y + 8, 200, "Crítica (Metascore)", SIN if critica is None else str(int(critica)),
               "" if v("n_criticas") is None else f"{n(v('n_criticas'))} críticas",
               sufijo="" if critica is None else "/ 100")
    b = h.caja(X, y + a + 18, 200, "Público (IMDb)", SIN if publico is None else n(publico, 1),
               "" if v("votos_total") is None else f"{n(v('votos_total'))} votos",
               sufijo="" if publico is None else "/ 10")
    alto_rec = a + b + 26
    votos = [0 if vacio(x.get(f"votos_{i}")) else float(x[f"votos_{i}"]) for i in range(1, 11)]
    if sum(votos) > 0:
        hist = histograma_votos(votos, 510, max(alto_rec, 170))
        h.pegar(hist, X + 218, y, 510, max(alto_rec, 170), cubrir=False)
    else:
        h.texto(X + 218 + 255, y + alto_rec / 2, "Sin datos de votos del público.", 13, False, GRIS_CLARO, ancla="mm")
    y += max(alto_rec, 170) + 24

    # Recorrido
    h.espaciado(X, y, "Recorrido")
    y += 26
    est = None if vacio(f["fecha_estreno"]) else pd.Timestamp(f["fecha_estreno"])
    cand = [(pd.Timestamp(d), md) for d, md in ((x.get("fecha_digital"), "digital"),
                                                 (x.get("fecha_fisico"), "en DVD / Blu-ray"))
            if not vacio(d) and est is not None and pd.Timestamp(d) >= est]
    if cand:
        salida, medio = min(cand)
        h.rect(X, y, W, 50, radio=8, borde="#E8F2EC", relleno="#F3F9F5")
        h.d.rectangle((P(X), P(y), P(X + 4), P(y + 50)), fill=VERDE)
        dias_v = f"{n((salida - est).days)} días"
        h.texto(X + 18, y + 9, dias_v, 16, True)
        h.texto(X + 22 + h.ancho(dias_v, 16, True), y + 9, "de exclusividad en cines", 16)
        h.texto(X + 18, y + 31, f"Del estreno ({fa(est)}) a la primera salida {medio} ({fa(salida)})", 12.5, False, GRIS)
        y += 62
    rec = lanz[lanz["id"] == pid].sort_values("fecha").head(8)
    if rec.empty:
        h.texto(X, y, SIN, 14, False, GRIS_CLARO)
        y += 30
    else:
        cols = [("Tipo", 210, "l", False), ("Fecha", 165, "l", False), ("Detalle", 355, "l", False)]
        y, _ = h.tabla(X, y, cols, [(r.tipo, fa(r.fecha), r.detalle or "") for r in rec.itertuples()], 1600,
                       tam=14, alto_fila=27)
    y += 24

    # Equipo y elenco
    c = cred[cred["id"] == pid]
    eq = c[c["grupo"] == "Equipo"].sort_values("orden")
    eq = [(nom, " · ".join(dict.fromkeys(g["rol"]))) for nom, g in eq.groupby("nombre", sort=False)]
    el = c[c["grupo"] == "Elenco"].sort_values("orden")
    el = [(r.nombre, r.personaje or "") for r in el.itertuples()]
    limite = 1630
    if y + 60 < limite:
        w_col = (W - 26) / 2
        for xx, titulo, filas, w1 in ((X, "Equipo", eq, 150), (X + w_col + 26, "Elenco", el, 165)):
            h.espaciado(xx, y, titulo)
            if not filas:
                h.texto(xx, y + 32, SIN, 14, False, GRIS_CLARO)
                continue
            cols = [("", w1, "l", True), ("", w_col - w1, "l", False)]
            y_fin, hechas = h.tabla(xx, y + 24, cols, filas[:10], limite - 22, tam=13.5, alto_fila=27, encabezado=False)
            if hechas < len(filas):
                h.texto(xx + 6, y_fin + 8, f"y {len(filas) - hechas} más", 12.5, False, GRIS)

    h.pie("Box Office Mojo (recaudación, ranking y salas), IMDb (puntajes y elenco) y TMDB (sinopsis, afiche, "
          "producción, presupuesto y fechas). Recaudaciones en dólares nominales, sin ajuste por inflación. "
          f"El presupuesto es el informado en TMDB (mundial). {ATRIB_TMDB} {ATRIB_IMDB}")
    return h.jpg()


# =============================================================================
# Resumen de trayectoria
# =============================================================================
def corto(t, largo=26):
    t = str(t)
    return t if len(t) <= largo else t[:largo - 1].rstrip() + "…"


def linea_tiempo(film, w, h):
    """Un punto por película: año de estreno y recaudación en EE. UU. Se nombran las tres más taquilleras."""
    d = film.dropna(subset=["taquilla"]).copy()
    fig, ax = plt.subplots(figsize=(w / 100, h / 100))
    plt.rcParams["font.family"] = "Inter"
    if d.empty:
        ax.text(0.5, 0.5, "Sin datos de recaudación.", ha="center", va="center", color="#888888", fontsize=10,
                transform=ax.transAxes)
        ax.axis("off")
        return grafico_a_imagen(fig)
    # Desplazamiento horizontal si hay varias películas en el mismo año
    d["orden"] = d.groupby("anio").cumcount()
    d["cuantas"] = d.groupby("anio")["anio"].transform("size")
    d["x"] = d["anio"] + (d["orden"] - (d["cuantas"] - 1) / 2) * 0.22
    d["y"] = d["taquilla"] / 1e6
    mayor = d["y"].idxmax()
    top3 = d.nlargest(3, "y").index
    ax.scatter(d["x"], d["y"], s=28, color=[VERDE if i == mayor else AZUL for i in d.index], zorder=3,
               edgecolors="white", linewidths=0.6)
    ymax = d["y"].max()
    for i in top3:
        r = d.loc[i]
    a0, a1 = int(d["anio"].min()), int(d["anio"].max())
    a0, a1 = min(a0, a1 - 2), max(a1, a0 + 2)
    for i in top3:
        r = d.loc[i]
        pos = (r["x"] - a0) / max(1, a1 - a0)
        ha, dx = ("left", -4) if pos < 0.18 else (("right", 4) if pos > 0.82 else ("center", 0))
        ax.annotate(f"{corto(r['titulo'], 24)} · {n(r['y'])} M", (r["x"], r["y"]), xytext=(dx, 7),
                    textcoords="offset points", ha=ha, fontsize=7.5, color="#222222", fontweight="bold")
    ax.set_xlim(a0 - 0.8, a1 + 0.8)
    paso = 1 if a1 - a0 <= 10 else 2
    ax.set_xticks(range(a0, a1 + 1, paso))
    ax.set_ylim(0, ymax * 1.22)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(formato_ar))
    ax.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax.set_axisbelow(True)
    estilo_ejes(ax)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.96, bottom=0.1)
    return grafico_a_imagen(fig)


def resumen_trayectoria(bio_id, pel, fichas, cred, per):
    b = per.loc[bio_id]
    c = cred[cred["bio_id"] == bio_id].merge(pel[["id", "titulo", "anio", "taquilla", "ranking_anual"]].reset_index(drop=True), on="id")
    c = c[~c["titulo"].str.contains(REESTRENO, na=False)]
    orden_roles = ["Actuación", "Dirección", "Guion", "Producción", "Música", "Fotografía", "Montaje",
                   "Diseño de producción"]
    filas = []
    for pid, g in c.groupby("id", sort=False):
        roles = sorted(dict.fromkeys(g["rol"]), key=lambda r: orden_roles.index(r) if r in orden_roles else 99)
        pj = g.loc[g["rol"] == "Actuación", "personaje"].dropna()
        filas.append({"id": pid, "titulo": g["titulo"].iloc[0], "anio": int(g["anio"].iloc[0]),
                      "taquilla": g["taquilla"].iloc[0], "ranking": g["ranking_anual"].iloc[0],
                      "rol": " · ".join(roles) + (f" ({pj.iloc[0]})" if len(pj) else "")})
    film = pd.DataFrame(filas, columns=["id", "titulo", "anio", "taquilla", "ranking", "rol"])
    if len(film):
        film = film.join(fichas[["critica", "publico"]], on="id").sort_values(["anio", "titulo"])
    else:
        film["critica"] = film["publico"] = None

    h = Hoja()
    h.encabezado("Resumen de trayectoria")
    h.lateral(descargar_imagen(b.get("foto_grande") or b.get("foto")), "Foto no disponible")

    # ----- Lateral: datos personales -----
    X, W = 90, 294
    y = 632
    h.espaciado(X, y, "Datos")
    y += 26
    nac, fal = b.get("nacimiento"), b.get("fallecimiento")
    def edad(hasta):
        nn, hh = pd.Timestamp(nac), pd.Timestamp(hasta)
        return hh.year - nn.year - ((hh.month, hh.day) < (nn.month, nn.day))
    y += h.caja(X, y, W, "Nacimiento", fa(nac)) + 10
    if not vacio(fal):
        y += h.caja(X, y, W, "Fallecimiento", fa(fal)) + 10
        y += h.caja(X, y, W, "Edad", SIN if vacio(nac) else f"Falleció a los {edad(fal)} años") + 10
    else:
        y += h.caja(X, y, W, "Edad", SIN if vacio(nac) else f"{edad(hoy())} años") + 10
    y += h.caja(X, y, W, "Lugar de nacimiento", b.get("lugar") if not vacio(b.get("lugar")) else SIN) + 10
    roles = SIN if vacio(b.get("roles")) else " · ".join(str(b["roles"]).split("|"))
    y += h.caja(X, y, W, "Roles en la app", roles) + 10
    w2 = (W - 10) / 2
    top = b.get("top_pct")
    h.caja(X, y, w2, "Popularidad", SIN if vacio(top) else f"Top {int(top)} %", "" if vacio(top) else "en TMDB")
    anios = f"{film['anio'].min()}–{film['anio'].max()}" if len(film) else ""
    h.caja(X + w2 + 10, y, w2, "Películas", str(len(film)), anios)

    # ----- Columna principal -----
    X, W = 438, 730
    y = 150
    for linea in h.cortar(b["nombre"], 44, W, True, 2):
        h.texto(X, y, linea, 44, True)
        y += 52
    h.texto(X, y + 2, roles if roles != SIN else "", 20, False, GRIS)
    y += 44
    bio = b.get("biografia")
    h.espaciado(X, y, "Biografía")
    y += 26
    y = h.parrafo(X, y, bio if not vacio(bio) else SIN, 14.5, W, 22.5, color="#222222" if not vacio(bio) else GRIS_CLARO,
                  max_lineas=8) + 20

    h.espaciado(X, y, "Sus películas en la app")
    y += 26
    con = film.dropna(subset=["taquilla"])
    total = con["taquilla"].sum() if len(con) else None
    mejor = con.loc[con["taquilla"].idxmax()] if len(con) else None
    imdb = film["publico"].mean() if len(film) and film["publico"].notna().any() else None
    a = h.caja(X, y, w2 := (W - 10) / 2, "Recaudación total en EE. UU.", m(total), f"Suma de {len(con)} películas" if len(con) else "",
               fuerte=True, tam_valor=22)
    b2 = h.caja(X + w2 + 10, y, w2, "Promedio por película", m(total / len(con)) if len(con) else SIN, fuerte=True, tam_valor=22)
    y += max(a, b2) + 10
    a = h.caja(X, y, w2, "Película más taquillera", SIN if mejor is None else mejor["titulo"],
               "" if mejor is None else f"{mejor['anio']} · {m(mejor['taquilla'])}", fuerte=True, tam_valor=18, max_lineas=2)
    b2 = h.caja(X + w2 + 10, y, w2, "Puntaje promedio del público", SIN if imdb is None else f"{n(imdb, 1)} / 10",
                "" if imdb is None else "IMDb", fuerte=True, tam_valor=22)
    y += max(a, b2) + 24

    h.espaciado(X, y, "Recaudación de sus películas")
    y += 22
    graf = linea_tiempo(film, 730, 250)
    h.pegar(graf, X, y, 730, 250, cubrir=False)
    y += 252
    nota = ("Cada punto es una película: año de estreno y recaudación en EE. UU. (millones de USD nominales). "
            "Se nombran las tres más taquilleras; en verde, la mayor.")
    y = h.parrafo(X, y, nota, 11.5, W, 16, color=GRIS) + 20

    h.espaciado(X, y, "Filmografía en la app")
    y += 22
    cols = [("Año", 44, "l", False), ("Película", 246, "l", True), ("Rol", 190, "l", False),
            ("Taquilla EE.\nUU.", 85, "r", False), ("Ranking\nanual", 70, "r", False),
            ("Crítica", 50, "r", False), ("IMDb", 45, "r", False)]
    def filas_de(t):
        return [(str(r.anio), r.titulo, r.rol, m(r.taquilla) if not vacio(r.taquilla) else SIN,
                 "" if vacio(r.ranking) else f"N.º {int(r.ranking)}", "" if vacio(r.critica) else str(int(r.critica)),
                 "" if vacio(r.publico) else n(r.publico, 1)) for r in t.itertuples()]
    # Si no entran todas, se eligen las más taquilleras que entran y se ordenan por año
    k = len(film)
    while k > 0:
        tabla = film if k == len(film) else film.loc[film["taquilla"].fillna(0).nlargest(k).index].sort_values(["anio", "titulo"])
        _, entran = h.tabla(X, y, cols, filas_de(tabla), 1620, tam=13, alto_fila=26, dibujar=False)
        if entran == k:
            break
        k = min(k - 1, entran)
    filas_t = filas_de(tabla) if k > 0 else []
    if not filas_t:
        h.texto(X, y + 8, SIN, 14, False, GRIS_CLARO)
    else:
        y_fin, hechas = h.tabla(X, y, cols, filas_t, 1620, tam=13, alto_fila=26)
        nota = "En orden cronológico. No se incluyen los reestrenos. Ranking anual mundial; crítica según Metascore (0 a 100)."
        if hechas < len(film):
            nota += f" Se muestran {hechas} de {len(film)} películas (las más taquilleras)."
        h.parrafo(X, y_fin + 8, nota, 11.5, W, 15, color=GRIS, max_lineas=2)

    h.pie("Box Office Mojo (recaudación, ranking y salas), IMDb (puntajes y elenco) y TMDB (foto, biografía y datos "
          f"personales). Recaudaciones en dólares nominales, sin ajuste por inflación. {ATRIB_TMDB} {ATRIB_IMDB}")
    return h.jpg()
