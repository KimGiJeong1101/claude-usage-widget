"""User-editable settings (currently just the refresh interval)."""

import json
from dataclasses import asdict, dataclass

from usage_widget.paths import config_path

DEFAULT_REFRESH_SECONDS = 60


@dataclass
class Config:
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS

    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self) -> None:
        config_path().write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
