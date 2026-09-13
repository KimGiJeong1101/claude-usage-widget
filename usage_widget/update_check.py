"""GitHub Releases(깃허브에 올라온 릴리즈 목록)를 확인해서, 지금 실행 중인
버전보다 더 새로운 버전이 있는지 확인하는 파일.

별도의 "업데이트 서버"를 우리가 직접 만들 필요가 없다 -- 깃허브 자체가
제공하는 "가장 최근 릴리즈" API를 호출해서 버전 번호만 비교하면 끝이다.
그래서 이 파일이 하는 일은 그냥 주기적으로 인터넷에 물어보고(GET 요청)
숫자를 비교하는 것뿐이다.

여기서는 "새 버전이 있다"는 걸 확인하고 알려주기만 한다(트레이 알림 +
릴리즈 페이지로 이동하는 메뉴 항목). 실제로 다운로드해서 실행 중인
파일을 바꿔치기하는 건 이 파일이 아니라 self_update.py가 한다 -- 실행
중인 .exe 파일은 원래 함부로 덮어쓸 수 없는 등 훨씬 조심해서 다뤄야 할
게 많기 때문에 일부러 역할을 나눴다.
"""

import re
from typing import Optional

import httpx

from usage_widget import __version__

_REPO = "KimGiJeong1101/claude-usage-widget"
_API_URL = f"https://api.github.com/repos/{_REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{_REPO}/releases/latest"


def _parse_version(text: str) -> tuple:
    """예: "v1.2.3" 문자열을 (1, 2, 3)이라는 숫자 튜플로 바꿔준다. 이렇게
    숫자로 바꿔야 "1.10.0이 1.9.0보다 큰가?" 같은 비교를 문자열 순서가
    아니라 진짜 숫자 크기로 정확히 할 수 있다. 만약 태그 이름이 이 형식과
    안 맞으면(오타, 다른 규칙으로 붙인 태그 등) 빈 튜플 `()`을 돌려주는데,
    이러면 나중에 비교할 때 "업데이트 없음"으로 조용히 처리돼서, 이상한
    태그 하나 때문에 프로그램이 에러로 죽는 일은 없다."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", text.strip())
    if not match:
        return ()
    return tuple(int(part) for part in match.groups())


def check_for_update() -> Optional[str]:
    """가장 최근 릴리즈의 버전 문자열(예: "0.2.0")을 돌려준다 -- 단, 그
    버전이 지금 실행 중인 버전보다 진짜로 더 새로울 때만. 더 새롭지
    않으면 None을 돌려준다.

    확인 과정에서 뭔가 잘못돼도(인터넷 연결 안 됨, 깃허브 API 요청 횟수
    제한에 걸림, 예상과 다른 응답이 옴 등) 마찬가지로 None을 돌려준다.
    이렇게 해두면, 확인 과정 자체가 실패했을 때 "새 버전이 있다"고 잘못
    알려주는 일은 절대 없다."""
    try:
        response = httpx.get(_API_URL, timeout=10, follow_redirects=True)
        response.raise_for_status()
        tag = response.json()["tag_name"]
    except Exception:
        return None

    latest = _parse_version(tag)
    current = _parse_version(__version__)
    if not latest or not current or latest <= current:
        return None
    return tag.lstrip("v")
