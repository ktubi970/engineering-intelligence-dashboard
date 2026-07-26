import argparse
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from engineering_intelligence.domain import DataContractError, RepositoryRef
from engineering_intelligence.github_client import GitHubClient
from engineering_intelligence.pipeline import GitHubDataSource, refresh_snapshot

DEFAULT_REPOSITORIES = (
    RepositoryRef.parse("pandas-dev/pandas"),
    RepositoryRef.parse("streamlit/streamlit"),
)
DEFAULT_OUTPUT_DIR = Path("data/snapshots")


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _repository_ref(value: str) -> RepositoryRef:
    try:
        return RepositoryRef.parse(value)
    except DataContractError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh privacy-minimized public GitHub snapshot data.",
    )
    parser.add_argument(
        "--repo",
        action="append",
        dest="repositories",
        type=_repository_ref,
        help="Public GitHub repository in owner/repository form; repeat as needed.",
    )
    parser.add_argument(
        "--limit-per-repo",
        type=_positive_integer,
        default=150,
        help="Maximum pull requests and workflow runs fetched per repository.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for pull_requests.csv, workflow_runs.csv, and metadata.json.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[..., GitHubDataSource] = GitHubClient,
) -> int:
    args = _parser().parse_args(argv)
    repositories = args.repositories or list(DEFAULT_REPOSITORIES)
    process_environment = os.environ if environ is None else environ
    client = client_factory(token=process_environment.get("GITHUB_TOKEN"))
    metadata = refresh_snapshot(
        client,
        repositories,
        args.output_dir,
        pr_limit=args.limit_per_repo,
    )
    print(
        f"Refreshed {metadata.pull_request_rows} pull requests and "
        f"{metadata.workflow_run_rows} workflow runs across "
        f"{len(repositories)} repositories into {args.output_dir}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
