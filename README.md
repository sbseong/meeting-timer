# meeting-timer

구글 캘린더를 읽어 **지금 회의가 끝날 때까지**, **다음 회의가 시작할 때까지** 남은 시간을 맥 메뉴바와 브라우저에 실시간으로 보여 주는 앱. 회의에 자주 늦는 사람용.

*A macOS menu bar countdown for Google Calendar: time left in the current meeting and time until the next one. [English below](#english).*

```
▶ 주간회의 49:52 남음  │  🟢 디자인 리뷰 1:19:52
```

## 기능
- 메뉴바 : 지금 회의(끝까지 남은 시간)와 다음 회의(시작까지 남은 시간)를 1초마다 표시
  - 다음 회의 색 : 🟢 10분 초과 · 🟡 10분 이내 · 🟠 5분 이내 · 🔴 1분 이내
  - 회의 시작 후 5분 동안 : `🔴 주간회의 +01:20` (지난 시간)
  - 회의 끝나기 5분 전부터 : `🔴 주간회의 04:59 남음`
  - 메뉴 : 오늘 일정 목록. 일정을 누르면 회의 링크(Meet·Zoom·Teams) 열림
- 이동 알림 : 3분 전 화면 가운데 「지금 이동하세요」 경고창
  - 메뉴바 메뉴 → 「이동 알림」에서 1~5분 전 중 고름. 바로 적용되고 다시 켜도 유지
  - 「끄기 (사전 알람 없음)」을 고르면 이동 알림만 꺼짐. 정각 경고창은 그대로 뜸
- 시작 시각 : 화면 가운데 경고창. 「참여하기」를 누르면 회의 링크 열림
- 대시보드 : http://127.0.0.1:8765
  - 지금 회의(진행 막대) / 다음 회의 카운트다운 / 두 회의 사이 여유 시간 / 오늘·내일 일정
  - 지각이면 화면 깜빡임
- 빼는 일정 : 종일 일정, 내가 거절한 일정, 취소된 일정 ('한가함' 일정은 기본으로 보임, `include_free`로 끔)
- 여러 캘린더 지원 (같은 회의는 한 번만 표시). 메뉴 「연동된 캘린더」에서 캘린더 이름·ID(메일 주소) 확인. 비밀 주소 전체는 표시하지 않음

## 요구 사항
- macOS, Python 3.10 이상
  - 맥 기본 `python3`은 3.9라서 그대로는 설치가 멈춤. 먼저 새 파이썬 설치 : `brew install python@3.12` (또는 python.org 설치 파일)
- 구글 캘린더의 **iCal 형식 비공개 주소** (회사 계정은 관리자가 막아 두었을 수 있음)

## 설치
```zsh
git clone https://github.com/sbseong/meeting-timer.git
cd meeting-timer
./setup.sh                          # 기본 python3 사용
PYTHON=python3.12 ./setup.sh        # 파이썬을 골라 쓸 때
```
- `Python 3.10 이상이 필요합니다` 가 나오면 위 요구 사항대로 새 파이썬을 설치한 뒤 `PYTHON=` 으로 지정

## 캘린더 주소 저장 (맥 키체인)
캘린더 주소는 파일이 아닌 **맥 키체인**에 저장. 앱이 주소를 읽을 때마다 맥이 확인 창을 띄우고, 로그인 암호를 넣어야 허용됨.

1. 구글 캘린더 웹 → 내 캘린더 옆 ⋮ → 설정 및 공유 → 「캘린더 통합」 → **iCal 형식의 비공개 주소** 복사
2. 터미널에서 저장 (입력값은 화면·명령 기록에 안 남음. 확인용으로 두 번 입력)
   ```zsh
   security add-generic-password -a ical -s meeting-timer -T "" -w
   ```
   - `-T ""` : 어떤 프로그램도 미리 허용하지 않음 → 읽을 때마다 확인 창
   - 캘린더가 여러 개면 아래 「캘린더 여러 개 연결」 참고
3. `./run.sh` 로 실행 → 확인 창에서 로그인 암호를 넣고 **「허용」**
   - **「항상 허용」은 누르지 말 것.** 누르면 그 뒤로는 묻지 않음
   - 앱은 켤 때 한 번만 묻고, 주소는 메모리에만 둠
   - 「거부」하면 다시 묻지 않음. 메뉴의 「지금 새로고침」을 누르면 거부한 항목만 다시 물음

- 주소 바꾸기 : `security delete-generic-password -a ical -s meeting-timer` 후 2번 다시, 앱 재시작
- 비공개 주소는 비밀번호와 같음. 유출되면 구글 캘린더 같은 화면에서 「재설정」

## 캘린더 여러 개 연결
회사·개인 계정처럼 캘린더가 여러 개면 **캘린더마다 비공개 주소를 따로** 저장. 앱이 모두 합쳐서 보여 줌.

1. 주소 모으기
   - 계정이 다르면 그 계정으로 구글 캘린더에 로그인해서 복사 (위 1번과 같은 경로)
   - 한 계정 안의 다른 캘린더(내가 만든 캘린더)도 캘린더마다 주소가 따로 있음
   - 공유받은 캘린더는 권한에 따라 비공개 주소가 안 보일 수 있음. 그때는 그 캘린더 주인에게 요청
   - 회사 계정은 관리자가 비공개 주소를 막아 두었으면 「캘린더 통합」에 주소가 없음
2. 저장 : 둘 중 하나
   - **항목을 나눠 저장 (권장)** : 캘린더마다 이름을 바꿔 저장. 최대 9개 (`ical` ~ `ical9`)
     ```zsh
     security add-generic-password -a ical  -s meeting-timer -T "" -w   # 첫 번째 캘린더
     security add-generic-password -a ical2 -s meeting-timer -T "" -w   # 두 번째 캘린더
     security add-generic-password -a ical3 -s meeting-timer -T "" -w   # 세 번째 …
     ```
     - 앱을 켤 때 확인 창이 항목 수만큼 뜸 (2개면 2번). **모두 「허용」**
     - 한 캘린더만 바꾸거나 지우기 쉬움
   - **한 항목에 몰아 저장** : 주소를 띄어 써서 한 번에 붙여 넣기. 확인 창이 한 번만 뜸
     ```zsh
     security add-generic-password -a ical -s meeting-timer -T "" -w
     # 암호 입력 칸에 「주소1 주소2」처럼 띄어 써서 붙여 넣기
     ```
     - 주소 하나를 바꿀 때도 전부 다시 입력해야 함
3. 확인 : 메뉴바 메뉴 → **「연동된 캘린더: N개」**
   - 하위 메뉴에 `캘린더 이름 · 캘린더 ID(보통 메일 주소)`가 줄마다 나옴. 비밀 주소 전체는 안 보임
   - 개수가 모자라면 아래 표대로 확인

| 메뉴에 보이는 것 | 뜻 | 할 일 |
| --- | --- | --- |
| `⚠ 키체인 ical2 : 허용 안 됨` | 그 항목의 확인 창을 거부했거나 놓침 | 「지금 새로고침」 → 다시 뜬 확인 창에서 「허용」 |
| `⚠ 캘린더이름 (받기 실패)` | 주소는 읽었지만 구글에서 받지 못함 | 인터넷 확인. 계속되면 주소가 재설정됐을 수 있으니 새 주소로 다시 저장 |
| 캘린더가 아예 안 보임 | 저장 이름이 `ical`~`ical9`가 아니거나 `-s meeting-timer`를 빠뜨림 | `security find-generic-password -a ical2 -s meeting-timer` 로 항목이 있는지 확인 (값은 안 나옴) |
| 같은 이름이 두 번 | 같은 주소를 두 항목에 저장 | 한 항목을 지우고 다른 캘린더 주소로 다시 저장 |

- 여러 캘린더에 같은 회의(제목·시작 시각이 같음)가 있으면 한 번만 보임
- 거절한 일정은 캘린더마다 그 캘린더 주인의 메일로 판단해서 뺌. 계정이 여러 개여도 `my_email`은 비워 둬도 됨
- 저장한 뒤에는 앱을 다시 켜야 새 캘린더를 읽음 (메뉴 「종료」 → `./run.sh`)

## 로그인 때 자동 실행
```zsh
./install_autostart.sh          # 등록 (바로 한 번 켜짐)
./install_autostart.sh remove   # 해제
```
- 로그인할 때마다 키체인 확인 창이 뜸 (저장한 항목 수만큼)
- 앱이 오류로 꺼지면 자동으로 다시 켬. 메뉴의 「종료」로 끄면 다시 켜지 않음
- 실행 기록 : `meeting_timer.log`

## 설정 (선택)
`cp config.example.json config.json` 후 수정.

| 항목 | 기본값 | 뜻 |
| --- | --- | --- |
| `ical_urls` | `[]` | 비우면 키체인 사용 (권장). 여기 넣으면 키체인 대신 이 주소 사용 |
| `my_email` | `""` | 거절한 일정을 빼는 기준 메일. 비워도 캘린더마다 주인 메일(캘린더 ID)로 판단. 주소에 메일이 안 드러나는 캘린더를 쓸 때만 넣음 |
| `refresh_minutes` | `5` | 캘린더를 다시 받는 주기(분) |
| `alert_minutes` | `[]` | 화면 오른쪽 위 알림 시점(회의 몇 분 전). 기본은 없음. 구글 캘린더 자체 알림과 겹치지 않게 함. 예 `[10, 5]` |
| `move_alert_minutes` | `3` | 회의 몇 분 전에 「지금 이동하세요」 경고창을 띄울지. 메뉴에서 1~5분으로 바꾸거나 끌 수 있음. `0` 이면 끔 |
| `popup_at_start` | `true` | 시작 시각 경고창 사용 여부 |
| `include_all_day` | `false` | 종일 일정 포함 여부 |
| `include_free` | `true` | '한가함'으로 표시된 일정 포함 여부 |
| `port` | `8765` | 대시보드 포트 |

## 보안 메모
- 대시보드는 `127.0.0.1` 에만 열림. 같은 맥에서만 접속 가능
- 다른 웹사이트가 대시보드 API로 일정을 읽지 못하게 Host·Origin 헤더 확인
- 오류 문구에 캘린더 주소가 나오지 않게 가림
- 회의 링크는 `http`/`https` 주소만 열고, 그 밖의 주소(`javascript:` 등)는 무시

## 파일
- `calendar_source.py` : iCal 받기, 반복 일정 펼치기, 거절·종일 일정 거르기, 키체인 읽기
- `menubar.py` : 메뉴바 앱과 알림 (대시보드 서버도 같이 띄움)
- `server.py`, `static/index.html` : 대시보드

---

## English

A small macOS menu bar app that reads your Google Calendar and shows, every second:
- **Current meeting**: time until it ends
- **Next meeting**: time until it starts (color turns 🟢 → 🟡 → 🟠 → 🔴 as it approaches)

It pops up a "time to move" dialog 3 minutes before (change it to 1–5 min or turn it off from the menu bar menu → 이동 알림) and another with a "Join" button at start time, and serves a local dashboard at http://127.0.0.1:8765. The UI text is in Korean.

### Requirements
- macOS, Python 3.10+ (the stock macOS `python3` is 3.9; install a newer one, e.g. `brew install python@3.12`)
- The **secret iCal address** of your Google Calendar (may be disabled by your Workspace admin)

### Install
```zsh
git clone https://github.com/sbseong/meeting-timer.git
cd meeting-timer
./setup.sh            # creates .venv and installs rumps, icalendar, recurring-ical-events
# or pick a Python explicitly:
PYTHON=python3.12 ./setup.sh
```

### Store your calendar URL in the macOS Keychain
1. Google Calendar → Settings → your calendar → *Integrate calendar* → copy **Secret address in iCal format**.
2. Save it (you'll be prompted; nothing is echoed or stored in shell history):
   ```zsh
   security add-generic-password -a ical -s meeting-timer -T "" -w
   ```
   `-T ""` trusts no app, so macOS asks for your login password every time the app reads it.
3. `./run.sh`, then click **Allow** (not *Always Allow*) in the Keychain prompt. The URL is read once at startup and kept only in memory.

### Multiple calendars
Store **one secret iCal address per calendar**; the app merges them.

1. Collect the addresses. For another Google account, sign in with that account and copy its address the same way. Calendars shared with you may not show a secret address unless you have enough permission, and Workspace admins can disable it entirely.
2. Save them, either:
   - **One entry per calendar (recommended)**: `-a ical`, `-a ical2`, … up to `-a ical9`.
     ```zsh
     security add-generic-password -a ical  -s meeting-timer -T "" -w
     security add-generic-password -a ical2 -s meeting-timer -T "" -w
     ```
     macOS asks once per entry at startup; allow each one.
   - **All in one entry**: paste the addresses separated by spaces at the password prompt. Only one prompt, but you must re-enter all of them to change one.
3. Check the menu bar menu → **연동된 캘린더: N개** (linked calendars). Each line shows `calendar name · calendar ID` (usually the owner's email); the secret address itself is never shown.
   - `⚠ 키체인 ical2 : 허용 안 됨` — you denied or missed that Keychain prompt. Click 지금 새로고침 (refresh) and it asks again for that entry only.
   - `⚠ … (받기 실패)` — the address was read but the download failed. Check your network, or the address may have been reset.
   - A calendar is missing entirely — check the entry name (`ical`…`ical9`) and `-s meeting-timer`.

The same meeting in several calendars (same title and start time) is shown once. Declined events are filtered per calendar using that calendar's owner email, so `my_email` can stay empty. Restart the app after adding a calendar.

### Start at login
```zsh
./install_autostart.sh          # install LaunchAgent
./install_autostart.sh remove   # uninstall
```

### Config (optional)
Copy `config.example.json` to `config.json`. See the table above for keys (`alert_minutes`, `refresh_minutes`, `my_email`, `include_all_day`, `include_free`, `port`, …).

Excluded events: all-day, declined by you, and cancelled. Events marked "free" (transparent) are shown by default; set `include_free` to `false` to hide them.

## License
MIT
