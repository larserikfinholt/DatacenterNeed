"""Strict normalization for audited Statistics Norway PxWebApi responses."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


class SsbContractError(ValueError):
    """Raised when an SSB response no longer matches the audited contract."""


@dataclass(frozen=True)
class EmployeeCell:
    value: int | None
    missing_reason: str | None
    occupation_code: str
    occupation_label: str
    period: str
    unit: str
    reference_period: str
    measurement_type: str
    classification_id: str


EXPECTED_DIMENSIONS = ["Kjonn", "Alder", "Yrke", "ContentsCode", "Tid"]
EXPECTED_CODES = {
    "Kjonn": "0",
    "Alder": "999D",
    "Yrke": "2512",
    "ContentsCode": "Lonsstakere",
    "Tid": "2025K4",
}
SSB_DATA_URL = "https://data.ssb.no/api/pxwebapi/v2/tables/11658/data"
SSB_QUERY = {
    "lang": "en",
    "valueCodes[Kjonn]": "0",
    "valueCodes[Alder]": "999D",
    "valueCodes[Yrke]": "2512",
    "valueCodes[ContentsCode]": "Lonsstakere",
    "valueCodes[Tid]": "2025K4",
    "outputFormat": "json-stat2",
}


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SsbContractError(f"{name} must be an object")
    return value


def _single_code(dimension: dict[str, Any], name: str) -> str:
    category = _require_mapping(dimension.get("category"), f"dimension {name} category")
    index = _require_mapping(category.get("index"), f"dimension {name} index")
    if list(index) != [EXPECTED_CODES[name]] or index[EXPECTED_CODES[name]] != 0:
        raise SsbContractError(f"dimension {name} does not contain the audited cell")
    return EXPECTED_CODES[name]


def _cell_status(response: dict[str, Any]) -> str | None:
    status = response.get("status")
    if status is None:
        return None
    if isinstance(status, dict):
        value = status.get("0")
    elif isinstance(status, list) and len(status) == 1:
        value = status[0]
    else:
        raise SsbContractError("cell status has an unexpected shape")
    return str(value) if value else None


def normalize_employee_cell(response: dict[str, Any]) -> EmployeeCell:
    """Validate and normalize the audited table 11658 employee response."""
    try:
        if response.get("version") != "2.0" or response.get("class") != "dataset":
            raise SsbContractError("response is not a JSON-stat2 dataset")
        if response.get("source") != "Statistics Norway":
            raise SsbContractError("response publisher changed")
        if response.get("id") != EXPECTED_DIMENSIONS or response.get("size") != [1] * 5:
            raise SsbContractError("response dimensions changed")
        px = _require_mapping(
            _require_mapping(response.get("extension"), "extension").get("px"), "extension.px"
        )
        if px.get("tableid") != "11658":
            raise SsbContractError("response table changed")

        dimensions = _require_mapping(response.get("dimension"), "dimension")
        if set(dimensions) != set(EXPECTED_DIMENSIONS):
            raise SsbContractError("response dimension definitions changed")
        for name in EXPECTED_DIMENSIONS:
            _single_code(_require_mapping(dimensions.get(name), f"dimension {name}"), name)

        occupation = _require_mapping(dimensions["Yrke"]["category"], "occupation category")
        occupation_label = _require_mapping(occupation.get("label"), "occupation labels").get(
            "2512"
        )
        if occupation_label != "Software developers":
            raise SsbContractError("occupation label changed")
        described_by = dimensions["Yrke"].get("link", {}).get("describedby", [])
        classification = described_by[0].get("extension", {}).get("Yrke", "")
        if "urn:ssb:classification:klass:7" not in classification:
            raise SsbContractError("occupation classification changed")

        contents = dimensions["ContentsCode"]
        category = _require_mapping(contents.get("category"), "contents category")
        unit = _require_mapping(category.get("unit"), "contents units").get("Lonsstakere", {})
        if unit.get("base") != "persons" or unit.get("decimals") != 0:
            raise SsbContractError("employee unit changed")
        extension = _require_mapping(contents.get("extension"), "contents extension")
        reference_period = extension.get("refperiod", {}).get("Lonsstakere")
        measurement_type = extension.get("measuringType", {}).get("Lonsstakere")
        if reference_period != "Mid-month of the quarter" or measurement_type != "Stock":
            raise SsbContractError("employee measurement boundary changed")

        values = response.get("value")
        if not isinstance(values, list) or len(values) != 1:
            raise SsbContractError("response must contain exactly one value")
        status = _cell_status(response)
        value = values[0]
        if value is None:
            return EmployeeCell(
                value=None,
                missing_reason=f"SSB cell status: {status or 'missing'}",
                occupation_code="2512",
                occupation_label=occupation_label,
                period="2025K4",
                unit="persons",
                reference_period=reference_period,
                measurement_type=measurement_type,
                classification_id="7",
            )
        if status is not None or not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SsbContractError("employee value or status is invalid")
        return EmployeeCell(
            value=value,
            missing_reason=None,
            occupation_code="2512",
            occupation_label=occupation_label,
            period="2025K4",
            unit="persons",
            reference_period=reference_period,
            measurement_type=measurement_type,
            classification_id="7",
        )
    except (IndexError, KeyError, TypeError) as error:
        raise SsbContractError("response does not match the audited SSB contract") from error


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def fetch_employee_snapshot(
    output_path: Path,
    *,
    client: httpx.Client | None = None,
    retrieved_date: str | None = None,
) -> dict[str, Any]:
    """Fetch, validate, and atomically archive the pinned table 11658 cell."""
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            timeout=httpx.Timeout(20, connect=10),
            transport=httpx.HTTPTransport(retries=2),
            headers={"User-Agent": "DatacenterNeed/0.1 (+https://github.com/)"},
        )
    try:
        try:
            response = client.get(SSB_DATA_URL, params=SSB_QUERY)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            raise SsbContractError(f"SSB request failed: {error}") from error
    finally:
        if owns_client:
            client.close()

    if not isinstance(payload, dict):
        raise SsbContractError("SSB response must be an object")
    normalized = normalize_employee_cell(payload)
    snapshot = _canonical_json(payload)
    query_url = str(httpx.URL(SSB_DATA_URL, params=SSB_QUERY))
    manifest = {
        "table_id": "11658",
        "query_url": query_url,
        "retrieved_date": retrieved_date or datetime.now(UTC).date().isoformat(),
        "source_updated": payload.get("updated"),
        "sha256": hashlib.sha256(snapshot).hexdigest(),
        "normalized_value": normalized.value,
        "license": "CC BY 4.0",
    }
    manifest_content = _canonical_json(manifest)

    expected_names = {"table-11658-cell.json", "manifest.json"}
    if output_path.exists():
        if not output_path.is_dir() or output_path.is_symlink():
            raise ValueError("snapshot output must be a regular directory")
        if {path.name for path in output_path.iterdir()} - expected_names:
            raise ValueError("snapshot directory contains unrelated files")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_path.name}-", dir=output_path.parent))
    backup = output_path.with_name(f".{output_path.name}.backup")
    if backup.exists():
        shutil.rmtree(temporary)
        raise ValueError(f"previous snapshot backup requires manual recovery: {backup}")
    try:
        (temporary / "table-11658-cell.json").write_bytes(snapshot)
        (temporary / "manifest.json").write_bytes(manifest_content)
        if output_path.exists():
            os.replace(output_path, backup)
        try:
            os.replace(temporary, output_path)
        except BaseException:
            if backup.exists():
                os.replace(backup, output_path)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest