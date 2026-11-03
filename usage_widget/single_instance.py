"""이 앱이 실수로 여러 개 동시에 실행되는 것을 막는 파일.

이게 없으면, exe를 두 번 실행하면(습관적으로 다시 더블클릭하거나, 자동
시작과 수동 실행이 우연히 겹치거나 등) 서로 아무 관련 없는 두 개의
백그라운드 프로세스가 생겨버린다. 그러면 트레이 아이콘도 두 개가 뜨고,
각자 PyInstaller onefile 방식이 쓰는 임시 폴더(exe를 실행할 때마다
압축을 풀어두는 폴더)를 따로 만들고 지우다가 서로 부딪혀서 "임시 폴더를
지울 수 없습니다" 같은 경고가 뜨기도 한다 (특히 자동 업데이트로 재시작할
때 자주 보임).
"""

import errno
import socket
import sys
from typing import Optional

# 로컬(내 컴퓨터 안에서만 쓰는) 포트 번호 중 아무 의미 없이 하나 골라서
# 고정해둔 것 -- 다른 프로그램이 우연히 이 포트를 쓸 가능성이 낮은,
# 흔히 안 쓰는 대역에서 그냥 하나 정한 값이다.
_LOCK_PORT = 48273

# "Local\" 접두사 = 지금 로그인한 사용자 세션 안에서만 보이는 이름이다.
# 같은 PC의 다른 Windows 사용자는 각자 자기 위젯을 따로 실행할 수 있어야
# 하므로 "Global\"을 쓰지 않는다.
_MUTEX_NAME = "Local\\ClaudeUsageWidget-single-instance"
_ERROR_ALREADY_EXISTS = 183

# Windows의 소켓 오류는 errno 값이 WSA 계열 번호(10048)로 온다.
_ADDR_IN_USE_ERRNOS = {errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", 10048)}

_lock_socket: Optional[socket.socket] = None
_mutex_handle = None


def _acquire_windows_mutex() -> Optional[bool]:
    """Windows 네임드 뮤텍스로 확인한다. 이미 다른 인스턴스가 있으면
    False, 처음이면 True, 뮤텍스 자체를 못 만들면(아주 드문 경우) None을
    돌려줘서 소켓 방식만으로 판단하게 한다.

    예전에는 아래 소켓 방식만 썼는데, Hyper-V/WSL2/Docker가 깔린 PC에서는
    Windows가 포트 대역을 통째로 예약해버리는 경우가 있다(재부팅할 때마다
    대역이 바뀜). 이 포트가 하필 그 대역에 들어가면 bind가 "이미 사용 중"이
    아니라 "권한 없음" 에러로 실패하는데, 그걸 "이미 실행 중"으로 착각해서
    앱이 한 번도 안 떠 있는데도 "이미 실행 중입니다"만 보여주고 꺼졌다.
    뮤텍스는 포트와 아무 상관이 없어서 이런 일이 없다. 프로세스가 죽으면
    OS가 핸들을 알아서 정리해주는 것도 소켓 방식과 같다."""
    import ctypes
    from ctypes import wintypes

    global _mutex_handle
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        return None
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    # 소켓과 같은 이유로, 핸들을 닫지 않고 전역 변수에 붙잡아둔다.
    _mutex_handle = handle
    return True


def _acquire_port() -> bool:
    """내 컴퓨터 안에서만 쓰는 포트(TCP 소켓) 하나를 점유해보는 방식이다.
    Windows/macOS/Linux 어디서든 똑같이 동작하고, 프로세스가 정상 종료되든
    강제로 죽든 OS가 알아서 그 포트를 다시 풀어주기 때문에 따로 뒷정리를
    해줄 필요도 없다. Windows에서는 뮤텍스가 있지만 이것도 계속 잡아둔다 --
    뮤텍스가 생기기 전의 구버전은 이 포트만 보고 판단하기 때문에, 구버전과
    새 버전이 동시에 떠버리는 걸 막으려면 여기도 같이 잡고 있어야 한다.

    "이미 사용 중" 에러일 때만 False(다른 인스턴스가 있음)를 돌려준다. 그
    외의 bind 실패(예약된 포트 대역이라 "권한 없음" 등)는 다른 인스턴스가
    있다는 증거가 아니므로 True로 보고 그냥 실행을 계속한다 -- 그런 PC에서
    중복 실행 방지가 잠깐 안 되는 것보다, 앱이 아예 안 켜지는 게 훨씬
    나쁘다."""
    global _lock_socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", _LOCK_PORT))
    except OSError as exc:
        sock.close()
        return exc.errno not in _ADDR_IN_USE_ERRNOS
    # 이 소켓을 절대 닫지 않고 프로세스가 살아있는 내내 붙잡고 있는 것
    # 자체가 바로 "잠금(lock)"의 정체다. 함수가 끝나도 이 변수(전역 변수,
    # 모듈 전체에서 공유되는 변수)에 담아두는 이유는, 그렇게 안 하면
    # 파이썬이 "아무도 안 쓰는 값"이라고 판단해서 가비지 컬렉션(안 쓰는
    # 메모리를 자동으로 정리하는 기능) 때 이 소켓을 일찍 닫아버릴 수
    # 있기 때문이다.
    _lock_socket = sock
    return True


def acquire() -> bool:
    """이미 다른 인스턴스(같은 프로그램의 다른 실행 중인 복사본)가 실행
    중이면 False를 돌려준다."""
    if sys.platform == "win32" and _acquire_windows_mutex() is False:
        return False
    return _acquire_port()
