"""맥 메뉴바에 다음 회의까지 남은 시간을 1초마다 보여 준다.

- 메뉴바: '🟢 주간회의 12:34' 꼴. 남은 시간에 따라 🟢(10분 초과) 🟡(10분 이내) 🟠(5분 이내) 🔴(1분 이내·지각)
- 알림: config 의 alert_minutes(기본 10·5·1분 전)에 맥 알림
- 시작 시각: 화면 가운데 경고창 (참여 링크가 있으면 '참여하기' 버튼)
- 같은 프로세스에서 브라우저 대시보드(http://127.0.0.1:8765)도 띄운다
"""
from __future__ import annotations

import subprocess
import threading
import webbrowser
from datetime import datetime

import rumps

from calendar_source import CalendarFeed, Event, save_setting
from server import serve

TITLE_MAX = 14   # 메뉴바에 보일 회의 제목 최대 글자 수
SHORT_BOTH = 8   # 지금·다음 회의를 같이 보일 때 제목 글자 수
MOVE_CHOICES = [1, 2, 3, 4, 5]  # 메뉴에서 고를 수 있는 '이동 알림' 시점(분 전)
END_SOON = 300   # 지금 회의가 이 초 이하로 남으면 빨간 표식


def fmt(sec: float) -> str:
    sec = max(0, int(sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def dot(sec: float) -> str:
    if sec <= 60:
        return "🔴"
    if sec <= 300:
        return "🟠"
    if sec <= 600:
        return "🟡"
    return "🟢"


def short(title: str, n: int = TITLE_MAX) -> str:
    title = " ".join(title.split())
    return title if len(title) <= n else title[: n - 1] + "…"


def _osa(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def notify(title: str, message: str) -> None:
    # rumps.notification 은 앱 번들이 아니면 안 뜰 때가 있어 osascript 를 쓴다
    script = f'display notification "{_osa(message)}" with title "{_osa(title)}" sound name "Glass"'
    subprocess.Popen(["osascript", "-e", script])


def popup(ev: Event, minutes_before: int = 0) -> None:
    """화면 가운데 경고창. minutes_before=0 이면 시작 알림, 그 밖이면 이동 알림.
    앱이 멈추지 않도록 별도 스레드에서 띄운다."""
    def run():
        buttons = '{"닫기", "참여하기"}' if ev.link else '{"확인"}'
        default = "참여하기" if ev.link else "확인"
        if minutes_before:
            head = f"{minutes_before}분 뒤 {ev.start:%H:%M} 회의. 지금 이동하세요."
            title = f"🚶 {ev.title}"
        else:
            head = f"{ev.start:%H:%M} 회의가 시작됐어요."
            title = f"⏰ {ev.title}"
        msg = f"{head}\n{ev.location}".strip()
        script = (
            'beep\n'
            f'display dialog "{_osa(msg)}" with title "{_osa(title)}" '
            f'buttons {buttons} default button "{default}" with icon caution giving up after 120'
        )
        out = subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout
        if ev.link and "참여하기" in out:
            webbrowser.open(ev.link)
    threading.Thread(target=run, daemon=True).start()


class MeetingTimerApp(rumps.App):
    def __init__(self):
        super().__init__("⏳", quit_button=None)
        self.feed = CalendarFeed()
        self.port = self.feed.cfg.get("port", 8765)
        self.alert_minutes = sorted(self.feed.cfg.get("alert_minutes", [10, 5, 1]), reverse=True)
        self.fired: set[tuple] = set()
        self._menu_sig = None
        self.feed.start_background()
        try:
            serve(self.feed, self.port)
        except OSError as e:  # 포트가 이미 쓰이면 대시보드 없이 메뉴바만 돈다
            print(f"대시보드 서버를 못 띄움 (port {self.port}): {e}", flush=True)
        self._rebuild_menu()
        rumps.Timer(self.tick, 1).start()

    # --- 메뉴 ---
    def _rebuild_menu(self):
        events = self.feed.events_list()
        today = datetime.now().date()
        todays = [ev for ev in events if ev.start.date() == today]
        sig = (tuple((ev.title, ev.start) for ev in todays), self.feed.last_error, datetime.now().minute)
        if sig == self._menu_sig:
            return
        self._menu_sig = sig
        now = datetime.now().astimezone()

        self.menu.clear()
        self.menu.add(rumps.MenuItem("대시보드 열기", callback=lambda _: webbrowser.open(f"http://127.0.0.1:{self.port}")))
        self.menu.add(rumps.MenuItem("지금 새로고침", callback=lambda _: self.feed.refresh_now()))
        self.menu.add(self._move_menu())
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("오늘 일정"))
        if not todays:
            self.menu.add(rumps.MenuItem("  일정 없음"))
        for ev in todays:
            mark = "✓ " if ev.end <= now else ("▶ " if ev.start <= now else "   ")
            label = f"{mark}{ev.start:%H:%M}–{ev.end:%H:%M}  {ev.title}"
            cb = (lambda link: (lambda _: webbrowser.open(link)))(ev.link) if ev.link else None
            self.menu.add(rumps.MenuItem(label, callback=cb))
        if self.feed.last_error:
            self.menu.add(rumps.separator)
            self.menu.add(rumps.MenuItem(f"⚠ {self.feed.last_error[:80]}"))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("종료", callback=lambda _: rumps.quit_application()))

    def _move_menu(self) -> rumps.MenuItem:
        """'이동 알림' 하위 메뉴: 1~5분 전 중 하나를 고르거나 끈다. 고른 값은 config.json 에 저장."""
        cur = self.feed.cfg.get("move_alert_minutes", 3) or 0
        parent = rumps.MenuItem(f"이동 알림: {cur}분 전" if cur else "이동 알림: 꺼짐")
        for m in [0] + MOVE_CHOICES:  # 0 = 끄기
            label = "0분 (끄기)" if m == 0 else f"{m}분 전"
            item = rumps.MenuItem(label, callback=(lambda m: (lambda _: self._set_move(m)))(m))
            item.state = int(m == cur)
            parent.add(item)
        return parent

    def _set_move(self, minutes: int) -> None:
        self.feed.cfg["move_alert_minutes"] = minutes
        save_setting("move_alert_minutes", minutes)
        self._menu_sig = None  # 체크 표시를 바로 다시 그린다

    # --- 1초마다 ---
    def tick(self, _):
        now = datetime.now().astimezone()
        self._rebuild_menu()

        if self.feed.last_ok is None and "키체인" in self.feed.last_error:
            self.title = "⚙️ 캘린더 설정 필요"
            return
        if self.feed.last_ok is None:
            self.title = "⏳ 불러오는 중" if not self.feed.last_error else "⚠️ 캘린더 오류"
            return

        events = self.feed.events_list()
        self._check_alerts(events, now)

        self.title = self._compose_title(events, now)

    def _compose_title(self, events: list[Event], now: datetime) -> str:
        """메뉴바 글자: [지금 회의 · 끝까지 남은 시간]  │  [다음 회의 · 시작까지 남은 시간]"""
        current = [ev for ev in events if ev.start <= now < ev.end]
        nxt = self.feed.next_event(now)
        n = SHORT_BOTH if (current and nxt) else TITLE_MAX
        parts = []
        if current:
            ev = current[-1]  # 겹치면 가장 늦게 시작한 회의
            elapsed = (now - ev.start).total_seconds()
            if elapsed < 300:  # 시작 5분 안: 지각 경고
                parts.append(f"🔴 {short(ev.title, n)} +{fmt(elapsed)}")
            else:
                left = (ev.end - now).total_seconds()
                mark = "🔴" if left <= END_SOON else "▶"  # 끝나기 5분 전부터 빨강
                parts.append(f"{mark} {short(ev.title, n)} {fmt(left)} 남음")
        if nxt:
            sec = (nxt.start - now).total_seconds()
            prefix = "" if nxt.start.date() == now.date() else "내일 "
            if sec > 3 * 3600:  # 3시간 넘게 남았으면 시작 시각만
                parts.append(f"{dot(sec)} {prefix}{nxt.start:%H:%M} {short(nxt.title, n)}")
            else:
                parts.append(f"{dot(sec)} {short(nxt.title, n)} {fmt(sec)}")
        return "  │  ".join(parts) if parts else "✅ 남은 회의 없음"

    def _check_alerts(self, events: list[Event], now: datetime):
        for ev in events:
            sec = (ev.start - now).total_seconds()
            key = (ev.title, ev.start)
            for m in self.alert_minutes:
                # 앱을 늦게 켰을 때 지난 알림이 한꺼번에 뜨지 않도록 90초 창 안에서만 보낸다
                if m * 60 - 90 < sec <= m * 60 and (key, m) not in self.fired:
                    self.fired.add((key, m))
                    notify(f"{m}분 뒤 회의", f"{ev.start:%H:%M} {ev.title}")
            move = self.feed.cfg.get("move_alert_minutes", 3) or 0
            if move > 0 and move * 60 - 90 < sec <= move * 60 and (key, "move") not in self.fired:
                self.fired.add((key, "move"))
                popup(ev, minutes_before=move)
            if self.feed.cfg.get("popup_at_start", True) and -120 < sec <= 0 and (key, 0) not in self.fired:
                self.fired.add((key, 0))
                popup(ev)


if __name__ == "__main__":
    # Dock 에 파이썬 아이콘이 뜨지 않게 메뉴바 전용 앱으로 둔다
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    MeetingTimerApp().run()
