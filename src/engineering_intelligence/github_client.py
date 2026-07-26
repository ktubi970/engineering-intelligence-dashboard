from collections.abc import Mapping
from typing import Protocol, cast

import requests

from engineering_intelligence.domain import RepositoryRef


class HttpResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]

    def json(self) -> object: ...


class HttpTransport(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object],
        timeout: float,
    ) -> HttpResponse: ...


class RequestsTransport:
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object],
        timeout: float,
    ) -> requests.Response:
        return requests.get(url, headers=headers, params=params, timeout=timeout)


class GitHubApiError(RuntimeError):
    """Raised when GitHub responds with an API error."""


class GitHubRateLimitError(GitHubApiError):
    """Raised when GitHub rejects a request because its rate limit is exhausted."""


class GitHubClient:
    _API_ROOT = "https://api.github.com"
    _TIMEOUT_SECONDS = 15.0

    def __init__(self, transport: HttpTransport | None = None, token: str | None = None) -> None:
        self._transport = transport or RequestsTransport()
        self._token = token

    def get_repository(self, repository: RepositoryRef) -> dict[str, object]:
        return cast(
            dict[str, object],
            self._get_json(f"/repos/{repository.slug}", {}),
        )

    def list_merged_pull_requests(
        self, repository: RepositoryRef, limit: int
    ) -> list[dict[str, object]]:
        merged: list[dict[str, object]] = []
        page = 1
        while len(merged) < limit:
            records = cast(
                list[dict[str, object]],
                self._get_json(
                    f"/repos/{repository.slug}/pulls",
                    {"state": "closed", "per_page": 100, "page": page},
                ),
            )
            if not records:
                break
            merged.extend(record for record in records if record.get("merged_at") is not None)
            page += 1
        return merged[:limit]

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "MergeLens/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def get_pull_request(self, repository: RepositoryRef, number: int) -> dict[str, object]:
        return cast(
            dict[str, object],
            self._get_json(f"/repos/{repository.slug}/pulls/{number}", {}),
        )

    def list_workflow_runs(self, repository: RepositoryRef, limit: int) -> list[dict[str, object]]:
        payload = cast(
            dict[str, object],
            self._get_json(
                f"/repos/{repository.slug}/actions/runs",
                {"per_page": limit, "page": 1},
            ),
        )
        return cast(list[dict[str, object]], payload["workflow_runs"])[:limit]

    def _get_json(self, path: str, params: Mapping[str, object]) -> object:
        response = self._transport.get(
            f"{self._API_ROOT}{path}",
            headers=self._headers(),
            params=params,
            timeout=self._TIMEOUT_SECONDS,
        )
        is_rate_limited = response.status_code in {403, 429} and (
            response.headers.get("x-ratelimit-remaining") == "0"
        )
        if is_rate_limited:
            raise GitHubRateLimitError("GitHub API rate limit exceeded")
        if not 200 <= response.status_code < 300:
            raise GitHubApiError(f"GitHub API request failed with status {response.status_code}")
        try:
            return response.json()
        except ValueError as error:
            raise GitHubApiError("GitHub returned malformed JSON") from error
