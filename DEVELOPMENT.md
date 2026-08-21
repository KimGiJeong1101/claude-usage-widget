# 개발 환경 세팅 가이드

다른 PC(노트북 등)에서 이 프로젝트를 이어서 개발할 때 참고하는 문서입니다.
팀 동료에게 배포용 실행 파일을 안내하는 문서는 [README.md](README.md)를 참고하세요 —
이 문서는 **소스 코드를 직접 열어서 수정/실행**하는 개발자 관점의 세팅 가이드입니다.

## 1. 사전 준비물

- **Python 3.10 이상**
- **Google Chrome** (일반 설치본) — claude.ai 로그인 시 Playwright가 번들 Chromium이
  아니라 실제로 설치된 Chrome을 `channel="chrome"`으로 띄웁니다. Chromium만으로는
  Cloudflare 봇 감지에 걸려서 로그인이 안 됩니다.
- **Git**
- (Windows) 별도 설치 불필요 — WebView2 런타임은 Windows 10 21H2 이상 / Windows 11에
  기본 내장돼 있습니다.
- 에디터는 VS Code + Claude Code 확장 사용을 권장합니다 (이 프로젝트가 그렇게 개발돼
  왔습니다). 필수는 아닙니다.

## 2. 클론 & 가상환경

```bash
git clone https://github.com/KimGiJeong1101/claude-usage-widget.git
cd claude-usage-widget

python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
```

## 3. 의존성 설치

```bash
pip install -e ".[build]"
playwright install chromium
```

`-e .`은 이 저장소를 "editable" 모드로 설치합니다 — 코드를 고치면 재설치 없이 바로
반영됩니다. `[build]`는 PyInstaller까지 같이 설치합니다(패키징까지 해볼 계획이 없다면
그냥 `pip install -e .`만 해도 됩니다). `playwright install chromium`은 Playwright의
드라이버를 받는 것으로, 실제 로그인/조회에 쓰이는 건 위에서 설치한 시스템 Chrome이지만
Playwright 자체가 동작하려면 필요합니다.

## 4. 실행

```bash
python -m usage_widget.main
```

최초 실행 시 로그인 창(Chrome)이 뜹니다. 로그인하면 트레이 아이콘으로 상주합니다.
**PC마다 별도로 로그인해야 합니다** — 세션 쿠키가 로컬에 저장되는 방식이라 다른 PC로
자동으로 옮겨가지 않습니다 (아래 5번 참고).

## 5. 로컬에 저장되는 데이터

계정 자격 증명은 저장하지 않지만, 로그인 세션 쿠키와 설정값은 OS 표준 사용자 데이터
폴더에 저장됩니다 (`platformdirs` 기준):

| OS | 경로 |
| --- | --- |
| Windows | `%LOCALAPPDATA%\ClaudeUsageWidget\ClaudeUsageWidget\` |
| macOS | `~/Library/Application Support/ClaudeUsageWidget/` |
| Linux | `~/.local/share/ClaudeUsageWidget/` |

이 폴더 안 `session_state.json`(로그인 세션), `config.json`(갱신 주기/트레이 아이콘
스타일 등)은 저장소 바깥, PC별 로컬 파일이라 git으로 옮겨지지 않습니다. 새 PC에서는
그냥 4번처럼 다시 로그인하면 됩니다.

## 6. 기획/진행 메모 (`notes/`)

`notes/claude-usage-widget-plan.md`(이 프로젝트의 기획/진행 메모)는 공개 저장소에 올릴
내용이 아니라서, `usage_widget` 저장소 안에 있지만 **별도의 private GitHub 저장소로
독립적으로 관리**됩니다 (`notes/` 자체가 자기만의 `.git`을 가진 중첩 저장소이고,
바깥쪽 `usage_widget` 저장소의 `.gitignore`가 `notes/`를 통째로 무시합니다).

그래서 `usage_widget`을 클론하는 것과는 별개로, `notes/`는 따로 클론해야 합니다:

```bash
cd claude-usage-widget          # usage_widget 저장소 루트
git clone <notes 저장소 URL> notes
```

이후로는 `notes/` 폴더 안에서 평소처럼 `git add`/`commit`/`push`/`pull`을 쓰면 됩니다 —
바깥쪽 `usage_widget` 저장소와는 완전히 독립된 별개의 히스토리입니다.

## 7. 웹 UI(팝업) 수정 시 팁

팝업 3개(`usage_widget/assets/web/usage.html`, `settings.html`, `account.html`)는
pywebview 창 없이 **브라우저에서 그냥 파일을 직접 열어도** 레이아웃/스타일은
바로 확인할 수 있습니다 (단, `window.pywebview.api` 호출 부분은 당연히 동작하지
않으므로 데이터는 안 채워집니다). 레이아웃/색상만 빠르게 확인할 때 유용합니다.

전체 동작(파이썬 ↔ JS 연결 포함)을 확인하려면 4번처럼 앱을 실제로 띄워서 트레이
아이콘을 클릭해봐야 합니다.

## 8. 패키징까지 해보고 싶다면

[README.md의 "배포용 실행 파일 직접 빌드하기"](README.md#-개발자용) 섹션을 참고하세요.

## 9. 일상적인 git 작업 흐름 (여러 PC 오갈 때)

이 폴더 안에는 **완전히 독립된 git 저장소가 2개** 있다는 걸 항상 기억하세요:

| 저장소 | 위치 | 성격 |
| --- | --- | --- |
| `claude-usage-widget` | 프로젝트 루트 (`usage_widget/`) | 공개, 코드/README 등 |
| `claude-usage-widget-notes` | `notes/` 하위 폴더 | 비공개, 기획 메모(`claude-usage-widget-plan.md`) |

`notes/`는 바깥쪽 저장소가 완전히 무시(`.gitignore`)하고 있어서, 코드 쪽에서
`git add -A`/`git commit`을 해도 `notes/` 안의 변경사항은 전혀 영향을 안 받습니다.
**즉, 코드를 커밋하는 것과 메모를 커밋하는 건 완전히 별개의 작업**이고, 각자 자기
폴더 안에서 명령을 실행해야 합니다.

### 작업 시작할 때 (PC를 바꿔서 앉았을 때)

```bash
git pull                 # 프로젝트 루트에서 — 코드 최신화
cd notes && git pull && cd ..   # 메모도 최신화
```

두 개 다 받아야 다른 PC에서 마지막으로 고친 내용을 놓치지 않습니다.

### 작업 끝내고 PC를 옮길 때

코드를 고쳤다면:

```bash
git add -A
git commit -m "무엇을 왜 고쳤는지"
git push
```

`notes/claude-usage-widget-plan.md`를 고쳤다면 (별도로):

```bash
cd notes
git add -A
git commit -m "무엇을 업데이트했는지"
git push
cd ..
```

둘 다 고쳤다면 두 저장소 모두 커밋·푸시해야, 다음에 다른 PC에서 앉았을 때 위
"작업 시작할 때" 단계에서 전부 받아집니다.

### 팁

- 혼자 쓰는 저장소라 브랜치/PR 없이 그냥 `main`에 바로 커밋해도 무방합니다.
- 뭘 커밋하려는지 헷갈리면 `git status`를 먼저 찍어보세요 — 코드 쪽 저장소에서
  찍으면 `notes/`는 아예 안 보이는 게 정상입니다(무시되고 있으니까).
- `.venv/`, 로그인 세션(`session_state.json`), 설정(`config.json`)은 애초에
  저장소 안에 없거나 `.gitignore`로 막혀 있어서 신경 쓸 필요 없습니다 (5번 참고).

## 자주 막히는 지점

- **로그인 창에서 계속 "사람인지 확인" 챌린지가 반복됨**: Google Chrome이 설치돼
  있는지, Playwright가 번들 Chromium이 아니라 실제 Chrome을 쓰고 있는지 확인하세요
  (`usage_widget/auth.py`의 `channel="chrome"`).
- **팝업이 하나도 안 뜨고 조용히 실패함**: 콘솔에 찍히는 에러를 먼저 확인하세요 —
  `python -m usage_widget.main`을 터미널에서 직접 실행하면(트레이로 안 내려가고)
  스택 트레이스가 그대로 보입니다.
- **Windows에서 팝업 모서리가 각지게 보임**: WebView2 런타임이 오래됐거나 없는
  환경일 수 있습니다. Windows 업데이트를 확인하세요.
