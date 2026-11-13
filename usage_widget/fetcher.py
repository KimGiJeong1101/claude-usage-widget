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
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from playwright.sync_api import sync_playwright

from usage_widget.paths import session_state_path

API_BASE = "https://claude.ai/api/organizations"
BOOTSTRAP_ENDPOINT = "https://claude.ai/edge-api/bootstrap?statsig_hashing_algorithm=djb2&growthbook_format=sdk"

# 이 파일의 두 함수(fetch_usage/fetch_account_info)는 호출될 때마다 headless
# Chrome을 매번 새로 하나씩 띄운다. 그런데 이 앱은 백그라운드 자동 갱신
# 스레드(main.py의 _refresh_loop, 기본 60초 주기)와 사용자가 팝업에서
# 직접 누르는 수동 새로고침이 서로 다른 스레드에서 언제든 동시에 실행될 수
# 있다 -- 타이밍이 겹치면 헤드리스 Chrome 프로세스가 한 번에 2개씩 뜨는
# 셈이다. 사양이 넉넉한 PC에서는 별문제 없이 둘 다 제시간에 끝나지만,
# CPU/메모리가 빠듯한 PC에서는 이 순간 리소스 경쟁 때문에 둘 중 하나(또는
# 둘 다)가 Playwright의 기본 타임아웃(30초)을 넘겨버려 "새로고침이 이유
# 없이 가끔 실패하는" 것처럼 보이는 원인이 된다.
#
# auth.py의 login_and_save_session()(로그인용 화면이 보이는 Chrome)도 이
# 락을 같이 쓴다 -- 그래야 "세션이 만료돼서 백그라운드 스레드가 재로그인
# 창을 띄우려는 순간, 하필 사용자가 수동 새로고침을 눌러서 재로그인 창이
# 하나 더 뜨는" 것 같은 경쟁도 막을 수 있다. 이름 앞에 밑줄(_)이 없는 건
# 그래서다 -- 이 파일 밖(auth.py)에서도 가져다 쓰는 걸 전제로 한 이름이다.
# 이 락으로 headless/화면 있는 Chrome 실행이 절대 동시에 겹치지 않고 항상
# 순서대로만 실행되게 막는다.
browser_launch_lock = threading.Lock()


class SessionExpiredError(Exception):
    """저장해둔 로그인 쿠키가 더 이상 안 먹혀서, 다시 로그인해야 할 때
    발생시키는(raise) 예외."""


# 이 상태 코드일 때만 "세션이 만료됐다"(= 다시 로그인해야 한다)고 판단한다.
# 예전에는 200이 아닌 응답을 전부 세션 만료로 취급했는데, 그러면 claude.ai
# 서버가 잠깐 장애(5xx)가 나거나 요청 횟수 제한(429)에 걸리기만 해도 멀쩡한
# 세션을 두고 Chrome 로그인 창이 불쑥 떠버렸다. 그런 일시적인 오류는 그냥
# "이번 갱신 실패"로 처리하고 다음 주기에 다시 시도하면 된다.
_SESSION_EXPIRED_STATUSES = (401, 403)


def _check_status(response, what: str) -> None:
    if response.status == 200:
        return
    message = f"{what} returned {response.status}"
    if response.status in _SESSION_EXPIRED_STATUSES:
        raise SessionExpiredError(message)
    raise RuntimeError(message)


@dataclass
class LimitInfo:
    """사용량 한도 하나(예: 5시간 세션, 주간 전체, 특정 모델 전용 주간 한도).

    kind는 API가 주는 종류 문자열 그대로다 -- 지금 확인된 값은 "session",
    "weekly_all", "weekly_scoped"(특정 모델 전용) 세 가지지만, 처음 보는
    값이 와도 버리지 않고 그대로 들고 있다가 화면에서 "기타 한도"로
    보여준다. model은 모델 전용 한도일 때 그 모델의 표시 이름(예: "Fable").
    is_active는 API가 "지금 적용 중인 한도"로 표시해준 것이다."""

    kind: str
    percent: int
    resets_at: Optional[datetime]
    model: Optional[str] = None
    is_active: bool = False


@dataclass
class AccountInfo:
    """계정 팝업에 보여줄 신원 정보. email만 필수로 보장된 값이고, name/
    organization은 계정 설정에 따라 없을 수도 있어서(예: 소속 조직 없이
    혼자 쓰는 개인 워크스페이스) 둘 다 Optional로 다룬다."""

    email: str
    name: Optional[str] = None
    organization: Optional[str] = None


@dataclass
class UsageData:
    """session_percent/week_percent는 트레이 아이콘(5시간 세션, 이중 막대의
    주간)이 쓰는 대표값이고, 팝업은 limits 목록을 있는 그대로 전부 그린다."""

    session_percent: int
    week_percent: int
    limits: List[LimitInfo] = field(default_factory=list)
    # 이 데이터를 받아온 시각 -- 사용량 팝업 아래쪽의 "마지막 갱신: N분 전"에 쓴다.
    fetched_at: datetime = field(default_factory=datetime.now)


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

    with browser_launch_lock, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        try:
            context = browser.new_context(storage_state=str(session_state_path()))

            orgs_response = context.request.get(API_BASE)
            _check_status(orgs_response, "organizations list")
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
            _check_status(usage_response, "usage endpoint")
            data = usage_response.json()
        finally:
            browser.close()

    # resets_at이 null로 오는 경우(섹션 11.1)와 같은 이유로, 구간 자체
    # ("five_hour"/"seven_day")나 utilization 값이 통째로 null로 올 수도
    # 있다고 보고 방어한다 -- 이걸 안 하면 TypeError가 나는데, 하필 시작
    # 시점의 첫 조회에서 나면 앱이 아예 실행되지 않는다.
    five_hour = data.get("five_hour") or {}
    seven_day = data.get("seven_day") or {}
    session_percent = round(five_hour.get("utilization") or 0)
    week_percent = round(seven_day.get("utilization") or 0)

    limits = _parse_limits(data.get("limits"))
    if not limits:
        # "limits" 목록이 없는 응답(예전 형식이거나 일부 요금제)이면, 원래
        # 보여주던 세션/주간 두 개만으로 대신 채운다.
        limits = [
            LimitInfo("session", session_percent, _parse_reset_at(five_hour.get("resets_at"))),
            LimitInfo("weekly_all", week_percent, _parse_reset_at(seven_day.get("resets_at"))),
        ]
    return UsageData(session_percent=session_percent, week_percent=week_percent, limits=limits)


def _parse_limits(raw) -> List[LimitInfo]:
    """API 응답의 "limits" 목록을 읽는다. 이 목록은 계정/요금제에 따라 개수가
    다르고(예: 특정 모델 전용 주간 한도가 붙는 계정이 있음), Anthropic이
    언제든 새 종류를 추가할 수 있어서, 고정된 몇 개만 골라 읽지 않고 들어온
    걸 전부 그대로 담는다. 항목 하나가 이상한 모양이어도 그 항목만 건너뛴다
    -- 그 하나 때문에 사용량 조회 전체가 실패하면 안 된다."""
    if not isinstance(raw, list):
        return []
    limits = []
    for item in raw:
        try:
            scope = item.get("scope") or {}
            model = (scope.get("model") or {}).get("display_name")
            limits.append(
                LimitInfo(
                    kind=str(item.get("kind") or ""),
                    percent=round(item.get("percent") or 0),
                    resets_at=_parse_reset_at(item.get("resets_at")),
                    model=model,
                    is_active=bool(item.get("is_active")),
                )
            )
        except (AttributeError, TypeError, ValueError):
            continue
    return limits


def fetch_account_info() -> AccountInfo:
    """claude.ai 웹앱이 맨 처음 로딩될 때 자기가 직접 호출하는 API 주소다
    (claude.ai 자체 코드 안에서 apiPrefix + "/bootstrap"라는 이름으로
    쓰이는 걸 확인해서 그대로 가져다 씀). 이 주소를 호출하면 계정 정보를
    이것저것 돌려주는데, 그 안에 지금 로그인된 세션이 누구 계정인지(이름,
    이메일, 소속 조직)가 들어있어서, "계정" 팝업에서 현재 로그인된 사람이
    누구인지 보여줄 때 이 값들을 쓴다.

    응답 안에는 이 밖에도 feature flag 같은 내부용 값들이 잔뜩 들어있는데,
    그런 건 Anthropic이 예고 없이 수시로 바꿀 수 있는 값들이라 믿고 화면에
    보여줄 만한 게 못 된다. 그래서 그런대로 안정적으로 보이는 이름/이메일/
    소속 조직 이름, 이 세 개만 꺼내 쓴다."""
    if not session_state_path().exists():
        raise SessionExpiredError("no saved session")

    with browser_launch_lock, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        try:
            context = browser.new_context(storage_state=str(session_state_path()))
            response = context.request.get(BOOTSTRAP_ENDPOINT)
            _check_status(response, "bootstrap endpoint")
            data = response.json()
        finally:
            browser.close()

    account = data["account"]
    # 첫 번째로 속한 조직만 쓴다 -- fetch_usage()가 조직을 고를 때와 같은
    # 이유로, 여러 조직에 속한 계정을 제대로 가려낼 방법이 없어서 그냥
    # 첫 번째 것으로 단순하게 처리해둔다.
    memberships = account.get("memberships") or []
    organization = (memberships[0].get("organization") or {}).get("name") if memberships else None
    return AccountInfo(
        email=account["email_address"],
        name=account.get("full_name") or account.get("display_name") or None,
        organization=organization,
    )


def fetch_usage_mock() -> UsageData:
    """로그인 세션이나 인터넷 연결이 없어도 트레이 아이콘/팝업 화면을
    개발/테스트해볼 수 있도록, 진짜 데이터 대신 가짜로 만들어둔 데이터."""
    from datetime import timedelta

    now = datetime.now()
    return UsageData(
        session_percent=42,
        week_percent=67,
        limits=[
            LimitInfo("session", 42, now + timedelta(hours=2, minutes=15)),
            LimitInfo("weekly_all", 67, now + timedelta(days=3, hours=4), is_active=True),
            LimitInfo("weekly_scoped", 85, now + timedelta(days=3, hours=4), model="Fable"),
        ],
    )
