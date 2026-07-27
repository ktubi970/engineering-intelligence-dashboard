from __future__ import annotations

import re
from pathlib import Path

from engineering_intelligence.model import train_merge_time_model
from engineering_intelligence.pipeline import load_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _artifact_path(relative_path: str) -> Path:
    path = PROJECT_ROOT / relative_path
    assert path.is_file(), f"Missing required project artifact: {relative_path}"
    return path


def _artifact(relative_path: str) -> str:
    return _artifact_path(relative_path).read_text(encoding="utf-8")


def test_ci_runs_the_binding_quality_gate_on_master_and_pull_requests() -> None:
    workflow = _artifact(".github/workflows/ci.yml")

    assert re.search(r"(?m)^  push:\s*\n    branches: \[master\]\s*$", workflow)
    assert re.search(r"(?m)^  pull_request:\s*$", workflow)
    assert "actions/checkout@v4" in workflow
    assert "actions/setup-python@v5" in workflow
    assert 'python-version: "3.13"' in workflow
    assert "cache: pip" in workflow
    assert "python -m pip install -r requirements-dev.txt" in workflow
    for command in (
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m pytest --cov=engineering_intelligence "
        "--cov-report=term-missing --cov-fail-under=85",
    ):
        assert re.search(rf"(?m)^\s+run: {re.escape(command)}\s*$", workflow)


def test_recruiter_readme_and_supporting_documents_publish_the_core_contract() -> None:
    pulls, workflows, _ = load_snapshot(PROJECT_ROOT / "data" / "snapshots")

    readme = _artifact("README.md")
    for anchor in (
        "# MergeLens",
        "engineering-intelligence-dashboard",
        "## 30-second value",
        "## Features",
        "## Metric definitions",
        "## Architecture",
        "## Installation",
        "## Offline demo",
        "## Optional data refresh",
        "## Tests",
        "## Model results",
        "## Limitations",
        "## Privacy",
        "## License",
        "streamlit run streamlit_app.py",
        "python scripts/refresh_data.py",
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m pytest --cov=engineering_intelligence "
        "--cov-report=term-missing --cov-fail-under=85",
    ):
        assert anchor in readme

    document_anchors = {
        "docs/architecture.md": ("GitHub public REST API", "pandas", "Streamlit", "failure"),
        "docs/data-card.md": (
            str(len(pulls)),
            str(len(workflows)),
            "privacy",
            "## Limitations",
        ),
        "docs/model-card.md": (
            "opening-time",
            "chronological",
            "RandomForestRegressor",
            "non-causal",
        ),
        "docs/quality-evidence.md": ("Local evidence", "GitHub Actions"),
        "docs/agentic-development.md": ("Task 1", "Task 8", "Option 1", "RED", "GREEN"),
        "LICENSE": ("MIT License", "MergeLens contributors"),
    }
    for relative_path, anchors in document_anchors.items():
        document = _artifact(relative_path)
        for anchor in anchors:
            assert anchor in document


def test_agent_guardrails_allow_scoped_work_and_prohibit_unsafe_claims() -> None:
    agents = _artifact("AGENTS.md").lower()

    for permission in ("scoped code", "tests", "documentation", "local verification"):
        assert permission in agents
    for prohibition in (
        "secret access",
        "secret output",
        "unsupported production claims",
        "network calls in tests",
        "silent model-metric changes",
        "author or developer scoring",
        "destructive git commands",
        "deployment without an explicit in-scope request",
        "evidence before completion",
    ):
        assert prohibition in agents


def test_published_portfolio_claims_match_verified_snapshot_and_evaluation() -> None:
    pulls, workflows, _ = load_snapshot(PROJECT_ROOT / "data" / "snapshots")
    result = train_merge_time_model(pulls)
    model_mae = f"{result.mae_hours:.12f}"
    baseline_mae = f"{result.baseline_mae_hours:.12f}"
    difference = f"{abs(result.mae_hours - result.baseline_mae_hours):.12f}"

    if result.mae_hours < result.baseline_mae_hours:
        winner = "model"
        result_sentence = "The model outperforms the baseline on this snapshot."
        model_card_difference = f"model is {difference} hours better"
    elif result.baseline_mae_hours < result.mae_hours:
        winner = "baseline"
        result_sentence = "The model underperforms the baseline on this snapshot."
        model_card_difference = f"model is {difference} hours worse"
    else:
        winner = "tie"
        result_sentence = "The model matches the baseline on this snapshot."
        model_card_difference = "model and baseline are equal"

    honest_result = "tie" if winner == "tie" else f"{winner} wins"

    readme = _artifact("README.md")
    for claim in (
        f"{len(pulls)} merged pull requests and {len(workflows)} completed workflow runs",
        f"model and the newest 20% ({result.test_rows} rows) is held out for evaluation.",
        f"- Random-forest MAE: **{model_mae} hours**",
        f"- Training-median baseline MAE: **{baseline_mae} hours**",
        f"- Winner: **{winner}**, by **{difference} hours**",
        result_sentence,
    ):
        assert claim in readme

    model_card = _artifact("docs/model-card.md")
    training_rows = len(pulls) - result.test_rows
    for claim in (
        f"With {len(pulls)} committed rows, that produces {training_rows} training rows and "
        f"{result.test_rows}\ntest rows.",
        f"| Test rows | {result.test_rows} |",
        f"| Random-forest MAE | {model_mae} hours |",
        f"| Train-median baseline MAE | {baseline_mae} hours |",
        f"| Difference | {model_card_difference} |",
        f"| Honest result | {honest_result} |",
        result_sentence.replace("this snapshot", "the committed snapshot"),
    ):
        assert claim in model_card


def test_publication_artifacts_are_real_and_match_verified_remote_evidence() -> None:
    screenshot = _artifact_path("docs/images/dashboard.png").read_bytes()
    assert screenshot.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(screenshot) > 50_000

    readme = _artifact("README.md")
    assert "![MergeLens dashboard overview](docs/images/dashboard.png)" in readme

    pull_request_body = _artifact(".github/pull_request_body.md")
    for anchor in (
        "## Verified summary",
        r".venv\Scripts\python.exe -m ruff check .",
        r".venv\Scripts\python.exe -m ruff format --check .",
        r".venv\Scripts\python.exe -m pytest --cov=engineering_intelligence "
        "--cov-report=term-missing --cov-fail-under=85",
        "300 merged pull requests and 199 completed workflow runs",
        "GitHub public REST API",
        "The model underperforms the baseline on this snapshot.",
        "![MergeLens dashboard overview](https://github.com/ktubi970/engineering-intelligence-dashboard/blob/codex/engineering-intelligence-dashboard/docs/images/dashboard.png?raw=true)",
        "## Limitations",
    ):
        assert anchor in pull_request_body

    quality_evidence = _artifact("docs/quality-evidence.md")
    live_url = "https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/"
    ci_url = (
        "https://github.com/ktubi970/engineering-intelligence-dashboard/"
        "actions/runs/30259194189/job/89954838617"
    )
    for document in (readme, quality_evidence, pull_request_body):
        assert live_url in document
        assert ci_url in document
        assert "f987033" in document
        assert "passed in 57s" in document
        lowered = document.lower()
        assert "phase a" not in lowered
        assert "pending" not in lowered

    assert "https://github.com/ktubi970/engineering-intelligence-dashboard/pull/1" in (
        quality_evidence
    )
    for remote_observation in (
        "MergeLens \u00b7 Streamlit",
        "`Delivery pulse`, `Bottlenecks`, and `Forecast & trust`",
        "account/API 403/404",
    ):
        assert remote_observation in quality_evidence


def test_committed_snapshot_covers_the_six_default_repositories() -> None:
    expected_repositories = [
        "pandas-dev/pandas",
        "streamlit/streamlit",
        "microsoft/vscode",
        "tensorflow/tensorflow",
        "rust-lang/rust",
        "ruby/ruby",
    ]

    pulls, workflows, metadata = load_snapshot(PROJECT_ROOT / "data" / "snapshots")

    assert metadata["repositories"] == expected_repositories
    assert set(pulls["repository"]) == set(expected_repositories)
    assert set(workflows["repository"]).issubset(expected_repositories)
    assert len(pulls) == 150 * len(expected_repositories)
