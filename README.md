<div align="center">

# Claude Usage Widget

**claude.ai 세션 / 주간 사용량을 트레이 아이콘으로 항상 확인하세요**

[![Latest Release](https://img.shields.io/github/v/release/KimGiJeong1101/claude-usage-widget?label=release&color=4a9eff)](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest)
[![Build](https://github.com/KimGiJeong1101/claude-usage-widget/actions/workflows/release.yml/badge.svg)](https://github.com/KimGiJeong1101/claude-usage-widget/actions/workflows/release.yml)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-6e6e6e)](#다운로드)

<img src="docs/screenshot.png" width="480" alt="Claude Usage Widget 팝업 목업">

</div>

## ✨ 특징

- 🟢 **트레이 상주**: 세션(5시간) 사용량을 원형 게이지로 항상 표시, 클릭하면 세션/주간 상세 팝업
- 🔄 **즉시 새로고침**: 갱신 주기를 기다리지 않고 팝업에서 바로 최신 데이터 확인
- 🔐 **최초 1회 로그인**: 이후엔 자동으로 세션 유지, 재부팅해도 다시 로그인 안 해도 됨
- 🪟🍎 **Windows / macOS 지원**

## 📥 다운로드

Python 설치 없이 바로 쓸 수 있는 빌드입니다. 아래 링크는 항상 **최신 릴리즈**를 가리킵니다.

| OS | 형식 | 다운로드 |
| --- | --- | --- |
| Windows | 설치형 (.msi) | **[다운로드](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget.msi)** |
| Windows | 포터블 (.zip, 설치 없이 실행) | **[다운로드](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-win.zip)** |
| macOS | 디스크 이미지 (.dmg) | **[다운로드](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-mac.dmg)** |

<details>
<summary>실행 시 경고가 뜬다면?</summary>
<br>

코드 서명이 안 된 빌드라 아래 경고가 뜰 수 있습니다 — 정상입니다.

- **Windows**: SmartScreen이 "알 수 없는 게시자"라고 뜨면 → **추가 정보** → **실행**
- **macOS**: "확인되지 않은 개발자" 경고가 뜨면 → 파일 우클릭 → **열기**

</details>

## 사용법

최초 실행 시 로그인 창이 뜨고, 로그인하면 트레이/메뉴바 아이콘으로 상주합니다.

| 동작 | 결과 |
| --- | --- |
| 좌클릭 | 세션/주간 사용량 %와 리셋 시간 팝업 (클릭 위치 근처에 뜨고, 마우스가 벗어나면 자동으로 닫힘) |
| 팝업의 ⟳ | 갱신 주기를 기다리지 않고 즉시 새로고침 |
| 우클릭 | 설정(갱신 주기, 초 단위) / 종료 |

## 🛠️ 개발자용

<details>
<summary>동작 방식 (자세히 보기)</summary>
<br>

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

</details>

<details>
<summary>소스에서 직접 실행하기</summary>
<br>

**요구 사항**: Python 3.10+, Google Chrome (로그인 시 실제 Chrome 채널을 사용합니다)

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e .
playwright install chromium
python -m usage_widget.main
```

</details>

<details>
<summary>배포용 실행 파일 직접 빌드하기 (Windows)</summary>
<br>

```bash
pip install -e ".[build]"
pyinstaller --onefile --windowed --name ClaudeUsageWidget --add-data "usage_widget/assets;usage_widget/assets" run.py
```

`dist/ClaudeUsageWidget.exe`가 생성됩니다. Playwright 드라이버가 통째로
포함되어 exe 용량이 큰 편입니다(수십 MB). macOS는 각자의 macOS 환경에서
같은 명령으로 따로 빌드해야 합니다 (크로스 빌드 불가). `v*` 형태의 git 태그를
push하면 GitHub Actions가 Windows/macOS 빌드를 자동으로 만들어 릴리즈에 올립니다.

</details>

## 참고

- 개인/팀 내부용으로 만든 도구이며, Anthropic의 공식 제품이 아닙니다.
- 자기 자신의 claude.ai 계정으로만 사용하도록 설계되어 있습니다.
- UI 폰트로 [Pretendard](https://github.com/orioncactus/pretendard)(SIL OFL 1.1 라이선스, `usage_widget/assets/fonts/LICENSE` 참고)를 번들로 포함합니다.
  Windows에서는 설치 없이 프로세스 단위로 폰트를 등록해서 사용하고, macOS/Linux에서는 아직 이 방식이 구현되어 있지 않아 OS 기본 폰트로 표시됩니다.
