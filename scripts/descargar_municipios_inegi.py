"""Descarga y consolida los poligonos municipales oficiales (Marco Geoestadistico INEGI 2020).

Fuente: https://github.com/PhantomInsights/mexico-geojson (2020/states/*.json)
Salida: data/geospatial/mexico_municipios.geojson (CVEGEO, simplificado para web).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE = "https://raw.githubusercontent.com/PhantomInsights/mexico-geojson/main/2020/states/"
TREE = "https://api.github.com/repos/PhantomInsights/mexico-geojson/git/trees/main?recursive=1"
OUT = Path(__file__).resolve().parents[1] / "data" / "geospatial" / "mexico_municipios.geojson"


def main() -> None:
    with urllib.request.urlopen(TREE, timeout=60) as r:
        tree = json.load(r)["tree"]
    names = [t["path"] for t in tree if t["path"].startswith("2020/states/") and t["path"].endswith(".json")]
    print(f"{len(names)} archivos estatales")
    frames = []
    for p in sorted(names):
        url = BASE + urllib.parse.quote(p.split("/")[-1])
        gdf = gpd.read_file(url)
        frames.append(gdf[["CVEGEO", "CVE_ENT", "CVE_MUN", "NOM_MUN", "geometry"]])
        print(" ", p, len(gdf))
    allg = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
    allg["geometry"] = allg.geometry.simplify(0.002, preserve_topology=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    allg.to_file(OUT, driver="GeoJSON")
    print("Municipios:", len(allg), "->", OUT)


if __name__ == "__main__":
    main()

