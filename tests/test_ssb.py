import hashlib
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from datacenter_need.sources.ssb import (
    SsbContractError,
    fetch_employee_snapshot,
    normalize_employee_cell,
)

SNAPSHOT_DIR = Path("data/sources/ssb/11658-2512-2025K4")


def employee_response() -> dict:
    dimensions = {
        "Kjonn": {
            "label": "sex",
            "category": {"index": {"0": 0}, "label": {"0": "Both sexes"}},
        },
        "Alder": {
            "label": "age",
            "category": {"index": {"999D": 0}, "label": {"999D": "All ages"}},
        },
        "Yrke": {
            "label": "occupation",
            "category": {"index": {"2512": 0}, "label": {"2512": "Software developers"}},
            "link": {
                "describedby": [
                    {
                        "extension": {
                            "Yrke": "urn:ssb:classification:klass:7 "
                            "urn:ssb:conceptvariable:vardok:1118"
                        }
                    }
                ]
            },
        },
        "ContentsCode": {
            "label": "contents",
            "category": {
                "index": {"Lonsstakere": 0},
                "label": {"Lonsstakere": "Number of employees"},
                "unit": {"Lonsstakere": {"base": "persons", "decimals": 0}},
            },
            "extension": {
                "refperiod": {"Lonsstakere": "Mid-month of the quarter"},
                "measuringType": {"Lonsstakere": "Stock"},
            },
        },
        "Tid": {
            "label": "quarter",
            "category": {"index": {"2025K4": 0}, "label": {"2025K4": "2025K4"}},
        },
    }
    return {
        "version": "2.0",
        "class": "dataset",
        "label": "11658: Employees, jobs, and earnings, by sex, age, occupation and quarter",
        "source": "Statistics Norway",
        "updated": "2026-08-13T06:00:00Z",
        "id": ["Kjonn", "Alder", "Yrke", "ContentsCode", "Tid"],
        "size": [1, 1, 1, 1, 1],
        "dimension": dimensions,
        "extension": {"px": {"tableid": "11658", "official-statistics": True}},
        "value": [8224],
    }


def test_normalizes_pinned_employee_cell() -> None:
    normalized = normalize_employee_cell(employee_response())
    assert normalized.value == 8224
    assert normalized.occupation_code == "2512"
    assert normalized.occupation_label == "Software developers"
    assert normalized.period == "2025K4"
    assert normalized.unit == "persons"
    assert normalized.reference_period == "Mid-month of the quarter"
    assert normalized.measurement_type == "Stock"
    assert normalized.classification_id == "7"


def test_preserves_suppressed_cell_as_missing() -> None:
    response = employee_response()
    response["value"] = [None]
    response["status"] = {"0": "confidential"}
    normalized = normalize_employee_cell(response)
    assert normalized.value is None
    assert normalized.missing_reason == "SSB cell status: confidential"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda response: response.update(size=[1, 1, 2, 1, 1]),
        lambda response: response["dimension"]["Yrke"]["category"]["index"].update({"2511": 1}),
        lambda response: response["dimension"]["ContentsCode"]["category"]["unit"][
            "Lonsstakere"
        ].update(base="employees"),
        lambda response: response.update(value=[8224, 1]),
    ],
)
def test_rejects_changed_response_contract(mutation) -> None:
    response = deepcopy(employee_response())
    mutation(response)
    with pytest.raises(SsbContractError):
        normalize_employee_cell(response)


def test_rejects_invalid_response_shape() -> None:
    with pytest.raises(SsbContractError):
        normalize_employee_cell({"error": "upstream failure"})


def test_fetch_writes_validated_snapshot_and_manifest(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["valueCodes[Yrke]"] == "2512"
        return httpx.Response(200, json=employee_response())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        manifest = fetch_employee_snapshot(tmp_path, client=client, retrieved_date="2026-09-09")

    assert json.loads((tmp_path / "table-11658-cell.json").read_text())["value"] == [8224]
    assert manifest["normalized_value"] == 8224
    assert manifest["retrieved_date"] == "2026-09-09"
    assert len(manifest["sha256"]) == 64


def test_invalid_refresh_preserves_last_good_snapshot(tmp_path: Path) -> None:
    existing = b'{"last_good":true}\n'
    (tmp_path / "table-11658-cell.json").write_bytes(existing)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "changed response"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(SsbContractError),
    ):
        fetch_employee_snapshot(tmp_path, client=client, retrieved_date="2026-09-09")

    assert (tmp_path / "table-11658-cell.json").read_bytes() == existing


def test_repository_snapshot_replays_with_matching_checksum() -> None:
    snapshot = (SNAPSHOT_DIR / "table-11658-cell.json").read_bytes()
    manifest = json.loads((SNAPSHOT_DIR / "manifest.json").read_text())
    normalized = normalize_employee_cell(json.loads(snapshot))

    assert hashlib.sha256(snapshot).hexdigest() == manifest["sha256"]
    assert normalized.value == manifest["normalized_value"] == 8224