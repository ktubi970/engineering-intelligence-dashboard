from dataclasses import dataclass


class DataContractError(ValueError):
    """Raised when external or stored data violates the project contract."""


@dataclass(frozen=True, slots=True)
class RepositoryRef:
    owner: str
    name: str

    @classmethod
    def parse(cls, value: str) -> "RepositoryRef":
        parts = value.strip().split("/")
        if len(parts) != 2 or not all(parts):
            raise DataContractError("Repository must use the owner/repository form.")
        return cls(owner=parts[0], name=parts[1])

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"
