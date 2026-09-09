"""Pinned SSB contracts for broad Norway workforce and electricity observations."""

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

from datacenter_need.sources.ssb import SsbContractError

OCCUPATION_CODES = ("1", "2", "3_01-03", "4", "5", "6", "7", "8", "9", "0b")
OCCUPATION_LABELS = {
    "1": "Managers",
    "2": "Professionals",
    "3_01-03": "Technicians and associate professionals, armed forces",
    "4": "Clerical support workers",
    "5": "Service and sales workers",
    "6": "Skilled agricultural, forestry and fishery workers",
    "7": "Craft and related trades workers",
    "8": "Plant and machine operators and assemblers",
    "9": "Elementary occupations",
    "0b": "Unspecified or unidentifiable occupations",
}
OCCUPATION_QUERY = {
    "lang": "en",
    "valueCodes[Kjonn]": "0",
    "valueCodes[Alder]": "999D",
    "valueCodes[Yrke]": ",".join(OCCUPATION_CODES),
    "valueCodes[ContentsCode]": "Lonsstakere",
    "valueCodes[Tid]": "2025K4",
    "outputFormat": "json-stat2",
}
OCCUPATION_URL = "https://data.ssb.no/api/pxwebapi/v2/tables/11658/data"
ELECTRICITY_CODES = ("ProdTotal", "Nettoforbruk")
ELECTRICITY_LABELS = {"ProdTotal": "Production, total", "Nettoforbruk": "Net consumption"}
ELECTRICITY_QUERY = {
    "lang": "en",
    "valueCodes[ContentsCode]": ",".join(ELECTRICITY_CODES),
    "valueCodes[Tid]": "2025",
    "outputFormat": "json-stat2",
}
ELECTRICITY_URL = "https://data.ssb.no/api/pxwebapi/v2/tables/08307/data"


@dataclass(frozen=True)
class SsbCell:
    code: str
    label: str
    value: int | float | None
    missing_reason: str | None


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SsbContractError(f"{name} must be an object")
    return value


def _codes(dimension: dict[str, Any], name: str) -> list[str]:
    category = _mapping(dimension.get("category"), f"dimension {name} category")
    index = _mapping(category.get("index"), f"dimension {name} index")
    if sorted(index.values()) != list(range(len(index))):
        raise SsbContractError(f"dimension {name} index is invalid")
    return [code for code, _ in sorted(index.items(), key=lambda item: item[1])]


def _status(response: dict[str, Any], index: int) -> str | None:
    status = response.get("status")
    if status is None:
        return None
    if isinstance(status, dict):
        value = status.get(str(index))
    elif isinstance(status, list) and len(status) == len(response.get("value", [])):
        value = status[index]
    else:
        raise SsbContractError("cell status has an unexpected shape")
    return str(value) if value else None


def _cells(
    response: dict[str, Any], dimension_name: str, expected_codes: tuple[str, ...]
) -> list[SsbCell]:
    dimensions = _mapping(response.get("dimension"), "dimension")
    dimension = _mapping(dimensions.get(dimension_name), f"dimension {dimension_name}")
    codes = _codes(dimension, dimension_name)
    if codes != list(expected_codes):
        raise SsbContractError(f"dimension {dimension_name} codes changed")
    labels = _mapping(dimension["category"].get("label"), f"dimension {dimension_name} labels")
    values = response.get("value")
    if not isinstance(values, list) or len(values) != len(expected_codes):
        raise SsbContractError("response value count changed")
    cells = []
    for index, code in enumerate(codes):
        value = values[index]
        status = _status(response, index)
        if value is None:
            cells.append(SsbCell(code, str(labels[code]), None, f"SSB cell status: {status or 'missing'}"))
        elif (
            status is not None
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value < 0
        ):
            raise SsbContractError("cell value or status is invalid")
        else:
            cells.append(SsbCell(code, str(labels[code]), value, None))
    return cells


def normalize_broad_occupations(response: dict[str, Any]) -> list[SsbCell]:
    if response.get("version") != "2.0" or response.get("class") != "dataset":
        raise SsbContractError("response is not a JSON-stat2 dataset")
    if response.get("source") != "Statistics Norway":
        raise SsbContractError("response publisher changed")
    if response.get("id") != ["Kjonn", "Alder", "Yrke", "ContentsCode", "Tid"]:
        raise SsbContractError("occupation response dimensions changed")
    if response.get("size") != [1, 1, len(OCCUPATION_CODES), 1, 1]:
        raise SsbContractError("occupation response size changed")
    dimensions = _mapping(response.get("dimension"), "dimension")
    expected_singletons = {"Kjonn": "0", "Alder": "999D", "ContentsCode": "Lonsstakere", "Tid": "2025K4"}
    for name, code in expected_singletons.items():
        if _codes(_mapping(dimensions.get(name), f"dimension {name}"), name) != [code]:
            raise SsbContractError(f"dimension {name} changed")
    contents = _mapping(dimensions["ContentsCode"].get("category"), "contents category")
    unit = _mapping(contents.get("unit"), "contents units").get("Lonsstakere", {})
    extension = _mapping(dimensions["ContentsCode"].get("extension"), "contents extension")
    if unit.get("base") != "persons" or unit.get("decimals") != 0:
        raise SsbContractError("employee unit changed")
    if extension.get("refperiod", {}).get("Lonsstakere") != "Mid-month of the quarter":
        raise SsbContractError("employee reference period changed")
    if extension.get("measuringType", {}).get("Lonsstakere") != "Stock":
        raise SsbContractError("employee measurement type changed")
    cells = _cells(response, "Yrke", OCCUPATION_CODES)
    if {cell.code: cell.label for cell in cells} != OCCUPATION_LABELS:
        raise SsbContractError("occupation labels changed")
    return cells


def normalize_electricity(response: dict[str, Any]) -> list[SsbCell]:
    if response.get("version") != "2.0" or response.get("class") != "dataset":
        raise SsbContractError("response is not a JSON-stat2 dataset")
    if response.get("source") != "Statistics Norway":
        raise SsbContractError("response publisher changed")
    if response.get("id") != ["ContentsCode", "Tid"] or response.get("size") != [2, 1]:
        raise SsbContractError("electricity response dimensions changed")
    dimensions = _mapping(response.get("dimension"), "dimension")
    if _codes(_mapping(dimensions.get("Tid"), "dimension Tid"), "Tid") != ["2025"]:
        raise SsbContractError("electricity year changed")
    contents_dimension = _mapping(dimensions.get("ContentsCode"), "dimension ContentsCode")
    category = _mapping(contents_dimension.get("category"), "contents category")
    units = _mapping(category.get("unit"), "contents units")
    extension = _mapping(contents_dimension.get("extension"), "contents extension")
    for code in ELECTRICITY_CODES:
        if units.get(code, {}).get("base") != "GWh" or units.get(code, {}).get("decimals") != 0:
            raise SsbContractError("electricity unit changed")
        if extension.get("refperiod", {}).get(code) != "The entire year":
            raise SsbContractError("electricity reference period changed")
        if extension.get("measuringType", {}).get(code) != "Flow":
            raise SsbContractError("electricity measurement type changed")
    cells = _cells(response, "ContentsCode", ELECTRICITY_CODES)
    if {cell.code: cell.label for cell in cells} != ELECTRICITY_LABELS:
        raise SsbContractError("electricity labels changed")
    return cells


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def fetch_norway_baseline_snapshot(
    output_path: Path,
    *,
    client: httpx.Client | None = None,
    retrieved_date: str | None = None,
) -> dict[str, Any]:
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            timeout=httpx.Timeout(20, connect=10),
            transport=httpx.HTTPTransport(retries=2),
            headers={"User-Agent": "DatacenterNeed/0.1 (+https://github.com/)"},
        )
    responses: list[tuple[str, str, dict[str, str], dict[str, Any]]] = []
    try:
        for name, url, query in (
            ("table-11658-broad.json", OCCUPATION_URL, OCCUPATION_QUERY),
            ("table-08307-electricity.json", ELECTRICITY_URL, ELECTRICITY_QUERY),
        ):
            try:
                response = client.get(url, params=query)
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, json.JSONDecodeError) as error:
                raise SsbContractError(f"SSB request failed: {error}") from error
            if not isinstance(payload, dict):
                raise SsbContractError("SSB response must be an object")
            responses.append((name, url, query, payload))
    finally:
        if owns_client:
            client.close()

    occupations = normalize_broad_occupations(responses[0][3])
    electricity = normalize_electricity(responses[1][3])
    files = {name: _canonical_json(payload) for name, _, _, payload in responses}
    manifest = {
        "retrieved_date": retrieved_date or datetime.now(UTC).date().isoformat(),
        "license": "CC BY 4.0",
        "sources": {
            name: {
                "query_url": str(httpx.URL(url, params=query)),
                "source_updated": payload.get("updated"),
                "sha256": hashlib.sha256(files[name]).hexdigest(),
            }
            for name, url, query, payload in responses
        },
        "normalized": {
            "occupation_employees": {cell.code: cell.value for cell in occupations},
            "electricity_gwh": {cell.code: cell.value for cell in electricity},
        },
    }
    files["manifest.json"] = _canonical_json(manifest)

    expected_names = set(files)
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
        for name, content in files.items():
            (temporary / name).write_bytes(content)
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