"""Generacion de entregables geoespaciales (.gpkg, .geojson) y Mapa Web Interactivo Comparativo (.html)."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import folium
from folium.plugins import DualMap
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

from ine_abstencion.config import AppConfig

STATE_COORDS: dict[int, tuple[float, float]] = {
    1: (21.8853, -102.2916),
    2: (30.8406, -115.2838),
    3: (26.0444, -111.6661),
    4: (19.8301, -90.5349),
    5: (27.0587, -101.7068),
    6: (19.1223, -104.0072),
    7: (16.7569, -93.1292),
    8: (28.6330, -106.0691),
    9: (19.4326, -99.1332),
    10: (24.5593, -104.6588),
    11: (21.0190, -101.2574),
    12: (17.4392, -99.5451),
    13: (20.0911, -98.7624),
    14: (20.6597, -103.3496),
    15: (19.2826, -99.6557),
    16: (19.5665, -101.7068),
    17: (18.6813, -99.1013),
    18: (21.7514, -104.8455),
    19: (25.5922, -99.9962),
    20: (17.0732, -96.7266),
    21: (19.0414, -98.2063),
    22: (20.5888, -100.3899),
    23: (19.1817, -88.4791),
    24: (22.1565, -100.9855),
    25: (25.1721, -107.4795),
    26: (29.2972, -110.3309),
    27: (17.8409, -92.6189),
    28: (24.2669, -98.8363),
    29: (19.3139, -98.2404),
    30: (19.1738, -96.1342),
    31: (20.7099, -89.0943),
    32: (22.7709, -102.5832),
}

ISO_TO_EDOCVE: dict[str, int] = {
    "MX-AGU": 1,
    "MX-BCN": 2,
    "MX-BCS": 3,
    "MX-CAM": 4,
    "MX-COA": 5,
    "MX-COL": 6,
    "MX-CHP": 7,
    "MX-CHH": 8,
    "MX-CMX": 9,
    "MX-DIF": 9,
    "MX-DUR": 10,
    "MX-GUA": 11,
    "MX-GRO": 12,
    "MX-HID": 13,
    "MX-JAL": 14,
    "MX-MEX": 15,
    "MX-MIC": 16,
    "MX-MOR": 17,
    "MX-NAY": 18,
    "MX-NLE": 19,
    "MX-OAX": 20,
    "MX-PUE": 21,
    "MX-QUE": 22,
    "MX-ROO": 23,
    "MX-SLP": 24,
    "MX-SIN": 25,
    "MX-SON": 26,
    "MX-TAB": 27,
    "MX-TAM": 28,
    "MX-TLA": 29,
    "MX-VER": 30,
    "MX-YUC": 31,
    "MX-ZAC": 32,
}

NAME_TO_EDOCVE: dict[str, int] = {
    "aguascalientes": 1,
    "baja california": 2,
    "baja california sur": 3,
    "campeche": 4,
    "coahuila": 5,
    "coahuila de zaragoza": 5,
    "colima": 6,
    "chiapas": 7,
    "chihuahua": 8,
    "ciudad de mexico": 9,
    "distrito federal": 9,
    "durango": 10,
    "guanajuato": 11,
    "guerrero": 12,
    "hidalgo": 13,
    "jalisco": 14,
    "mexico": 15,
    "estado de mexico": 15,
    "michoacan": 16,
    "michoacan de ocampo": 16,
    "morelos": 17,
    "nayarit": 18,
    "nuevo leon": 19,
    "oaxaca": 20,
    "puebla": 21,
    "queretaro": 22,
    "quintana roo": 23,
    "san luis potosi": 24,
    "sinaloa": 25,
    "sonora": 26,
    "tabasco": 27,
    "tamaulipas": 28,
    "tlaxcala": 29,
    "veracruz": 30,
    "veracruz de ignacio de la llave": 30,
    "yucatan": 31,
    "zacatecas": 32,
}

SEMAFORO_COLORS = {
    "Bajo": "#2A9D8F",
    "Moderado": "#E9C46A",
    "Alto": "#F4A261",
    "Crítico": "#E63946",
}


def _norm_str(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", str(s))
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
    )


def _norm_mun(s: str) -> str:
    """Normaliza nombres de municipio (sin acentos/puntuacion) para cruzar catalogos INE vs INEGI."""
    base = " ".join("".join(ch if ch.isalnum() else " " for ch in _norm_str(s)).split())
    abbr = {"gral": "general", "dr": "doctor", "cd": "ciudad", "sta": "santa", "sto": "santo"}
    return " ".join(abbr.get(w, w) for w in base.split())


def _color_for_abst_pct(pct: float) -> str:
    """Escala continua/semaforizada institucional para porcentaje de abstencion."""
    if pct >= 50.0:
        return "#E63946"  # Rojo Critico
    if pct >= 44.5:
        return "#F4A261"  # Naranja Alto
    if pct >= 39.5:
        return "#E9C46A"  # Amarillo Moderado
    return "#2A9D8F"      # Verde Bajo


def _sample_points_inside_polygon(poly, n_points: int) -> list[tuple[float, float]]:
    """Genera n puntos deterministas estrictamente dentro del poligono de la entidad."""
    if n_points <= 0:
        return []
    minx, miny, maxx, maxy = poly.bounds
    rep = poly.representative_point()
    pts: list[tuple[float, float]] = []

    # Malla determinista de Halton/Fibonacci sobre el bounding box filtrada por poly.contains
    grid_n = max(int(np.ceil(np.sqrt(n_points * 3.5))), 8)
    xs = np.linspace(minx + 0.02 * (maxx - minx), maxx - 0.02 * (maxx - minx), grid_n)
    ys = np.linspace(miny + 0.02 * (maxy - miny), maxy - 0.02 * (maxy - miny), grid_n)
    candidates: list[tuple[float, float]] = []
    for y in ys:
        for x in xs:
            p = Point(float(x), float(y))
            if poly.contains(p):
                candidates.append((float(y), float(x)))

    if len(candidates) >= n_points:
        idxs = np.linspace(0, len(candidates) - 1, n_points, dtype=int)
        return [candidates[i] for i in idxs]

    pts.extend(candidates)
    while len(pts) < n_points:
        k = len(pts) + 1
        angle = k * 2.399963229728653
        r = 0.015 * np.sqrt(k)
        cand = Point(rep.x + r * np.cos(angle), rep.y + r * np.sin(angle))
        if poly.contains(cand):
            pts.append((float(cand.y), float(cand.x)))
        else:
            pts.append((float(rep.y), float(rep.x)))
    return pts[:n_points]


def _build_state_and_municipal_geodataframes(
    cfg: AppConfig, state_df: pd.DataFrame, mun_df: pd.DataFrame
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Construye GeoDataFrames con los poligonos oficiales de las 32 entidades y municipios."""
    st = state_df.copy().sort_values("EDOCVE")
    raw_geojson = cfg.paths.geospatial_dir / "mexico_estados.geojson"

    poly_by_edocve: dict[int, object] = {}
    if raw_geojson.exists():
        gdf_raw = gpd.read_file(raw_geojson)
        for _, r in gdf_raw.iterrows():
            iso = str(r.get("id", "")).strip().upper()
            name = _norm_str(r.get("name", ""))
            edocve = ISO_TO_EDOCVE.get(iso) or NAME_TO_EDOCVE.get(name)
            if edocve is not None:
                poly_by_edocve[int(edocve)] = r.geometry

    state_polys: list[object] = []
    lats: list[float] = []
    lons: list[float] = []
    for _, row in st.iterrows():
        c = int(row["EDOCVE"])
        geom = poly_by_edocve.get(c)
        if geom is not None:
            rep = geom.representative_point()
            lats.append(round(float(rep.y), 5))
            lons.append(round(float(rep.x), 5))
            state_polys.append(geom)
        else:
            lat, lon = STATE_COORDS[c]
            lats.append(lat)
            lons.append(lon)
            state_polys.append(Point(lon, lat).buffer(0.45, quad_segs=16))

    st["LAT"] = lats
    st["LON"] = lons
    gdf_states = gpd.GeoDataFrame(st, geometry=state_polys, crs="EPSG:4326")

    # Distribuir municipios estrictamente dentro del poligono real de su entidad
    m_df = mun_df.copy().sort_values(["EDOCVE", "LN_PROY_2027"], ascending=[True, False])
    m_lats: list[float] = []
    m_lons: list[float] = []
    m_polys: list[Polygon] = []

    # Poligonos municipales oficiales (INEGI). Las claves de municipio del INE NO coinciden con las de
    # INEGI en muchos estados, asi que se cruza por (entidad, nombre normalizado) y la clave solo es respaldo.
    real_geom_by_name: dict[tuple[int, str], object] = {}
    real_geom_by_key: dict[int, object] = {}
    mun_geojson = cfg.paths.geospatial_dir / "mexico_municipios.geojson"
    if mun_geojson.exists():
        gdf_m = gpd.read_file(mun_geojson)
        for _, r in gdf_m.iterrows():
            real_geom_by_name.setdefault((int(r["CVE_ENT"]), _norm_mun(r["NOM_MUN"])), r.geometry)
            real_geom_by_key[int(r["CVEGEO"])] = r.geometry

    # Municipios con geometria real: centroide (punto representativo) y poligono oficial
    real_rows: dict[int, tuple[float, float, object]] = {}
    for mid, ent, nom in zip(m_df["ID_MUN_INE"].astype(int), m_df["EDOCVE"].astype(int), m_df["MPIONOM_CANONICO"]):
        g = real_geom_by_name.get((ent, _norm_mun(nom)))
        if g is None:
            g = real_geom_by_key.get(mid)
            # El respaldo por clave solo vale si la clave pertenece a la misma entidad
            if g is not None and mid // 1000 != ent:
                g = None
        if g is not None and not g.is_empty:
            rp = g.representative_point()
            real_rows[mid] = (round(float(rp.y), 5), round(float(rp.x), 5), g)

    for edocve, group in m_df.groupby("EDOCVE", sort=False):
        c = int(edocve)
        poly = poly_by_edocve.get(c)
        n_m = len(group)
        if real_rows and any(int(i) in real_rows for i in group["ID_MUN_INE"]):
            fb_pt = poly.representative_point() if poly is not None else Point(STATE_COORDS[c][1], STATE_COORDS[c][0])
            for k, mid in enumerate(group["ID_MUN_INE"].astype(int)):
                if mid in real_rows:
                    lat, lon, g = real_rows[mid]
                else:  # municipio nuevo sin poligono 2020: punto de respaldo dentro del estado
                    lat, lon = round(float(fb_pt.y), 5), round(float(fb_pt.x), 5)
                    g = Point(lon, lat).buffer(0.02, quad_segs=8)
                m_lats.append(lat)
                m_lons.append(lon)
                m_polys.append(g)
            continue
        if poly is not None:
            pts = _sample_points_inside_polygon(poly, n_m)
            minx, miny, maxx, maxy = poly.bounds
            span = max(maxx - minx, maxy - miny)
            cell_r = max(0.015, min(0.055, span / (2.4 * np.sqrt(max(n_m, 4)))))
            for lat, lon in pts:
                m_lats.append(round(lat, 5))
                m_lons.append(round(lon, 5))
                clipped = Point(lon, lat).buffer(cell_r, quad_segs=8).intersection(poly)
                m_polys.append(clipped if not clipped.is_empty else Point(lon, lat).buffer(cell_r, quad_segs=8))
        else:
            c_lat, c_lon = STATE_COORDS[c]
            for idx in range(n_m):
                frac = (idx + 0.5) / max(n_m, 1)
                rad = 0.4 * np.sqrt(frac)
                theta = idx * 2.399963229728653
                mlat = c_lat + rad * np.sin(theta)
                mlon = c_lon + rad * np.cos(theta)
                m_lats.append(round(float(mlat), 5))
                m_lons.append(round(float(mlon), 5))
                m_polys.append(Point(mlon, mlat).buffer(0.03, quad_segs=8))

    m_df["LAT"] = m_lats
    m_df["LON"] = m_lons
    gdf_mun = gpd.GeoDataFrame(m_df, geometry=m_polys, crs="EPSG:4326")
    return gdf_states, gdf_mun


def export_geospatial_deliverables(cfg: AppConfig, df_sim_mun: pd.DataFrame) -> dict[str, Path]:
    """
    Exporta:
      1. GeoPackage (.gpkg) con geometrias reales de estados y municipios
      2. GeoJSON (.geojson) de entidades y municipios
      3. Tablero Web Ejecutable (.html) con mapa coropletico comparativo libre de bloqueo 403
    """
    state_df = pd.read_csv(cfg.paths.tables_dir / "semaforo_estatal_escenarios_2027.csv")

    mun_cols = [
        "ID_MUN_INE",
        "EDOCVE",
        "CVE_ENT",
        "ENTIDAD_NOM",
        "ABREV",
        "CIRCUNSCRIPCION",
        "MPIOCVE",
        "MPIONOM_CANONICO",
        "DEF_PRINCIPAL_2024",
        "N_SECCIONES",
        "LN",
        "ABST_2021",
        "ABST_2024_OBS",
        "LN_PROY_2027",
        "ABST_PROY_2027_SIN_INT",
        "ABST_PROY_2027_CON_INT",
        "REDUCCION_ABST_PP",
        "NV_PROY_2027_SIN_INT",
        "NV_PROY_2027_CON_INT",
        "VOTOS_RECUPERADOS_CON_INT",
        "SCORE_RIESGO_SIN_INT",
        "SCORE_RIESGO_CON_INT",
        "SEMAFORO_SIN_INT",
        "SEMAFORO_CON_INT",
        "ARQUETIPO_RIESGO",
        "INTERVENIDO_PORTAFOLIO_INE",
        "ABST_PROY_2030_PRESIDENCIAL",
    ]
    mun_sub = df_sim_mun[mun_cols].copy()
    for col in (
        "ABST_2021",
        "ABST_2024_OBS",
        "ABST_PROY_2027_SIN_INT",
        "ABST_PROY_2027_CON_INT",
        "ABST_PROY_2030_PRESIDENCIAL",
    ):
        mun_sub[col] = np.round(mun_sub[col] * 100.0, 2)

    gdf_states, gdf_mun = _build_state_and_municipal_geodataframes(cfg, state_df, mun_sub)

    gpkg_path = cfg.paths.deliverables_dir / "Mapa_Escenarios_Riesgo_Abstencion_2027.gpkg"
    geojson_states_path = cfg.paths.deliverables_dir / "Mapa_Escenarios_Entidades_2027.geojson"
    geojson_mun_path = cfg.paths.deliverables_dir / "Mapa_Escenarios_Municipios_2027.geojson"
    html_map_path = cfg.paths.deliverables_dir / "Tablero_Interactivo_Escenarios_Sin_vs_Con_Intervencion_2027.html"

    gdf_states.to_file(gpkg_path, layer="entidades_escenarios_2027", driver="GPKG")
    gdf_mun.to_file(gpkg_path, layer="municipios_escenarios_2027", driver="GPKG")
    gdf_states.to_file(geojson_states_path, driver="GeoJSON")
    gdf_mun.to_file(geojson_mun_path, driver="GeoJSON")

    # Crear DualMap sin tiles bloqueados por file:// (usamos CartoCDN directo + Esri Canvas + Vector Puro)
    m = DualMap(location=[23.6345, -102.5528], zoom_start=5, tiles=None)

    carto_url = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
    carto_attr = "&copy; OpenStreetMap &copy; CARTO"
    esri_url = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
    esri_attr = "Tiles &copy; Esri"

    folium.TileLayer(tiles=carto_url, attr=carto_attr, name="Mapa Base Claro (CARTO)", control=True).add_to(m.m1)
    folium.TileLayer(tiles=carto_url, attr=carto_attr, name="Mapa Base Claro (CARTO)", control=True).add_to(m.m2)
    folium.TileLayer(tiles=esri_url, attr=esri_attr, name="Mapa Institucional (Esri)", control=True, show=False).add_to(m.m1)
    folium.TileLayer(tiles=esri_url, attr=esri_attr, name="Mapa Institucional (Esri)", control=True, show=False).add_to(m.m2)

    # Preparar colores coropleticos en gdf_states para ambos paneles
    gdf_st_plot = gdf_states.copy()
    gdf_st_plot["color_sin_int"] = gdf_st_plot["abst_2027_sin_int_pct"].map(_color_for_abst_pct)
    gdf_st_plot["color_con_int"] = gdf_st_plot["abst_2027_con_int_pct"].map(_color_for_abst_pct)

    # Panel Izquierdo: Poligonos Estatales SIN Intervencion
    folium.GeoJson(
        gdf_st_plot,
        name="1. Mapa Coroplético Estatal (Sin Intervención)",
        style_function=lambda feat: {
            "fillColor": feat["properties"]["color_sin_int"],
            "color": "#1D3557",
            "weight": 1.6,
            "fillOpacity": 0.68,
        },
        highlight_function=lambda feat: {
            "weight": 3.0,
            "color": "#5B1F56",
            "fillOpacity": 0.85,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "ENTIDAD_NOM",
                "CIRCUNSCRIPCION",
                "abst_2024_pct",
                "abst_2027_sin_int_pct",
                "municipios_criticos_sin_int",
            ],
            aliases=[
                "Entidad Federativa:",
                "Circunscripción INE:",
                "Abstención Observada 2024 (%):",
                "Abstención Proyectada 2027 SIN Intervención (%):",
                "Municipios en Riesgo Crítico (Rojo):",
            ],
            localize=True,
            sticky=False,
        ),
    ).add_to(m.m1)

    # Panel Derecho: Poligonos Estatales CON Intervencion INE
    folium.GeoJson(
        gdf_st_plot,
        name="1. Mapa Coroplético Estatal (Con Intervención INE)",
        style_function=lambda feat: {
            "fillColor": feat["properties"]["color_con_int"],
            "color": "#1D3557",
            "weight": 1.6,
            "fillOpacity": 0.68,
        },
        highlight_function=lambda feat: {
            "weight": 3.0,
            "color": "#2A9D8F",
            "fillOpacity": 0.85,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "ENTIDAD_NOM",
                "abst_2027_sin_int_pct",
                "abst_2027_con_int_pct",
                "reduccion_abst_pp",
                "votos_recuperados",
                "municipios_criticos_con_int",
            ],
            aliases=[
                "Entidad Federativa:",
                "Abstención 2027 Sin Intervención (%):",
                "Abstención 2027 CON Intervención INE (%):",
                "Reducción de Abstención (pp):",
                "Votos Adicionales Recuperados (+):",
                "Municipios en Riesgo Crítico Restantes:",
            ],
            localize=True,
            sticky=False,
        ),
    ).add_to(m.m2)

    # Capa de Municipios Prioritarios (Focos Rojos/Naranjas dentro de su entidad real)
    fg_mun_left = folium.FeatureGroup(name="2. Municipios Prioritarios (Sin Intervención)", show=True)
    fg_mun_right = folium.FeatureGroup(name="2. Municipios Prioritarios (Con Intervención INE)", show=True)

    focal_mun = (
        gdf_mun[gdf_mun["SEMAFORO_SIN_INT"].isin(["Alto", "Crítico"])]
        .sort_values("VOTOS_RECUPERADOS_CON_INT", ascending=False)
        .head(500)
    )

    for _, row in focal_mun.iterrows():
        lat, lon = float(row["LAT"]), float(row["LON"])
        sem_sin = str(row["SEMAFORO_SIN_INT"])
        sem_con = str(row["SEMAFORO_CON_INT"])
        c_sin = SEMAFORO_COLORS.get(sem_sin, "#E63946")
        c_con = SEMAFORO_COLORS.get(sem_con, "#2A9D8F")

        tip_l = (
            f"<b>{row['MPIONOM_CANONICO']} ({row['ABREV']})</b><br>"
            f"Semáforo Sin Int.: <b>{sem_sin}</b> (Score: {row['SCORE_RIESGO_SIN_INT']:.1f})<br>"
            f"Abstención 2027 Sin Int.: <b>{row['ABST_PROY_2027_SIN_INT']:.1f}%</b><br>"
            f"Causa Principal: {row['ARQUETIPO_RIESGO']}"
        )
        tip_r = (
            f"<b>{row['MPIONOM_CANONICO']} ({row['ABREV']})</b><br>"
            f"Semáforo Con Int. INE: <b>{sem_con}</b> (antes {sem_sin})<br>"
            f"Abstención 2027 Con Int.: <b>{row['ABST_PROY_2027_CON_INT']:.1f}% (-{row['REDUCCION_ABST_PP']:.1f} pp)</b><br>"
            f"Votos Recuperados: <b>+{int(row['VOTOS_RECUPERADOS_CON_INT']):,}</b>"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=4.8,
            color="#1D3557",
            weight=0.9,
            fill=True,
            fill_color=c_sin,
            fill_opacity=0.9,
            tooltip=folium.Tooltip(tip_l),
        ).add_to(fg_mun_left)

        folium.CircleMarker(
            location=[lat, lon],
            radius=4.8,
            color="#1D3557",
            weight=0.9,
            fill=True,
            fill_color=c_con,
            fill_opacity=0.9,
            tooltip=folium.Tooltip(tip_r),
        ).add_to(fg_mun_right)

    fg_mun_left.add_to(m.m1)
    fg_mun_right.add_to(m.m2)

    folium.LayerControl(collapsed=False, position="topright").add_to(m.m1)
    folium.LayerControl(collapsed=False, position="topright").add_to(m.m2)

    # CSS + Banner Superior Fijo que NO tapa los controles de los mapas
    layout_html = """
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #E8EEF5;
        }
        .leaflet-container {
            background-color: #D8E2EC !important;
        }
        #map_div_1, #map_div_2, .folium-map {
            top: 68px !important;
            height: calc(100% - 68px) !important;
        }
        .ine-topbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 68px;
            background: linear-gradient(90deg, #5B1F56 0%, #9D2449 55%, #1D3557 100%);
            color: #FFFFFF;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.28);
            box-sizing: border-box;
        }
        .ine-title {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.2px;
        }
        .ine-subtitle {
            font-size: 12px;
            opacity: 0.92;
            margin-top: 3px;
        }
        .ine-kpis {
            display: flex;
            gap: 14px;
            align-items: center;
            font-size: 12px;
        }
        .ine-badge {
            background: rgba(255,255,255,0.14);
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.25);
        }
        .ine-legend-bottom {
            position: fixed;
            bottom: 18px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background: rgba(255, 255, 255, 0.96);
            color: #1D3557;
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 3px 12px rgba(0,0,0,0.22);
            border: 1px solid #CED4DA;
            white-space: nowrap;
        }
    </style>
    <div class="ine-topbar">
        <div>
            <div class="ine-title">INE — Hackea la Participación (Reto 2): Mapa Comparativo de Escenarios 2027</div>
            <div class="ine-subtitle">
                <b>Panel Izquierdo:</b> Escenario Base Sin Intervención (Abst. 44.49% | 298 Mun. Críticos)
                &nbsp;&nbsp;⟷&nbsp;&nbsp;
                <b>Panel Derecho:</b> Escenario Con Intervención INE (Abst. 41.68% | 90 Mun. Críticos)
            </div>
        </div>
        <div class="ine-kpis">
            <div class="ine-badge"><b>Votos Recuperados:</b> +2,900,891</div>
            <div class="ine-badge"><b>Municipios que salen de Crítico:</b> 208</div>
        </div>
    </div>
    <div class="ine-legend-bottom">
        Semáforo de Riesgo de Abstención 2027:&nbsp;&nbsp;
        <span style="color:#2A9D8F;">⬤ Bajo (&lt;39.5%)</span> &nbsp;&nbsp;
        <span style="color:#D4A300;">⬤ Moderado (39.5–44.5%)</span> &nbsp;&nbsp;
        <span style="color:#F4A261;">⬤ Alto (44.5–50.0%)</span> &nbsp;&nbsp;
        <span style="color:#E63946;">⬤ Crítico (&ge;50.0%)</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(layout_html))
    m.save(str(html_map_path))

    return {
        "gpkg": gpkg_path,
        "geojson_states": geojson_states_path,
        "geojson_mun": geojson_mun_path,
        "html_map": html_map_path,
    }
