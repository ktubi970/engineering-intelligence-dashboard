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


class FakeGitHubClient:
    def __init__(self) -> None:
        first = load_fixture("pull_detail.json")
        assert isinstance(first, dict)
        self.pull_details: dict[int, dict[str, object]] = {
            101: first,
            99: {
                **first,
                "number": 99,
                "title": "Ship fixtures safely",
                "body": "No identity persists.",
                "user": {
                    "login": "second-private-login",
                    "email": "second-private@example.invalid",
                    "avatar_url": "https://example.invalid/second-avatar",
                },
                "created_at": "2025-12-29T10:00:00Z",
                "merged_at": "2025-12-31T10:00:00Z",
                "author_association": "MEMBER",
                "head": {"sha": "second-private-head-sha"},
                "additions": 30,
                "deletions": 10,
                "changed_files": 4,
                "commits": 2,
            },
        }
        workflow_payload = load_fixture("workflow_runs.json")
        assert isinstance(workflow_payload, dict)
        workflow_runs = workflow_payload["workflow_runs"]
        assert isinstance(workflow_runs, list)
        self.workflow_runs = workflow_runs

    def list_merged_pull_requests(
        self,
        repository: RepositoryRef,
        limit: int,
    ) -> list[dict[str, object]]:
        del repository
        return [{"number": number} for number in (101, 99)][:limit]

    def get_pull_request(
        self,
        repository: RepositoryRef,
        number: int,
    ) -> dict[str, object]:
        del repository
        return self.pull_details[number]

    def list_workflow_runs(
        self,
        repository: RepositoryRef,
        limit: int,
    ) -> list[dict[str, object]]:
        del repository
        return self.workflow_runs[:limit]


@pytest.fixture
def fake_github_client() -> FakeGitHubClient:
    return FakeGitHubClient()


@pytest.fixture
def raw_pull_details() -> list[dict[str, object]]:
    return [
        {
            "number": 101,
            "title": "Merge metrics fast",
            "body": "A public summary.",
            "user": {
                "login": "private-login",
                "email": "private@example.invalid",
                "avatar_url": "https://example.invalid/avatar",
            },
            "created_at": "2026-01-01T10:00:00Z",
            "merged_at": "2026-01-03T10:00:00Z",
            "labels": [{"name": "enhancement"}],
            "author_association": "CONTRIBUTOR",
            "head": {"sha": "private-head-sha"},
            "additions": 120,
            "deletions": 20,
            "changed_files": 7,
            "commits": 3,
        }
    ]


@pytest.fixture
def raw_workflow_runs() -> list[dict[str, object]]:
    payload = load_fixture("workflow_runs.json")
    assert isinstance(payload, dict)
    runs = payload["workflow_runs"]
    assert isinstance(runs, list)
    return runs
