from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import FakeGitHubClient

from engineering_intelligence.pipeline import GitHubDataSource, load_snapshot
from scripts.refresh_data import main


def _client_factory(
    client: FakeGitHubClient,
    captured_tokens: list[str | None],
) -> Callable[..., GitHubDataSource]:
    def factory(*, token: str | None) -> GitHubDataSource:
        captured_tokens.append(token)
        return client

    return factory


def test_cli_uses_default_repositories_environment_token_and_sanitized_output(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_tokens: list[str | None] = []
    secret = "never-print-this-token"

    exit_code = main(
        [
            "--output-dir",
            str(tmp_path),
            "--limit-per-repo",
            "1",
        ],
        environ={"GITHUB_TOKEN": secret},
        client_factory=_client_factory(fake_github_client, captured_tokens),
    )

    pulls, workflows, metadata = load_snapshot(tmp_path)
    output = capsys.readouterr()
    assert exit_code == 0
    assert captured_tokens == [secret]
    assert metadata["repositories"] == [
        "pandas-dev/pandas",
        "streamlit/streamlit",
    ]
    assert len(pulls) == 2
    assert len(workflows) == 2
    assert output.out == (
        f"Refreshed 2 pull requests and 2 workflow runs across 2 repositories into {tmp_path}.\n"
    )
    assert secret not in output.out + output.err
    assert "Authorization" not in output.out + output.err


def test_cli_accepts_repeated_repositories_and_limit(
    tmp_path: Path,
    fake_github_client: FakeGitHubClient,
) -> None:
    captured_tokens: list[str | None] = []

    main(
        [
            "--repo",
            "apache/arrow",
            "--repo",
            "psf/requests",
            "--limit-per-repo",
            "2",
            "--output-dir",
            str(tmp_path),
        ],
        environ={},
        client_factory=_client_factory(fake_github_client, captured_tokens),
    )

    pulls, workflows, metadata = load_snapshot(tmp_path)
    assert captured_tokens == [None]
    assert metadata["repositories"] == ["apache/arrow", "psf/requests"]
    assert len(pulls) == 4
    assert len(workflows) == 4


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_cli_rejects_non_positive_limits_before_creating_client(
    limit: str,
) -> None:
    def forbidden_factory(*, token: str | None) -> GitHubDataSource:
        raise AssertionError(f"Client must not be created with token {token!r}")

    with pytest.raises(SystemExit, match="2"):
        main(
            ["--limit-per-repo", limit],
            environ={"GITHUB_TOKEN": "unused-secret"},
            client_factory=forbidden_factory,
        )
