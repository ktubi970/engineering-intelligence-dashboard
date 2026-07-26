import json
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from engineering_intelligence.domain import RepositoryRef


@dataclass
class FakeResponse:
    status_code: int
    payload: object
    headers: Mapping[str, str]

    def json(self) -> object:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


@dataclass(frozen=True)
class RecordedRequest:
    url: str
    headers: Mapping[str, str]
    params: Mapping[str, object]
    timeout: float


class FakeTransport:
    def __init__(self) -> None:
        self._responses: deque[FakeResponse] = deque()

        self.requests: list[RecordedRequest] = []

    def queue_json(
        self,
        status_code: int,
        payload: object,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self._responses.append(FakeResponse(status_code, payload, headers or {}))

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object],
        timeout: float,
    ) -> FakeResponse:
        self.requests.append(RecordedRequest(url, headers, params, timeout))
        if not self._responses:
            raise AssertionError("No fake GitHub response was queued.")
        return self._responses.popleft()


def load_fixture(name: str) -> object:
    path = Path(__file__).parent / "fixtures" / "github" / name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def fake_transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def repository() -> RepositoryRef:
    return RepositoryRef.parse("example/project")
