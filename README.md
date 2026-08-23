<div align="center">

# Claude Usage Widget

**claude.ai 세션 / 주간 사용량을, 창을 열어보지 않고도 트레이 아이콘 한 번의 시선으로**

[![Latest Release](https://img.shields.io/github/v/release/KimGiJeong1101/claude-usage-widget?label=release&color=4a9eff&style=flat-square)](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/KimGiJeong1101/claude-usage-widget/release.yml?label=build&style=flat-square)](https://github.com/KimGiJeong1101/claude-usage-widget/actions/workflows/release.yml)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-6e6e6e?style=flat-square)](#-다운로드)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](pyproject.toml)

<br>

<img src="docs/screenshot.png" width="420" alt="Claude Usage Widget 사용량 팝업">

</div>

<br>

<p align="center">
  <a href="#-특징">특징</a> •
  <a href="#-미리보기">미리보기</a> •
  <a href="#-다운로드">다운로드</a> •
  <a href="#사용법">사용법</a> •
  <a href="#-개발자용">개발자용</a> •
  <a href="#참고">참고</a>
</p>

<br>

## ✨ 특징

<table>
<tr>
<td width="33%" valign="top">

### 📊 실시간 트레이 게이지
세션(5시간) 사용량이 트레이 아이콘 + 툴팁(%)에 항상 표시됩니다. 클릭 한 번으로 세션 / 주간 상세 팝업까지.

</td>
<td width="33%" valign="top">

### 📑 독립적인 다중 팝업
사용량 / 설정 / 계정 팝업을 동시에 여러 개 띄워둘 수 있습니다. 같은 팝업을 또 열면 새로 뜨는 대신 기존 창을 앞으로 가져와요.

</td>
<td width="33%" valign="top">

### 📌 팝업 고정
기본은 마우스가 벗어나면 자동으로 닫히고, 고정 버튼 하나로 계속 띄워둘 수 있습니다.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🔄 즉시 새로고침
버튼 한 번으로 바로 최신 데이터를 가져오고, 백그라운드 자동 갱신 결과도 열려 있는 팝업에 실시간으로 반영됩니다.

</td>
<td width="33%" valign="top">

### 📏 팝업 크기 조절
오른쪽 아래 손잡이를 드래그해서 세 팝업 모두 원하는 크기로 늘리거나 줄일 수 있습니다.

</td>
<td width="33%" valign="top">

### 💧 투명도 조절
사용량 팝업 전용 — 창 자체(텍스트 포함)를 통째로 반투명하게, 원하는 정도로 슬라이더로 조절합니다.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🎨 트레이 아이콘 5종
도넛 게이지 / 배터리 / 막대 / 숫자 / 원형 채움 중 취향대로. 설정에서 바로 바꿀 수 있어요.

</td>
<td width="33%" valign="top">

### 🔑 계정 관리
로그인된 계정 확인, 다른 계정으로 전환, 로그아웃(로그아웃 중엔 추적을 완전히 멈춤).

</td>
<td width="33%" valign="top">

### 🚀 자동 시작
PC를 켤 때 자동으로 실행할지 여부를 설정에서 켜고 끌 수 있습니다 (Windows).

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🔐 최초 1회 로그인
이후엔 세션이 자동으로 유지돼서, 재부팅해도 다시 로그인할 필요가 없습니다.

</td>
<td width="33%" valign="top">

### ⬆️ 업데이트 확인
우클릭 메뉴에 항상 현재 버전이 표시되고, 클릭 한 번으로 바로 확인할 수 있습니다. 새 버전이 있으면 Windows는 그 자리에서 바로 적용까지.

</td>
<td width="33%" valign="top">

### 💻🍎 크로스플랫폼
하나의 코드베이스로 Windows / macOS 빌드를 모두 제공합니다.

</td>
</tr>
</table>

<br>

## 🖼️ 미리보기

<div align="center">

<table>
<tr>
<td align="center" width="50%">
<img src="docs/screenshot.png" width="300" alt="사용량 팝업"><br>
<sub>사용량 팝업 — 클릭 위치 근처에 뜨고, 📌로 고정하지 않으면 마우스가 벗어날 때 자동으로 닫힙니다</sub>
</td>
<td align="center" width="50%">
<img src="docs/screenshot-opacity.png" width="300" alt="투명도 조절"><br>
<sub>투명도 슬라이더 — 창 전체가 뒤 화면이 비칠 정도로 반투명해집니다</sub>
</td>
</tr>
</table>

<br>

<table>
<tr>
<td align="center" width="50%">
<img src="docs/screenshot-settings.png" width="260" alt="설정 팝업"><br>
<sub>설정 — 자동갱신 주기 / 트레이 아이콘 스타일 / 자동 실행</sub>
</td>
<td align="center" width="50%">
<img src="docs/screenshot-account.png" width="260" alt="계정 팝업"><br>
<sub>계정 — 로그인 상태 확인 / 전환 / 로그아웃</sub>
</td>
</tr>
</table>

</div>

<br>

## 📥 다운로드

Python 설치 없이 바로 쓸 수 있는 빌드입니다. 아래 링크는 항상 **최신 릴리즈**를 가리킵니다.

<div align="center">

| OS | 형식 | 다운로드 |
| :---: | :---: | :---: |
| 💻 Windows | 설치형 (.msi, 시작 메뉴·바탕화면 바로가기 생성) | **[다운로드](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget.msi)** |
| 💻 Windows | 포터블 (.zip) | **[다운로드](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-win.zip)** |
| 🍎 macOS | 디스크 이미지 (.dmg) | **[다운로드](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-mac.dmg)** |

</div>

> [!WARNING]
> **macOS 빌드는 아직 실제 Mac에서 동작 검증이 되지 않았습니다.** GitHub Actions로 macOS 러너에서 빌드는 되지만, 실사용 테스트 전이라 다운로드해도 정상적으로 실행되지 않을 수 있습니다. macOS에서 문제를 겪으셨다면 이슈로 알려주세요.

<details>
<summary><b>실행 시 경고가 뜬다면?</b></summary>
<br>

코드 서명이 안 된 빌드라 아래 경고가 뜰 수 있습니다 — 정상입니다.

- **Windows**: SmartScreen이 "알 수 없는 게시자"라고 뜨면 → **추가 정보** → **실행**
- **macOS**: "확인되지 않은 개발자" 경고가 뜨면 → 파일 우클릭 → **열기**

</details>

<br>

## 사용법

최초 실행 시 로그인 창이 뜨고, 로그인하면 트레이/메뉴바 아이콘으로 상주합니다.

| 동작 | 결과 |
| --- | --- |
| 좌클릭 | 세션/주간 사용량 %와 리셋 시간 팝업 (클릭 위치 근처에 뜨고, 마우스가 벗어나면 자동으로 닫힘) |
| 팝업의 💧 / 📌 / ⟳ | 투명도 슬라이더 펼치기 / 팝업 고정(안 닫히게) / 즉시 새로고침 |
| 팝업 오른쪽 아래 손잡이 | 드래그해서 팝업 크기 조절 |
| 우클릭 → 열기 | 좌클릭과 동일하게 사용량 팝업을 엽니다 |
| 우클릭 → 설정 | 자동갱신 주기, 트레이 아이콘 스타일, (Windows) PC 시작 시 자동 실행 여부 |
| 우클릭 → 계정 | 현재 로그인 계정 확인, 계정 변경(재로그인), 로그아웃 |
| 우클릭 → 현재 버전: vX.Y.Z | 클릭하면 그 자리에서 업데이트를 확인 — 최신이면 알림, 새 버전이 있으면 Windows는 바로 적용, 그 외에는 다운로드 페이지로 이동 |
| 우클릭 → 종료 | 위젯 완전히 종료 |

<br>

## 🛠️ 개발자용

<details>
<summary><b>동작 방식 (자세히 보기)</b></summary>
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
- "로그아웃"은 단순히 세션을 지우는 것이 아니라, 사용자가 다시 로그인하기 전까지
  백그라운드 새로고침/자동 재로그인 시도를 완전히 멈추는 일시정지 상태입니다.
- Windows 자동 시작은 관리자 권한 없이 `HKEY_CURRENT_USER` 레지스트리의
  Run 키에 등록하는 방식으로 동작합니다.
- 팝업 UI는 [`pywebview`](https://pywebview.flowrl.com/)로 구현되어 있습니다 — 각 팝업 창
  안에 OS 내장 웹뷰(Windows는 WebView2, macOS는 WKWebView)를 띄우고 그 위에
  HTML/CSS/JS로 그리는 방식이며, 트레이/로그인/설정/자동 시작 같은 기능 로직은 그대로
  파이썬입니다. Windows에서 완전히 둥근 모서리를 만들기 위해 `SetWindowRgn` Win32 API로
  창 자체를 둥근 모양으로 잘라내는 방식을 씁니다(일반적인 투명 배경 방식은 모서리에
  잔상이 남는 문제가 있었습니다).
- 프레임 없는 창이라 OS 리사이즈 테두리가 없어서, 팝업 크기 조절은 오른쪽 아래 손잡이를
  드래그한 만큼 파이썬 쪽에서 직접 `window.resize()`를 호출하는 방식으로 구현했습니다.
- 사용량 팝업의 투명도는 CSS `opacity`가 아니라 Windows의 `WS_EX_LAYERED` +
  `SetLayeredWindowAttributes` API로 창 전체(텍스트 포함)에 실제 알파 블렌딩을 적용합니다
  — 그래서 카드 배경색뿐 아니라 창 전체가 하나의 유리판처럼 같이 흐려집니다.
- 새 버전 확인은 GitHub Releases API로 현재 버전과 최신 태그를 비교하는 방식이라
  별도 업데이트 서버가 필요 없습니다. 트레이 메뉴의 "현재 버전" 항목은 항상 떠 있고,
  클릭하면 그 자리에서 즉시 확인합니다 (최신이면 알림만, 새 버전이 있으면 바로
  업데이트로 이어짐) — 백그라운드에서도 일정 주기로 같은 확인을 돌려서 알림을 띄웁니다.
- Windows에서 "지금 업데이트"를 누르면, 최신 포터블 zip을 내려받아 옆에 스테이징해두고
  **detached cmd.exe 헬퍼**를 하나 띄웁니다. 이 헬퍼가 (1) 지금 이 프로세스가 완전히
  종료될 때까지 기다렸다가 (2) 그제서야 새 파일을 원래 경로로 옮기고 (3) 실행합니다.
  실행 중인 프로세스가 스스로를 새 exe로 바꿔치기하고 곧장 재실행하는 방식은
  PyInstaller 6.9+ 부트로더의 보안 검증("자기 자신과 같은 실행 파일에 의해 spawn된
  것처럼 보이면 그 부모가 실제로 그 파일을 그대로 실행 중인지 확인")에 걸려서 재시작이
  실패했던 걸 이렇게 우회했습니다. 이 과정에서 두 가지를 더 맞춰야 했는데, 자식
  프로세스가 부모의 환경변수(부트로더 내부 기록 포함)를 그대로 물려받지 않도록
  `PYINSTALLER_RESET_ENVIRONMENT=1`을 심어줘야 했고, 헬퍼가 새 exe를 띄우자마자
  바로 종료해버리면 그 exe의 부트로더가 "부모가 누구인지" 조회하는 시점에 이미 부모가
  사라져 있어서 짧은 대기 시간도 넣어야 했습니다. macOS는 `.app` 번들 구조상 같은
  방식이 안 통해서 아직 다운로드 페이지 안내로만 동작합니다.
- 릴리즈에는 `ClaudeUsageWidget-win.zip`처럼 고정된 이름(자동 업데이트/README
  다운로드 링크가 항상 최신을 가리키기 위해 절대 안 바뀌는 이름)과, 사람이 알아보기
  쉽게 버전이 붙은 사본(`ClaudeUsageWidget-0.2.7-win.zip`)이 같이 올라갑니다. 후자는
  [Releases 페이지](https://github.com/KimGiJeong1101/claude-usage-widget/releases)에서만
  볼 수 있습니다.

</details>

<details>
<summary><b>소스에서 직접 실행하기</b></summary>
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

다른 PC에서 이어서 개발할 때 필요한 세팅(로그인 세션 저장 위치, 웹 UI 미리보기 팁 등)은
[DEVELOPMENT.md](DEVELOPMENT.md)를 참고하세요.

</details>

<details>
<summary><b>배포용 실행 파일 직접 빌드하기 (Windows)</b></summary>
<br>

```bash
pip install -e ".[build]"
pyinstaller --onefile --windowed --name ClaudeUsageWidget --icon installer/icon/ClaudeUsageWidget.ico --add-data "usage_widget/assets;usage_widget/assets" run.py
```

`--icon`을 빼면 실행 파일에 PyInstaller 기본 아이콘이 그대로 붙습니다. `dist/ClaudeUsageWidget.exe`가 생성됩니다. Playwright 드라이버가 통째로
포함되어 exe 용량이 큰 편입니다(수십 MB). macOS는 각자의 macOS 환경에서
같은 명령으로 따로 빌드해야 합니다 (크로스 빌드 불가). `v*` 형태의 git 태그를
push하면 GitHub Actions가 Windows/macOS 빌드를 자동으로 만들어 릴리즈에 올립니다.

</details>

<br>

## 참고

- 개인/팀 내부용으로 만든 도구이며, Anthropic의 공식 제품이 아닙니다.
- 자기 자신의 claude.ai 계정으로만 사용하도록 설계되어 있습니다.
- UI 폰트로 [Pretendard](https://github.com/orioncactus/pretendard)(SIL OFL 1.1 라이선스, `usage_widget/assets/fonts/LICENSE` 참고)를 번들로 포함합니다.
  웹뷰 안에서 CSS `@font-face`로 직접 로드하는 방식이라 별도 OS 등록 없이 Windows/macOS/Linux 어디서나 동일하게 표시됩니다.

<br>

<div align="center">
<sub>Built for N2SOFT-AX</sub>
</div>
