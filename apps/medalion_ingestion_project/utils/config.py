"""Medalion-specific config helpers (legacy product names, domain mappings)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dataplatform.config import ConfigLoader


def resolve_product(
    loader: ConfigLoader,
    name: str,
    environment: str | None = None,
) -> dict[str, Any]:
    """Resolve pipeline config — legacy products/ or process/domain mapping."""
    legacy = loader.config_dir / f"products/{name}.yml"
    if legacy.exists():
        return loader.read_yaml(legacy)

    env = environment
    mapping: dict[str, tuple[str, str]] = {
        "hdl_ingest": ("ingestion", "orders"),
        "kpi_metrics": ("transformation", "kpi"),
        "analytics_export": ("transformation", "analytics_export"),
    }
    if name in mapping:
        process_name, domain_key = mapping[name]
        section = loader.process(process_name, env).get(domain_key, {})
        return {"product": name, **section}

    if name == "brewery_etl":
        ingestion = loader.process("ingestion", env).get("brewery", {})
        transformation = loader.process("transformation", env).get("brewery", {})
        merged = dict(ingestion)
        if "dq" in transformation:
            merged["dq"] = transformation["dq"]
        merged["product"] = name
        return merged

    raise FileNotFoundError(f"Unknown product/process config: {name}")
