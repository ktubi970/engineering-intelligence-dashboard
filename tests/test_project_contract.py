from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

from engineering_intelligence.model import train_merge_time_model
from engineering_intelligence.pipeline import load_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_COMMIT = "a051ffe5198506a79f9be66112320cac47d0de3f"
EVIDENCE_CI_URL = (
    "https://github.com/ktubi970/engineering-intelligence-dashboard/actions/runs/30346530403"
)
EVIDENCE_TEST_RESULT = "173 passed"
EVIDENCE_COVERAGE = "94.68%"
PUBLIC_DEPLOYMENT_URL = (
    "https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/"
)
PREMERGE_COMMIT = "abaebd6115685e049dcad37599709a67f9ec2647"
PREMERGE_PYTHON = "Python 3.13.9"
PREMERGE_FORMAT_RESULT = "33 files already formatted"
APPLICATION_TREE_SHA = "b6f9ae229650ad21bfafac5b9696e8e25374015d"
PUBLICATION_MANIFEST_PATH = "docs/evidence/final-publication.json"
DASHBOARD_SCREENSHOT_SHA256 = "c7a72236d3f6535607634edc6cb57d6a13fc5752235892c720d8ac5b67338c96"
SNAPSHOT_METADATA_SHA256 = "0fe555b2a381433548d5e1a4b1860c403dec74521361d1410d7cd2a029d28826"
PR_VERIFIED_SUMMARY_SHA256 = "8bf6dda33500797dabf0ec58bd1466e905e76ec5546634775578ae98ea8cf45e"
PR_LOCAL_GATE_SHA256 = "6e0d1a63fe1f5b4f2a195d2e8865ffa57d9ce3386e1fd7ff3eaeb9777f81dc74"
QUALITY_FINAL_LOCAL_GATE_SHA256 = "73025085e6131187d3de0afa2f19b66bb85c8cc66a0b70632fde512dded39c8a"
QUALITY_FINAL_CI_SHA256 = "97476d42317d8e4f93976fca66d73b1510c66f664f6b3c6630c1f7c9e112d7bb"
INTEGRATION_COMMIT = "b9e4db677d6d29d0354061d9b86fdc8033a490a9"
INTEGRATION_SCREENSHOT_BYTES = 91_844
INTEGRATION_SCREENSHOT_CAPTION = "restoring all six repositories"
INTEGRATION_SCREENSHOT_URL = (
    "https://github.com/ktubi970/engineering-intelligence-dashboard/blob/"
    f"{INTEGRATION_COMMIT}/docs/images/dashboard.png?raw=true"
)


def _artifact_path(relative_path: str) -> Path:
    path = PROJECT_ROOT / relative_path
    assert path.is_file(), f"Missing required project artifact: {relative_path}"
    return path


def _artifact(relative_path: str) -> str:
    return _artifact_path(relative_path).read_text(encoding="utf-8")


def _markdown_section(document: str, heading: str) -> str:
    marker = f"{heading}\n"
    start = document.index(marker) + len(marker)
    level = len(heading) - len(heading.lstrip("#"))
    next_heading = re.search(rf"(?m)^#{{1,{level}}} ", document[start:])
    end = len(document) if next_heading is None else start + next_heading.start()
    return document[start:end].strip()


def _normalized(document: str) -> str:
    return " ".join(document.split())


def _assert_evidence_section(
    section: str,
    expected_digest: str,
    required_claims: tuple[str, ...],
) -> None:
    normalized = _normalized(section)
    actual_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    assert actual_digest == expected_digest
    for required_claim in required_claims:
        assert required_claim in normalized


def _assert_final_public_browser_evidence(section: str) -> None:
    expected = _normalized(
        f"""
        Machine-readable source:
        [`docs/evidence/final-publication.json`](evidence/final-publication.json).

        On 2026-07-28, a fresh anonymous browser session opened
        https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/
        without sign-in and verified:

        - 900 merged pull requests and all six repositories: `microsoft/vscode`,
          `pandas-dev/pandas`, `ruby/ruby`, `rust-lang/rust`, `streamlit/streamlit`,
          and `tensorflow/tensorflow`;
        - the exact tabs `Overview`, `Drivers & retrospective patterns`,
          `Forecast & trust`, and `Technical stack`;
        - an interactive forecast whose default input returned a visible 1.5-hour
          random-forest estimate alongside the 9.5-hour train-median estimate;
        - the visible model evaluation of 9.7 hours MAE versus 12.5 hours for the
          baseline;
        - no application traceback; and
        - no horizontal overflow at the tested 1280-pixel desktop and 390-pixel
          narrow viewports.

        The browser console's five errors were anonymous-platform requests to
        `/api/v2/user/details` returning HTTP 404. They were not application
        exceptions and did not prevent any tested interaction.

        Streamlit's public metadata showed that the deployment was configured to
        `codex/engineering-intelligence-dashboard`; GitHub showed that branch at
        `{PREMERGE_COMMIT}`. The visible four-tab, 900-row state matched that
        application tree, which was merged into `master` as `{EVIDENCE_COMMIT}`.
        This point-in-time verification is not an uptime guarantee.
        """
    )
    assert _normalized(section) == expected


def _sha256(relative_path: str) -> str:
    return hashlib.sha256(_artifact_path(relative_path).read_bytes()).hexdigest()


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
    pulls, workflows, _ = load_snapshot(PROJECT_ROOT / "data" / "snapshots")

    readme = _artifact("README.md")
    for anchor in (
        "# MergeLens",
        "engineering-intelligence-dashboard",
        "## See it in action",
        "## What you can explore",
        "## Run it locally",
        "## Prediction model",
        "## How it works",
        "## Trust and limits",
        "## Project details",
        "## License",
        "streamlit run streamlit_app.py",
        "python scripts/refresh_data.py",
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m pytest --cov=engineering_intelligence "
        "--cov-report=term-missing --cov-fail-under=85",
    ):
        assert anchor in readme

    assert len(readme.split()) < 1_000
    for removed_heading in (
        "## Agentic engineering with Codex, Sol, and Ultra reasoning",
        "## Metric definitions",
        "## Architecture",
        "## Installation",
        "## Offline demo",
        "## Optional data refresh",
        "## Tests",
        "## Model results",
        "## Limitations",
        "## Privacy",
    ):
        assert removed_heading not in readme

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


def test_readme_defines_the_prediction_mathematically() -> None:
    readme = _artifact("README.md")

    for mathematical_anchor in (
        r"Y_i =",
        r"\mathrm{merged\_at}_i-\mathrm{created\_at}_i",
        r"X_i =",
        r"\mathrm{year}(t_i)",
        r"\mathrm{weekday}(t_i)",
        r"\widehat{Y}_i = f(X_i)",
        r"\phi(X_i)",
        r"\sum_{b=1}^{200}T_b",
        r"\operatorname{MAE}",
        r"\left|Y_i-\widehat{Y}_i\right|",
    ):
        assert mathematical_anchor in readme

    for model_contract in (
        "pull requests that eventually merge",
        "No developer identity",
        "200-tree random forest",
        "maximum depth 8",
        "at least 3 training samples per leaf",
        "newest 20%",
        "median merge time from the training set",
    ):
        assert model_contract in readme


def test_published_portfolio_claims_match_verified_snapshot_and_evaluation() -> None:
    pulls, workflows, _ = load_snapshot(PROJECT_ROOT / "data" / "snapshots")
    result = train_merge_time_model(pulls)
    assert result.mae_hours == pytest.approx(9.73, abs=0.02)
    assert result.baseline_mae_hours == pytest.approx(12.484162037037, abs=1e-12)
    assert result.mae_hours < result.baseline_mae_hours

    model_mae_display = f"{result.mae_hours:.1f}"
    baseline_mae_display = f"{result.baseline_mae_hours:.1f}"
    relative_reduction_display = (
        f"{100 * (result.baseline_mae_hours - result.mae_hours) / result.baseline_mae_hours:.0f}%"
    )
    assert (model_mae_display, baseline_mae_display, relative_reduction_display) == (
        "9.7",
        "12.5",
        "22%",
    )

    readme = _artifact("README.md")
    for claim in (
        "900 merged pull requests and 560 completed workflow runs",
        "The newest 20% (180 rows) is the chronological test set.",
        "622",
        "180",
        "98",
        "2026-07-24T08:38:56+00:00",
        f"{model_mae_display} hours",
        f"{baseline_mae_display} hours",
        f"about {relative_reduction_display} lower average error",
        "estimates the number of hours",
        "pull requests that eventually merge",
    ):
        assert claim in readme

    model_card = _artifact("docs/model-card.md")
    training_rows = result.train_rows
    for claim in (
        "With 900 committed rows, that produces 720 earlier candidates and 180 chronological "
        "test rows.",
        "98 unavailable labels are purged, leaving 622 training rows.",
        "| As-of cutoff | 2026-07-24T08:38:56+00:00 |",
        "| Training rows | 622 |",
        "| Test rows | 180 |",
        "| Purged unavailable labels | 98 |",
        f"| Random-forest MAE | {model_mae_display} hours (rounded) |",
        f"| Train-median baseline MAE | {baseline_mae_display} hours (rounded) |",
        f"| Relative MAE reduction | about {relative_reduction_display} |",
        "| Honest result | random forest wins |",
        "The random forest has lower MAE on this fixed committed-snapshot holdout.",
        "estimated merge time among pull requests that eventually merge",
        f"With {len(pulls)} committed rows, that produces {len(pulls) - result.test_rows} earlier "
        f"candidates and {result.test_rows} chronological test rows.",
        f"| Test rows | {result.test_rows} |",
        f"| As-of cutoff | {result.cutoff.isoformat()} |",
        f"| Training rows | {training_rows} |",
        f"| Purged unavailable labels | {result.purged_rows} |",
        f"| Training-median estimate | {result.baseline_hours:.12f} hours |",
    ):
        assert claim in model_card

    pull_request_body = _artifact(".github/pull_request_body.md")
    for claim in (
        f"- Random-forest MAE: {model_mae_display} hours (rounded)",
        f"- Training-median baseline MAE: {baseline_mae_display} hours (rounded)",
        f"- Winner: random forest, with about {relative_reduction_display} lower MAE",
    ):
        assert claim in pull_request_body

    for document in (model_card, pull_request_body):
        assert "rounded to one decimal" in document
        assert "execution environments" in document
        assert "does not isolate a single causal factor" in document

    for document in (readme, model_card, pull_request_body):
        assert "9.734692264131" not in document
        assert "2.749469772906" not in document

    quality_evidence = _artifact("docs/quality-evidence.md")
    for exact_environment_evidence in (
        "Windows 3.13.9: `9.734692264131` hours",
        "Linux 3.13.14: `9.725297316958` hours",
        "The train-median baseline remained `12.484162037037` hours",
        "30342316589/job/90220463967",
    ):
        assert exact_environment_evidence in quality_evidence


def test_publication_artifacts_are_real_and_match_verified_remote_evidence() -> None:
    manifest = json.loads(_artifact(PUBLICATION_MANIFEST_PATH))
    snapshot_metadata = _artifact_path("data/snapshots/metadata.json").read_bytes()
    assert b"\r" not in snapshot_metadata
    assert hashlib.sha256(snapshot_metadata).hexdigest() == SNAPSHOT_METADATA_SHA256

    assert set(manifest) == {
        "schema_version",
        "recorded_date",
        "source_provenance",
        "local_gate",
        "github_actions",
        "public_deployment",
        "artifacts",
    }
    assert manifest["schema_version"] == 1
    assert manifest["recorded_date"] == "2026-07-28"

    source_provenance = manifest["source_provenance"]
    assert source_provenance == {
        "deployment_branch": "codex/engineering-intelligence-dashboard",
        "premerge_commit": PREMERGE_COMMIT,
        "premerge_tree": APPLICATION_TREE_SHA,
        "master_merge_commit": EVIDENCE_COMMIT,
        "master_merge_tree": APPLICATION_TREE_SHA,
        "identical_application_tree": True,
    }

    local_gate_manifest = manifest["local_gate"]
    assert local_gate_manifest == {
        "commit": PREMERGE_COMMIT,
        "platform": "Windows",
        "python": "3.13.9",
        "ruff_lint": "passed",
        "formatted_files": 33,
        "tests_passed": 173,
        "coverage_percent": 94.68,
        "diff_check": "passed",
    }

    ci_manifest = manifest["github_actions"]
    assert ci_manifest == {
        "run_id": 30346530403,
        "job_id": 90233932955,
        "url": EVIDENCE_CI_URL,
        "commit": EVIDENCE_COMMIT,
        "conclusion": "success",
        "platform": "Ubuntu 24.04",
        "python": "3.13.14",
        "ruff_lint": "passed",
        "formatted_files": 33,
        "tests_passed": 173,
        "coverage_percent": 94.68,
    }

    deployment_manifest = manifest["public_deployment"]
    assert deployment_manifest == {
        "url": ("https://engineering-intelligence-dashboard-jq9xccatzgwy9y9hcrwmor.streamlit.app/"),
        "anonymous_access": True,
        "merged_pull_requests": 900,
        "repositories": [
            "microsoft/vscode",
            "pandas-dev/pandas",
            "ruby/ruby",
            "rust-lang/rust",
            "streamlit/streamlit",
            "tensorflow/tensorflow",
        ],
        "tabs": [
            "Overview",
            "Drivers & retrospective patterns",
            "Forecast & trust",
            "Technical stack",
        ],
        "model_mae_hours": 9.7,
        "baseline_mae_hours": 12.5,
        "default_model_estimate_hours": 1.5,
        "default_baseline_estimate_hours": 9.5,
        "application_traceback": False,
        "desktop_viewport_width": 1280,
        "desktop_horizontal_overflow": False,
        "narrow_viewport_width": 390,
        "narrow_horizontal_overflow": False,
        "platform_console_errors": 5,
        "platform_error_endpoint": "/api/v2/user/details",
        "platform_error_status": 404,
    }

    assert _sha256("docs/images/dashboard.png") == DASHBOARD_SCREENSHOT_SHA256
    artifacts = manifest["artifacts"]
    assert artifacts == {
        "local_dashboard_png": {
            "path": "docs/images/dashboard.png",
            "scope": "local",
            "sha256": DASHBOARD_SCREENSHOT_SHA256,
            "bytes": INTEGRATION_SCREENSHOT_BYTES,
            "width": 1440,
            "height": 1000,
        },
        "snapshot_metadata": {
            "path": "data/snapshots/metadata.json",
            "sha256": SNAPSHOT_METADATA_SHA256,
        },
    }

    screenshot_path = _artifact_path("docs/images/dashboard.png")
    _assert_dashboard_screenshot_contract(screenshot_path)
    assert screenshot_path.stat().st_size == INTEGRATION_SCREENSHOT_BYTES

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
        "900 merged pull requests and 560 completed workflow runs",
        "GitHub public REST API",
        "The random forest has lower MAE than the baseline on this fixed snapshot.",
        "estimated merge time among pull requests that eventually merge",
        f"![MergeLens dashboard overview]({INTEGRATION_SCREENSHOT_URL})",
        INTEGRATION_SCREENSHOT_CAPTION,
        f"PNG, {INTEGRATION_SCREENSHOT_BYTES:,} bytes",
        "## Limitations",
    ):
        assert anchor in pull_request_body

    quality_evidence = _artifact("docs/quality-evidence.md")
    normalized_quality_evidence = _normalized(quality_evidence)
    for historical_marker in (
        ("At that Task 8 revision, the integrated, time-safe evaluation used 223 training rows"),
        "for the then-current Task 9 branch.",
        "include the then-current contract",
    ):
        assert historical_marker in normalized_quality_evidence
    for stale_historical_present_tense in (
        "evaluation uses 223 training rows",
        "for the current branch.",
        "include the current contract",
    ):
        assert stale_historical_present_tense not in normalized_quality_evidence

    readme_live_demo = _markdown_section(readme, "## See it in action")
    pull_request_summary = _markdown_section(
        pull_request_body,
        "## Verified summary",
    )
    pull_request_local_gate = _markdown_section(
        pull_request_body,
        "## Local quality commands",
    )
    final_local_gate = _markdown_section(
        quality_evidence,
        "## Final pre-merge local quality gate",
    )
    final_ci = _markdown_section(
        quality_evidence,
        "## Final merged-master GitHub Actions evidence",
    )
    final_public = _markdown_section(
        quality_evidence,
        "## Final public deployment verification",
    )

    public_summary_claims = (
        PUBLICATION_MANIFEST_PATH,
        PUBLIC_DEPLOYMENT_URL,
        "2026-07-28",
        "fresh anonymous browser session",
        "900 merged pull requests",
        "six repositories",
        "Overview",
        "Drivers & retrospective patterns",
        "Forecast & trust",
        "Technical stack",
        "interactive forecast",
        "9.7 hours",
        "12.5 hours",
        "no application traceback",
        "horizontal overflow",
        EVIDENCE_CI_URL,
        EVIDENCE_COMMIT,
        EVIDENCE_TEST_RESULT,
        EVIDENCE_COVERAGE,
    )
    local_gate_claims = (
        PREMERGE_COMMIT,
        PREMERGE_PYTHON,
        PREMERGE_FORMAT_RESULT,
        EVIDENCE_TEST_RESULT,
        EVIDENCE_COVERAGE,
        "git diff --check",
    )
    ci_claims = (
        EVIDENCE_CI_URL,
        EVIDENCE_COMMIT,
        EVIDENCE_TEST_RESULT,
        EVIDENCE_COVERAGE,
        "Python 3.13.14",
        PREMERGE_FORMAT_RESULT,
    )
    evidence_section_contracts = (
        (
            pull_request_summary,
            PR_VERIFIED_SUMMARY_SHA256,
            public_summary_claims,
        ),
        (pull_request_local_gate, PR_LOCAL_GATE_SHA256, local_gate_claims),
        (
            final_local_gate,
            QUALITY_FINAL_LOCAL_GATE_SHA256,
            local_gate_claims,
        ),
        (final_ci, QUALITY_FINAL_CI_SHA256, ci_claims),
    )
    for evidence_section, expected_digest, required_claims in evidence_section_contracts:
        _assert_evidence_section(
            evidence_section,
            expected_digest,
            required_claims,
        )

    normalized_readme_live_demo = _normalized(readme_live_demo)
    for claim in (
        PUBLIC_DEPLOYMENT_URL,
        "July 28, 2026",
        "without sign-in",
        "all six repositories",
        "point-in-time check",
        PUBLICATION_MANIFEST_PATH,
        "docs/quality-evidence.md",
    ):
        assert claim in normalized_readme_live_demo

    for internal_evidence_detail in (
        EVIDENCE_COMMIT,
        EVIDENCE_TEST_RESULT,
        EVIDENCE_COVERAGE,
        "Technical stack",
    ):
        assert internal_evidence_detail not in normalized_readme_live_demo

    _assert_final_public_browser_evidence(final_public)
    assert PUBLIC_DEPLOYMENT_URL in final_public

    for mutation in (
        "The following claims are false.\n\n" + final_public,
        (final_public + "\n\nContrary to the above, an application traceback occurred."),
        (
            final_public + "\n\nContrary to the above, the application tree was not merged "
            "into `master`."
        ),
        final_public.replace(
            "a fresh anonymous browser session",
            "no fresh anonymous browser session",
            1,
        ),
        final_public.replace(
            "no horizontal overflow",
            "cannot confirm no horizontal overflow",
            1,
        ),
        final_public.replace(
            "which was merged into `master` as",
            "which was not merged into `master` as",
            1,
        ),
        final_public.replace("1280-pixel", "1200-pixel", 1),
        final_public.replace("390-pixel", "430-pixel", 1),
        final_public.replace("five errors", "four errors", 1),
        final_public.replace(PREMERGE_COMMIT, "0" * 40, 1),
        final_public.replace(EVIDENCE_COMMIT, "f" * 40, 1),
        final_public.replace(
            "no application traceback",
            "an application traceback",
            1,
        ),
    ):
        assert mutation != final_public
        with pytest.raises(AssertionError):
            _assert_final_public_browser_evidence(mutation)

    for evidence_section, expected_digest, required_claims in evidence_section_contracts:
        for mutation in (
            "The following claims are false.\n\n" + evidence_section,
            evidence_section + "\n\nContrary to the above, these checks did not pass.",
            evidence_section.replace(
                EVIDENCE_TEST_RESULT,
                "173 checks did not pass",
                1,
            ),
        ):
            with pytest.raises(AssertionError):
                _assert_evidence_section(
                    mutation,
                    expected_digest,
                    required_claims,
                )

    for current_publication_document in (readme, pull_request_body):
        lowered = current_publication_document.lower()
        assert "phase a" not in lowered
        assert "pending" not in lowered
        for superseded_current_claim in (
            "currently auth-gated",
            "not yet a recruiter-accessible public showcase",
            "owner must make it public",
            "reboots it in streamlit community cloud",
            "82e86b2fedc2526f6fc1eff6ce27941efbe0a00b",
            "170 passed",
            "172 passed",
            "94.54%",
        ):
            assert superseded_current_claim not in lowered

    stale_claims = (
        "30259194189",
        "89954838617",
        "f987033",
        "passed in 57s",
        "91 passed",
        "96 tests",
    )
    for document in (readme, quality_evidence, pull_request_body):
        for stale_claim in stale_claims:
            assert stale_claim not in document

    tracked_markdown_paths = (
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / ".github" / "pull_request_body.md",
        *sorted((PROJECT_ROOT / "docs").rglob("*.md")),
    )
    for markdown_path in tracked_markdown_paths:
        assert stale_claims[2] not in markdown_path.read_text(encoding="utf-8"), (
            f"Superseded evidence SHA remains in {markdown_path.relative_to(PROJECT_ROOT)}"
        )

    assert "https://github.com/ktubi970/engineering-intelligence-dashboard/pull/1" in (
        quality_evidence
    )
    for remote_observation in (
        "HTTP 303",
        "share.streamlit.io/-/auth/app",
        "auth-gated",
        "superseded",
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


def test_readme_names_the_current_product_views() -> None:
    readme = _artifact("README.md")

    for view_name in (
        "Delivery overview",
        "Where work slows down",
        "Merge-time estimate",
    ):
        assert view_name in readme

    for old_view_name in (
        "Drivers & retrospective patterns",
        "Forecast & trust",
        "Technical stack",
    ):
        assert old_view_name not in readme


def test_pr_body_pins_screenshot_to_an_immutable_commit_url() -> None:
    pull_request_body = _artifact(".github/pull_request_body.md")
    expected_url = INTEGRATION_SCREENSHOT_URL
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


def test_readme_links_to_deeper_engineering_records_without_repeating_them() -> None:
    readme = _artifact("README.md")

    for link in (
        "[Architecture](docs/architecture.md)",
        "[Data card](docs/data-card.md)",
        "[Model card](docs/model-card.md)",
        "[Quality evidence](docs/quality-evidence.md)",
        "[Agentic development](docs/agentic-development.md)",
        "[Repository guardrails](AGENTS.md)",
    ):
        assert link in readme

    assert "Codex + Sol + Ultra" not in readme
    assert "read-only independent review agents" not in readme
    assert "1 failed, 7 passed" not in readme


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
