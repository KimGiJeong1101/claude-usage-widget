"""User-editable settings (refresh interval, tray icon style)."""

import json
from dataclasses import asdict, dataclass

from usage_widget.paths import config_path
from usage_widget.tray_icon import DEFAULT_STYLE as DEFAULT_TRAY_ICON_STYLE

DEFAULT_REFRESH_SECONDS = 60
DEFAULT_USAGE_POPUP_OPACITY = 100


@dataclass
class Config:
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS
    tray_icon_style: str = DEFAULT_TRAY_ICON_STYLE
    # Percent (40-100) -- only the usage popup's card backgrounds fade with
    # this; settings/account aren't looked at often enough to bother (see
    # claude-usage-widget-plan.md 13.12).
    usage_popup_opacity: int = DEFAULT_USAGE_POPUP_OPACITY

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
