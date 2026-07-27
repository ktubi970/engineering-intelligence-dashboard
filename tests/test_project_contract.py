from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _artifact_path(relative_path: str) -> Path:
    path = PROJECT_ROOT / relative_path
    assert path.is_file(), f"Missing required project artifact: {relative_path}"
    return path


def _artifact(relative_path: str) -> str:
    return _artifact_path(relative_path).read_text(encoding="utf-8")


def _assert_dashboard_screenshot_contract(screenshot_path: Path) -> None:
    screenshot = screenshot_path.read_bytes()
    assert screenshot.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(screenshot) > 50_000
    with Image.open(screenshot_path) as image:
        assert image.format == "PNG", f"Expected PNG, got {image.format}"
        image.verify()
    with Image.open(screenshot_path) as image:
        assert image.format == "PNG", f"Expected PNG, got {image.format}"
        assert image.size == (1_440, 1_000), (
            f"Expected dashboard screenshot size 1440x1000, got {image.size}"
        )


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
        "docs/data-card.md": ("300", "199", "privacy", "## Limitations"),
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
    readme = _artifact("README.md")
    for claim in (
        "300 merged pull requests and 199 completed workflow runs",
        "model and the newest 20% (60 rows) is held out for evaluation.",
        "- Random-forest MAE: **26.624744394610 hours**",
        "- Training-median baseline MAE: **21.071861111111 hours**",
        "- Winner: **baseline**, by **5.552883283499 hours**",
        "The model underperforms the baseline on this snapshot.",
    ):
        assert claim in readme

    model_card = _artifact("docs/model-card.md")
    for claim in (
        "With 300 committed rows, that produces 240 training rows and 60\ntest rows.",
        "| Test rows | 60 |",
        "| Random-forest MAE | 26.624744394610 hours |",
        "| Train-median baseline MAE | 21.071861111111 hours |",
        "| Difference | model is 5.552883283499 hours worse |",
        "| Honest result | baseline wins |",
        "The model underperforms the baseline on the committed snapshot.",
    ):
        assert claim in model_card


def test_publication_artifacts_are_real_and_match_verified_remote_evidence() -> None:
    screenshot_path = _artifact_path("docs/images/dashboard.png")
    _assert_dashboard_screenshot_contract(screenshot_path)

    requirements_dev = _artifact("requirements-dev.txt").splitlines()
    assert "pillow==12.3.0" in requirements_dev

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
        "![MergeLens dashboard overview](https://github.com/ktubi970/engineering-intelligence-dashboard/blob/ce303f2a4b5d81e98a478ec542542698e0f991b1/docs/images/dashboard.png?raw=true)",
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


def test_publication_screenshot_contract_rejects_corrupt_png(tmp_path: Path) -> None:
    corrupt_screenshot = tmp_path / "corrupt-dashboard.png"
    corrupt_screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + (b"\x00" * 60_000))

    with pytest.raises(UnidentifiedImageError):
        _assert_dashboard_screenshot_contract(corrupt_screenshot)


def test_publication_screenshot_contract_rejects_wrong_dimensions(
    tmp_path: Path,
) -> None:
    source_screenshot = _artifact_path("docs/images/dashboard.png")
    wrong_size_screenshot = tmp_path / "wrong-size-dashboard.png"
    with Image.open(source_screenshot) as source_image:
        source_image.crop((0, 0, 1_440, 999)).save(
            wrong_size_screenshot,
            format="PNG",
        )
    assert wrong_size_screenshot.stat().st_size > 50_000

    with pytest.raises(AssertionError, match="1440x1000"):
        _assert_dashboard_screenshot_contract(wrong_size_screenshot)


def test_readme_uses_exact_current_public_tab_names() -> None:
    readme = _artifact("README.md")

    for tab_name in (
        "Overview",
        "Drivers & retrospective patterns",
        "Forecast & trust",
    ):
        assert tab_name in readme


def test_pr_body_pins_screenshot_to_an_immutable_commit_url() -> None:
    pull_request_body = _artifact(".github/pull_request_body.md")
    expected_url = (
        "https://github.com/ktubi970/engineering-intelligence-dashboard/blob/"
        "ce303f2a4b5d81e98a478ec542542698e0f991b1/docs/images/dashboard.png?raw=true"
    )
    match = re.search(r"!\[MergeLens dashboard overview\]\(([^)]+)\)", pull_request_body)
    assert match is not None
    screenshot_url = match.group(1)

    assert screenshot_url == expected_url
    assert re.fullmatch(
        r"https://github\.com/ktubi970/engineering-intelligence-dashboard/blob/"
        r"[0-9a-f]{40}/docs/images/dashboard\.png\?raw=true",
        screenshot_url,
    )
    assert "codex/engineering-intelligence-dashboard" not in screenshot_url


def test_readme_explains_the_codex_sol_ultra_engineering_workflow() -> None:
    readme = _artifact("README.md")
    heading = "## Agentic engineering with Codex, Sol, and Ultra reasoning"

    assert heading in readme
    start = readme.index(heading)
    next_heading = readme.find("\n## ", start + len(heading))
    section = readme[start:] if next_heading == -1 else readme[start:next_heading]
    lowered = section.lower()

    for anchor in (
        "Codex + Sol + Ultra",
        "coordinator",
        "task decomposition",
        "scoped implementation agents",
        "RED",
        "GREEN",
        "read-only independent review agents",
        "Git worktrees",
        "commit boundaries",
        "pytest",
        "Ruff",
        "coverage",
        "GitHub Actions",
        "Playwright",
        "human approval",
        "`tests/test_project_contract.py`",
        "`.github/workflows/ci.yml`",
        "1 failed, 7 passed",
        "2 failed, 8 deselected",
        "2 passed, 8 deselected",
        "[Agentic development](docs/agentic-development.md)",
        "[AGENTS.md](AGENTS.md)",
    ):
        assert anchor in section

    for failure_or_guardrail in (
        "hallucinated changes",
        "weak tests",
        "drift between local, ci, and live",
        "no secret output",
        "no developer scoring",
        "evidence, not ai claims",
        "does not claim that every historical change or subagent",
    ):
        assert failure_or_guardrail in lowered
