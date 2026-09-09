import hashlib
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from datacenter_need.sources.ssb import SsbContractError
from datacenter_need.sources.ssb_norway import (
    ELECTRICITY_CODES,
    ELECTRICITY_LABELS,
    OCCUPATION_CODES,
    OCCUPATION_LABELS,
    fetch_norway_baseline_snapshot,
    normalize_broad_occupations,
    normalize_electricity,
)


def dimension(codes: tuple[str, ...], labels: dict[str, str]) -> dict:
    return {
        "category": {
            "index": {code: index for index, code in enumerate(codes)},
            "label": labels,
        }
    }


def occupation_response() -> dict:
    contents = dimension(("Lonsstakere",), {"Lonsstakere": "Number of employees"})
    contents["category"]["unit"] = {"Lonsstakere": {"base": "persons", "decimals": 0}}
    contents["extension"] = {
        "refperiod": {"Lonsstakere": "Mid-month of the quarter"},
        "measuringType": {"Lonsstakere": "Stock"},
    }
    return {
        "version": "2.0",
        "class": "dataset",
        "source": "Statistics Norway",
        "updated": "2026-08-13T06:00:00Z",
        "id": ["Kjonn", "Alder", "Yrke", "ContentsCode", "Tid"],
        "size": [1, 1, 10, 1, 1],
        "dimension": {
            "Kjonn": dimension(("0",), {"0": "Both sexes"}),
            "Alder": dimension(("999D",), {"999D": "All ages"}),
            "Yrke": dimension(OCCUPATION_CODES, OCCUPATION_LABELS),
            "ContentsCode": contents,
            "Tid": dimension(("2025K4",), {"2025K4": "2025K4"}),
        },
        "value": [244602, 755885, 437008, 168016, 611726, 27006, 255152, 184471, 146640, 8530],
    }


def electricity_response() -> dict:
    contents = dimension(ELECTRICITY_CODES, ELECTRICITY_LABELS)
    contents["category"]["unit"] = {
        code: {"base": "GWh", "decimals": 0} for code in ELECTRICITY_CODES
    }
    contents["extension"] = {
        "refperiod": {code: "The entire year" for code in ELECTRICITY_CODES},
        "measuringType": {code: "Flow" for code in ELECTRICITY_CODES},
    }
    return {
        "version": "2.0",
        "class": "dataset",
        "source": "Statistics Norway",
        "updated": "2026-05-08T06:00:00Z",
        "id": ["ContentsCode", "Tid"],
        "size": [2, 1],
        "dimension": {
            "ContentsCode": contents,
            "Tid": dimension(("2025",), {"2025": "2025"}),
        },
        "value": [161793, 130125],
    }


def test_normalizes_pinned_broad_occupation_and_electricity_cells() -> None:
    occupations = normalize_broad_occupations(occupation_response())
    electricity = normalize_electricity(electricity_response())
    assert sum(cell.value for cell in occupations if cell.value is not None) == 2_839_036
    assert {cell.code: cell.value for cell in electricity} == {
        "ProdTotal": 161793,
        "Nettoforbruk": 130125,
    }


def test_preserves_missing_cells_and_rejects_boundary_change() -> None:
    response = occupation_response()
    response["value"][0] = None
    response["status"] = {"0": "confidential"}
    assert normalize_broad_occupations(response)[0].missing_reason == "SSB cell status: confidential"

    changed = deepcopy(electricity_response())
    changed["dimension"]["ContentsCode"]["category"]["unit"]["ProdTotal"]["base"] = "MWh"
    with pytest.raises(SsbContractError, match="unit"):
        normalize_electricity(changed)


def test_fetch_validates_both_responses_before_atomic_write(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = occupation_response() if "11658" in str(request.url) else electricity_response()
        return httpx.Response(200, json=payload)

    output = tmp_path / "snapshot"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        manifest = fetch_norway_baseline_snapshot(
            output, client=client, retrieved_date="2026-09-09"
        )
    assert {path.name for path in output.iterdir()} == {
        "manifest.json",
        "table-08307-electricity.json",
        "table-11658-broad.json",
    }
    assert manifest["normalized"]["occupation_employees"]["1"] == 244602

    before = {path.name: path.read_bytes() for path in output.iterdir()}

    def invalid_handler(request: httpx.Request) -> httpx.Response:
        payload = occupation_response() if "11658" in str(request.url) else {"error": "changed"}
        return httpx.Response(200, json=payload)

    with (
        httpx.Client(transport=httpx.MockTransport(invalid_handler)) as client,
        pytest.raises(SsbContractError),
    ):
        fetch_norway_baseline_snapshot(output, client=client, retrieved_date="2026-09-09")
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


def test_repository_snapshots_replay_with_matching_checksums() -> None:
    snapshot = Path("data/sources/ssb/norway-2025-baseline")
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    occupation_bytes = (snapshot / "table-11658-broad.json").read_bytes()
    electricity_bytes = (snapshot / "table-08307-electricity.json").read_bytes()

    occupations = normalize_broad_occupations(json.loads(occupation_bytes))
    electricity = normalize_electricity(json.loads(electricity_bytes))
    assert hashlib.sha256(occupation_bytes).hexdigest() == manifest["sources"][
        "table-11658-broad.json"
    ]["sha256"]
    assert hashlib.sha256(electricity_bytes).hexdigest() == manifest["sources"][
        "table-08307-electricity.json"
    ]["sha256"]
    assert sum(cell.value for cell in occupations if cell.value is not None) == 2_839_036
    assert [cell.value for cell in electricity] == [161_793, 130_125]