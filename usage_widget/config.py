"""User-editable settings (refresh interval, tray icon style)."""

import json
from dataclasses import asdict, dataclass, fields

from usage_widget.i18n import DEFAULT_LANGUAGE
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
    language: str = DEFAULT_LANGUAGE

    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        # config.json is shared by whatever version of the app last wrote
        # it -- an older build (without a field a newer one added, e.g.
        # `language`) would otherwise crash on a file a newer build saved,
        # since dataclass.__init__ rejects unexpected keyword arguments.
        # Dropping unknown keys instead just falls back to that field's
        # default, which is the same as if it had never been saved at all.
        known_fields = {f.name for f in fields(cls)}
        data = {key: value for key, value in data.items() if key in known_fields}
        return cls(**data)

    def save(self) -> None:
        config_path().write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
