"""
¿Cómo le fue? · Datos complementarios (TMDB e IMDb)

Completa los datos de Box Office Mojo con la información obtenida de TMDB e IMDb
y genera los archivos Parquet que usan las pantallas de información extra,
personas y resúmenes. Se ejecuta después de preparar_datos.py:

    python preparar_datos.py
    python preparar_datos_tmdb.py

Entrada (carpeta ./datos_tmdb, no se sube al repositorio):
    datos_peliculas_tmdb.csv     ficha ampliada de cada película
    tmdb_lanzamientos_bom.csv    fechas de lanzamiento (cines, digital, físico, TV)
    crew_cast_unificado.csv      equipo técnico (BOM) y elenco (IMDb)
    bio.csv                      datos personales (TMDB)

Salida (carpeta ./data):
    fichas.parquet         datos ampliados por película (id de la app)
    lanzamientos.parquet   recorrido de cada película
    creditos.parquet       equipo y elenco de cada película
    personas.parquet       personas con al menos una película en la app
    peliculas.parquet      se actualiza "salas_max" con el máximo de la serie diaria

Criterios
    - Se vincula por release + year; si se repite, se conserva la fila más completa.
    - Ante diferencias entre fuentes se conserva el dato de Box Office Mojo.
    - Los reestrenos no cuentan en las filmografías ni en la cantidad de películas.
    - Idiomas, países y lugares de nacimiento se traducen al español.
"""
import re
from pathlib import Path

import pandas as pd
from babel import Locale

ENTRADA = Path("datos_tmdb")
SALIDA = Path("data")
ES, EN = Locale("es"), Locale("en")

ROLES = {"Actor": "Actuación", "Director": "Dirección", "Writer": "Guion", "Producer": "Producción",
         "Composer": "Música", "Cinematographer": "Fotografía", "Editor": "Montaje",
         "Production Designer": "Diseño de producción"}
ORDEN_ROLES = list(ROLES.values())
TIPOS = {"Premiere": "Premiere", "Cine": "Cines", "Cine limitado": "Cines (limitado)",
         "Digital": "Digital", "Físico": "DVD / Blu-ray", "TV": "TV"}
REESTRENO = re.compile(r"(?i)re-?release|anniversary|\b3d\b release|remaster")

PAIS_EN = {v: k for k, v in EN.territories.items()}
PAIS_EN.update({"USA": "US", "UK": "GB", "England": "GB-ENG", "Scotland": "GB-SCT",
                "Wales": "GB-WLS", "Northern Ireland": "GB-NIR", "West Germany": "DE",
                "Soviet Union": "SU", "USSR": "SU", "Czechoslovakia": "CS", "Yugoslavia": "YU"})
PAIS_ESPECIAL = {"GB-ENG": "Inglaterra", "GB-SCT": "Escocia", "GB-WLS": "Gales",
                 "GB-NIR": "Irlanda del Norte", "SU": "Unión Soviética", "CS": "Checoslovaquia",
                 "YU": "Yugoslavia"}


def vacio(v):
    return v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and not v.strip())


def idiomas_es(codigos):
    if vacio(codigos):
        return None
    nombres = [ES.languages.get(c, c) for c in str(codigos).split("|") if c and c != "xx"]
    return ", ".join(dict.fromkeys(n[:1].upper() + n[1:] for n in nombres)) or None


def paises_es(codigos):
    if vacio(codigos):
        return None
    nombres = [ES.territories.get(c, c) for c in str(codigos).split("|") if c]
    return ", ".join(dict.fromkeys(nombres)) or None


def lugar_es(texto):
    """'Salford, Lancashire, England, UK' -> 'Salford, Lancashire, Inglaterra, Reino Unido'."""
    if vacio(texto):
        return None
    texto = re.sub(r"\s*\[.*?\]", "", str(texto))          # '[now Slovakia]'
    salida = []
    for parte in (x.strip() for x in texto.split(",")):
        cod = PAIS_EN.get(parte)
        salida.append(PAIS_ESPECIAL.get(cod) or (ES.territories.get(cod) if cod else None) or parte)
    return ", ".join(dict.fromkeys(x for x in salida if x)) or None


def fecha(v):
    return pd.to_datetime(v, errors="coerce")


def texto(v):
    return None if vacio(v) else str(v).strip()


def main():
    pel = pd.read_parquet(SALIDA / "peliculas.parquet")
    dia = pd.read_parquet(SALIDA / "diaria.parquet")
    clave = pel[["id", "titulo", "anio"]].rename(columns={"titulo": "release", "anio": "year"})

    # ---------- Máximo de cines: el mayor valor de la serie diaria ----------
    maximo = dia.groupby("id")["salas"].max()
    # (nunca menor que las salas del fin de semana de estreno que informa la ficha)
    pel["salas_max"] = pel[["salas_max"]].assign(d=pel["id"].map(maximo)).max(axis=1)
    pel.to_parquet(SALIDA / "peliculas.parquet", index=False)

    # ---------- Fichas ----------
    t = pd.read_csv(ENTRADA / "datos_peliculas_tmdb.csv")
    t = (t.assign(_n=t.notna().sum(axis=1)).sort_values("_n", ascending=False)
          .drop_duplicates(["release", "year"]).drop(columns="_n"))
    t = clave.merge(t, on=["release", "year"], how="left")
    votos = {f"votos_{i}": t[f"viewers_qty_{i}"] for i in range(1, 11)}
    fichas = pd.DataFrame({
        "id": t["id"],
        "sinopsis": t["sinopsis"].map(texto),
        "sinopsis_en": t["sinopsis_idioma"].eq("en"),
        "afiche": t["poster_link_small"].map(texto),
        "afiche_grande": t["poster_link_big"].map(texto),
        "presupuesto": t["budget"].where(t["budget"] > 0),
        "saga": t["saga"].map(texto).str.removesuffix(" Collection"),
        "saga_id": t["saga_id"],
        "titulo_original": t["original_title"].map(texto),
        "idioma_original": t["original_language"].map(idiomas_es),
        "idiomas": t["spoken_languages"].map(idiomas_es),
        "pais_origen": t["origin_country"].map(paises_es),
        "paises_produccion": t["production_countries"].map(paises_es),
        "productoras": t["production_companies"].map(texto).str.replace("|", ", ", regex=False),
        "trailer": t["trailer_link"].map(texto),
        "trailer_es": t["trailer_link_es"].map(texto),
        "fecha_digital": fecha(t["fecha_digital"]),
        "fecha_fisico": fecha(t["fecha_fisico"]),
        "critica": t["critic_score"],
        "n_criticas": t["critiq_qty"],
        "publico": t["viewers_score"],
        "votos_total": t["viewers_qty_total"],
        **votos,
        "mundial": t["worldwide_bo"].where(t["worldwide_bo"] > 0),
        "link_imdb": t["imdb_link"].map(texto),
        "link_tmdb": t["tmdb_link"].map(texto),
    })
    fichas.to_parquet(SALIDA / "fichas.parquet", index=False)

    # ---------- Recorrido ----------
    lz = pd.read_csv(ENTRADA / "tmdb_lanzamientos_bom.csv").merge(clave, on=["release", "year"])
    nota = (lz["nota"].fillna("").astype(str)
            .str.replace("70mm IMAX Re-Release", "Reestreno en IMAX 70 mm", regex=False)
            .str.replace(r"(?i)re-?release", "Reestreno", regex=True))
    lanz = pd.DataFrame({"id": lz["id"], "tipo": lz["tipo_nombre"].map(TIPOS).fillna(lz["tipo_nombre"]),
                         "fecha": fecha(lz["fecha"]), "detalle": nota})
    lanz = lanz.dropna(subset=["fecha"]).drop_duplicates().sort_values(["id", "fecha"])
    lanz.to_parquet(SALIDA / "lanzamientos.parquet", index=False)

    # ---------- Créditos ----------
    cc = pd.read_csv(ENTRADA / "crew_cast_unificado.csv", dtype={"bio_id": str}).merge(clave, on=["release", "year"])
    cred = pd.DataFrame({"id": cc["id"], "bio_id": cc["bio_id"], "nombre": cc["person"].astype(str),
                         "grupo": cc["group"].map({"Cast": "Elenco", "Crew": "Equipo"}),
                         "rol": cc["role"].map(ROLES).fillna(cc["role"]),
                         "personaje": cc["character"].map(texto), "orden": cc["orden"]})
    cred = cred.dropna(subset=["bio_id"]).drop_duplicates(["id", "bio_id", "grupo", "rol"])
    cred = cred.sort_values(["id", "grupo", "orden"])
    cred.to_parquet(SALIDA / "creditos.parquet", index=False)

    # ---------- Personas ----------
    reestrenos = set(pel.loc[pel["titulo"].str.contains(REESTRENO), "id"])
    propias = cred[~cred["id"].isin(reestrenos)]
    cuenta = propias.groupby("bio_id")["id"].nunique()
    roles = propias.groupby("bio_id")["rol"].agg(
        lambda r: "|".join(x for x in ORDEN_ROLES if x in set(r)))
    b = pd.read_csv(ENTRADA / "bio.csv", dtype={"bio_id": str})
    b = b[b["bio_id"].isin(cuenta.index)].drop_duplicates("bio_id")
    per = pd.DataFrame({
        "bio_id": b["bio_id"], "nombre": b["nombre"].astype(str),
        "roles": b["bio_id"].map(roles), "n_peliculas": b["bio_id"].map(cuenta).astype(int),
        "foto": b["foto_link"].map(texto), "foto_grande": b["foto_link_big"].map(texto),
        "nacimiento": fecha(b["fecha_nacimiento"]), "fallecimiento": fecha(b["fecha_fallecimiento"]),
        "lugar": b["lugar_nacimiento"].map(lugar_es),
        "biografia": b["biografia"].map(texto), "biografia_en": b["biografia_idioma"].eq("en"),
        "sitio_web": b["homepage"].map(texto),
        "imdb": b["imdb_person_id"].map(texto), "tmdb": b["person_id"],
        "popularidad": b["popularidad"],
    })
    # Popularidad: porcentaje de personas de la app con un índice TMDB mayor
    pop = per["popularidad"]
    per["top_pct"] = (pop.rank(ascending=False, method="min") / pop.notna().sum() * 100).clip(lower=1).round()
    per["nombre_norm"] = per["nombre"].str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii").str.lower()
    per = per.sort_values(["n_peliculas", "popularidad"], ascending=False)
    per.to_parquet(SALIDA / "personas.parquet", index=False)

    print(f"Fichas: {fichas['sinopsis'].notna().sum():,} con sinopsis de {len(fichas):,} películas")
    print(f"Recorrido: {len(lanz):,} fechas · Créditos: {len(cred):,} · Personas: {len(per):,}")
    print(f"Máximo de cines actualizado en {maximo.gt(0).sum():,} películas · Reestrenos excluidos: {len(reestrenos)}")


if __name__ == "__main__":
    main()
