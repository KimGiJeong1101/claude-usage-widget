// 사용량/설정/계정 팝업들과 시작 스플래시 화면이 공유하는 번역 테이블.
// 트레이 아이콘/알림 문구는 Python 쪽(usage_widget/i18n.py)에 별도로 똑같은
// 내용을 한 벌 더 갖고 있다 -- 이 JS 파일을 Python에서 그대로 가져다 쓸(import)
// 수는 없기 때문이다. 그래서 사용자에게 보이는 새 문구를 추가할 때마다
// 두 곳의 키를 손으로 맞춰서 동기화해줘야 한다.
const I18N_TRANSLATIONS = {
  ko: {
    "usage.title": "Claude 사용량",
    "usage.opacity_tooltip": "투명도",
    "usage.pin_tooltip": "고정",
    "usage.refresh_tooltip": "새로고침",
    "reset.not_started": "아직 사용 시작 전",
    "reset.days": "리셋까지 {days}일 {hours}시간 후",
    "reset.hours": "리셋까지 {hours}시간 {minutes}분 후",
    "common.close_tooltip": "닫기",
    "common.resize_tooltip": "크기 조절",
    "settings.title": "설정",
    "settings.refresh_interval_label": "자동갱신 주기",
    "settings.seconds_unit": "초",
    "settings.refresh_interval_hint": "예: 900초 = 15분",
    "settings.tray_style_label": "트레이 아이콘",
    "settings.autostart_label": "PC 시작 시 자동 실행",
    "settings.language_label": "언어",
    "settings.section_display": "화면",
    "settings.section_behavior": "동작",
    "settings.autosave_hint": "변경 사항은 바로 저장됩니다",
    "settings.theme_label": "테마",
    "settings.theme_system": "시스템 설정",
    "settings.theme_light": "라이트",
    "settings.theme_dark": "다크",
    "usage.updated": "마지막 갱신: {when}",
    "usage.updated_failed": "갱신 실패 · 마지막 성공: {when}",
    "time.just_now": "방금 전",
    "time.minutes_ago": "{minutes}분 전",
    "time.hours_ago": "{hours}시간 전",
    "account.title": "계정",
    "account.status_logged_in_label": "현재 로그인",
    "account.status_logged_out_label": "현재 상태",
    "account.checking": "확인 중...",
    "account.logged_out_value": "로그아웃됨",
    "account.switch_button": "계정 변경",
    "account.login_button": "로그인",
    "account.logout_button": "로그아웃",
    "splash.status": "실행 중입니다...",
  },
  en: {
    "usage.title": "Claude Usage",
    "usage.opacity_tooltip": "Opacity",
    "usage.pin_tooltip": "Pin",
    "usage.refresh_tooltip": "Refresh",
    "reset.not_started": "Not started yet",
    "reset.days": "Resets in {days}d {hours}h",
    "reset.hours": "Resets in {hours}h {minutes}m",
    "common.close_tooltip": "Close",
    "common.resize_tooltip": "Resize",
    "settings.title": "Settings",
    "settings.refresh_interval_label": "Refresh interval",
    "settings.seconds_unit": "sec",
    "settings.refresh_interval_hint": "e.g. 900 sec = 15 min",
    "settings.tray_style_label": "Tray icon",
    "settings.autostart_label": "Run automatically at startup",
    "settings.language_label": "Language",
    "settings.section_display": "DISPLAY",
    "settings.section_behavior": "BEHAVIOR",
    "settings.autosave_hint": "Changes are saved automatically",
    "settings.theme_label": "Theme",
    "settings.theme_system": "System",
    "settings.theme_light": "Light",
    "settings.theme_dark": "Dark",
    "usage.updated": "Last updated: {when}",
    "usage.updated_failed": "Refresh failed · last success: {when}",
    "time.just_now": "just now",
    "time.minutes_ago": "{minutes} min ago",
    "time.hours_ago": "{hours} h ago",
    "account.title": "Account",
    "account.status_logged_in_label": "Currently signed in",
    "account.status_logged_out_label": "Current status",
    "account.checking": "Checking...",
    "account.logged_out_value": "Logged out",
    "account.switch_button": "Switch account",
    "account.login_button": "Log in",
    "account.logout_button": "Log out",
    "splash.status": "Starting...",
  },
  ja: {
    "usage.title": "Claude 使用量",
    "usage.opacity_tooltip": "透明度",
    "usage.pin_tooltip": "固定",
    "usage.refresh_tooltip": "更新",
    "reset.not_started": "まだ使用開始前",
    "reset.days": "リセットまで{days}日{hours}時間",
    "reset.hours": "リセットまで{hours}時間{minutes}分",
    "common.close_tooltip": "閉じる",
    "common.resize_tooltip": "サイズ変更",
    "settings.title": "設定",
    "settings.refresh_interval_label": "自動更新間隔",
    "settings.seconds_unit": "秒",
    "settings.refresh_interval_hint": "例：900秒＝15分",
    "settings.tray_style_label": "トレイアイコン",
    "settings.autostart_label": "PC起動時に自動実行",
    "settings.language_label": "言語",
    "settings.section_display": "表示",
    "settings.section_behavior": "動作",
    "settings.autosave_hint": "変更はすぐに保存されます",
    "settings.theme_label": "テーマ",
    "settings.theme_system": "システム設定",
    "settings.theme_light": "ライト",
    "settings.theme_dark": "ダーク",
    "usage.updated": "最終更新: {when}",
    "usage.updated_failed": "更新失敗 · 最終成功: {when}",
    "time.just_now": "たった今",
    "time.minutes_ago": "{minutes}分前",
    "time.hours_ago": "{hours}時間前",
    "account.title": "アカウント",
    "account.status_logged_in_label": "現在ログイン中",
    "account.status_logged_out_label": "現在の状態",
    "account.checking": "確認中...",
    "account.logged_out_value": "ログアウト済み",
    "account.switch_button": "アカウント変更",
    "account.login_button": "ログイン",
    "account.logout_button": "ログアウト",
    "splash.status": "起動しています...",
  },
  "zh-CN": {
    "usage.title": "Claude 用量",
    "usage.opacity_tooltip": "透明度",
    "usage.pin_tooltip": "固定",
    "usage.refresh_tooltip": "刷新",
    "reset.not_started": "尚未开始使用",
    "reset.days": "距重置还有{days}天{hours}小时",
    "reset.hours": "距重置还有{hours}小时{minutes}分钟",
    "common.close_tooltip": "关闭",
    "common.resize_tooltip": "调整大小",
    "settings.title": "设置",
    "settings.refresh_interval_label": "自动刷新间隔",
    "settings.seconds_unit": "秒",
    "settings.refresh_interval_hint": "例如：900秒 = 15分钟",
    "settings.tray_style_label": "托盘图标",
    "settings.autostart_label": "开机自动启动",
    "settings.language_label": "语言",
    "settings.section_display": "显示",
    "settings.section_behavior": "行为",
    "settings.autosave_hint": "更改会立即保存",
    "settings.theme_label": "主题",
    "settings.theme_system": "跟随系统",
    "settings.theme_light": "浅色",
    "settings.theme_dark": "深色",
    "usage.updated": "上次更新：{when}",
    "usage.updated_failed": "刷新失败 · 上次成功：{when}",
    "time.just_now": "刚刚",
    "time.minutes_ago": "{minutes}分钟前",
    "time.hours_ago": "{hours}小时前",
    "account.title": "账户",
    "account.status_logged_in_label": "当前登录",
    "account.status_logged_out_label": "当前状态",
    "account.checking": "正在确认...",
    "account.logged_out_value": "已注销",
    "account.switch_button": "切换账户",
    "account.login_button": "登录",
    "account.logout_button": "注销",
    "splash.status": "正在启动...",
  },
};

function i18nText(lang, key) {
  const table = I18N_TRANSLATIONS[lang] || I18N_TRANSLATIONS.ko;
  return table[key] ?? I18N_TRANSLATIONS.ko[key] ?? key;
}

// i18n.py의 t(key, lang, **kwargs)처럼 "{days}" 같은 자리 표시자를 채운다.
function i18nFormat(lang, key, vars) {
  return i18nText(lang, key).replace(/\{(\w+)\}/g, (m, name) => (name in vars ? vars[name] : m));
}

// 리셋 시각을 "11월 16일 (일) 오전 1:00"처럼 그 언어 습관에 맞는 형식으로
// 보여줄 때 쓰는 로케일 -- 날짜/시간 형식은 브라우저(WebView2)의 Intl이
// 언어별로 알아서 맞춰준다.
const I18N_DATE_LOCALES = { ko: "ko-KR", en: "en-US", ja: "ja-JP", "zh-CN": "zh-CN" };

// 트레이 아이콘 스타일 이름(도넛 게이지/배터리/...)은 설정 팝업이 열릴 때
// Python 쪽(usage_widget/i18n.py의 tray_style_labels())에서 초기 데이터로
// 내려주는데, 이때 이미 팝업을 연 시점에 켜져 있던 언어로 번역이 끝난
// 상태로 온다. 저장하고 팝업을 다시 열면 이 방식으로도 문제없이 새 언어로
// 보이지만, 언어 드롭다운을 바꿀 때 그 자리에서 바로 미리보기를 보여주는
// 기능(settings.html 참고)은 서버(Python)를 다시 호출해서 새로 받아오는
// 과정이 없다 -- 그래서 이 파일 안에 똑같은 내용을 한 벌 더 따로 갖고 있어야
// 하고, 이 파일의 다른 부분들과 마찬가지로 Python 쪽과 손으로 맞춰서
// 동기화해줘야 한다.
const I18N_TRAY_STYLE_LABELS = {
  ko: { donut: "도넛 게이지", battery: "배터리", bar: "막대", big_number: "숫자", dual_bar: "이중 막대" },
  en: { donut: "Donut gauge", battery: "Battery", bar: "Bar", big_number: "Number", dual_bar: "Dual bars" },
  ja: { donut: "ドーナツゲージ", battery: "バッテリー", bar: "バー", big_number: "数字", dual_bar: "二本バー" },
  "zh-CN": { donut: "环形量表", battery: "电池", bar: "条形", big_number: "数字", dual_bar: "双条形" },
};

function trayStyleLabel(lang, key) {
  const table = I18N_TRAY_STYLE_LABELS[lang] || I18N_TRAY_STYLE_LABELS.ko;
  return table[key] ?? I18N_TRAY_STYLE_LABELS.ko[key] ?? key;
}

// data-i18n(-title) 속성이 붙은 모든 요소의 텍스트/툴팁을 `lang` 언어로
// 바꿔치기한다. 저장된 언어 정보를 담은 초기 데이터가 Python으로부터
// 도착한 딱 그 시점에 한 번 호출된다 -- HTML에 하드코딩되어 있는 한국어
// 텍스트는, 이 데이터를 받아오는 왕복 호출(round-trip)이 끝나기 전
// 아주 짧은 순간 동안만 보여주는 "JS 실행 전 임시 대체 화면"일 뿐이다.
function applyI18n(lang) {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = i18nText(lang, el.getAttribute("data-i18n"));
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = i18nText(lang, el.getAttribute("data-i18n-title"));
  });
}
