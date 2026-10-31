"""Carga centralizada de configuracion y rutas del proyecto."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "config.toml"


@dataclass(frozen=True)
class PathsConfig:
    project_root: Path
    raw_data_dir: Path
    silver_dir: Path
    gold_dir: Path
    geospatial_dir: Path
    outputs_dir: Path
    figures_dir: Path
    tables_dir: Path
    maps_dir: Path
    deliverables_dir: Path

    def ensure_dirs(self) -> None:
        for p in (
            self.silver_dir,
            self.gold_dir,
            self.geospatial_dir,
            self.outputs_dir,
            self.figures_dir,
            self.tables_dir,
            self.maps_dir,
            self.deliverables_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig
    elections: dict[str, Any]
    privacy: dict[str, Any]
    risk_index: dict[str, float]
    scenarios: dict[str, float]


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or DEFAULT_CONFIG_PATH
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    p = raw["paths"]
    paths = PathsConfig(
        project_root=PROJECT_ROOT,
        raw_data_dir=(PROJECT_ROOT / p["raw_data_dir"]).resolve(),
        silver_dir=(PROJECT_ROOT / p["silver_dir"]).resolve(),
        gold_dir=(PROJECT_ROOT / p["gold_dir"]).resolve(),
        geospatial_dir=(PROJECT_ROOT / p["geospatial_dir"]).resolve(),
        outputs_dir=(PROJECT_ROOT / p["outputs_dir"]).resolve(),
        figures_dir=(PROJECT_ROOT / p["figures_dir"]).resolve(),
        tables_dir=(PROJECT_ROOT / p["tables_dir"]).resolve(),
        maps_dir=(PROJECT_ROOT / p["maps_dir"]).resolve(),
        deliverables_dir=(PROJECT_ROOT / p["deliverables_dir"]).resolve(),
    )
    paths.ensure_dirs()
    return AppConfig(
        paths=paths,
        elections=raw["elections"],
        privacy=raw["privacy"],
        risk_index=raw["risk_index"],
        scenarios=raw["scenarios"],
    )

