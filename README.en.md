<div align="center">

# Claude Usage Widget

**Your claude.ai session / weekly usage, one glance at the tray icon away — no window to open**

[![Latest Release](https://img.shields.io/github/v/release/KimGiJeong1101/claude-usage-widget?label=release&color=4a9eff&style=flat-square)](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/KimGiJeong1101/claude-usage-widget/release.yml?label=build&style=flat-square)](https://github.com/KimGiJeong1101/claude-usage-widget/actions/workflows/release.yml)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-6e6e6e?style=flat-square)](#-download)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](pyproject.toml)

<br>

<img src="docs/screenshot.png" width="420" alt="Claude Usage Widget usage popup">

</div>

<br>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-preview">Preview</a> •
  <a href="#-download">Download</a> •
  <a href="#usage">Usage</a> •
  <a href="#-for-developers">For Developers</a> •
  <a href="#notes">Notes</a>
</p>

<p align="center">
  <sub><a href="README.md">한국어</a> · English</sub>
</p>

<br>

## ✨ Features

<table>
<tr>
<td width="33%" valign="top">

### 📊 Live tray gauge
Session (5-hour) usage always shows in the tray icon + tooltip (%). One click opens the session / weekly detail popup.

</td>
<td width="33%" valign="top">

### 📑 Independent, multiple popups
Open the usage / settings / account popups at the same time. Opening the same one again brings the existing window forward instead of stacking a new one.

</td>
<td width="33%" valign="top">

### 📌 Pin a popup open
By default a popup closes as soon as the cursor leaves it; the pin button keeps it open.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🔄 Instant refresh
One button fetches the latest data immediately, and background auto-refresh results also reflect live in any popup that's already open.

</td>
<td width="33%" valign="top">

### 📏 Resizable popups
Drag the handle in the bottom-right corner to resize any of the three popups.

</td>
<td width="33%" valign="top">

### 💧 Adjustable opacity
Usage popup only — fades the whole window (text included) to whatever translucency you set with a slider.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🎨 5 tray icon styles
Donut gauge / battery / bar / number / liquid fill — pick your favorite, switch anytime in Settings.

</td>
<td width="33%" valign="top">

### 🔑 Account management
Check who's signed in, switch accounts, or log out (logging out fully pauses tracking).

</td>
<td width="33%" valign="top">

### 🚀 Launch at startup
Toggle whether the app launches automatically when you turn your PC on (Windows).

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🔐 Log in once
Your session stays signed in after that — no need to log in again even after a reboot.

</td>
<td width="33%" valign="top">

### ⬆️ Update check
The right-click menu always shows the current version; click it to check on the spot. If a new version exists, Windows applies it right there.

</td>
<td width="33%" valign="top">

### 💻🍎 Cross-platform
One codebase, builds for both Windows and macOS.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🌐 Multi-language
Supports 한국어 / English / 日本語 / 中文(简体). Switch instantly in Settings — the tray menu picks it up right away.

</td>
<td width="33%" valign="top">

### 🔒 Single-instance guard
Detects if it's already running and quits quietly after letting you know, instead of ending up with several tray icons.

</td>
</tr>
</table>

<br>

## 🖼️ Preview

<div align="center">

<table>
<tr>
<td align="center" width="50%">
<img src="docs/screenshot.png" width="300" alt="Usage popup"><br>
<sub>Usage popup — opens near where you clicked, and closes automatically once the cursor leaves unless pinned with 📌</sub>
</td>
<td align="center" width="50%">
<img src="docs/screenshot-opacity.png" width="300" alt="Opacity control"><br>
<sub>Opacity slider — the whole window turns translucent enough to see what's behind it</sub>
</td>
</tr>
</table>

<br>

<table>
<tr>
<td align="center" width="50%">
<img src="docs/screenshot-settings.png" width="260" alt="Settings popup"><br>
<sub>Settings — language / auto-refresh interval / tray icon style / launch at startup</sub>
</td>
<td align="center" width="50%">
<img src="docs/screenshot-account.png" width="260" alt="Account popup"><br>
<sub>Account — check sign-in status / switch / log out</sub>
</td>
</tr>
</table>

<br>

<img src="docs/screenshot-splash.png" width="220" alt="Startup loading screen"><br>
<sub>A brief loading screen right after launch — a tray notification confirms it once more as it fades out</sub>

<sub>(Screenshots show the Korean UI, the app's default language)</sub>

</div>

<br>

## 📥 Download

No Python install needed — these are ready-to-run builds. The links below always point to the **latest release**.

<div align="center">

| OS | Format | Download |
| :---: | :---: | :---: |
| 💻 Windows | Installer (.msi, adds Start Menu / desktop shortcuts) | **[Download](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget.msi)** |
| 💻 Windows | Portable (.zip) | **[Download](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-win.zip)** |
| 🍎 macOS (Apple Silicon) | Disk image (.dmg) | **[Download](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-mac.dmg)** |
| 🍎 macOS (Apple Silicon) | App bundle (.zip) | **[Download](https://github.com/KimGiJeong1101/claude-usage-widget/releases/latest/download/ClaudeUsageWidget-mac.zip)** |

</div>

> [!WARNING]
> **The macOS build hasn't been verified on a real Mac yet, and it's currently Apple Silicon (M1+) only.** GitHub Actions' `macos-latest` runner is arm64, so that's what the build comes out as — it won't run at all on an Intel Mac (wrong architecture). If you run into trouble on macOS, please open an issue.

<details>
<summary><b>Seeing a warning when you run it?</b></summary>
<br>

These builds aren't code-signed, so the warnings below are expected — not a sign anything's wrong.

- **Windows**: If SmartScreen says "unknown publisher" → **More info** → **Run anyway**
- **macOS**: If you see "unidentified developer" → right-click the file → **Open**

</details>

<br>

## Usage

A brief loading screen appears right after launch; the first time, a login window opens, and once you sign in the app settles into the tray/menu-bar icon. A short notification also fires the moment the icon appears, so you'll notice it even if you weren't watching the taskbar.

| Action | Result |
| --- | --- |
| Left-click | Opens the session/weekly usage % and reset-time popup (appears near your click, closes automatically once the cursor leaves) |
| 💧 / 📌 / ⟳ on the popup | Expand the opacity slider / pin the popup open / refresh immediately |
| Bottom-right handle on a popup | Drag to resize |
| Right-click → Open | Same as left-click — opens the usage popup |
| Right-click → Settings | Language, auto-refresh interval, tray icon style, and (Windows) launch-at-startup |
| Right-click → Account | Check who's signed in, switch accounts (re-login), or log out |
| Right-click → Current version: vX.Y.Z | Click to check for updates right there — a notification if you're current, an in-place update on Windows if not, or the download page otherwise |
| Right-click → Quit | Fully exits the widget |

<br>

## 🛠️ For Developers

<details>
<summary><b>How it works (details)</b></summary>
<br>

- claude.ai doesn't offer an official public API for this usage data.
- So this project replicates the unofficial endpoint the claude.ai web app itself calls
  internally (`/api/organizations/{org_id}/usage`). **It can stop working any time
  claude.ai changes its UI or internals.**
- A real browser window (Chrome) only opens for the very first login; the session
  cookie it saves is what drives every refresh after that. No account credentials
  are ever stored, and the session cookie lives only in the local per-user data
  folder (the OS's standard path).
- claude.ai sits behind Cloudflare bot protection, which blocks plain HTTP clients
  (`httpx` and the like). This project routes requests through a headless
  Playwright browser context instead (without rendering a full page) to get past
  that.
- "Log out" isn't just clearing the session — it's a real paused state that fully
  stops background refreshing and automatic re-login attempts until you sign back
  in.
- Windows auto-start is registered via the `HKEY_CURRENT_USER` registry Run key,
  with no admin rights required.
- The popup UI is built with [`pywebview`](https://pywebview.flowrl.com/) — each popup window hosts the
  OS's built-in webview (WebView2 on Windows, WKWebView on macOS) and is drawn
  with HTML/CSS/JS on top of it, while the tray/login/settings/auto-start logic
  stays plain Python. Fully rounded corners on Windows are done by clipping the
  native window with the `SetWindowRgn` Win32 API (the usual transparent-background
  approach left visible artifacts around the corners).
- Frameless windows have no OS resize border, so resizing a popup calls
  `window.resize()` directly from Python by however far you dragged the
  bottom-right handle.
- The usage popup's opacity isn't CSS `opacity` — it's real alpha blending over
  the *entire* window (text included) via Windows' `WS_EX_LAYERED` +
  `SetLayeredWindowAttributes` APIs, so the whole window fades together like one
  sheet of glass, not just the card backgrounds.
- Update checks compare the running version against the latest GitHub Releases
  tag, so no separate update server is needed. The tray menu's "current version"
  item is always visible; clicking it checks immediately (just a notification if
  you're current, straight into the update if not) — the same check also runs
  periodically in the background.
- Clicking "Update now" on Windows downloads the latest portable zip, stages it,
  and spawns a **detached cmd.exe helper**. That helper (1) waits for this
  process to fully exit, (2) only then moves the new file into place, and
  (3) launches it. A running process replacing itself with a new exe and
  relaunching immediately trips PyInstaller 6.9+'s bootloader security check
  ("if this exe looks like it was spawned by an identical exe, verify the parent
  process is really still running that exact file") — routing through an
  unrelated parent process (cmd.exe) sidesteps that entirely. Two more things had
  to be lined up: the child process needed `PYINSTALLER_RESET_ENVIRONMENT=1` so
  it wouldn't inherit the parent's bootloader bookkeeping, and the helper needed a
  short delay after launching the new exe before deleting itself, since exiting
  too fast left the new exe's bootloader unable to query a parent that had
  already vanished. macOS can't use the same trick given its `.app` bundle
  structure, so it's still download-page-only there.
- Releases ship both a fixed filename (`ClaudeUsageWidget-win.zip`, for example —
  never renamed, since the auto-updater and README download links depend on it
  always pointing at the latest release) and a versioned copy
  (`ClaudeUsageWidget-0.3.5-win.zip`) for humans to tell builds apart. The latter
  is only visible on the [Releases page](https://github.com/KimGiJeong1101/claude-usage-widget/releases).
- There used to be a gap right after launch — before the login check and first
  usage fetch finished, the tray icon didn't exist yet, so nothing showed up on
  screen at all. A small loading screen now covers that gap: the check/fetch
  moved to a background thread, pywebview's event loop starts immediately so the
  loading screen can actually render, and once everything's ready that screen
  closes and the tray icon appears.
- Language (한국어/English/日本語/中文(简体)) is managed as two separate translation
  tables — one for whatever Python itself draws (tray text, notifications,
  `usage_widget/i18n.py`), one for whatever the popup HTML/JS draws
  (`assets/web/i18n.js`) — kept in sync by hand since the web layer can't import
  a Python module. Tray menu labels are callables re-evaluated every time the
  menu is about to be shown, so a language change in Settings takes effect on the
  next right-click with no restart; a popup that's already open needs to be
  reopened to pick up the new language.
- The short notification right after launch is implemented via `pystray`'s
  `icon.run(setup=...)` callback — it only fires once the icon has actually been
  registered in the tray, avoiding a `notify()` call before there's anything to
  attach it to. Forcing the usage popup open, pinned, on every launch was
  considered and rejected — it fights the whole reason this app lives in the
  tray in the first place (a window left open all the time is no different from
  pinning the Claude app itself always-on-top).
- `config.json` is read by whatever version happens to run next — source or exe,
  a newer or older one — since it's shared across all of them. `Config.load()`
  drops any field it doesn't recognize, and falls back to defaults entirely
  (rather than crashing) if the file can't be parsed at all — invalid JSON, a
  write that got cut off mid-save, a value of the wrong type. Worst case, your
  preferences reset; the login session (a separate file) is never affected.
- The single-instance guard binds a fixed local TCP port as a mutex — unlike a
  Windows named mutex or a Unix PID file, it works identically regardless of OS,
  and the OS releases the port automatically if the process dies, so there's
  nothing to clean up. If another instance already holds it, the second launch
  shows a native `tkinter` message box (before `init_gui()` even runs) and exits
  immediately — no need to boot up pywebview for a process that's about to end
  anyway.
- If an automatic update fails (a very old install, a network hiccup, etc.), the
  failure notification is followed by opening the GitHub Releases page
  automatically, so a failed automatic update still ends with manual download
  one click away.

</details>

<details>
<summary><b>Running from source</b></summary>
<br>

**Requirements**: Python 3.10+, Google Chrome (login uses the real Chrome channel)

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e .
playwright install chromium
python -m usage_widget.main
```

For setup you'll need when continuing development on another PC (where the login
session is stored, tips for previewing the web UI, etc.), see
[DEVELOPMENT.md](DEVELOPMENT.md).

</details>

<details>
<summary><b>Building a distributable executable yourself (Windows)</b></summary>
<br>

```bash
pip install -e ".[build]"
pyinstaller --onefile --windowed --name ClaudeUsageWidget --icon installer/icon/ClaudeUsageWidget.ico --add-data "usage_widget/assets;usage_widget/assets" run.py
```

Drop `--icon` and the executable keeps PyInstaller's default icon. This produces
`dist/ClaudeUsageWidget.exe`. Bundling the whole Playwright driver makes the exe
fairly large (tens of MB). macOS has to be built on an actual macOS machine with
the same command (no cross-building). Pushing a `v*`-style git tag makes GitHub
Actions build both Windows and macOS automatically and attach them to a release.

</details>

<br>

## Notes

- Built for personal/internal team use — not an official Anthropic product.
- Designed to be used only with your own claude.ai account.
- Bundles [Pretendard](https://github.com/orioncactus/pretendard) (SIL OFL 1.1 license, see
  `usage_widget/assets/fonts/LICENSE`) as its UI font — loaded directly inside the
  webview via CSS `@font-face`, so it renders identically on Windows/macOS/Linux
  with no separate OS-level installation.

<br>

<div align="center">
<sub>Built for N2SOFT-AX</sub>
</div>
