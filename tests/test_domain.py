import pytest

from engineering_intelligence.domain import DataContractError, RepositoryRef


def test_repository_ref_parses_owner_and_name() -> None:
    ref = RepositoryRef.parse("pandas-dev/pandas")
    assert (ref.owner, ref.name, ref.slug) == (
        "pandas-dev",
        "pandas",
        "pandas-dev/pandas",
    )


@pytest.mark.parametrize("value", ["", "pandas", "/pandas", "pandas/", "a/b/c"])
def test_repository_ref_rejects_invalid_slugs(value: str) -> None:
    with pytest.raises(DataContractError, match="owner/repository"):
        RepositoryRef.parse(value)
