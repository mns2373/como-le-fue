"""
¿Cómo le fue? · Preparación de datos

Convierte los tres CSV exportados desde el notebook en tres archivos Parquet
livianos que lee la app (carpeta ./data).

    python preparar_datos.py

Entrada (carpeta ./datos_originales):
    df_datos_peliculas_app.csv   ficha de cada película
    rec_day_rel_app.csv          recaudación día por día de cada película
    df_rec_dia_total_app.csv     recaudación total del mercado por día

Criterios aplicados
    - Cobertura desde el 1/1/2003 (se descartan registros anteriores).
    - Películas y serie diaria se unen por release + year.
    - Se excluyen las películas con recaudación doméstica 0: figuran en el
      ranking anual mundial pero no tuvieron estreno en Estados Unidos.
    - Si release + year se repite, se conserva la fila más completa.
    - Las películas sin serie diaria se conservan (la app muestra sus datos
      generales y avisa que no hay recaudación diaria).
"""
import ast
import unicodedata
from pathlib import Path

import pandas as pd

ENTRADA = Path("datos_originales")
SALIDA = Path("data")
FECHA_INICIO = pd.Timestamp("2003-01-01")
ANIO_INICIO = FECHA_INICIO.year

# Traducción de géneros de Box Office Mojo (editar o vaciar para dejarlos en inglés)
GENEROS_ES = {
    "Action": "Acción", "Adventure": "Aventura", "Animation": "Animación",
    "Biography": "Biografía", "Comedy": "Comedia", "Crime": "Policial",
    "Documentary": "Documental", "Drama": "Drama", "Family": "Familiar",
    "Fantasy": "Fantasía", "History": "Histórica", "Horror": "Terror",
    "Music": "Música", "Musical": "Musical", "Mystery": "Misterio",
    "Reality-TV": "Reality", "Romance": "Romance", "Sci-Fi": "Ciencia ficción",
    "Short": "Cortometraje", "Sport": "Deportes", "Thriller": "Suspenso",
    "War": "Bélica", "Western": "Western",
}
MPAA_ES = {"Not Rated": "Sin calificación"}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para la búsqueda parcial."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower().strip()


def leer_generos(valor):
    if pd.isna(valor):
        return []
    try:
        lista = ast.literal_eval(valor) if isinstance(valor, str) else list(valor)
    except (ValueError, SyntaxError):
        lista = [g.strip() for g in str(valor).strip("[]").split(",")]
    return [GENEROS_ES.get(g.strip(" '\""), g.strip(" '\"")) for g in lista if str(g).strip()]


def preparar_peliculas():
    p = pd.read_csv(ENTRADA / "df_datos_peliculas_app.csv")
    n0 = len(p)
    p = p[p["year"] >= ANIO_INICIO]
    n_corte = len(p)
    p = p[p["domestic"] > 0]
    n_sin_eeuu = n_corte - len(p)
    # Duplicados de release + year: se queda la fila con más datos
    p = (p.assign(_completos=p.notna().sum(axis=1))
           .sort_values(["_completos", "domestic"], ascending=False)
           .drop_duplicates(["release", "year"])
           .drop(columns="_completos"))

    pel = pd.DataFrame({
        "titulo": p["release"].astype(str),
        "anio": p["year"].astype(int),
        "mpaa": p["mpaa"].replace(MPAA_ES),
        "distribuidora": p["domestic_distributor"],
        "duracion_min": p["running_time_min"],
        "fecha_estreno": pd.to_datetime(p["release_date_start"], errors="coerce"),
        "apertura": p["opening_bo"],
        "salas_max": p["theaters"],
        "generos": p["genres_list"].map(leer_generos),
        "dias_cartel": p["date_count"],
        "ranking_anual": p["rank"].astype(int),
        "mejor_puesto": p["rank_daily"],
        "taquilla": p["domestic"],
        "link": p["bom_link"].str.split("?").str[0],
    })
    pel["titulo_norm"] = pel["titulo"].map(normalizar)
    pel = pel.sort_values("taquilla", ascending=False).reset_index(drop=True)
    pel.insert(0, "id", pel.index.astype(int))
    print(f"Películas: {n0:,} filas leídas, {n0 - n_corte:,} anteriores a {ANIO_INICIO}, "
          f"{n_sin_eeuu:,} sin estreno en EE.UU. (recaudación 0) -> {len(pel):,} películas")
    return pel


def preparar_diaria(pel):
    d = pd.read_csv(ENTRADA / "rec_day_rel_app.csv")
    if (d["year"] != d["year_launch"]).any():
        print("  AVISO: year y year_launch no coinciden en algunas filas; se usa year.")
    d = d[d["year"] >= ANIO_INICIO].copy()
    d["fecha"] = pd.to_datetime(d["date_norm"], errors="coerce")

    # Fechas faltantes: se reconstruyen con el día en cartel de otra fila de la misma película
    faltan = d["fecha"].isna()
    if faltan.any():
        ref = (d[~faltan].groupby(["release", "year"])
                 .apply(lambda g: (g["fecha"] - pd.to_timedelta(g["day"], unit="D")).median(),
                        include_groups=False)
                 .rename("base"))
        d = d.join(ref, on=["release", "year"])
        d.loc[faltan, "fecha"] = d.loc[faltan, "base"] + pd.to_timedelta(d.loc[faltan, "day"], unit="D")
        d = d.drop(columns="base")
        print(f"  {faltan.sum()} fechas faltantes reconstruidas a partir del día en cartel")

    claves = pel[["id", "titulo", "anio"]].rename(columns={"titulo": "release", "anio": "year"})
    d = d.merge(claves, on=["release", "year"], how="inner")
    dup = d.duplicated(["id", "fecha"])
    if dup.any():
        print(f"  {dup.sum()} filas repetidas (misma película y fecha) descartadas")
        d = d[~dup]
    d = d.dropna(subset=["fecha"]).sort_values(["id", "fecha"])

    dia = pd.DataFrame({
        "id": d["id"].astype("int32"),
        "fecha": d["fecha"],
        "dia": d["day"].astype("int32"),
        "recaudacion": d["daily"].astype("int64"),
        "acumulado": d["to date"].astype("int64"),
        "salas": d["theaters"].astype("int32"),
        "puesto": d["rank"].astype("int16"),
    })
    print(f"Serie diaria: {len(dia):,} filas de {dia['id'].nunique():,} películas")
    return dia


def preparar_mercado():
    t = pd.read_csv(ENTRADA / "df_rec_dia_total_app.csv")
    t["fecha"] = pd.to_datetime(t["date_normalized"])
    t = t[t["fecha"] >= FECHA_INICIO].sort_values("fecha")
    merc = pd.DataFrame({
        "fecha": t["fecha"],
        "total": t["total_gross"],
        "top1": t["#1_gross"],
        "top10": t["top_10_gross"],
        "pelicula_1": t["#1_release"],
        "en_cartel": t["releases"],
    }).reset_index(drop=True)
    print(f"Mercado: {len(merc):,} días, del {merc['fecha'].min():%d/%m/%Y} "
          f"al {merc['fecha'].max():%d/%m/%Y}")
    return merc


def main():
    SALIDA.mkdir(exist_ok=True)
    pel = preparar_peliculas()
    dia = preparar_diaria(pel)
    pel["tiene_diaria"] = pel["id"].isin(dia["id"])
    print(f"  {(~pel['tiene_diaria']).sum():,} películas sin serie diaria (se muestran sin gráfico)")
    merc = preparar_mercado()

    pel.to_parquet(SALIDA / "peliculas.parquet", index=False)
    dia.to_parquet(SALIDA / "diaria.parquet", index=False)
    merc.to_parquet(SALIDA / "mercado.parquet", index=False)
    tam = sum(f.stat().st_size for f in SALIDA.glob("*.parquet")) / 1e6
    print(f"\nListo: 3 archivos en ./{SALIDA} ({tam:.1f} MB en total)")


if __name__ == "__main__":
    main()
