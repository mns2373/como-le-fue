"""
Imagen descargable (PNG 16:9, 1920x1080) del detalle de una película.

Formato aprobado:
- Título, distribuidora y calificación, subtítulo con país y moneda, total y apertura.
- Recaudación diaria (columnas al 75 %) y acumulada (línea con borde blanco), en dos ejes.
- Bandas grises para los fines de semana (viernes a domingo).
- Panel inferior con el puesto en el ranking diario.
- Se muestra hasta que la película reúne COBERTURA % de su recaudación.
"""
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as md                      # noqa: E402
import matplotlib.patheffects as pe                # noqa: E402
import matplotlib.pyplot as plt                    # noqa: E402
import matplotlib.ticker as mt                     # noqa: E402
import pandas as pd                                # noqa: E402
from matplotlib import font_manager                # noqa: E402
from matplotlib.patches import Patch               # noqa: E402

COBERTURA = 95          # % de la recaudación total que se grafica
AZUL, VERDE, GRIS = "#2F80D0", "#1F8F5C", "#555555"
AUTOR = "Martín Nicolás Serafini"

# Fuente Inter incluida en assets/fuentes (en Streamlit Cloud no está instalada)
_FUENTES = Path(__file__).parent / "assets" / "fuentes"
for _f in _FUENTES.glob("*.otf"):
    font_manager.fontManager.addfont(str(_f))
_FAMILIA = "Inter" if any(_FUENTES.glob("Inter-*.otf")) else "DejaVu Sans"


def _num(x, dec=1):
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _miles(x, _):
    return f"{x:,.0f}".replace(",", ".")


def _texto(v, defecto="Sin dato"):
    return defecto if v is None or (not isinstance(v, (list, tuple)) and pd.isna(v)) else str(v)


def nombre_archivo(f):
    base = "".join(c if c.isalnum() else "_" for c in f"{f['titulo']}_{f['anio']}").strip("_")
    while "__" in base:
        base = base.replace("__", "_")
    return f"como_le_fue_{base.lower()}.png"


def generar_png(f, serie):
    """f: fila de la película; serie: recaudación diaria de esa película. Devuelve bytes PNG."""
    serie = serie.sort_values("fecha")
    final = serie["acumulado"].iloc[-1]
    corte = serie.loc[serie["acumulado"] >= final * COBERTURA / 100, "fecha"].iloc[0]
    s = serie[serie["fecha"] <= corte]
    dias = (corte - s["fecha"].iloc[0]).days + 1

    with plt.rc_context({"font.family": _FAMILIA, "font.size": 15, "axes.edgecolor": "#999",
                         "xtick.color": GRIS, "ytick.color": GRIS, "axes.labelcolor": "#444"}):
        fig = plt.figure(figsize=(16, 9), dpi=120)

        # ---- Encabezado y pie ----
        fig.text(0.045, 0.935, f"{f['titulo']} ({f['anio']})", fontsize=30, fontweight="bold", color="#111")
        datos = [d for d in (_texto(f.get("distribuidora"), ""),
                             f"Calificación {f['mpaa']}" if pd.notna(f.get("mpaa")) else "") if d]
        fig.text(0.045, 0.893, " · ".join(datos) or " ", fontsize=16, color="#444")
        fig.text(0.045, 0.858, "Evolución de la taquilla en Estados Unidos · Diaria y acumulada en USD "
                 "(sin ajuste por inflación)", fontsize=16, color="#444")
        resumen = f"Total: {_num(f['taquilla'] / 1e6)} M"
        if pd.notna(f.get("apertura")):
            resumen += f" · Apertura: {_num(f['apertura'] / 1e6)} M"
        fig.text(0.955, 0.893, resumen, fontsize=16, color="#111", ha="right", fontweight="bold")
        if COBERTURA < 100:
            nota = (f"Se muestran los primeros {dias} días en cartel, hasta el {corte:%d/%m/%Y}, que reúnen el "
                    f"{COBERTURA} % de la recaudación total. Se omiten la cola final y los reestrenos.")
            fig.text(0.045, 0.062, nota, fontsize=12.5, color=GRIS)
        fig.text(0.045, 0.03, "Fuente: Box Office Mojo · Elaboración propia", fontsize=12, color="#777")
        fig.text(0.955, 0.03, f"¿Cómo le fue? · {AUTOR}", fontsize=12, color="#777", ha="right")

        # ---- Gráfico principal ----
        ax = fig.add_axes([0.075, 0.33, 0.85, 0.45])
        ax.spines["top"].set_visible(False)
        ax.grid(axis="y", color="#eee")
        ax.set_axisbelow(True)
        ax.bar(s["fecha"], s["recaudacion"] / 1e6, width=0.8, color=AZUL, alpha=0.75, label="Diaria", zorder=2)
        ax.set_ylabel("Diaria (millones de USD)")
        ax.yaxis.set_major_formatter(mt.FuncFormatter(_miles))
        ax.set_ylim(0)
        ax.tick_params(labelbottom=False)
        ax2 = ax.twinx()
        ax2.spines["top"].set_visible(False)
        ax2.plot(s["fecha"], s["acumulado"] / 1e6, color=VERDE, linewidth=3, label="Acumulada",
                 path_effects=[pe.Stroke(linewidth=5.5, foreground="white"), pe.Normal()])
        ax2.set_ylabel("Acumulada (millones de USD)")
        ax2.yaxis.set_major_formatter(mt.FuncFormatter(_miles))
        ax2.set_ylim(0, final / 1e6 * 1.05)
        ax.margins(x=0.01)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        banda = Patch(facecolor="#000", alpha=0.07, lw=0)
        ax.legend(h1 + h2 + [banda], l1 + l2 + ["Fin de semana (viernes a domingo)"], loc="upper left",
                  bbox_to_anchor=(0, 1.135), ncol=3, frameon=False, fontsize=14)

        # ---- Panel del puesto diario ----
        axr = fig.add_axes([0.075, 0.15, 0.85, 0.14], sharex=ax)
        axr.step(s["fecha"], s["puesto"], where="mid", color="#333", linewidth=2)
        peor = int(s["puesto"].max())
        if peor <= 10:
            axr.fill_between(s["fecha"], s["puesto"], 10.5, step="mid", color="#333", alpha=0.08)
            axr.set_ylim(10.5, 0.5)
            axr.set_yticks([1, 3, 5, 7, 10])
        else:
            axr.set_yscale("log")
            axr.fill_between(s["fecha"], s["puesto"], peor * 1.15, step="mid", color="#333", alpha=0.08)
            axr.set_ylim(peor * 1.15, 0.85)
            axr.set_yticks([t for t in (1, 2, 5, 10, 20, 50, 100) if t <= peor * 1.15])
            axr.yaxis.set_minor_locator(mt.NullLocator())
        axr.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"N.º {int(v)}"))
        axr.tick_params(axis="y", labelsize=12)
        axr.set_ylabel("Puesto", labelpad=14)
        axr.grid(axis="y", color="#eee")
        axr.set_axisbelow(True)
        for lado in ("top", "right"):
            axr.spines[lado].set_visible(False)
        if dias <= 70:
            axr.xaxis.set_major_locator(md.WeekdayLocator(byweekday=md.FR))
            axr.xaxis.set_major_formatter(md.DateFormatter("%d/%m"))
        else:
            axr.xaxis.set_major_locator(md.MonthLocator())
            axr.xaxis.set_major_formatter(md.DateFormatter("%m/%Y"))

        # ---- Bandas de fin de semana (viernes a domingo) ----
        inicio, fin = s["fecha"].min(), s["fecha"].max()
        viernes = pd.date_range(inicio - pd.Timedelta(days=6), fin, freq="W-FRI")
        for v in viernes:
            desde = max(v, inicio) - pd.Timedelta(hours=12)
            hasta = min(v + pd.Timedelta(days=2), fin) + pd.Timedelta(hours=12)
            if hasta > desde:
                for a in (ax, axr):
                    a.axvspan(desde, hasta, color="#000", alpha=0.05, lw=0, zorder=0)

        buffer = io.BytesIO()
        fig.savefig(buffer, format="png")
        plt.close(fig)
    return buffer.getvalue()
