"""팝업 창들(사용량/설정/계정)을 담당하는 파일. tkinter가 아니라
pywebview로 만든다 -- 실제 화면(HTML/CSS/JS)은
usage_widget/assets/web/*.html에 있고, 이 파일은 그 화면과 파이썬 코드를
이어주는 다리 역할만 한다(창을 만들고, 위치를 잡고, 각 화면이 호출하는
js_api 객체를 준비하는 것).

## 스레드에 대해

pywebview는 webview.start()를 부르기 전에 창이 최소 하나는 이미 만들어져
있어야 하고, 그 호출은 자신을 부른 스레드를 그 자리에서 멈추게 만든다 --
tkinter의 "숨겨진 root 창 하나 만들어두고 mainloop() 돌리기"와 같은
구조다. tkinter와 다른 점: pywebview의 create_window()/destroy()는
"어느 스레드에서 불러도 안전하다"고 공식적으로 문서화돼 있다(실제로도
확인함: webview.start()가 메인 스레드를 멈추고 있는 동안, 다른
백그라운드 스레드에서 새 창을 만들어도 프로그램이 안 죽는다). 그래서
pystray의 메뉴 콜백에서 root.after(...) 같은 걸 거치지 않고 팝업을
바로 열 수 있다.
"""

import ctypes
import json
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import webview
from webview.window import FixPoint

from usage_widget import autostart, i18n
from usage_widget.config import Config
from usage_widget.fetcher import UsageData
from usage_widget.tray_icon import DEFAULT_STYLE

_ASSET_DIR = Path(__file__).parent / "assets" / "web"
_IS_WINDOWS = sys.platform == "win32"

_root_window: Optional[webview.Window] = None


def init_gui() -> None:
    """pywebview가 start()를 실행하기 전에 필요로 하는, 화면에 안 보이는
    숨겨진 창을 하나 만들어둔다. 이 창은 앱이 살아있는 내내 계속 존재한다.
    이 창을 없애는 것(아래 shutdown_gui 참고)이 곧 앱을 진짜로 종료시키는
    방법이다 -- pywebview를 뒤에서 돌리고 있는 창 관련 라이브러리는 "마지막
    창이 닫히면" 자기도 같이 종료되기 때문이다."""
    global _root_window
    if _root_window is None:
        _root_window = webview.create_window("root", html="<html></html>", hidden=True)


def run_gui_loop() -> None:
    webview.start()


def shutdown_gui() -> None:
    """숨겨진 root 창을 없애야 pywebview의 내부 반복문(native loop)이
    끝난다. 그런데 이것만으로는, 그 시점에 마침 열려 있던 사용량/설정/계정
    팝업들은 전혀 안 건드려진다 -- 그 팝업들은 완전히 별개의 창이라서,
    "종료"를 눌러도 화면에 그대로 남아있는(주인 없이 붕 떠버린) 버그가
    실제로 보고된 적이 있다. 그래서 root 창을 없애기 전에, 열려 있는
    팝업들을 먼저 전부 닫아야 화면에서 진짜로 다 사라진다."""
    with _singleton_dict_lock:
        windows = list(_singleton_windows.values())
    for window in windows:
        _safe_destroy(window)
    if _root_window is not None:
        _root_window.destroy()


def _screen_size() -> Optional[tuple]:
    if not _IS_WINDOWS:
        return None
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def _cursor_pos() -> Optional[tuple]:
    if not _IS_WINDOWS:
        return None

    class _Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = _Point()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _position_near_cursor(width: int, height: int) -> tuple:
    """팝업을 클릭한 위치 근처에 띄우되, 화면 가장자리 중 커서와 가까운
    쪽 반대 방향으로 열리게 한다 -- 예전 tkinter 버전의 플라이아웃과
    이유가 같다: 이 팝업은 마우스가 벗어나면 바로 닫히기 때문에, 뜨자마자
    커서 바로 아래에 있어야만 한다. 아직 이 위치 계산을 구현 안 한
    플랫폼(Windows가 아닌 경우)에서는 pywebview 자체의 기본 배치
    (None, None)로 대체된다.

    지금은 사용량 팝업의 실제 위치 계산으로는 _position_near_tray가 이
    함수를 대체했다(왜 바꿨는지는 그쪽 설명 참고) -- 이 함수는 작업표시줄의
    "작업 영역" 정보를 무슨 이유로든 못 읽어왔을 때 _position_near_tray가
    대신 쓰는 안전장치(폴백)로만 남아있다."""
    cursor = _cursor_pos()
    screen = _screen_size()
    if cursor is None or screen is None:
        return None, None
    cursor_x, cursor_y = cursor
    screen_w, screen_h = screen
    gap = 24

    y = cursor_y - height + gap if cursor_y > screen_h / 2 else cursor_y - gap
    x = cursor_x - width + gap if cursor_x > screen_w / 2 else cursor_x - gap
    x = max(0, min(x, screen_w - width))
    y = max(0, min(y, screen_h - height))
    return int(x), int(y)


_SPI_GETWORKAREA = 0x0030


def _work_area() -> Optional[tuple]:
    """Windows가 "작업표시줄을 뺀 나머지 사용 가능한 화면 영역"으로 정해둔
    사각형 범위를 돌려준다 -- 창을 최대화했을 때 작업표시줄 밑으로 안
    들어가게 하려고 Windows 자신도 쓰는 바로 그 값이다. "작업표시줄은 항상
    화면 맨 아래에 있고, 화면 전체 크기(GetSystemMetrics)에서 그만큼
    빼면 된다"고 무작정 가정하는 대신 이 값을 직접 읽어오기 때문에,
    작업표시줄이 어느 쪽(위/아래/왼쪽/오른쪽)에 도킹돼 있든, 자동 숨김
    상태든, 어느 모니터가 주 모니터든 상관없이 _position_near_tray가 잘
    동작한다."""
    if not _IS_WINDOWS:
        return None

    class _Rect(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = _Rect()
    if not ctypes.windll.user32.SystemParametersInfoW(_SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def _macos_menubar_position(width: int, height: int) -> Optional[tuple]:
    """macOS용으로 _position_near_tray와 같은 역할을 하려는 최선의
    시도(best-effort)다: 화면 오른쪽 위(메뉴바 상태 아이콘들, 이 앱의
    트레이 아이콘도 포함돼서 모여있는 곳) 근처에 앵커(고정)한다. 이건
    macOS의 네이티브 메뉴바 드롭다운(와이파이, 제어 센터, 배터리 등)이
    커서를 따라가지 않고 항상 메뉴바 바로 아래에서 열리는 것과 같은
    원리다.

    **미검증** -- 이걸 테스트해볼 실제 Mac이 아직 없었다. AppKit(macOS의
    화면 그리기 라이브러리)의 좌표계는 Windows와 달리 화면 왼쪽 "아래"가
    원점(0,0)이다(Windows는 왼쪽 "위"가 원점). 아래 코드에서 이 차이를
    뒤집어서, pywebview의 create_window()가 모든 플랫폼에서 공통으로
    기대하는 "왼쪽 위가 원점인" (x, y) 좌표로 맞춰주려고 하는데, 바로 이
    좌표 뒤집기 계산 부분이 실제 Mac에서 검증했을 때 고쳐야 할 가능성이
    가장 높은 부분이다."""
    if _IS_WINDOWS:
        return None
    try:
        from AppKit import NSScreen
    except ImportError:
        return None
    screen = NSScreen.mainScreen()
    if screen is None:
        return None
    full = screen.frame()
    visible = screen.visibleFrame()  # 메뉴바(그리고 독Dock이 화면에 붙어 있다면 그것도) 뺀 나머지 영역
    screen_w, screen_h = full.size.width, full.size.height
    gap = 8

    menu_bar_bottom_from_top = screen_h - (visible.origin.y + visible.size.height)
    x = screen_w - width - gap
    y = menu_bar_bottom_from_top + gap
    x = max(0, min(x, screen_w - width))
    y = max(0, min(y, screen_h - height))
    return int(x), int(y)


def _position_near_tray(width: int, height: int) -> tuple:
    """팝업을 시스템 트레이/메뉴바 바로 옆에 앵커한다 -- Windows의 네이티브
    플라이아웃(볼륨/네트워크/배터리)이나 macOS의 와이파이/제어 센터가
    그러듯이, "클릭했을 때 커서가 우연히 어디 있었는지"가 아니라 트레이가
    실제로 있는 위치 옆에 붙인다. 지인 피드백: 원래 커서를 따라다니던
    방식은 일반적인 Windows 플라이아웃처럼 안 느껴진다고 함. 화면 크기만
    보고 추측하는 대신 작업표시줄의 실제 작업 영역에 앵커하면, 부수적으로
    예전 방식이 틀리던 경우들도 같이 고쳐진다 -- 작업표시줄이 아래쪽이
    아닌 다른 곳에 도킹돼 있는 경우라거나, 트레이 아이콘을 직접 클릭한 게
    아니라 우클릭 메뉴의 "열기" 항목으로 열어서 커서가 트레이 근처에
    전혀 없는 경우 등.

    (x, y, grow_upward)를 돌려준다 -- grow_upward는 나중에 이 창의 크기를
    키울 때 어느 방향으로 키우는 게 안전한지 알려주는 값이다(자세한
    사용처는 _box_vertical_resizer 참고). 아래 4가지 도킹 방향 중 3가지처럼
    창의 아래쪽 경계가 뭔가(대개는 작업표시줄)에 딱 붙어서 앵커됐다면
    True가 된다 -- 이럴 때 리사이즈가 원래 하던 대로 아래쪽으로 창을
    키우면 곧바로 그 작업표시줄을 침범하게 된다."""
    work = _work_area()
    screen = _screen_size()
    if work is None or screen is None:
        macos_pos = _macos_menubar_position(width, height)
        if macos_pos is not None:
            return (*macos_pos, False)  # 위쪽 메뉴바 밑에 앵커된 경우 -- 아래로 자라도 안전함
        return (*_position_near_cursor(width, height), False)

    left, top, right, bottom = work
    screen_w, screen_h = screen
    gap = 12
    grow_upward = True

    if bottom < screen_h:  # 작업표시줄이 아래쪽에 도킹 (압도적으로 가장 흔한 경우)
        x, y = right - width - gap, bottom - height - gap
    elif top > 0:  # 작업표시줄이 위쪽에 도킹
        x, y = right - width - gap, top + gap
        grow_upward = False  # 위쪽에 앵커됐으니 -- 아래로 자라는 게 오히려 작업표시줄에서 멀어지는 방향
    elif right < screen_w:  # 작업표시줄이 오른쪽에 도킹
        x, y = right - width - gap, bottom - height - gap
    elif left > 0:  # 작업표시줄이 왼쪽에 도킹
        x, y = left + gap, bottom - height - gap
    else:  # 작업표시줄 위치를 못 찾음 -- 화면 오른쪽 아래 구석으로 대신 배치
        x, y = screen_w - width - gap, screen_h - height - gap

    x = max(0, min(x, screen_w - width))
    y = max(0, min(y, screen_h - height))
    return int(x), int(y), grow_upward


def _position_centered(width: int, height: int) -> tuple:
    screen = _screen_size()
    if screen is None:
        return None, None
    screen_w, screen_h = screen
    return int((screen_w - width) / 2), int((screen_h - height) / 2)


_destroy_lock = threading.Lock()


def _safe_destroy(window: webview.Window) -> None:
    """창을 최대 한 번만 없앤다 -- 어떤 흐름에서는(예: 아주 빠르게 두 번
    클릭하는 경우) close_fn이 연달아 두 번 불릴 수도 있는데, 이렇게 하면
    두 번째 호출은 그냥 아무 일도 안 하고 넘어가서, 두 스레드가 동시에
    같은 창을 없애려다 충돌하는 걸 막아준다."""
    with _destroy_lock:
        if getattr(window, "_uw_destroyed", False):
            return
        window._uw_destroyed = True
    try:
        window.destroy()
    except Exception:
        pass


_PANEL_RADIUS = 20  # common.css의 --radius 값과 반드시 일치해야 함


def _round_corners(window: webview.Window, radius: int = _PANEL_RADIUS) -> None:
    """Win32 API를 이용해서, 네이티브 창 자체를 둥근 사각형 모양으로
    잘라낸다(클리핑).

    pywebview에서 Windows용 transparent=True 옵션은 사실 "페이지 자체의
    배경"만 투명하게 만들어줄 뿐이다(그래서 CSS가 Form의 배경색을 그
    너머로 비치게 할 수 있는 것뿐). 창 그 자체를 OS 차원에서 픽셀 단위로
    진짜 투명하게 만들어주는 건 아니다. 그래서 우리가 CSS로 둥글게 만든
    모서리 바깥쪽 부분은 여전히 불투명한 사각형 창의 일부로 남아있었고,
    그게 둥근 패널 뒤에서 각진 자국처럼 눈에 보이는 문제가 있었다. 창의
    실제 영역 자체를 잘라내면 그 모서리를 OS 차원에서 아예 없애버릴 수
    있어서, 이런 식으로 투명하게 "보이도록" 애쓸 필요가 없다. 덤으로
    transparent=True를 안 써도 돼서, pywebview가 원래 transparent가
    False일 때만 적용해주는 자연스러운 그림자 효과도 얻게 됐다.

    이 잘라낼 영역의 크기는 create_window에 넘긴 논리적인(logical)
    가로/세로 값이 아니라, 실제 물리적(physical) 픽셀 단위로 읽고
    계산해야 한다: pywebview는 내부적으로 모니터의 DPI(화면 배율) 값에
    따라 창의 진짜 네이티브 크기를 다시 스케일링한다(예: 125% 배율에서는
    360x400짜리 창이 실제로는 약 450x500 크기의 win32 창이 된다). 만약
    스케일 안 된 논리적 크기 그대로 계산하면, 잘라내는 영역이 실제 창보다
    작아져서, 100% 초과 배율의 화면에서는 여전히 각진 모서리가 살짝
    남아있게 된다. 창이 실제로 화면에 뜬 시점에 window.native.Size(그리고
    반지름도 같은 비율로)를 읽어오면, pywebview가 내부적으로 하는 배율
    계산을 우리가 또 따로 중복해서 할 필요가 없다."""
    if not _IS_WINDOWS:
        return

    def apply(*_args):
        try:
            hwnd = window.native.Handle.ToInt32()
            scale = ctypes.windll.user32.GetDpiForWindow(hwnd) / 96.0
            w, h = window.native.Size.Width, window.native.Size.Height
            r = int(radius * scale)
            region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, r * 2, r * 2)
            ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
        except Exception:
            pass

    window.events.shown += apply
    # 리사이즈 그립(모서리 손잡이, resize_by()/common.js 참고)으로 크기를
    # 바꾸면 window.native.Size가 실시간으로 바뀌는데, 이건 OS가 직접
    # 창 크기를 바꿔줄 때와 똑같은 효과다 -- 그래서 클리핑(잘라내기)도
    # 다시 적용해줘야, 처음 창이 떴을 때 크기 기준으로 잘려있던 둥근
    # 모서리가 새로 바뀐 크기에도 계속 맞게 유지된다.
    window.events.resized += apply


_GWL_EXSTYLE = -20
_WS_EX_LAYERED = 0x00080000
_LWA_ALPHA = 0x2


def _apply_window_opacity(window: webview.Window, percent: int) -> None:
    """페이지 일부분만 CSS opacity로 흐리게 만드는 게 아니라, Win32의
    WS_EX_LAYERED + SetLayeredWindowAttributes API를 이용해서 네이티브
    창 "전체"를 반투명하게 만든다. 이전에 한 번 시도했던 방식은 CSS
    ::before 오버레이로 사용량 카드의 색깔 있는 배경/테두리만 흐리게
    했었는데(글자는 또렷하게 남기려고 일부러 그렇게 함) -- 그건 원하는
    결과가 아니었다: 카톡(KakaoTalk)의 반투명 채팅창처럼, 글자까지
    포함해서 창 전체가 하나의 유리판처럼 흐려져야 한다는 요청이었다.
    진짜 창 자체를 "레이어(층)"로 다루면, 그 창이 그리는 모든 픽셀이
    뒤에 있는 화면과 섞여서 표현되는데, 이게 그 효과를 낼 수 있는 유일한
    방법이다."""
    if not _IS_WINDOWS:
        return
    try:
        hwnd = window.native.Handle.ToInt32()
        percent = min(100, max(40, int(percent)))
        alpha = round(percent / 100 * 255)
        user32 = ctypes.windll.user32
        ex_style = user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, ex_style | _WS_EX_LAYERED)
        user32.SetLayeredWindowAttributes(hwnd, 0, alpha, _LWA_ALPHA)
    except Exception:
        pass


def _apply_initial_opacity(window: webview.Window, percent: int) -> None:
    """_round_corners와 똑같은 DPI/타이밍 이유 때문에: window.native는
    창이 실제로 화면에 뜨기 전까지는 안정적으로 쓸 수가 없다. 그래서
    저장해둔 투명도 값(100%가 아닌 경우)을 처음 적용할 때도 창이 뜨는
    이벤트를 기다렸다가 한다. 나중에 슬라이더를 움직여서 실시간으로
    값이 바뀔 때는 이미 창이 뜬 지 한참 지난 뒤라서, 그때는 그냥
    _apply_window_opacity를 바로 부르면 된다."""
    if not _IS_WINDOWS or percent >= 100:
        return

    def apply(*_args):
        _apply_window_opacity(window, percent)

    window.events.shown += apply


# pywebview의 WinForms(.NET의 창 그리기 방식) 백엔드는 프레임이 없는
# 창으로 바꾸기 "전에" 먼저 Form.Size(창 크기)를 설정한다(winforms.py 안을
# 보면, 창 생성 코드 위쪽에서 Size를 정하고, FormBorderStyle을 None으로
# 바꾸는 건 그 뒤에 일어난다). 그런데 WinForms는 테두리 스타일이 바뀌어도
# ClientSize(테두리를 뺀 실제 내용 영역 크기)는 그대로 유지하려고 한다.
# 그 결과, 나중에 테두리/제목표시줄이 없어지고 나면, 그만큼(원래 있었을
# 테두리 두께만큼)이 그냥 통째로 사라져서 창이 우리가 요청한 크기보다
# 항상 작게 뜬다 -- 여러 크기로 직접 테스트해서 확인함: 항상 정확히
# 가로 16px, 세로 39px씩 작아진다(이 숫자는 Windows의 일반적인
# 비클라이언트 영역 크기와 얼추 맞다: 좌우 리사이즈 테두리 약 8px씩,
# 제목표시줄+위쪽 테두리 약 31px). 이건 화면 배율(DPI) 100%에서만
# 확인했다 -- 테두리 크기도 보통 DPI에 따라 같이 커지므로, 다른 배율
# 에서는 이 고정 보정값이 살짝 안 맞을 수도 있지만, 아예 보정을 안 하는
# 것보다는 훨씬 정확할 것이다. 창을 만들 때 요청하는 크기에 미리 이만큼
# 더해두면, 실제로 생기는 창 크기가 CSS로 설계해둔 크기와 맞아떨어져서,
# 예상보다 작은 창 안에 내용물이 조용히 잘려나가는 일이 없어진다.
_WINFORMS_SIZE_FUDGE = (16, 39)


def _new_window(title: str, page: str, js_api, width: int, height: int, position: tuple) -> webview.Window:
    """팝업들은 서로 완전히 독립적이다 -- 사용량/설정/계정 팝업을 전부
    동시에 띄워둘 수 있고, 각자 따로 닫을 수 있다."""
    x, y = position
    create_width, create_height = width, height
    if _IS_WINDOWS:
        create_width += _WINFORMS_SIZE_FUDGE[0]
        create_height += _WINFORMS_SIZE_FUDGE[1]
    window = webview.create_window(
        title,
        url=str(_ASSET_DIR / page),
        js_api=js_api,
        width=create_width,
        height=create_height,
        x=x,
        y=y,
        frameless=True,
        easy_drag=True,
        # shadow=True로 하면(transparent=False일 때) pywebview가
        # DwmExtendFrameIntoClientArea + DwmSetWindowAttribute를 호출해서
        # 네이티브 그림자를 만들어주는데, 이 두 번째 호출이 DWM(Windows의
        # 창 그리기 관리자)한테 "기본 비클라이언트 창 프레임을 다시
        # 그려라"라고 강제로 시키는 효과가 있다. 이게 우리가 SetWindowRgn
        # 으로 잘라낸 둥근 모서리와 충돌해서, 특히 창이 포커스를 받을 때
        # 위쪽 가장자리에 점선 테두리가 스치듯 나타나는 문제가 있었다.
        # 그럴 가치가 없어서 -- 네이티브 그림자 없이 두는 게 둥근 모서리를
        # 깔끔하게 유지해준다.
        shadow=False,
        on_top=True,
        resizable=False,
        # Windows에서는 대신 아래 _round_corners()로 진짜 둥근 모서리를
        # 만든다(왜 여기서 transparent=True를 못 믿는지는 그 함수의 설명
        # 참고). 다른 플랫폼은 아직 검증을 안 해봐서, 일단 예전 방식
        # 그대로 둔다.
        transparent=not _IS_WINDOWS,
    )
    _round_corners(window)
    return window


def _reset_status_text(reset_at: Optional[datetime], lang: str) -> str:
    """아직 그 구간에서 한 번도 사용한 적이 없으면(예: 5시간 세션이 막
    리셋된 직후, 아직 다음 메시지를 보내기 전) API가 리셋 시각 값을
    안 내려준다."""
    if reset_at is None:
        return i18n.t("reset.not_started", lang)
    delta = reset_at - datetime.now()
    total_minutes = max(int(delta.total_seconds()) // 60, 0)
    days, remainder = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder, 60)
    if days:
        return i18n.t("reset.days", lang, days=days, hours=hours)
    return i18n.t("reset.hours", lang, hours=hours, minutes=minutes)


def _box_closer(box: list) -> Callable[[], None]:
    """나중에 box 리스트에 담기게 될 창을 없애주는, "닫기" 콜백 함수를
    만들어서 돌려준다. 이걸 js_api 객체의 속성(attribute)으로 직접 들고
    있는 게 아니라, 지역 변수인 리스트를 감싼 평범한 클로저(closure,
    함수가 자기 주변 변수를 계속 기억하고 있는 것) 형태로 만든 이유:
    이렇게 하면 js_api.close()가 창에 접근은 하면서도, js_api 객체
    자신은 그 창을 가리키는 참조를 절대 직접 들고 있지 않게 된다(이
    "서로를 참조하는 고리"가 왜 문제가 되는지는 _UsageApi의 설명 참고)."""
    return lambda: box and _safe_destroy(box[0])


_MIN_POPUP_SIZE = (260, 220)


def _box_resizer(box: list, size: list) -> Callable[[float, float], None]:
    """common.js의 드래그 손잡이(window.pywebview.api.resize_by)를 위한
    리사이즈 콜백을 만들어서 돌려준다. _box_closer와 똑같은 "box를 감싼
    클로저" 방식을 쓴다 -- js_api가 창을 직접 들고 있으면 안 되기
    때문이다(_UsageApi의 설명 참고). `size`는 지금 이 팝업의 [가로,
    세로] 크기를 논리적 픽셀 단위로 계속 기록해두는 값이다. 프레임 없는
    창은 OS가 제공하는 크기 조절 테두리가 없어서, 이 함수가 window.resize()
    를 부르는 유일한 통로다. 여기서 최소 크기 아래로는 안 줄어들게
    막아주는 이유는, 드래그를 계속하다가 팝업이 레이아웃을 감당 못 할
    만큼 작아지는 걸 막기 위해서다."""

    def _resize(dw: float, dh: float) -> None:
        if not box:
            return
        size[0] = max(_MIN_POPUP_SIZE[0], size[0] + dw)
        size[1] = max(_MIN_POPUP_SIZE[1], size[1] + dh)
        try:
            box[0].resize(int(size[0]), int(size[1]))
        except Exception:
            pass

    return _resize


def _box_vertical_resizer(box: list, size: list, grow_upward: bool) -> Callable[[float], None]:
    """사용량 팝업의 투명도 스트립 토글(usage.html 참고) 전용으로, 세로
    높이만 조절하는 함수다. _box_resizer의 드래그 손잡이용 리사이즈와는
    다르다: 모서리를 손으로 드래그해서 늘릴 때는 사용자가 드래그하는
    방향을 그대로 눈으로 따라가야 자연스럽다(그래서 기본값인
    FixPoint.NORTH|WEST를 쓴다 -- 왼쪽 위 모서리는 그대로 두고 크기만
    늘어남). 하지만 투명도 스트립이 열리고 닫히는 건 사람이 드래그하는 게
    아니라 자동으로 일어나는 리사이즈라서 따라갈 커서 자체가 없고, 여기서
    아무 생각 없이 기본값대로 아래로만 늘리면, _position_near_tray가
    창의 아래쪽 경계를 작업표시줄에 딱 붙여서 앵커해둔 경우 그대로
    작업표시줄을 침범하게 된다. 그래서 이럴 땐 FixPoint.SOUTH를 써서,
    아래쪽 경계(그리고 작업표시줄 옆에 붙여둔 그 앵커 위치)는 그대로
    고정하고 위쪽 경계를 움직이는 방식으로 늘리고 줄인다. `grow_upward`
    값은 팝업이 처음 만들어질 때, 그 창이 실제로 어느 쪽 경계에
    앵커됐는지를 보고 딱 한 번만 정해지고, 그 팝업이 살아있는 동안 계속
    고정된 값으로 쓰인다 -- 스트립을 열 때와 닫을 때 서로 다른
    fix_point를 쓰면, 창이 원래 있던 자리에서 슬쩍 어긋나 버리기
    때문이다."""
    fix_point = (FixPoint.SOUTH | FixPoint.WEST) if grow_upward else (FixPoint.NORTH | FixPoint.WEST)

    def _resize(dh: float) -> None:
        if not box:
            return
        size[1] = max(_MIN_POPUP_SIZE[1], size[1] + dh)
        try:
            box[0].resize(int(size[0]), int(size[1]), fix_point=fix_point)
        except Exception:
            pass

    return _resize


def _box_opacity_setter(box: list) -> Callable[[int], None]:
    """나중에 box 리스트에 담기게 될 창에, _apply_window_opacity를 통해
    투명도 퍼센트 값을 적용해주는 함수를 만들어서 돌려준다. _box_closer/
    _box_resizer와 똑같은 "리스트를 감싼 클로저" 패턴이라서, js_api가
    창을 직접 들고 있는 일이 없다."""

    def _apply(percent: int) -> None:
        if box:
            _apply_window_opacity(box[0], percent)

    return _apply


def _usage_to_dict(usage: UsageData, lang: str) -> dict:
    return {
        "session": {
            "percent": usage.session_percent,
            "reset_text": _reset_status_text(usage.session_reset_at, lang),
        },
        "week": {
            "percent": usage.week_percent,
            "reset_text": _reset_status_text(usage.week_reset_at, lang),
        },
    }


class _UsageApi:
    """close_fn은 Window 객체 자체를 직접 참조하는 게 아니라 평범한
    클로저다 -- js_api 객체는 자신을 담고 있는 webview.Window를 다시
    가리키는 속성을 절대로 들고 있으면 안 된다. 그런 "서로를 참조하는
    고리"(창 -> js_api -> 다시 창)가 생기면, 실제 테스트에서
    WinForms/EdgeChromium 백엔드가 거의 매번 멈춰버리는 걸 확인했다:
    내부적으로 뭔가를 검사하는 과정(reflection)이 js_api의 속성들을 쭉
    훑다가 창을 다시 만나면, 거기서 끝없이 재귀 호출을 반복하게 된다
    (`window.native.AccessibilityObject.Bounds.Empty.Empty...`처럼
    계속 파고들다가, 결국 "최대 재귀 깊이 초과"로 GUI 스레드 전체가
    멈춰버리는 크래시였다). 반면 지역 변수 안에 담아둔 클로저는 이런
    단순한 "속성을 하나씩 따라가며 훑는" 방식으로는 아예 도달할 수가
    없어서, 이런 참조 고리 자체가 생기지 않는다."""

    def __init__(
        self,
        usage: UsageData,
        refresh_fn: Optional[Callable[[], Optional[UsageData]]],
        close_fn: Callable[[], None],
        resize_fn: Callable[[float, float], None],
        vertical_resize_fn: Callable[[float], None],
        opacity: int,
        opacity_fn: Callable[[int], None],
        lang: str,
    ):
        self._usage = usage
        self._refresh_fn = refresh_fn
        self._close_fn = close_fn
        self._resize_fn = resize_fn
        self._vertical_resize_fn = vertical_resize_fn
        self._opacity = opacity
        self._opacity_fn = opacity_fn
        self._lang = lang

    def get_initial_data(self) -> dict:
        return {**_usage_to_dict(self._usage, self._lang), "opacity": self._opacity, "language": self._lang}

    def refresh(self) -> Optional[dict]:
        if self._refresh_fn is None:
            return None
        new_usage = self._refresh_fn()
        if new_usage is None:
            return None
        self._usage = new_usage
        return _usage_to_dict(new_usage, self._lang)

    def close(self) -> None:
        self._close_fn()

    def resize_by(self, dw: float, dh: float) -> None:
        self._resize_fn(dw, dh)

    def resize_height_by(self, dh: float) -> None:
        """드래그 손잡이가 아니라 투명도 스트립 토글이 쓰는 함수다 -- 왜
        이걸 별도 경로로 분리해야 했는지는 _box_vertical_resizer 설명
        참고."""
        self._vertical_resize_fn(dh)

    def preview_opacity(self, percent: int) -> None:
        """슬라이더를 드래그하는 동안 실시간으로 미리보기를 보여준다 --
        (_apply_window_opacity를 통해) 실제 창에 바로 적용은 되지만
        저장은 안 한다. 그래서 마우스를 떼기 전까지도 미리보기가 "실제로
        떼면 이렇게 보일 것"이라는 걸 정직하게 보여줄 수 있다."""
        try:
            self._opacity_fn(int(percent))
        except (TypeError, ValueError):
            pass

    def set_opacity(self, percent: int) -> None:
        """슬라이더에서 손을 뗐을 때 딱 한 번 호출된다 -- 최종 값을
        적용하고(혹시 이 호출 전에 preview_opacity가 한 번도 안 불렸을
        경우를 대비해서), 그 값을 저장해서 다음에 이 팝업을 다시 열어도
        기억하고 있게 한다."""
        try:
            percent = min(100, max(40, int(percent)))
        except (TypeError, ValueError):
            return
        self._opacity_fn(percent)
        config = Config.load()
        config.usage_popup_opacity = percent
        config.save()


_singleton_windows: dict = {}
# _singleton_windows 자체를 읽고 쓰는 걸 보호하는 락(아주 잠깐씩만 잠김)
# -- 아래 있는 "종류별 락"과는 다른 역할이다. 종류별 락은 (시간이 좀 걸릴
# 수도 있는) create() 호출 자체를 보호해서, 서로 관련 없는 팝업 종류끼리
# 서로를 기다리지 않게 해주는 것이다.
_singleton_dict_lock = threading.Lock()
_singleton_locks: dict = {}
_singleton_locks_meta_lock = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    """팝업 종류마다 각자 하나씩 락을 따로 쓴다 (전체가 락 하나를 같이
    쓰는 게 아니라) -- 안 그러면, 여는 데 시간이 좀 걸리는 팝업 하나를
    만드는 동안(예: WebView2/WinForms를 맨 처음 초기화할 때) 서로 아무
    관련 없는 다른 팝업(예: 설정 팝업)이 열리기 시작하는 것조차 막혀버릴
    수 있다 -- 두 클릭이 우연히 시간상 가깝게 일어났을 뿐인데도, 이
    둘은 원래 서로 독립적인 슬롯인데 말이다."""
    with _singleton_locks_meta_lock:
        if key not in _singleton_locks:
            _singleton_locks[key] = threading.Lock()
        return _singleton_locks[key]


def _focus_or_create(key: str, create: Callable[[], webview.Window]) -> None:
    """한 종류(`key`)의 팝업은 한 번에 최대 하나만 열려있게 보장한다.
    이게 없으면, 이미 열려있는 팝업을 트레이 아이콘(또는 메뉴 항목)을
    다시 클릭했을 때, 기존 창을 앞으로 가져오는 대신 겹쳐서 새 창이
    하나 더 떠버렸다."""
    lock = _lock_for(key)
    with lock:
        with _singleton_dict_lock:
            existing = _singleton_windows.get(key)
        if existing is None:
            window = create()
            with _singleton_dict_lock:
                _singleton_windows[key] = window
    if existing is not None:
        try:
            existing.show()
        except Exception:
            pass
        return

    def _unregister():
        with lock:
            with _singleton_dict_lock:
                if _singleton_windows.get(key) is window:
                    del _singleton_windows[key]

    window.events.closed += _unregister


def push_usage_update(usage: UsageData) -> None:
    """main.py가 백그라운드에서 사용량을 새로 가져오는 데 성공할 때마다
    호출한다. 이미 열려있는 사용량 팝업이 있으면 그 자리에서 바로 반영해서,
    사용자가 직접 새로고침 버튼을 눌러야만 최신 값이 보이는 상황을 막는다."""
    with _singleton_dict_lock:
        window = _singleton_windows.get("usage")
    if window is None:
        return
    lang = Config.load().language
    data = json.dumps(_usage_to_dict(usage, lang))
    try:
        window.evaluate_js(f"window.__pushUsage && window.__pushUsage({data})")
    except Exception:
        pass


def show_usage_popup(usage: UsageData, on_refresh: Optional[Callable[[], Optional[UsageData]]] = None) -> None:
    """on_refresh는 있는 경우, 새로고침 버튼을 눌렀을 때 인자 없이 호출되며
    새 데이터가 준비될 때까지 그 안에서 멈춰 있어도(block) 된다. 새로운
    UsageData를 반환하거나(실패 시 None) -- 여기서 멈춰 있어도 괜찮은 이유는
    pywebview가 js_api 호출을 자기 UI 스레드가 아닌 별도 스레드에서
    실행해주기 때문이다."""

    def create() -> webview.Window:
        box: list = []
        # 예전 높이 400은 카드 두 개(각각 96px 링 + 18px 여백)가 실제로
        # 필요로 하는 것보다 눈에 띄게 더 많은 빈 공간을 남겼다 -- usage.html의
        # <style>에서 링/여백을 줄인 것에 맞춰 이 높이도 함께 줄였다.
        width, height = 360, 340
        size = [width, height]
        config = Config.load()
        opacity = config.usage_popup_opacity
        lang = config.language
        opacity_fn = _box_opacity_setter(box)
        x, y, grow_upward = _position_near_tray(width, height)
        api = _UsageApi(
            usage,
            on_refresh,
            _box_closer(box),
            _box_resizer(box, size),
            _box_vertical_resizer(box, size, grow_upward),
            opacity,
            opacity_fn,
            lang,
        )
        window = _new_window(i18n.t("tray.tooltip_base", lang), "usage.html", api, width, height, (x, y))
        box.append(window)
        _apply_initial_opacity(window, opacity)
        return window

    _focus_or_create("usage", create)


class _SettingsApi:
    def __init__(
        self,
        config: Config,
        on_saved: Optional[Callable[[], None]],
        close_fn: Callable[[], None],
        resize_fn: Callable[[float, float], None],
    ):
        self._config = config
        self._on_saved = on_saved
        self._close_fn = close_fn
        self._resize_fn = resize_fn

    def get_initial_data(self) -> dict:
        return {
            "refresh_seconds": self._config.refresh_seconds,
            "tray_icon_style": self._config.tray_icon_style,
            "style_labels": i18n.tray_style_labels(self._config.language),
            "show_autostart": _IS_WINDOWS,
            "autostart_enabled": autostart.is_enabled() if _IS_WINDOWS else False,
            "language": self._config.language,
            "language_options": i18n.LANGUAGE_NAMES,
        }

    def save(self, payload: dict) -> None:
        try:
            self._config.refresh_seconds = max(5, int(payload.get("refresh_seconds", self._config.refresh_seconds)))
        except (TypeError, ValueError):
            pass
        self._config.tray_icon_style = payload.get("tray_icon_style") or DEFAULT_STYLE
        language = payload.get("language")
        if language in i18n.LANGUAGE_NAMES:
            self._config.language = language
        self._config.save()
        if _IS_WINDOWS:
            if payload.get("autostart"):
                autostart.enable()
            else:
                autostart.disable()
        if self._on_saved is not None:
            self._on_saved()

    def close(self) -> None:
        self._close_fn()

    def resize_by(self, dw: float, dh: float) -> None:
        self._resize_fn(dw, dh)


def show_settings_popup(on_saved: Optional[Callable[[], None]] = None) -> None:
    """on_saved는 있는 경우, 저장에 성공한 직후 호출된다 -- main.py가 다음
    예약된 갱신 시점까지 기다리지 않고 트레이 아이콘을 바로 새로고침할 수
    있게 해준다."""

    def create() -> webview.Window:
        config = Config.load()
        box: list = []
        # 언어 선택 카드가 생기기 전 높이(340x440)보다 90만큼 늘렸다 --
        # 새로 추가된 언어 카드가 body의 스크롤바 없이 바로 들어가도록 하기
        # 위해서다.
        width, height = 340, 530
        size = [width, height]
        api = _SettingsApi(config, on_saved, _box_closer(box), _box_resizer(box, size))
        window = _new_window(i18n.t("tray.settings", config.language), "settings.html", api, width, height, _position_centered(width, height))
        box.append(window)
        return window

    _focus_or_create("settings", create)


class _AccountApi:
    def __init__(
        self, email: Optional[str], is_logged_out: bool, on_switch: Callable, on_logout: Callable,
        close_fn: Callable[[], None], resize_fn: Callable[[float, float], None], lang: str,
    ):
        self._email = email
        self._is_logged_out = is_logged_out
        self._on_switch = on_switch
        self._on_logout = on_logout
        self._close_fn = close_fn
        self._resize_fn = resize_fn
        self._lang = lang

    def get_initial_data(self) -> dict:
        return {"email": self._email, "is_logged_out": self._is_logged_out, "language": self._lang}

    def switch_account(self) -> None:
        self._on_switch()

    def logout(self) -> None:
        self._on_logout()

    def close(self) -> None:
        self._close_fn()

    def resize_by(self, dw: float, dh: float) -> None:
        self._resize_fn(dw, dh)


def show_account_popup(email: Optional[str], is_logged_out: bool, on_switch: Callable, on_logout: Callable) -> None:
    """뭔가 되돌리기 어려운 동작을 하기 전에, 지금 어느 계정이 활성 상태인지
    먼저 확인시켜준다 -- 아래 두 버튼 모두 저장된 세션을 지워버리기 때문에,
    메뉴 클릭에 곧바로 반응해서 실행하는 대신 이 화면을 먼저 보여주면
    실수로 누른 클릭 한 번 때문에 아무 경고도 없이 강제 로그아웃되는 상황을
    막을 수 있다."""

    def create() -> webview.Window:
        box: list = []
        width, height = 320, 300
        size = [width, height]
        lang = Config.load().language
        api = _AccountApi(email, is_logged_out, on_switch, on_logout, _box_closer(box), _box_resizer(box, size), lang)
        window = _new_window(i18n.t("tray.account", lang), "account.html", api, width, height, _position_centered(width, height))
        box.append(window)
        return window

    _focus_or_create("account", create)


class _SplashApi:
    """스플래시 화면이 Python 쪽으로 다시 호출할 일은 어떤 언어로 보여줄지
    말고는 없다 -- 이 값은 창을 만드는 시점에 미리 받아서 갖고 있는다.
    이 창은 몇 초밖에 살지 않으므로, 다른 팝업들과 달리 도중에 Config를
    다시 확인할 필요가 없다."""

    def __init__(self, lang: str):
        self._lang = lang

    def get_language(self) -> dict:
        return {"language": self._lang}


def show_splash(lang: str) -> webview.Window:
    """시간이 걸릴 수 있는 로그인 확인과 첫 사용량 조회가 백그라운드 스레드에서
    끝나기도 전에, 시작하자마자 바로 보여준다 -- 이게 없으면 그 동안에는
    트레이 아이콘도 없고 화면에 뜬 창도 전혀 없어서, 앱이 조용히 실행에
    실패한 것처럼 보인다. 다시 열릴 일이 없으므로 싱글턴 창으로 등록하지
    않는다(_focus_or_create 참고) -- main.py가 필요한 참조를 직접 하나만
    들고 있다가, 시작 과정이 끝나면 스스로 닫는다."""
    width, height = 260, 220
    window = _new_window(
        "Claude Usage Widget", "splash.html", _SplashApi(lang), width, height, _position_centered(width, height)
    )
    return window


def close_splash(window: webview.Window) -> None:
    _safe_destroy(window)
