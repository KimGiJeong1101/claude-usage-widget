"""이 파일은 "자동 업데이트"의 실제 실행 담당이다.

전체 흐름을 2단계로 나눠서 생각하면 쉽다:
- 1단계(usage_widget/update_check.py): "새 버전이 나왔는지"만 확인하고 알려줌.
  실제로 뭔가를 바꾸거나 다운로드하진 않음.
- 2단계(이 파일): 사용자가 트레이 메뉴에서 "지금 업데이트"를 눌렀을 때, 실제로
  새 버전을 받아서 지금 실행 중인 exe 파일을 바꿔치기하고 새 버전을 실행하는
  진짜 작업을 함.

지금은 Windows에서만 동작한다 (아래 can_self_update() 참고).

## 왜 이렇게 복잡하게 짰나 -- 세 번의 시행착오 기록

"실행 중인 내 exe 파일을 새 파일로 바꾸고 재시작하기"는 얼핏 간단해 보이지만,
실제로 세 번이나 다른 이유로 실패해서 그때마다 원인을 찾아 고친 역사가 있다.
나중에 이 코드를 다시 볼 사람(미래의 나 포함)이 "왜 굳이 이렇게 복잡하게
했지?"라고 의아해하지 않도록 그 과정을 남겨둔다.

**시도 1 (실패): 내 프로세스가 직접 파일을 바꾸고 재시작**

처음엔 이렇게 했다: 지금 실행 중인 exe 파일 이름을 다른 이름으로 바꾸고(Windows는
"실행 중인 파일"이어도 이름을 바꾸는 건 허용한다 -- 지우거나 덮어쓰는 것만 안
될 뿐), 원래 이름 자리에 새로 받은 파일을 쓴 다음, 그 새 파일을 "내 프로세스의
자식 프로세스"로 바로 실행시켰다.

파일을 자유롭게 만질 수 있다는 점에서는 문제가 없었지만, 그렇게 실행한 새
exe가 시작하자마자 이런 에러를 내며 죽었다:
`"Security validation failure: parent process has different executable!"`

원인: PyInstaller(파이썬 코드를 하나의 .exe로 뭉쳐주는 도구) 6.9 버전부터,
onefile(파일 하나짜리) exe에는 "부트로더(bootloader)"라는 작은 보안 장치가
들어간다. 이 부트로더는 "혹시 내가 나 자신과 똑같은 프로그램에 의해 실행된
것처럼 보이면, 진짜로 그 부모 프로세스가 지금도 그 파일 그대로를 실행하고
있는 게 맞는지" 확인한다. 그런데 우리 경우엔 부모(이전 버전 exe)가 이미 이름이
바뀌고 내용도 다른 파일로 덮어써진 뒤였으니, 이 확인 과정에서 "수상하다"고
판단해서 막아버린 것이다.

**시도 2: cmd.exe를 대신 내세우기 (부분 성공)**

그래서 방식을 바꿨다: 내 프로세스가 직접 파일을 바꾸는 대신, cmd.exe(윈도우
기본 명령 프롬프트)로 아주 짧은 배치 스크립트 하나를 "완전히 독립된(부모와
상관없이 계속 실행되는, detached)" 프로세스로 하나 띄운다. 이 스크립트가:
(1) 지금 이 프로세스가 완전히 종료될 때까지 기다렸다가,
(2) 그제서야 새로 받아둔 파일을 원래 자리로 옮기고,
(3) 그 새 exe를 실행한다.

이렇게 하면 "나와 똑같은 프로그램이 나를 실행시켰다"는 조건 자체가 성립하지
않는다 -- 새로 실행된 exe 입장에서 부모는 cmd.exe지, 예전 버전의 이 앱이
아니기 때문이다. 게다가 프로세스가 완전히 종료된 뒤에만 파일을 건드리니,
"실행 중인 파일이라 지울 수 없다"는 문제 자체가 아예 없어져서, 예전처럼
파일 이름을 바꿔치기하는 편법도 더 이상 필요 없어졌다.

하지만 여기서 2가지 문제가 더 발견됐다:

- **문제 A**: 그런데도 새 exe가 여전히 "같은" 에러로 죽었다. 원인은
  환경변수(environment variable, 프로세스가 실행될 때 함께 물려받는 설정값들)
  때문이었다 -- cmd.exe도, 그리고 cmd.exe가 실행시키는 프로그램도, 기본적으로
  "자신을 실행시킨 프로세스"의 환경변수를 그대로 물려받는데, 그 안에는
  PyInstaller 부트로더가 남겨둔 "누가 나를 실행시켰는지"에 대한 내부 기록도
  포함돼 있었다. 그래서 새 exe도 여전히 (이미 종료된) 예전 프로세스를 부모로
  착각한 것이다. PyInstaller 공식 문서에 정확히 이 상황("나를 실행시킨
  프로세스보다 더 오래 살아야 하는 자식 프로세스를 띄울 때")에 대한 해결책이
  있었다: 자식 프로세스의 환경변수에 `PYINSTALLER_RESET_ENVIRONMENT=1`을
  심어주면, 그 부트로더는 예전 기록을 무시하고 "새로 시작하는 프로그램"으로
  취급한다.
- **문제 B**: 위 문제를 고치고 나니, 이번엔 다른 에러가 떴다:
  `"failed to obtain executable path for parent process!"`. 원인은 타이밍
  문제였다 -- 배치 스크립트가 새 exe를 `start`로 띄우자마자 곧바로 자기
  자신을 삭제(`del`)하고 끝나버렸는데, 그러면 cmd.exe(새 exe 입장에서는 진짜
  부모 프로세스)가 수백 밀리초 안에 사라져버린다. 새로 뜬 exe의 부트로더가
  "내 부모 프로세스가 실행 중인 파일 경로가 뭐지?"를 물어보려는 바로 그
  시점에 부모가 이미 없어져 있으면, 이 조회 자체가 실패한다. 그래서 `start`
  직후에 `timeout`으로 몇 초 대기 시간을 넣어서, cmd.exe가 그 조회가 끝날
  때까지는 살아있도록 했다.

## macOS는 아직 지원 안 함

macOS의 `.app`은 파일 하나가 아니라 폴더(디렉터리) 형태라서, 위와 같은
"파일 하나를 통째로 바꿔치기" 방식이 그대로 통하지 않는다. 그래서 macOS는
아직 이 자동 업데이트 기능이 없고, 다운로드 페이지로 안내만 한다.

## 아직 안 고친 한계점

이 코드는 지금 실행 중인 exe가 "그냥 압축 풀어서 쓰는 포터블 버전"인지,
아니면 "WiX로 만든 설치 프로그램(MSI)으로 정식 설치된 버전"인지 구분하지
않는다. MSI로 설치된 파일을 이런 식으로 몰래 바꿔치기하면, 나중에 Windows
설치 관리자가 "복구(repair)" 기능을 실행할 때 원래 설치됐던 (구)버전으로
되돌려버릴 수 있다. 이 문제는 아직 해결하지 않았다 -- 자세한 내용은
notes(private) 저장소의 기획 메모 참고.
"""

import io
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import httpx

_ZIP_URL = "https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-win.zip"

# 아래 두 문구는 사람이 읽으라고 쓴 한국어 메시지가 아니라, "어떤 종류의 에러인지"
# 코드끼리 구분하기 위한 식별 문자열이다. main.py가 이 정확한 문자열을 보고
# i18n.py의 번역 테이블에서 사용자 언어에 맞는 문구를 찾아 보여준다. 만약 여기서
# 그냥 한국어 문장을 직접 넣으면, 사용자가 설정을 영어/일본어/중국어로 바꿔놔도
# 이 에러가 뜰 때만 한국어 문장이 섞여서 나오는 문제가 생긴다.
_ERROR_NOT_SUPPORTED = "self-update is not supported on this build/platform"
_ERROR_NO_EXE_IN_ZIP = "no .exe found in the release zip"

# 이 배치 스크립트(윈도우 명령어를 순서대로 적어둔 텍스트 파일)가 하는 일:
# 지금 이 앱(곧 스스로 종료할 예정)이 진짜로 완전히 종료될 때까지 기다렸다가,
# 그제서야 미리 받아둔 새 파일을 원래 자리로 옮기고 실행한다.
#
# 인코딩은 UTF-8이 아니라 시스템 기본 코드페이지(ANSI, apply_update() 참고)로
# 저장한다 -- cmd.exe는 배치 파일을 읽을 때 기본적으로 시스템 코드페이지를
# 쓰는데, 파일 경로 안에 한글(사용자 이름이나 폴더 이름 등)이 섞여 있는 경우가
# 실제로 많아서 이 부분을 맞춰줘야 한다.
#
# "30번까지만 확인"이라고 정해둔 건, 혹시라도 이 프로세스가 무슨 이유로든 절대
# 안 꺼지는 상황을 대비한 안전장치일 뿐이다. 평소엔 "종료" 버튼을 눌렀을 때처럼
# (icon.stop() + shutdown_gui()) 거의 즉시 꺼지니까, 실제로는 이 대기 루프를
# 한두 번만 돌고 바로 다음 단계로 넘어가는 게 정상이다.
_RELAUNCH_SCRIPT = """@echo off
setlocal
set "PID={pid}"
set "TARGET={target}"
set "STAGED={staged}"
set /a COUNT=0
:waitloop
tasklist /FI "PID eq %PID%" 2>NUL | findstr /C:"%PID%" >nul
if %errorlevel%==0 (
    set /a COUNT+=1
    if %COUNT% GEQ 30 goto proceed
    timeout /t 1 /nobreak >nul
    goto waitloop
)
:proceed
move /Y "%STAGED%" "%TARGET%" >nul
start "" "%TARGET%"
timeout /t 2 /nobreak >nul
del "%~f0"
"""


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def can_self_update() -> bool:
    return is_frozen() and sys.platform == "win32"


def _current_exe_path() -> Path:
    return Path(sys.executable).resolve()


def _staged_path_for(exe: Path) -> Path:
    """새로 받은 exe 파일을 임시로 저장해두는 경로를 계산한다. 재시작 도우미
    스크립트가 이 파일을 나중에 원래 자리로 옮긴다. 지금 실행 중인 exe와 절대
    같은 경로일 수 없다 -- 실행 중인 파일은 열려 있는 상태라 덮어쓸 수 없기
    때문이다."""
    return exe.with_name(f"{exe.stem}.new{exe.suffix}")


def _relaunch_script_path_for(exe: Path) -> Path:
    return exe.with_name("_update_relaunch.bat")


def cleanup_stale_update_files() -> None:
    """업데이트가 중간에 끊긴 경우(예: 새 파일을 임시로 저장해뒀는데 재시작
    도우미가 실제로 파일을 바꿔치기하기 전에 앱이 강제 종료된 경우) 남아있는
    찌꺼기 파일들을 지운다. 프로그램을 시작할 때 한 번 호출하도록 만든,
    "되면 좋고 안 돼도 그만"인 정리 작업이다 -- 여기서 실패해도 그냥 다음
    번에 다시 시도하면 되고, 프로그램이 실행되는 데는 지장이 없다.

    예전(v0.2.3 이전) 방식이 남기던 `X.exe.old`라는 이름의 찌꺼기 파일도
    같이 지운다 -- 그 옛날 버전은 재시작 중간에 실패하면 이 이름의 파일이
    남는 문제가 있었는데(자세한 사연은 apply_update()의 설명 참고), 그 버그를
    이미 겪었던 사람이 업데이트를 안 했다면 이 파일이 영원히 남아있게 된다.
    (빌드 시점에 이미 굳어진 옛날 코드는, 나중에 새로 생긴 파일 이름 규칙을
    알 방법이 없으니 이렇게 새 코드 쪽에서 챙겨줘야 한다.)"""
    if not is_frozen():
        return
    current = _current_exe_path()
    legacy_old = current.with_name(current.name + ".old")
    for path in (_staged_path_for(current), _relaunch_script_path_for(current), legacy_old):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def _download_new_exe() -> bytes:
    response = httpx.get(_ZIP_URL, timeout=60, follow_redirects=True)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".exe")]
        if not names:
            raise RuntimeError(_ERROR_NO_EXE_IN_ZIP)
        return zf.read(names[0])


def apply_update() -> None:
    """최신 Windows 빌드를 다운로드해서 지금 실행 중인 exe 옆에 임시로
    저장해두고, 그 파일을 실제로 바꿔치기하고 실행하는 일을 맡을 "도우미
    프로세스"를 하나 띄운다. 이 도우미는 지금 이 프로세스가 완전히 종료될
    때까지 기다렸다가 움직인다 (왜 굳이 도우미를 따로 두는지는 이 파일 맨
    위의 설명 참고).

    다운로드/저장 과정에서 뭔가 실패하면 그대로 예외를 던진다 -- 호출한
    쪽(main.py)이 이걸 받아서 사용자에게 알려줘야 한다. 사용자는 방금 버튼을
    눌러서 뭔가 일어나길 기대하고 있으니, 조용히 실패해서는 안 되기 때문이다.

    이 함수가 정상적으로 끝났다는 건 "도우미 프로세스를 띄우는 데 성공했다"는
    뜻이지, 업데이트가 끝났다는 뜻은 아니다 -- 이 함수를 호출한 쪽이 그 다음
    할 일은, 지금 이 프로세스를 실제로 종료시키는 것이다. 도우미는 정확히
    "이 프로세스(PID)가 사라지는 것"을 기다리고 있으므로, 이 프로세스가 안
    끝나면 도우미도 영원히 아무 일도 못 하고 기다리기만 한다."""
    if not can_self_update():
        raise RuntimeError(_ERROR_NOT_SUPPORTED)

    new_exe_bytes = _download_new_exe()

    current = _current_exe_path()
    staged = _staged_path_for(current)
    staged.write_bytes(new_exe_bytes)

    script_path = _relaunch_script_path_for(current)
    script = _RELAUNCH_SCRIPT.format(pid=os.getpid(), target=current, staged=staged)
    script_path.write_text(script, encoding="mbcs")

    # 환경변수(environment variable, 프로세스를 실행할 때 함께 넘겨주는
    # 설정값 모음)에 PYINSTALLER_RESET_ENVIRONMENT=1을 심어서 넘겨준다.
    # 이 값이 있으면, 그걸 물려받은 onefile 부트로더는 "나는 새로 시작하는
    # 독립적인 프로그램이다"라고 인식하고, 자신을 실행시킨 프로세스의 정보와
    # 비교/검증하려 들지 않는다 (이건 PyInstaller가 공식적으로 안내하는
    # "나를 실행시킨 프로세스보다 더 오래 살아야 하는 자식 프로세스를 띄울
    # 때"의 해결책이다). 이걸 안 심어주면, cmd.exe와 그게 실행시키는 exe는
    # 기본적으로 지금 이 프로세스의 환경변수를 그대로 물려받는데, 그 안에는
    # "누가 나를 실행시켰는지"에 대한 PyInstaller 내부 기록이 남아있어서
    # (곧 종료될) 지금 이 프로세스를 계속 부모로 착각한다. 그러면 새로 실행된
    # exe가 또다시 "부모 프로세스의 실행 파일이 다르다"는 그 보안 검증에
    # 걸려서, 이 도우미 스크립트를 만든 이유가 무색해진다.
    env = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
        env=env,
    )
