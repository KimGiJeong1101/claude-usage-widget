# Claude Usage Widget

claude.ai의 사용량 한도(5시간 세션, 주간)를 트레이 아이콘과 팝업으로 보여주는
Windows·macOS 데스크톱 위젯. 혼자 개발하는 공개 저장소다.
사람용 개발 안내는 DEVELOPMENT.md, 사용자 안내는 README.md(영문 README.en.md)에 있다.

## 기술 스택
- Python 3.10 이상 (CI·릴리즈는 3.12). 버전은 usage_widget/__init__.py의 `__version__`
- pystray (트레이 아이콘), Pillow (아이콘 그리기), pywebview (팝업 창, 화면은 HTML/CSS/JS)
- Playwright + 설치된 Google Chrome (`channel="chrome"`) — 로그인과 사용량 조회.
  번들 Chromium은 Cloudflare 봇 차단에 걸린다.
- httpx (GitHub 릴리즈 확인), platformdirs (사용자 데이터 폴더)
- 패키징: PyInstaller(단일 exe/app), WiX v5(MSI), macOS는 CI에서 .dmg

## 명령
- 설치: `pip install -e ".[test]"` (빌드까지 하려면 `.[build]`), `playwright install chromium`
- 실행: `python -m usage_widget.main`
- 테스트: `pytest tests/ -v` (Chrome·로그인·인터넷 없이 가짜 객체로 수 초 안에 끝남)
- 아이콘 다시 만들기: `python scripts/generate_app_icon.py`
- 빌드·릴리즈: `v*` 태그를 push하면 .github/workflows/release.yml이 Windows·macOS 빌드를
  만들어 GitHub Release에 올린다. 로컬 빌드 명령도 그 파일을 기준으로 한다.

## 폴더 구조
| 경로 | 무엇 | 왜 있나 |
|---|---|---|
| usage_widget/ | 앱 본체 | main.py가 진입점이자 스레드 조율 담당 |
| usage_widget/assets/web/ | 팝업 화면(HTML/CSS/JS) | webui.py가 pywebview로 띄우고 js_api로 연결 |
| usage_widget/assets/fonts/ | Pretendard 폰트 | 팝업 화면(common.css)과 트레이 아이콘 글자에 씀 |
| tests/ | pytest | 동시성·락·설정 저장처럼 눈으로 확인하기 어려운 로직의 회귀 방지 |
| scripts/ | 수동 실행 스크립트 | 앱 아이콘 생성 |
| installer/ | WiX 설정, 아이콘 | MSI 빌드용 |
| run.py | PyInstaller 진입점 | 패키지 밖에 둬야 빌드한 상태에서도 패키지를 import할 수 있음 |
| notes/ | 기획 메모 | 별도의 비공개 git 저장소. 바깥 저장소는 .gitignore로 무시 |

## 용어표
| 한글 | 코드에서 쓰는 단어 | 메모 |
|---|---|---|
| 사용량 | usage | UsageData, fetch_usage |
| 한도 | limit | LimitInfo. 종류는 kind |
| 5시간 세션 한도 | session (kind 값) | 아래 "로그인 세션"과 다른 개념 |
| 주간 한도 | weekly_all / weekly_scoped | scoped는 특정 모델 전용 |
| 리셋 시각 | resets_at, reset_at | 두 표기가 섞여 있음 |
| 로그인 세션 | session_state, sessionKey | 쿠키 파일. SessionExpiredError |
| 재로그인 | relogin | |
| 갱신 / 새로고침 | refresh | 자동 _refresh_loop, 수동 _manual_refresh |
| 한도 알림 | limit alert | 80·90% 기준 |
| 팝업 | popup | 사용량·설정·계정·스플래시 |
| 트레이 아이콘 스타일 | tray_icon_style | donut, battery, bar, big_number, dual_bar |
| 투명도 | opacity | 사용량 팝업만 |
| 업데이트 확인 / 자동 업데이트 | update_check / self_update | 확인만 하는 쪽과 실제 교체하는 쪽을 나눔 |

## 하지 말아야 할 것
- 화면 문구를 추가하면 usage_widget/i18n.py와 assets/web/i18n.js 중 해당하는 쪽에 넣는다.
  둘은 따로 관리되는 번역표다.
- 릴리즈 파일 이름 ClaudeUsageWidget-win.zip·-mac.dmg 등은 바꾸지 않는다.
  self_update.py와 README의 "항상 최신" 링크가 그 이름을 쓴다.
- WiX는 v5에 고정돼 있다(v6부터 유지보수 비용 약관 동의가 필요함). 올리지 않는다.
- Chrome을 띄우는 코드는 fetcher.browser_launch_lock을 거친다. 동시에 두 개가 뜨면 타임아웃이 난다.
