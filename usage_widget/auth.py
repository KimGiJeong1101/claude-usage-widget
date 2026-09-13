"""처음 한 번만 하는 브라우저 로그인 담당 파일.

여기서 로그인에 성공하면 그 결과로 생긴 로그인 세션 쿠키를 파일로 저장해두고,
그 이후로는(fetcher.py에서) 무거운 브라우저를 매번 새로 띄우지 않고 가벼운
HTTP 요청만으로 사용량을 확인할 수 있게 된다."""

import time

from playwright.sync_api import sync_playwright

from usage_widget.paths import session_state_path

USAGE_URL = "https://claude.ai/settings/usage"
SESSION_COOKIE_NAME = "sessionKey"


def _has_session_cookie(context) -> bool:
    return any(c["name"] == SESSION_COOKIE_NAME for c in context.cookies())


def login_and_save_session() -> None:
    """진짜 브라우저 창을 하나 띄워서 사용자가 직접 claude.ai에 로그인하게
    하고, 로그인이 끝나면 그때 생긴 쿠키/localStorage를
    session_state_path()가 가리키는 파일에 저장한다."""
    with sync_playwright() as p:
        # Playwright에 기본으로 딸려오는 "Chrome for Testing" 브라우저가
        # 아니라, 사용자 컴퓨터에 실제로 설치돼있는 정품 Chrome을 띄운다.
        # 안 그러면 claude.ai의 "너 사람 맞아?" 확인(봇 차단)에 걸려서
        # 로그인 화면이 계속 반복된다.
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(viewport=None)
        page = context.new_page()
        page.goto(USAGE_URL)

        # claude.ai는 로그인이 성공하면 "sessionKey"라는 쿠키를 만들어준다.
        # "로그인 성공했는지"를 페이지 주소(URL)로 판단하지 않고 이 쿠키가
        # 생겼는지를 주기적으로 확인하는 이유: goto(USAGE_URL)로 이동한
        # 시점엔 로그인 여부와 상관없이 이미 주소는 USAGE_URL이라 URL만
        # 봐서는 구분이 안 되고, 로그인하는 동안 여러 중간 화면을 거쳐갈 수도
        # 있기 때문이다.
        try:
            while not _has_session_cookie(context):
                time.sleep(1)
        except Exception:
            return  # 로그인이 끝나기 전에 사용자가 브라우저 창을 닫아버린 경우

        # 로그인이 끝나면 Settings > Usage 화면이 아니라 다른 화면(예: 채팅
        # 첫 화면)에 있을 수도 있으니, 여기서 다시 한번 명시적으로 이동한다.
        # goto()는 페이지의 "load"(다 불러왔다) 이벤트까지만 기다리는데,
        # claude.ai는 웹소켓이나 폴링 같은 백그라운드 통신을 끊임없이 계속
        # 하기 때문에, 그보다 더 엄격한 "networkidle"(네트워크가 완전히
        # 조용해질 때까지)을 기다리면 그냥 시간 초과로 실패한다.
        page.goto(USAGE_URL)

        context.storage_state(path=str(session_state_path()))
        browser.close()


def has_saved_session() -> bool:
    return session_state_path().exists()
