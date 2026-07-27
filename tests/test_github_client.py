import socket
from collections.abc import Callable

import pytest
from conftest import FakeTransport, load_fixture

from engineering_intelligence.domain import RepositoryRef
from engineering_intelligence.github_client import (
    GitHubApiError,
    GitHubClient,
    GitHubRateLimitError,
)


def _workflow_run(run_id: int, *, status: str = "completed") -> dict[str, object]:
    return {
        "id": run_id,
        "name": "Tests",
        "status": status,
        "conclusion": "success" if status == "completed" else None,
        "created_at": "2026-01-02T11:00:00Z",
        "updated_at": "2026-01-02T11:12:00Z",
        "run_started_at": "2026-01-02T11:01:00Z",
        "html_url": f"https://github.com/example/project/actions/runs/{run_id}",
        "head_sha": "1" * 40,
    }


def test_client_returns_only_merged_pull_requests(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, load_fixture("pulls_page.json"))
    client = GitHubClient(transport=fake_transport, token=None)

    pulls = client.list_merged_pull_requests(repository, limit=2)

    assert [pull["number"] for pull in pulls] == [101, 99]


def test_client_uses_pinned_github_request_contract(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, load_fixture("pulls_page.json"))
    client = GitHubClient(transport=fake_transport, token="sanitized-token")

    client.list_merged_pull_requests(repository, limit=1)

    request = fake_transport.requests[0]
    assert request.url == "https://api.github.com/repos/example/project/pulls"
    assert request.headers == {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MergeLens/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": "Bearer sanitized-token",
    }
    assert request.params == {"state": "closed", "per_page": 100, "page": 1}
    assert request.timeout == 15.0


def test_client_omits_authorization_without_token(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, load_fixture("pulls_page.json"))
    client = GitHubClient(transport=fake_transport, token=None)

    client.list_merged_pull_requests(repository, limit=1)

    assert "Authorization" not in fake_transport.requests[0].headers


def test_client_translates_non_exhausted_403_to_api_error(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(403, {"message": "Forbidden"})
    client = GitHubClient(transport=fake_transport, token=None)

    with pytest.raises(GitHubApiError) as raised:
        client.list_merged_pull_requests(repository, limit=1)

    assert type(raised.value) is GitHubApiError


def test_client_translates_rate_limit_response(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(
        403,
        {"message": "API rate limit exceeded"},
        headers={"x-ratelimit-remaining": "0"},
    )
    client = GitHubClient(transport=fake_transport, token=None)

    with pytest.raises(GitHubRateLimitError, match="rate limit"):
        client.list_merged_pull_requests(repository, limit=1)


def test_client_paginates_until_it_collects_requested_merged_pulls(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    first_page = [pull for pull in load_fixture("pulls_page.json") if pull["number"] == 100]
    fake_transport.queue_json(200, first_page)
    fake_transport.queue_json(200, load_fixture("pulls_page.json"))
    client = GitHubClient(transport=fake_transport, token=None)

    pulls = client.list_merged_pull_requests(repository, limit=2)

    assert [pull["number"] for pull in pulls] == [101, 99]


def test_client_stops_pagination_when_github_returns_empty_page(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, [])
    client = GitHubClient(transport=fake_transport, token=None)

    pulls = client.list_merged_pull_requests(repository, limit=1)

    assert pulls == []


def test_client_returns_pull_request_detail(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, load_fixture("pull_detail.json"))
    client = GitHubClient(transport=fake_transport, token=None)

    pull = client.get_pull_request(repository, number=101)

    assert (pull["number"], pull["changed_files"], pull["commits"]) == (101, 7, 3)


def test_client_returns_public_repository_visibility(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(
        200,
        {"id": 42, "full_name": "example/project", "private": False},
    )
    client = GitHubClient(transport=fake_transport, token=None)

    metadata = client.get_repository(repository)

    assert metadata["private"] is False
    assert fake_transport.requests[0].url == "https://api.github.com/repos/example/project"
    assert fake_transport.requests[0].params == {}


def test_client_returns_workflow_runs(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, load_fixture("workflow_runs.json"))
    client = GitHubClient(transport=fake_transport, token=None)

    runs = client.list_workflow_runs(repository, limit=1)

    assert [(run["id"], run["conclusion"]) for run in runs] == [(9001, "success")]


def test_client_translates_malformed_json_to_api_error(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, ValueError("invalid JSON"))
    client = GitHubClient(transport=fake_transport, token=None)

    with pytest.raises(GitHubApiError, match="malformed JSON"):
        client.list_merged_pull_requests(repository, limit=1)


def test_client_translates_server_error_to_api_error(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(500, {"message": "Internal Server Error"})
    client = GitHubClient(transport=fake_transport, token=None)

    with pytest.raises(GitHubApiError, match="GitHub API request failed"):
        client.list_merged_pull_requests(repository, limit=1)


def test_client_translates_429_rate_limit_response(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(
        429,
        {"message": "API rate limit exceeded"},
        headers={"x-ratelimit-remaining": "0"},
    )
    client = GitHubClient(transport=fake_transport, token=None)

    with pytest.raises(GitHubRateLimitError, match="rate limit"):
        client.list_merged_pull_requests(repository, limit=1)


def test_client_paginates_workflow_runs_beyond_github_page_cap_and_truncates(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    first_page = [_workflow_run(run_id) for run_id in range(200, 100, -1)]
    second_page = [_workflow_run(100), _workflow_run(99)]
    fake_transport.queue_json(200, {"total_count": 102, "workflow_runs": first_page})
    fake_transport.queue_json(200, {"total_count": 102, "workflow_runs": second_page})
    client = GitHubClient(transport=fake_transport, token=None)

    runs = client.list_workflow_runs(repository, limit=101)

    assert len(runs) == 101
    assert [run["id"] for run in runs[:2]] == [200, 199]
    assert runs[-1]["id"] == 100
    assert [request.params for request in fake_transport.requests] == [
        {"per_page": 100, "page": 1},
        {"per_page": 100, "page": 2},
    ]


def test_client_fetches_empty_workflow_page_after_partial_completed_page(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    first_page = [
        _workflow_run(3),
        _workflow_run(2, status="in_progress"),
        _workflow_run(1),
    ]
    fake_transport.queue_json(200, {"total_count": 3, "workflow_runs": first_page})
    fake_transport.queue_json(200, {"total_count": 3, "workflow_runs": []})
    client = GitHubClient(transport=fake_transport, token=None)

    runs = client.list_workflow_runs(repository, limit=3)

    assert [run["id"] for run in runs] == [3, 1]
    assert [request.params["page"] for request in fake_transport.requests] == [1, 2]


def test_client_stops_workflow_pagination_on_short_final_page(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    short_page = [_workflow_run(2), _workflow_run(1)]
    fake_transport.queue_json(200, {"total_count": 2, "workflow_runs": short_page})
    client = GitHubClient(transport=fake_transport, token=None)

    runs = client.list_workflow_runs(repository, limit=4)

    assert [run["id"] for run in runs] == [2, 1]
    assert len(fake_transport.requests) == 1
    assert fake_transport.requests[0].params == {"per_page": 4, "page": 1}


def test_client_continues_workflow_pagination_past_non_completed_runs(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    first_page = [
        _workflow_run(4, status="queued"),
        _workflow_run(3, status="in_progress"),
    ]
    second_page = [_workflow_run(2), _workflow_run(1)]
    fake_transport.queue_json(200, {"total_count": 4, "workflow_runs": first_page})
    fake_transport.queue_json(200, {"total_count": 4, "workflow_runs": second_page})
    client = GitHubClient(transport=fake_transport, token=None)

    runs = client.list_workflow_runs(repository, limit=2)

    assert [run["id"] for run in runs] == [2, 1]
    assert [request.params for request in fake_transport.requests] == [
        {"per_page": 2, "page": 1},
        {"per_page": 2, "page": 2},
    ]


def test_suite_network_guard_blocks_stdlib_connection_entry_points(
    block_outbound_network: tuple[Callable[..., None], Callable[..., None]],
) -> None:
    reject_socket_connection, reject_create_connection = block_outbound_network
    assert socket.socket.connect is reject_socket_connection
    assert socket.socket.connect_ex is reject_socket_connection
    assert socket.create_connection is reject_create_connection

    address = ("example.invalid", 443)
    attempts = (
        lambda: socket.socket.connect(object(), address),
        lambda: socket.socket.connect_ex(object(), address),
        lambda: socket.create_connection(address),
    )
    for attempt in attempts:
        with pytest.raises(AssertionError, match="Outbound network is disabled during tests"):
            attempt()
