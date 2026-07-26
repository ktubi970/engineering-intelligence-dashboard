import pytest
from conftest import FakeTransport, load_fixture

from engineering_intelligence.domain import RepositoryRef
from engineering_intelligence.github_client import (
    GitHubApiError,
    GitHubClient,
    GitHubRateLimitError,
)


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


def test_client_returns_pull_request_detail(
    fake_transport: FakeTransport,
    repository: RepositoryRef,
) -> None:
    fake_transport.queue_json(200, load_fixture("pull_detail.json"))
    client = GitHubClient(transport=fake_transport, token=None)

    pull = client.get_pull_request(repository, number=101)

    assert (pull["number"], pull["changed_files"], pull["commits"]) == (101, 7, 3)


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
