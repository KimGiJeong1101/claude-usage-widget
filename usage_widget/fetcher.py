"""저장해둔 로그인 세션 쿠키를 이용해서, 주기적으로 사용량 데이터를 가져오는
파일.

claude.ai는 Cloudflare(웹사이트를 봇으로부터 보호해주는 서비스)의 봇 차단
기능이 걸려 있어서, 일반적인 HTTP 요청 도구(httpx 등)로는 유효한 로그인
쿠키를 갖고 있어도 그냥 다 막힌다 -- 진짜 브라우저의 네트워크 통신 방식을
그대로 쓰는 요청만 통과된다. Playwright(브라우저 자동화 도구)의 headless
(화면을 안 띄우는) context.request 기능을 쓰면, 페이지를 실제로 화면에
그리거나 웹사이트의 자바스크립트 코드를 실행하지 않고도 이 방식으로 요청을
보낼 수 있어서, 페이지를 통째로 여는 것보다 훨씬 가볍게 Cloudflare를
통과할 수 있다.
"""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from playwright.sync_api import sync_playwright

from usage_widget.paths import session_state_path

API_BASE = "https://claude.ai/api/organizations"
BOOTSTRAP_ENDPOINT = "https://claude.ai/edge-api/bootstrap?statsig_hashing_algorithm=djb2&growthbook_format=sdk"

# 이 파일의 두 함수(fetch_usage/fetch_account_email)는 호출될 때마다 headless
# Chrome을 매번 새로 하나씩 띄운다. 그런데 이 앱은 백그라운드 자동 갱신
# 스레드(main.py의 _refresh_loop, 기본 60초 주기)와 사용자가 팝업에서
# 직접 누르는 수동 새로고침이 서로 다른 스레드에서 언제든 동시에 실행될 수
# 있다 -- 타이밍이 겹치면 헤드리스 Chrome 프로세스가 한 번에 2개씩 뜨는
# 셈이다. 사양이 넉넉한 PC에서는 별문제 없이 둘 다 제시간에 끝나지만,
# CPU/메모리가 빠듯한 PC에서는 이 순간 리소스 경쟁 때문에 둘 중 하나(또는
# 둘 다)가 Playwright의 기본 타임아웃(30초)을 넘겨버려 "새로고침이 이유
# 없이 가끔 실패하는" 것처럼 보이는 원인이 된다. 이 락으로 두 headless
# Chrome 실행이 절대 동시에 겹치지 않고 항상 순서대로만 실행되게 막는다.
_fetch_lock = threading.Lock()


class SessionExpiredError(Exception):
    """저장해둔 로그인 쿠키가 더 이상 안 먹혀서, 다시 로그인해야 할 때
    발생시키는(raise) 예외."""


@dataclass
class UsageData:
    session_percent: int
    week_percent: int
    session_reset_at: Optional[datetime]
    week_reset_at: Optional[datetime]


def _parse_reset_at(iso_string: Optional[str]) -> Optional[datetime]:
    """API가 내려주는 시각 문자열(UTC 기준, 예: "...+00:00" 형식)을,
    이 프로젝트 다른 곳에서 쓰는 "시간대 정보 없는" datetime 형태로
    바꿔준다(datetime.now()도 마찬가지로 시간대 정보가 없어서, 형식을
    맞춰야 나중에 두 값을 서로 뺄셈 등으로 비교할 수 있다).

    "아직 그 구간(예: 5시간 세션)에서 한 번도 사용한 적이 없는 상태"라면
    API가 이 시각 값 자체를 null(없음)로 내려준다 -- 이럴 땐 "리셋까지
    앞으로 얼마 남았다"고 억지로 계산하지 않고, 그냥 None을 그대로
    돌려준다."""
    if iso_string is None:
        return None
    return datetime.fromisoformat(iso_string).astimezone().replace(tzinfo=None)


def fetch_usage() -> UsageData:
    if not session_state_path().exists():
        raise SessionExpiredError("no saved session")

    with _fetch_lock, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        try:
            context = browser.new_context(storage_state=str(session_state_path()))

            orgs_response = context.request.get(API_BASE)
            if orgs_response.status != 200:
                raise SessionExpiredError(
                    f"organizations list returned {orgs_response.status}"
                )
            organizations = orgs_response.json()
            if not organizations:
                raise SessionExpiredError("no organizations returned for this account")
            # 알려진 한계점: 만약 어떤 계정이 여러 개의 Claude 조직(organization,
            # 예를 들면 개인용 워크스페이스 하나 + 팀 워크스페이스 하나처럼)에
            # 동시에 속해 있다면, 여기서는 그냥 목록에서 첫 번째로 나오는
            # 조직을 무조건 선택한다. 그게 사용자가 진짜로 확인하고 싶은
            # 조직이 맞는지는 알 방법이 없다. 아직 고치지 않은 이유: 실제로
            # 이런 "여러 조직에 속한 계정"을 가진 사람이 나타난 적이 없어서,
            # "어떤 조직을 골라야 하는지" 알아서 판단하는 로직을 만들어봤자
            # 검증할 방법이 없다. 섣불리 추측하는 로직을 넣었다가 조용히
            # 엉뚱한 조직의 사용량을 보여주는 것보다는, 지금처럼 단순하고
            # 문서로 한계를 남겨두는 편이 더 안전하다고 판단했다.
            org_id = organizations[0]["uuid"]

            usage_response = context.request.get(f"{API_BASE}/{org_id}/usage")
            if usage_response.status != 200:
                raise SessionExpiredError(
                    f"usage endpoint returned {usage_response.status}"
                )
            data = usage_response.json()
        finally:
            browser.close()

    return UsageData(
        session_percent=round(data["five_hour"]["utilization"]),
        week_percent=round(data["seven_day"]["utilization"]),
        session_reset_at=_parse_reset_at(data["five_hour"]["resets_at"]),
        week_reset_at=_parse_reset_at(data["seven_day"]["resets_at"]),
    )


def fetch_account_email() -> str:
    """claude.ai 웹앱이 맨 처음 로딩될 때 자기가 직접 호출하는 API 주소다
    (claude.ai 자체 코드 안에서 apiPrefix + "/bootstrap"라는 이름으로
    쓰이는 걸 확인해서 그대로 가져다 씀). 이 주소를 호출하면 계정 정보를
    이것저것 돌려주는데, 그 안에 지금 로그인된 세션이 누구 계정인지 이메일
    주소가 들어있어서, "계정" 팝업에서 현재 로그인된 사람이 누구인지 보여줄
    때 이 값을 쓴다."""
    if not session_state_path().exists():
        raise SessionExpiredError("no saved session")

    with _fetch_lock, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        try:
            context = browser.new_context(storage_state=str(session_state_path()))
            response = context.request.get(BOOTSTRAP_ENDPOINT)
            if response.status != 200:
                raise SessionExpiredError(f"bootstrap endpoint returned {response.status}")
            data = response.json()
        finally:
            browser.close()

    return data["account"]["email_address"]


def fetch_usage_mock() -> UsageData:
    """로그인 세션이나 인터넷 연결이 없어도 트레이 아이콘/팝업 화면을
    개발/테스트해볼 수 있도록, 진짜 데이터 대신 가짜로 만들어둔 데이터."""
    from datetime import timedelta

    now = datetime.now()
    return UsageData(
        session_percent=42,
        week_percent=67,
        session_reset_at=now + timedelta(hours=2, minutes=15),
        week_reset_at=now + timedelta(days=3, hours=4),
    )
