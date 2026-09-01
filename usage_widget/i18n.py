"""Central translation table for tray menu/notification text and the tray
icon style labels.

The popup HTML/JS layer (assets/web/*.html) can't import this module, so it
keeps its own copy of the same keys in assets/web/i18n.js -- when adding a
new user-facing string, check whether it belongs here (Python-rendered:
tray, notifications, the usage popup's reset-time text) or there (anything
rendered inside a popup's HTML).
"""

from typing import Dict

from usage_widget.tray_icon import STYLE_LABELS as _KO_STYLE_LABELS

DEFAULT_LANGUAGE = "ko"

LANGUAGE_NAMES: Dict[str, str] = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh-CN": "中文(简体)",
}

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ko": {
        "tray.open": "열기",
        "tray.settings": "설정",
        "tray.account": "계정",
        "tray.quit": "종료",
        "tray.tooltip_base": "Claude 사용량",
        "tray.tooltip_logged_out": "로그아웃됨",
        "tray.tooltip_error": "갱신 실패, 재시도 중",
        "notify.started_msg": "트레이 아이콘으로 실행 중입니다",
        "dup.already_running_msg": "이미 실행 중입니다. 트레이 아이콘을 확인해주세요.",
        "update.applying": "업데이트 적용 중...",
        "update.checking": "업데이트 확인 중...",
        "update.new_version": "새 버전 있음 (v{version}) — {label}",
        "update.action_now": "지금 업데이트",
        "update.action_download": "다운로드",
        "update.current_version": "현재 버전: v{version}",
        "notify.update_title": "업데이트",
        "notify.update_downloading": "새 버전을 받는 중입니다...",
        "notify.update_failed_title": "잠시 후 다시 시도해주세요",
        "notify.update_failed_msg": "업데이트에 실패했습니다: {error}",
        "notify.check_title": "업데이트 확인",
        "notify.up_to_date_msg": "현재 최신 버전입니다 (v{version})",
        "notify.new_version_available_title": "새 버전이 나왔어요",
        "notify.new_version_available_msg": "Claude Usage Widget v{version} — {action}",
        "notify.new_version_action_self": "우클릭 메뉴에서 바로 적용할 수 있어요",
        "notify.new_version_action_download": "우클릭 메뉴에서 다운로드하세요",
        "reset.not_started": "아직 사용 시작 전",
        "reset.days": "리셋까지 {days}일 {hours}시간 후",
        "reset.hours": "리셋까지 {hours}시간 {minutes}분 후",
        "splash.status": "실행 중입니다...",
    },
    "en": {
        "tray.open": "Open",
        "tray.settings": "Settings",
        "tray.account": "Account",
        "tray.quit": "Quit",
        "tray.tooltip_base": "Claude Usage",
        "tray.tooltip_logged_out": "logged out",
        "tray.tooltip_error": "refresh failed, retrying",
        "notify.started_msg": "Running in the system tray",
        "dup.already_running_msg": "Already running. Check your system tray icon.",
        "update.applying": "Applying update...",
        "update.checking": "Checking for updates...",
        "update.new_version": "New version available (v{version}) — {label}",
        "update.action_now": "Update now",
        "update.action_download": "Download",
        "update.current_version": "Current version: v{version}",
        "notify.update_title": "Update",
        "notify.update_downloading": "Downloading the new version...",
        "notify.update_failed_title": "Please try again shortly",
        "notify.update_failed_msg": "Update failed: {error}",
        "notify.check_title": "Update check",
        "notify.up_to_date_msg": "You're already on the latest version (v{version})",
        "notify.new_version_available_title": "A new version is available",
        "notify.new_version_available_msg": "Claude Usage Widget v{version} — {action}",
        "notify.new_version_action_self": "Right-click the tray icon to apply it",
        "notify.new_version_action_download": "Right-click the tray icon to download it",
        "reset.not_started": "Not started yet",
        "reset.days": "Resets in {days}d {hours}h",
        "reset.hours": "Resets in {hours}h {minutes}m",
        "splash.status": "Starting...",
    },
    "ja": {
        "tray.open": "開く",
        "tray.settings": "設定",
        "tray.account": "アカウント",
        "tray.quit": "終了",
        "tray.tooltip_base": "Claude 使用量",
        "tray.tooltip_logged_out": "ログアウト済み",
        "tray.tooltip_error": "更新失敗、再試行中",
        "notify.started_msg": "トレイアイコンで実行中です",
        "dup.already_running_msg": "すでに実行中です。トレイアイコンをご確認ください。",
        "update.applying": "アップデート適用中...",
        "update.checking": "アップデートを確認中...",
        "update.new_version": "新しいバージョンがあります (v{version}) — {label}",
        "update.action_now": "今すぐアップデート",
        "update.action_download": "ダウンロード",
        "update.current_version": "現在のバージョン: v{version}",
        "notify.update_title": "アップデート",
        "notify.update_downloading": "新しいバージョンをダウンロード中です...",
        "notify.update_failed_title": "しばらくしてからもう一度お試しください",
        "notify.update_failed_msg": "アップデートに失敗しました: {error}",
        "notify.check_title": "アップデート確認",
        "notify.up_to_date_msg": "最新バージョンです (v{version})",
        "notify.new_version_available_title": "新しいバージョンが公開されました",
        "notify.new_version_available_msg": "Claude Usage Widget v{version} — {action}",
        "notify.new_version_action_self": "右クリックメニューからすぐに適用できます",
        "notify.new_version_action_download": "右クリックメニューからダウンロードしてください",
        "reset.not_started": "まだ使用開始前",
        "reset.days": "リセットまで{days}日{hours}時間",
        "reset.hours": "リセットまで{hours}時間{minutes}分",
        "splash.status": "起動しています...",
    },
    "zh-CN": {
        "tray.open": "打开",
        "tray.settings": "设置",
        "tray.account": "账户",
        "tray.quit": "退出",
        "tray.tooltip_base": "Claude 用量",
        "tray.tooltip_logged_out": "已注销",
        "tray.tooltip_error": "刷新失败，正在重试",
        "notify.started_msg": "正在托盘中运行",
        "dup.already_running_msg": "已经在运行中，请查看系统托盘图标。",
        "update.applying": "正在应用更新...",
        "update.checking": "正在检查更新...",
        "update.new_version": "有新版本 (v{version}) — {label}",
        "update.action_now": "立即更新",
        "update.action_download": "下载",
        "update.current_version": "当前版本：v{version}",
        "notify.update_title": "更新",
        "notify.update_downloading": "正在下载新版本...",
        "notify.update_failed_title": "请稍后重试",
        "notify.update_failed_msg": "更新失败：{error}",
        "notify.check_title": "检查更新",
        "notify.up_to_date_msg": "当前已是最新版本 (v{version})",
        "notify.new_version_available_title": "发现新版本",
        "notify.new_version_available_msg": "Claude Usage Widget v{version} — {action}",
        "notify.new_version_action_self": "右键菜单即可立即应用",
        "notify.new_version_action_download": "请通过右键菜单下载",
        "reset.not_started": "尚未开始使用",
        "reset.days": "距重置还有{days}天{hours}小时",
        "reset.hours": "距重置还有{hours}小时{minutes}分钟",
        "splash.status": "正在启动...",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    table = _TRANSLATIONS.get(lang, _TRANSLATIONS[DEFAULT_LANGUAGE])
    template = table.get(key) or _TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    return template.format(**kwargs) if kwargs else template


_STYLE_LABELS: Dict[str, Dict[str, str]] = {
    "ko": _KO_STYLE_LABELS,
    "en": {
        "donut": "Donut gauge",
        "battery": "Battery",
        "bar": "Bar",
        "big_number": "Number",
        "liquid": "Liquid fill",
    },
    "ja": {
        "donut": "ドーナツゲージ",
        "battery": "バッテリー",
        "bar": "バー",
        "big_number": "数字",
        "liquid": "円形フィル",
    },
    "zh-CN": {
        "donut": "环形量表",
        "battery": "电池",
        "bar": "条形",
        "big_number": "数字",
        "liquid": "圆形填充",
    },
}


def tray_style_labels(lang: str) -> Dict[str, str]:
    return _STYLE_LABELS.get(lang, _STYLE_LABELS[DEFAULT_LANGUAGE])
