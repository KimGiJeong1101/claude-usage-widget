# Claude Usage Widget

claude.ai의 **Settings &gt; Usage** 화면에 나오는 세션(5시간)/주간 사용량 %와 리셋 시간을,
트레이(Windows) / 메뉴바(macOS) 아이콘으로 항상 보여주는 데스크톱 위젯입니다.

## 다운로드

Python 설치 없이 바로 쓸 수 있는 빌드입니다 (아래 링크는 항상 최신 릴리즈를 가리킵니다).

- [Windows 설치 (.msi)](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget.msi)
- [Windows 포터블 (.zip, 설치 없이 실행)](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-win.zip)
- [macOS (.dmg)](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-mac.dmg)

코드 서명이 안 된 빌드라 실행 시 경고가 뜰 수 있습니다:

- **Windows**: SmartScreen이 "알 수 없는 게시자"라고 뜨면 → **추가 정보** → **실행**
- **macOS**: "확인되지 않은 개발자" 경고가 뜨면 → 파일 우클릭 → **열기**

## 동작 방식

- claude.ai는 이 사용량 정보를 가져올 수 있는 공식 공개 API를 제공하지 않습니다.
- 그래서 이 프로젝트는 claude.ai 웹 앱이 내부적으로 호출하는 비공식 엔드포인트
  (`/api/organizations/{org_id}/usage`)를 그대로 재현해서 사용합니다.
  **claude.ai의 UI/내부 구현이 바뀌면 언제든 동작하지 않을 수 있습니다.**
- 최초 실행 시에만 실제 브라우저 창(Chrome)을 띄워 로그인하고, 그때 저장된 세션
  쿠키로 이후 주기적인 갱신을 처리합니다. 계정 자격 증명은 저장하지 않으며,
  세션 쿠키는 로컬 사용자 데이터 폴더(OS별 표준 경로)에만 저장됩니다.
- claude.ai는 Cloudflare 봇 방어가 걸려 있어 일반 HTTP 클라이언트(`httpx` 등)로는
  요청이 막힙니다. 이 프로젝트는 Playwright의 headless 브라우저 컨텍스트를 통해
  요청을 보내는 방식으로 이를 우회합니다 (페이지 전체를 렌더링하지는 않음).

## 요구 사항

- Python 3.10+
- Google Chrome (로그인 시 실제 Chrome 채널을 사용합니다)

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e .
playwright install chromium
```

## 실행

```bash
python -m usage_widget.main
```

최초 실행 시 로그인 창이 뜨고, 로그인하면 트레이/메뉴바 아이콘으로 상주합니다.

- **좌클릭**: 세션(5시간)/주간 사용량 %와 리셋 시간이 담긴 상세 팝업이 클릭 위치 근처에 뜹니다 (마우스가 팝업 밖으로 나가면 자동으로 닫힘)
- **우클릭**: 설정(갱신 주기, 초 단위) / 종료 메뉴
- 트레이 아이콘 자체는 세션(5시간) 사용량만 원형 게이지로 표시합니다 (주간 수치는 팝업에서 확인)

## 배포용 실행 파일 만들기 (Windows)

Python/venv 설치 없이 동료들에게 나눠줄 수 있는 단일 `.exe`를 만들 수 있습니다.

```bash
pip install -e ".[build]"
pyinstaller --onefile --windowed --name ClaudeUsageWidget --add-data "usage_widget/assets;usage_widget/assets" run.py
```

`dist/ClaudeUsageWidget.exe`가 생성됩니다. Playwright 드라이버가 통째로
포함되어 exe 용량이 큰 편입니다(수십 MB). macOS는 각자의 macOS 환경에서
같은 명령으로 따로 빌드해야 합니다 (크로스 빌드 불가).

## 참고

- 개인/팀 내부용으로 만든 도구이며, Anthropic의 공식 제품이 아닙니다.
- 자기 자신의 claude.ai 계정으로만 사용하도록 설계되어 있습니다.
- UI 폰트로 [Pretendard](https://github.com/orioncactus/pretendard)(SIL OFL 1.1 라이선스, `usage_widget/assets/fonts/LICENSE` 참고)를 번들로 포함합니다.
  Windows에서는 설치 없이 프로세스 단위로 폰트를 등록해서 사용하고, macOS/Linux에서는 아직 이 방식이 구현되어 있지 않아 OS 기본 폰트로 표시됩니다.
