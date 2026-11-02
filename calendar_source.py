"""구글 캘린더 비공개 iCal 주소에서 오늘~내일 일정을 읽어 온다.

- 반복 일정은 recurring_ical_events 로 펼친다.
- 종일 일정, 내가 거절한 일정, '한가함(TRANSPARENT)' 일정은 기본으로 뺀다.
- 네트워크가 끊겨도 마지막으로 받은 일정을 계속 쓴다.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import icalendar
import recurring_ical_events

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

DEFAULT_CONFIG = {
    "ical_urls": [],             # 비워 두면 맥 키체인에서 읽는다 (권장)
    "my_email": "",              # 거절한 일정을 빼는 데 씀. 비우면 캘린더 이름(구글은 메일 주소)으로 추정
    "refresh_minutes": 5,        # 캘린더를 다시 받아오는 주기
    "alert_minutes": [10, 5, 1], # 회의 몇 분 전에 알림을 띄울지
    "popup_at_start": True,      # 시작 시각에 화면 가운데 경고창
    "include_all_day": False,
    "port": 8765,
}

URL_RE = re.compile(r"https?://[^\s<>\"']+")
MEET_HOSTS = ("meet.google.com", "zoom.us", "teams.microsoft.com", "webex.com")


KEYCHAIN_SERVICE = "meeting-timer"


KEYCHAIN_ACCOUNTS = ["ical"] + [f"ical{i}" for i in range(2, 10)]  # ical, ical2 … ical9


def read_keychain_urls() -> list[str]:
    """맥 키체인에 저장한 비공개 iCal 주소를 읽는다. 캘린더마다 항목을 따로 둔다.
    저장: security add-generic-password -a ical  -s meeting-timer -T "" -w   (첫 캘린더)
          security add-generic-password -a ical2 -s meeting-timer -T "" -w   (두 번째) …
    -T "" 로 저장하면 읽을 때마다 맥이 확인 창을 띄운다 (항목마다 한 번씩).
    없는 항목은 확인 창 없이 건너뛴다. 거부한 항목도 건너뛴다.
    한 항목에 주소 여러 개를 공백·쉼표로 넣어도 된다."""
    urls: list[str] = []
    for account in KEYCHAIN_ACCOUNTS:
        r = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            urls += [u for u in re.split(r"[\s,]+", r.stdout.strip()) if u]
    return urls


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    return cfg


@dataclass
class Event:
    title: str
    start: datetime
    end: datetime
    location: str = ""
    link: str = ""

    def to_json(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat()
        return d


def _find_meeting_link(comp) -> str:
    for key in ("X-GOOGLE-CONFERENCE", "URL"):
        v = comp.get(key)
        if v:
            return str(v)
    text = f"{comp.get('LOCATION', '')} {comp.get('DESCRIPTION', '')}"
    urls = URL_RE.findall(text)
    for u in urls:
        if any(h in u for h in MEET_HOSTS):
            return u
    return urls[0] if urls else ""


def _declined_by_me(comp, my_email: str) -> bool:
    if not my_email:
        return False
    attendees = comp.get("ATTENDEE")
    if attendees is None:
        return False
    if not isinstance(attendees, list):
        attendees = [attendees]
    for a in attendees:
        if str(a).lower().replace("mailto:", "") == my_email.lower():
            return str(a.params.get("PARTSTAT", "")).upper() == "DECLINED"
    return False


def _to_local(v) -> tuple[datetime, bool]:
    """date/datetime 을 로컬 시간대 datetime 으로. 두 번째 값은 종일 일정 여부."""
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.astimezone()  # 시간대 없는 값은 로컬로 본다
        return v.astimezone(), False
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day).astimezone(), True
    raise TypeError(v)


def parse_ics(raw: bytes, cfg: dict, start: datetime, end: datetime) -> list[Event]:
    cal = icalendar.Calendar.from_ical(raw)
    # 구글 기본 캘린더의 이름(X-WR-CALNAME)은 소유자 메일 주소다
    my_email = cfg.get("my_email") or ""
    if not my_email:
        calname = str(cal.get("X-WR-CALNAME", ""))
        my_email = calname if "@" in calname else ""
    events: list[Event] = []
    for comp in recurring_ical_events.of(cal).between(start, end):
        if str(comp.get("STATUS", "")).upper() == "CANCELLED":
            continue
        if str(comp.get("TRANSP", "")).upper() == "TRANSPARENT":
            continue
        if _declined_by_me(comp, my_email):
            continue
        s, all_day = _to_local(comp.decoded("DTSTART"))
        if all_day and not cfg.get("include_all_day"):
            continue
        if "DTEND" in comp:
            e, _ = _to_local(comp.decoded("DTEND"))
        elif "DURATION" in comp:
            e = s + comp.decoded("DURATION")
        else:
            e = s + (timedelta(days=1) if all_day else timedelta(0))
        events.append(Event(
            title=str(comp.get("SUMMARY", "(제목 없음)")),
            start=s, end=e,
            location=str(comp.get("LOCATION", "")),
            link=_find_meeting_link(comp),
        ))
    events.sort(key=lambda ev: ev.start)
    return events


class CalendarFeed:
    """백그라운드에서 주기적으로 캘린더를 받아 두고, 현재/다음 회의를 알려 준다."""

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config()
        self.events: list[Event] = []
        self.last_ok: datetime | None = None
        self.last_error: str = ""
        self._lock = threading.Lock()
        self._wake = threading.Event()
        # 키체인 주소는 앱을 켤 때 한 번만 읽어 메모리에 둔다 (디스크에는 쓰지 않음).
        # 실패하면 자동으로 다시 묻지 않고, 사용자가 '지금 새로고침'을 눌렀을 때만 다시 묻는다.
        self._kc_urls: list[str] | None = None
        self._kc_may_ask = True

    # --- 받아오기 ---
    def refresh(self) -> None:
        now = datetime.now().astimezone()
        day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window = (day0, day0 + timedelta(days=2))
        urls = self.urls()
        if not urls:
            self.last_error = "키체인 접근이 거부됐거나 주소가 없음. 메뉴의 '지금 새로고침'으로 다시 시도"
            return
        all_events: list[Event] = []
        errors = []
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "meeting-timer"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    all_events += parse_ics(r.read(), self.cfg, *window)
            except Exception as e:  # 네트워크·파싱 실패해도 앱은 계속 돈다
                # 오류 문구에 비공개 주소가 섞여 나오지 않게 가린다
                errors.append(f"{type(e).__name__}: {e}".replace(url, "(비공개 주소)"))
        if errors and not all_events:
            self.last_error = "; ".join(errors)
            return
        # 여러 캘린더에 같은 회의가 있으면 하나만 남긴다
        seen, uniq = set(), []
        for ev in sorted(all_events, key=lambda ev: ev.start):
            k = (ev.title, ev.start)
            if k not in seen:
                seen.add(k)
                uniq.append(ev)
        with self._lock:
            self.events = uniq
            self.last_ok = now
            self.last_error = "; ".join(errors)

    def urls(self) -> list[str]:
        """config.json 에 주소가 있으면 그것을, 없으면 키체인 값(한 번 읽어 둔 것)을 쓴다."""
        if self.cfg.get("ical_urls"):
            return list(self.cfg["ical_urls"])
        if self._kc_urls is None and self._kc_may_ask:
            self._kc_may_ask = False
            self._kc_urls = read_keychain_urls() or None
        return self._kc_urls or []

    def start_background(self) -> None:
        def loop():
            while True:
                self.refresh()
                self._wake.wait(self.cfg.get("refresh_minutes", 5) * 60)
                self._wake.clear()
        threading.Thread(target=loop, daemon=True).start()

    def refresh_now(self) -> None:
        """사용자가 직접 누른 새로고침. 키체인을 아직 못 읽었으면 이때 다시 묻는다."""
        if self._kc_urls is None:
            self._kc_may_ask = True
        self._wake.set()

    # --- 조회 ---
    def snapshot(self, now: datetime | None = None) -> dict:
        now = now or datetime.now().astimezone()
        with self._lock:
            events = list(self.events)
        today = now.date()
        current = [ev for ev in events if ev.start <= now < ev.end]
        upcoming = [ev for ev in events if ev.start > now]
        return {
            "now": now.isoformat(),
            "current": [ev.to_json() for ev in current],
            "next": upcoming[0].to_json() if upcoming else None,
            "today": [ev.to_json() for ev in events if ev.start.date() == today],
            "tomorrow": [ev.to_json() for ev in events if ev.start.date() == today + timedelta(days=1)],
            "last_ok": self.last_ok.isoformat() if self.last_ok else None,
            "error": self.last_error,
        }

    def next_event(self, now: datetime | None = None) -> Event | None:
        now = now or datetime.now().astimezone()
        with self._lock:
            return next((ev for ev in self.events if ev.start > now), None)

    def current_events(self, now: datetime | None = None) -> list[Event]:
        now = now or datetime.now().astimezone()
        with self._lock:
            return [ev for ev in self.events if ev.start <= now < ev.end]

    def events_list(self) -> list[Event]:
        with self._lock:
            return list(self.events)


if __name__ == "__main__":
    feed = CalendarFeed()
    t0 = time.time()
    feed.refresh()
    print(json.dumps(feed.snapshot(), ensure_ascii=False, indent=2))
    print(f"({time.time() - t0:.1f}s)")
