"""프로그램의 진입점(entry point, 프로그램이 시작될 때 제일 먼저 실행되는
부분). 트레이 아이콘을 계속 띄워두고, 백그라운드에서 주기적으로 사용량을
갱신하고, 클릭하면 상세 정보/설정 팝업을 띄우는 역할을 전부 이 파일이
조율한다.

## 스레드(thread) 구조에 대해

pywebview는 webview.start()(메인 스레드에서 실행해야 함)를 부르기 전에
창이 하나라도 미리 만들어져 있어야만, 그 안에서 자기만의 이벤트 루프(계속
돌면서 화면을 그리고 입력을 받는 반복문)를 돌릴 수 있다. 반면 pystray(트레이
아이콘 라이브러리)는 자기만의 별도 백그라운드 스레드에서 돈다.

팝업을 여는 콜백(버튼을 눌렀을 때 실행되는 함수)들은 pystray의 콜백
안에서 webui.show_*_popup을 바로 부르지 않고, 항상 작은 데몬 스레드로
한 번 감싸서 실행한다. 이렇게 하는 이유: pystray의 Windows용 내부 구현은
메뉴 클릭 콜백을 아주 낮은 수준의 OS 메시지 루프 안에서 직접 호출하는데,
예전에 tkinter를 쓰던 시절엔 그 안에서 tkinter의 블로킹(작업이 끝날 때까지
멈춰서 기다리는) 호출을 하면 프로그램이 그대로 죽어버리는 문제가 있었다
(자세한 건 git 커밋 기록 참고). 지금 쓰는 pywebview의 창 생성은 테스트해본
바로는 같은 문제가 없었지만, 이렇게 스레드로 한 번 감싸는 데 드는 비용은
거의 없고 혹시 모를 위험을 확실히 없애주니 그대로 유지한다.
"""

import threading
import time
import webbrowser
from typing import Optional

import pystray

from usage_widget import __version__, i18n, single_instance
from usage_widget.auth import has_saved_session, login_and_save_session
from usage_widget.config import DEFAULT_REFRESH_SECONDS, Config
from usage_widget.fetcher import SessionExpiredError, UsageData, fetch_account_email, fetch_usage
from usage_widget.paths import session_state_path
from usage_widget import self_update
from usage_widget.self_update import apply_update, can_self_update, cleanup_stale_update_files
from usage_widget.tray_icon import build_icon_image
from usage_widget.update_check import RELEASES_URL, check_for_update
from usage_widget.webui import (
    close_splash,
    init_gui,
    push_usage_update,
    run_gui_loop,
    shutdown_gui,
    show_account_popup,
    show_settings_popup,
    show_splash,
    show_usage_popup,
)

_UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60

_update_available_version: Optional[str] = None
_update_notified_versions: set = set()

_latest_usage = None
_last_error = None
_account_email = None
_logged_out = False  # 사용자가 명시적으로 "로그아웃"을 눌렀으면 True가 됨:
# 그 이후로는 "계정 변경"을 누르기 전까지, 사용량을 다시 가져오려는 시도도
# 자동 재로그인 시도도 완전히 멈춘 채로 있는다.


def _update_icon(icon: pystray.Icon) -> None:
    """지금 사용량 퍼센트를 트레이 아이콘에 반영한다. 만약 마지막으로
    시도한 갱신이 실패했거나 로그아웃 상태라면, 트레이 아이콘에 마우스를
    올렸을 때 뜨는 툴팁(tooltip)에 그 사실도 같이 적어준다 -- 이렇게 안
    하면, 백그라운드 스레드가 죽어버린 경우(예: 재로그인 창을 사용자가
    그냥 닫아버린 경우)에도 트레이 아이콘은 예전 데이터를 그대로 보여주고
    있을 텐데, 뭔가 잘못됐다는 걸 알려주는 표시가 전혀 없게 된다."""
    config = Config.load()
    lang = config.language
    base = i18n.t("tray.tooltip_base", lang)
    if _logged_out:
        icon.icon = build_icon_image(0, 0, style=config.tray_icon_style, logged_out=True)
        icon.title = f"{base} ({i18n.t('tray.tooltip_logged_out', lang)})"
        return
    icon.icon = build_icon_image(_latest_usage.session_percent, _latest_usage.week_percent, style=config.tray_icon_style)
    label = f"{base} ({_latest_usage.session_percent}%)"
    icon.title = label if _last_error is None else f"{label} ({i18n.t('tray.tooltip_error', lang)})"


def _fetch_with_relogin():
    """사용량을 가져오다가 로그인이 만료된 걸 발견하면 재로그인을 시도하고,
    그래도 안 되면 fetch_usage()가 던지는 예외를 그대로 다시 던진다 -- 이걸
    호출하는 쪽에서 이 예외를 알아서 잡아야 한다. 한 번 가져오다 실패한
    것(네트워크가 잠깐 끊기거나, 재로그인 창을 사용자가 그냥 닫거나,
    claude.ai가 API 형식을 바꾸는 등) 때문에 백그라운드 갱신 스레드가
    조용히 죽어버리거나 팝업이 먹통이 되면 안 되기 때문이다."""
    try:
        return fetch_usage()
    except SessionExpiredError:
        login_and_save_session()
        if not has_saved_session():
            raise  # 사용자가 로그인을 끝내지 않고 로그인 창을 그냥 닫아버린 경우
        return fetch_usage()


def _refresh_account_email() -> None:
    """되면 좋고 안 돼도 그만인 작업이다 -- 이메일 주소는 "계정" 팝업에서만
    보여주는 정보라서, 여기서 실패해도 사용량을 가져오는 것 자체에는 전혀
    영향을 주면 안 된다."""
    global _account_email
    try:
        _account_email = fetch_account_email()
    except Exception:
        _account_email = None


def _refresh_loop(icon: pystray.Icon) -> None:
    global _latest_usage, _last_error
    while True:
        try:
            config = Config.load()
            if not _logged_out:
                try:
                    _latest_usage = _fetch_with_relogin()
                    _last_error = None
                    push_usage_update(_latest_usage)
                except Exception as exc:
                    _last_error = str(exc)
                _update_icon(icon)
            interval = config.refresh_seconds
            if not isinstance(interval, (int, float)) or interval <= 0:
                interval = DEFAULT_REFRESH_SECONDS
            time.sleep(interval)
        except Exception:
            # config.json 안에 이 버전이 예상하지 못한 값이 들어있을 수도
            # 있다(예: 누가 직접 손으로 고치다가 refresh_seconds를 이상한
            # 값으로 만들어버린 경우). 이 반복문 안에서 일어나는 어떤
            # 예외든(time.sleep()에서 나는 예외도 포함) 잡지 않고 그냥
            # 두면, 이 데몬 스레드가 조용히 영원히 죽어버려서 트레이
            # 아이콘이 예전 데이터에 멈춰버리는데, 뭔가 잘못됐다는 표시가
            # 전혀 없게 된다 -- 이게 바로 _update_icon의 설명에서 경고하는
            # 바로 그 상황이다.
            time.sleep(DEFAULT_REFRESH_SECONDS)


def _manual_refresh(icon: pystray.Icon) -> Optional[UsageData]:
    """사용량을 새로 가져와서 돌려준다 (실패하면 None). 여기서 시간이 걸려도
    괜찮다: pywebview는 이런 js_api 호출을 화면을 그리는 스레드가 아니라
    이미 별도 스레드에서 처리해주기 때문에, 여기서 오래 걸려도 팝업 화면이
    멈추지 않는다."""
    global _latest_usage, _last_error
    try:
        _latest_usage = _fetch_with_relogin()
        _last_error = None
        _update_icon(icon)
        push_usage_update(_latest_usage)
        return _latest_usage
    except Exception as exc:
        _last_error = str(exc)
        _update_icon(icon)
        return None


def _do_logout(icon: pystray.Icon) -> None:
    global _logged_out, _account_email
    session_state_path().unlink(missing_ok=True)
    _logged_out = True
    _account_email = None
    _update_icon(icon)


def _do_switch_account(icon: pystray.Icon) -> None:
    """저장된 로그인 세션을 지우고, 바로 새 로그인 창을 띄운다. 수동
    새로고침과 마찬가지로 별도의 작업용 스레드(worker thread)에서 실행한다
    -- login_and_save_session()은 사용자가 로그인을 끝내거나 창을 닫을
    때까지 계속 멈춰서 기다리는 함수인데, 이걸 그냥 메인 스레드에서
    부르면 그동안 pystray의 메시지 루프 전체가 멈춰버린다."""

    def worker():
        global _latest_usage, _last_error, _logged_out
        session_state_path().unlink(missing_ok=True)
        try:
            login_and_save_session()
            _latest_usage = _fetch_with_relogin()
            _last_error = None
            _logged_out = False
            push_usage_update(_latest_usage)
            _refresh_account_email()
        except Exception as exc:
            _last_error = str(exc)
            _logged_out = True  # 로그인이 끝까지 안 됐으니 계속 일시정지 상태로 둔다(자꾸 재시도하며 귀찮게 하지 않음)
        _update_icon(icon)

    threading.Thread(target=worker, daemon=True).start()


def _show_account_dialog(icon: pystray.Icon) -> None:
    show_account_popup(
        _account_email,
        _logged_out,
        on_switch=lambda: _do_switch_account(icon),
        on_logout=lambda: _do_logout(icon),
    )


def _on_open(icon: pystray.Icon, item) -> None:
    if _logged_out:
        threading.Thread(target=lambda: _show_account_dialog(icon), daemon=True).start()
        return
    threading.Thread(
        target=lambda: show_usage_popup(_latest_usage, on_refresh=lambda: _manual_refresh(icon)),
        daemon=True,
    ).start()


def _on_settings(icon: pystray.Icon, item) -> None:
    def on_saved():
        _update_icon(icon)
        # _update_icon은 아이콘 이미지/툴팁만 다시 그려준다 -- 메뉴 항목
        # 이름들(열기/설정/계정/종료. 지금은 전부 언어에 따라 값이 바뀌는
        # 함수 형태다)은 다음에 뭔가 다른 이유로 update_menu()가 불릴 때까지
        # (예: 6시간마다 도는 업데이트 확인 루프) 다시 그려지지 않는다.
        # 그래서 icon.update_menu()를 여기서 직접 한 번 더 불러줘야, 설정에서
        # 언어를 바꿨을 때 "안 바뀐 것처럼 보이는" 문제가 안 생긴다.
        icon.update_menu()

    threading.Thread(target=lambda: show_settings_popup(on_saved=on_saved), daemon=True).start()


def _on_switch_account(icon: pystray.Icon, item) -> None:
    threading.Thread(target=lambda: _show_account_dialog(icon), daemon=True).start()


def _on_quit(icon: pystray.Icon, item) -> None:
    icon.stop()
    shutdown_gui()


_update_in_progress = False
_update_checking = False


def _update_menu_text(item) -> str:
    """이 메뉴 항목은 "새 버전이 있다는 걸 알게 됐을 때만" 나타나는 게
    아니라, 항상 보이게 만들었다. 그래야 지금 실행 중인 버전이 몇인지
    확인할 수 있는 고정된 자리가 생기고, 언제든 원할 때 바로 확인해볼 수
    있다 -- 백그라운드 확인 타이밍에 따라 메뉴 항목이 있다가 없다가 하는
    것보다 훨씬 예측 가능하다."""
    lang = Config.load().language
    if _update_in_progress:
        return i18n.t("update.applying", lang)
    if _update_checking:
        return i18n.t("update.checking", lang)
    if _update_available_version is not None:
        label = i18n.t("update.action_now", lang) if can_self_update() else i18n.t("update.action_download", lang)
        return i18n.t("update.new_version", lang, version=_update_available_version, label=label)
    return i18n.t("update.current_version", lang, version=__version__)


def _update_menu_enabled(item) -> bool:
    return not _update_in_progress and not _update_checking


def _start_update(icon: pystray.Icon) -> None:
    """새 버전을 다운로드해서 실제로 적용한다(Windows에서만 가능). 그 외
    환경에서는 그냥 릴리즈 페이지를 브라우저로 열어준다. 이 함수는
    _update_available_version에 이미 새 버전 정보가 들어있다고 가정하고
    동작한다 -- "이미 최신 버전입니다" 같은 경우를 확인해서 알려주는 건
    이 함수를 부르기 전에 호출하는 쪽에서 이미 처리했다는 뜻이다."""
    if not can_self_update():
        webbrowser.open(RELEASES_URL)
        return

    global _update_in_progress
    _update_in_progress = True
    icon.update_menu()

    def worker():
        global _update_in_progress
        lang = Config.load().language
        try:
            icon.notify(i18n.t("notify.update_downloading", lang), i18n.t("notify.update_title", lang))
            apply_update()
        except Exception as exc:
            _update_in_progress = False
            icon.update_menu()
            # self_update.py는 이 두 가지 경우에 대해 사람이 읽을 문장이
            # 아니라 고정된 영어 식별 문자열을 담아 예외를 던진다 -- 그래야
            # 여기서 그 문자열을 보고 지금 사용자가 쓰는 언어에 맞는 문구를
            # 찾아 보여줄 수 있기 때문이다. 우리가 미리 알고 있는 종류가
            # 아닌 예외(네트워크 오류 등)라면, 번역할 방법이 없으니 그냥
            # 원래 에러 문구를 그대로 보여준다.
            known_errors = {
                self_update._ERROR_NOT_SUPPORTED: "update.error_not_supported",
                self_update._ERROR_NO_EXE_IN_ZIP: "update.error_no_exe_in_zip",
            }
            error_text = i18n.t(known_errors[str(exc)], lang) if str(exc) in known_errors else str(exc)
            icon.notify(
                i18n.t("notify.update_failed_msg", lang, error=error_text), i18n.t("notify.update_failed_title", lang)
            )
            # 뭐가 문제였든 상관없이(지금 자동 업데이트 방식이 생기기 전의
            # 아주 오래된 설치본이라거나, 네트워크가 잠깐 끊겼다거나, 권한
            # 문제라거나) 알림 문구 하나만 띄워서는 사용자가 다음에 뭘 해야
            # 할지 알 수가 없다. 그래서 (Windows가 아니거나 소스로 직접
            # 실행 중일 때 이미 하고 있는 것과 똑같이) 릴리즈 페이지를
            # 자동으로 열어줘서, 자동 업데이트가 실패해도 최소한 수동으로
            # 다운로드하는 길은 클릭 한 번이면 바로 갈 수 있게 해둔다.
            webbrowser.open(RELEASES_URL)
            return
        # apply_update()는 다운로드한 파일을 임시로 저장해두고, "이
        # 프로세스(PID)가 완전히 종료되기를" 기다리는 도우미 프로세스를
        # 하나 띄우는 것까지만 했다. 그러니 이제 이 프로세스가 실제로
        # 종료돼야 하는데, 그건 트레이 메뉴의 "종료" 버튼을 눌렀을 때와
        # 똑같은 방법으로 한다 -- 안 그러면 도우미가 영원히 기다리기만
        # 한다.
        icon.stop()
        shutdown_gui()

    threading.Thread(target=worker, daemon=True).start()


def _on_update_click(icon: pystray.Icon, item) -> None:
    global _update_available_version, _update_checking

    if _update_in_progress or _update_checking:
        return

    if _update_available_version is not None:
        # 이미 알고 있는 정보가 있으면(주기적으로 도는 확인 루프가 이미
        # 찾아놨거나, 조금 전에 수동으로 확인해봤거나) 바로 다운로드/적용
        # 단계로 넘어간다.
        _start_update(icon)
        return

    # 아직 아무것도 모르는 상태: 이번 클릭 자체가 "지금 바로 확인해보기"
    # 동작이 된다 -- 다음 주기적 확인이 돌 때까지 기다리지 않는다.
    _update_checking = True
    icon.update_menu()

    def worker():
        global _update_available_version, _update_checking
        lang = Config.load().language
        version = check_for_update()
        _update_checking = False
        if version is None:
            icon.update_menu()
            icon.notify(i18n.t("notify.up_to_date_msg", lang, version=__version__), i18n.t("notify.check_title", lang))
            return
        _update_available_version = version
        _update_notified_versions.add(version)  # 이 버전에 대해 주기적 확인 루프가 또 알림을 띄우지 않도록 미리 등록해둠
        icon.update_menu()
        _start_update(icon)

    threading.Thread(target=worker, daemon=True).start()


def _update_check_loop(icon: pystray.Icon) -> None:
    """사용량 갱신 루프와는 완전히 독립적으로 돈다 -- 새 릴리즈가 나왔는지
    확인하는 주기는 사용자가 원하는 사용량 갱신 주기(config.refresh_seconds)와
    아무 상관이 없기 때문에, 일부러 그 값을 같이 쓰지 않는다."""
    global _update_available_version
    while True:
        version = check_for_update()
        _update_available_version = version
        if version is not None and version not in _update_notified_versions:
            _update_notified_versions.add(version)
            lang = Config.load().language
            action = (
                i18n.t("notify.new_version_action_self", lang)
                if can_self_update()
                else i18n.t("notify.new_version_action_download", lang)
            )
            try:
                icon.notify(
                    i18n.t("notify.new_version_available_msg", lang, version=version, action=action),
                    i18n.t("notify.new_version_available_title", lang),
                )
            except Exception:
                pass
        icon.update_menu()
        time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)


def _announce_started(icon: pystray.Icon) -> None:
    """pystray의 setup= 콜백이다: 이 아이콘이 그냥 만들어지기만 한 게
    아니라 실제로 트레이에 등록까지 끝난 시점에만 호출된다는 게 중요하다
    -- 그보다 더 일찍 icon.notify()를 부르면, 그 알림(풍선/토스트)을 붙일
    OS 쪽 트레이 항목이 아직 없어서 제대로 동작한다는 보장이 없다.

    실행할 때마다 사용량 팝업을 고정핀 박은 채로 강제로 띄우는 방법도
    고려했었지만(그 장단점에 대한 논의는 private notes 저장소의 기획
    메모 참고), 대신 짧은 토스트 알림 하나만 띄우는 쪽을 택했다 -- 작업
    표시줄을 안 보고 있던 사람도 "아, 실행됐구나"라는 확실한 신호는
    받되, 따로 처리해야 할 창이 새로 생기지 않는다."""
    icon.visible = True
    try:
        lang = Config.load().language
        icon.notify(i18n.t("notify.started_msg", lang), i18n.t("tray.tooltip_base", lang))
    except Exception:
        pass


def _run_tray(icon: pystray.Icon) -> None:
    threading.Thread(target=_refresh_loop, args=(icon,), daemon=True).start()
    threading.Thread(target=_update_check_loop, args=(icon,), daemon=True).start()
    icon.run(setup=_announce_started)


def _build_menu() -> pystray.Menu:
    """메뉴 항목 이름을 고정된 글자가 아니라 함수(호출할 때마다 값을 다시
    계산하는 콜러블, callable)로 만들었다 -- pystray는 메뉴를 화면에
    보여줄 때마다 이 함수를 다시 실행해서 최신 값을 가져온다. 그래서
    설정에서 언어를 바꾸면, 따로 뭔가를 새로고침하지 않아도 다음번에
    트레이 아이콘을 우클릭할 때 바로 새 언어로 보인다."""
    return pystray.Menu(
        pystray.MenuItem(lambda item: i18n.t("tray.open", Config.load().language), _on_open, default=True),
        pystray.MenuItem(lambda item: i18n.t("tray.settings", Config.load().language), _on_settings),
        pystray.MenuItem(lambda item: i18n.t("tray.account", Config.load().language), _on_switch_account),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_update_menu_text, _on_update_click, enabled=_update_menu_enabled),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda item: i18n.t("tray.quit", Config.load().language), _on_quit),
    )


def _notify_already_running() -> None:
    """pywebview 팝업이 아니라 그냥 OS의 기본 메시지 박스를 하나 띄운다 --
    이 함수가 불리는 시점은 init_gui()/run_gui_loop()가 아직 시작도 안 한
    아주 이른 시점이고, 어차피 이 프로세스는 곧바로 종료될 거라서, 이 한
    줄 메시지를 보여주려고 앱 전체의 webview 관련 기능을 새로 띄우는 건
    낭비다. tkinter는 파이썬 자체에 기본으로 들어있는 라이브러리라서
    (팝업 화면을 전부 pywebview로 옮긴 뒤에도 이것 때문에 새 의존성을
    추가할 필요는 없다), 아직 아무 것도 준비 안 된 이 시점에 뭔가를
    멈춰서 기다리는 대화상자를 보여줘야 하는 유일한 곳에서는 이렇게
    tkinter를 그대로 쓴다."""
    import tkinter
    from tkinter import messagebox

    lang = Config.load().language
    root = tkinter.Tk()
    root.withdraw()
    try:
        messagebox.showinfo(i18n.t("tray.tooltip_base", lang), i18n.t("dup.already_running_msg", lang))
    finally:
        root.destroy()


def run() -> None:
    """예전에는 pywebview의 이벤트 루프(run_gui_loop)가 시작되기도 전에,
    로그인 확인과 첫 사용량 조회를 메인 스레드에서 그대로 멈춰서 기다렸다
    -- 그래서 그 시간 동안은 화면에 창이 하나도 없었고, 프로그램이 그냥
    조용히 실행에 실패한 건지 구분할 방법이 없었다. 지금은 순서를 바꿔서:
    먼저 스플래시(잠깐 뜨는 로딩 화면)를 띄우고, 시간이 걸리는 작업은
    백그라운드 스레드로 옮기고, run_gui_loop()를 바로 시작해서 스플래시가
    실제로 화면에 그려지게 한다 (webview.create_window()/destroy()는
    메인 스레드가 아닌 다른 스레드에서 불러도 안전하다고 공식적으로
    문서화돼 있다 -- webui.py 맨 위 설명 참고)."""
    global _latest_usage
    if not single_instance.acquire():
        # 이미 다른 인스턴스(같은 프로그램의 다른 실행 중인 복사본)가 이
        # 잠금을 갖고 있다는 뜻이다 -- exe를 두 번 실행하면(습관적으로 다시
        # 더블클릭하거나, 자동 시작과 수동 실행이 우연히 겹치거나, 이미
        # 구버전이 실행 중인데 새로 받은 exe를 또 실행하거나 등) 예전에는
        # 서로 아무 관련 없는 두 번째 프로세스가 통째로 하나 더 생겨서,
        # 트레이 아이콘도 두 개가 되고 각자 PyInstaller onefile 방식이 쓰는
        # 임시 폴더도 따로 만들다가 서로 부딪히곤 했다. 그냥 종료하는 것
        # 자체로 문제는 해결되지만, 아무 설명 없이 조용히 종료하면
        # "더블클릭했는데 아무 반응이 없네?"처럼 보일 뿐이다 -- 앱의 GUI
        # 기능이 아직 하나도 안 켜진 이 시점에는, 그냥 메시지 박스 하나만
        # 띄워줘도 이유를 알려주기엔 충분하다.
        _notify_already_running()
        return
    cleanup_stale_update_files()

    init_gui()
    lang = Config.load().language
    splash = show_splash(lang)

    def bootstrap():
        global _latest_usage
        try:
            if not has_saved_session():
                # 이제 곧 로그인을 위한 진짜 Chrome 브라우저 창이 통째로
                # 뜰 예정이다 -- 그 밑에 작은 스플래시 화면이 계속 남아있을
                # 이유가 없으니 먼저 닫는다.
                close_splash(splash)
                login_and_save_session()
            _latest_usage = _fetch_with_relogin()
            _refresh_account_email()
        except Exception:
            close_splash(splash)
            shutdown_gui()
            raise
        close_splash(splash)

        icon = pystray.Icon(
            "claude-usage-widget",
            build_icon_image(
                _latest_usage.session_percent, _latest_usage.week_percent, style=Config.load().tray_icon_style
            ),
            i18n.t("tray.tooltip_base", Config.load().language),
            _build_menu(),
        )
        _run_tray(icon)

    threading.Thread(target=bootstrap, daemon=True).start()
    run_gui_loop()


if __name__ == "__main__":
    run()
