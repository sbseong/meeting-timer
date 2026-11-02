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
  - 메뉴 : 오늘 일정 목록. 일정을 누르면 회의 링크(Meet·Zoom·Teams) 열림
- 알림 : 10·5·1분 전 맥 알림 (소리 포함)
- 시작 시각 : 화면 가운데 경고창. 「참여하기」를 누르면 회의 링크 열림
- 대시보드 : http://127.0.0.1:8765
  - 지금 회의(진행 막대) / 다음 회의 카운트다운 / 두 회의 사이 여유 시간 / 오늘·내일 일정
  - 지각이면 화면 깜빡임
- 빼는 일정 : 종일 일정, 내가 거절한 일정, 취소된 일정, '한가함'으로 표시된 일정
- 여러 캘린더 지원 (같은 회의는 한 번만 표시)

## 요구 사항
- macOS, Python 3.10 이상
- 구글 캘린더의 **iCal 형식 비공개 주소** (회사 계정은 관리자가 막아 두었을 수 있음)

## 설치
```zsh
git clone https://github.com/sbseong/meeting-timer.git
cd meeting-timer
./setup.sh
```

## 캘린더 주소 저장 (맥 키체인)
캘린더 주소는 파일이 아닌 **맥 키체인**에 저장. 앱이 주소를 읽을 때마다 맥이 확인 창을 띄우고, 로그인 암호를 넣어야 허용됨.

1. 구글 캘린더 웹 → 내 캘린더 옆 ⋮ → 설정 및 공유 → 「캘린더 통합」 → **iCal 형식의 비공개 주소** 복사
2. 터미널에서 저장 (입력값은 화면·명령 기록에 안 남음. 확인용으로 두 번 입력)
   ```zsh
   security add-generic-password -a ical -s meeting-timer -T "" -w
   ```
   - `-T ""` : 어떤 프로그램도 미리 허용하지 않음 → 읽을 때마다 확인 창
   - 캘린더 추가 : `-a ical2`, `-a ical3` … (최대 `ical9`)로 따로 저장
   - 한 항목에 주소 여러 개를 띄어 써서 넣으면 확인 창도 한 번만 뜸
3. `./run.sh` 로 실행 → 확인 창에서 로그인 암호를 넣고 **「허용」**
   - **「항상 허용」은 누르지 말 것.** 누르면 그 뒤로는 묻지 않음
   - 앱은 켤 때 한 번만 묻고, 주소는 메모리에만 둠
   - 「거부」하면 다시 묻지 않음. 메뉴의 「지금 새로고침」을 누르면 다시 물음

- 주소 바꾸기 : `security delete-generic-password -a ical -s meeting-timer` 후 2번 다시, 앱 재시작
- 비공개 주소는 비밀번호와 같음. 유출되면 구글 캘린더 같은 화면에서 「재설정」

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
| `my_email` | `""` | 거절한 일정을 빼는 기준. 비우면 캘린더 이름(구글 기본 캘린더는 소유자 메일)으로 추정 |
| `refresh_minutes` | `5` | 캘린더를 다시 받는 주기(분) |
| `alert_minutes` | `[10, 5, 1]` | 알림 시점(회의 몇 분 전) |
| `popup_at_start` | `true` | 시작 시각 경고창 사용 여부 |
| `include_all_day` | `false` | 종일 일정 포함 여부 |
| `port` | `8765` | 대시보드 포트 |

## 보안 메모
- 대시보드는 `127.0.0.1` 에만 열림. 같은 맥에서만 접속 가능
- 다른 웹사이트가 대시보드 API로 일정을 읽지 못하게 Host·Origin 헤더 확인
- 오류 문구에 캘린더 주소가 나오지 않게 가림

## 파일
- `calendar_source.py` : iCal 받기, 반복 일정 펼치기, 거절·종일 일정 거르기, 키체인 읽기
- `menubar.py` : 메뉴바 앱과 알림 (대시보드 서버도 같이 띄움)
- `server.py`, `static/index.html` : 대시보드

---

## English

A small macOS menu bar app that reads your Google Calendar and shows, every second:
- **Current meeting**: time until it ends
- **Next meeting**: time until it starts (color turns 🟢 → 🟡 → 🟠 → 🔴 as it approaches)

It also sends notifications 10/5/1 minutes before, pops up a dialog with a "Join" button at start time, and serves a local dashboard at http://127.0.0.1:8765. The UI text is in Korean.

### Install
```zsh
git clone https://github.com/sbseong/meeting-timer.git
cd meeting-timer
./setup.sh            # creates .venv and installs rumps, icalendar, recurring-ical-events
```

### Store your calendar URL in the macOS Keychain
1. Google Calendar → Settings → your calendar → *Integrate calendar* → copy **Secret address in iCal format**.
2. Save it (you'll be prompted; nothing is echoed or stored in shell history):
   ```zsh
   security add-generic-password -a ical -s meeting-timer -T "" -w
   ```
   `-T ""` trusts no app, so macOS asks for your login password every time the app reads it. Add more calendars as `-a ical2` … `-a ical9`.
3. `./run.sh`, then click **Allow** (not *Always Allow*) in the Keychain prompt. The URL is read once at startup and kept only in memory.

### Start at login
```zsh
./install_autostart.sh          # install LaunchAgent
./install_autostart.sh remove   # uninstall
```

### Config (optional)
Copy `config.example.json` to `config.json`. See the table above for keys (`alert_minutes`, `refresh_minutes`, `my_email`, `include_all_day`, `port`, …).

Excluded events: all-day, declined by you, cancelled, and "free" (transparent) events.

## License
MIT
