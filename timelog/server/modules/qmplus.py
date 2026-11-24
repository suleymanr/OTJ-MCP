#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

from bs4 import BeautifulSoup

from timelog import paths
from timelog.config import QMPLUS_BASE, QMPLUS_HOME, UA
from timelog.server.modules.schemas import QmplusAuthRequired, QmplusError


def read_session() -> dict[str, Any]:
    data = paths.read_json(paths.QMPLUS_TOKENS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_cookies(
    cookies: list[dict[str, Any]] | None,
    sesskey: str | None = None,
    source: str = "browser",
) -> dict[str, Any]:
    wanted = {"MoodleSession", "MDL_SSP_AuthToken", "MDL_SSP_SessID", "MOODLEID1_"}
    data = read_session()

    for c in cookies or []:
        if c.get("name") in wanted and c.get("value"):
            data[c["name"]] = c["value"]

    if sesskey:
        data["sesskey"] = sesskey

    data["saved_at"] = int(time.time())
    data["source"] = source
    paths.write_json(paths.QMPLUS_TOKENS_FILE, data, mode=0o600)

    return session_state()


def session_state() -> dict[str, Any]:
    data = read_session()
    has = bool(data.get("MoodleSession"))

    return {
        "connected": has,
        "has_session": has,
        "saved_at": data.get("saved_at"),
        "sesskey": bool(data.get("sesskey")),
        "tokens_file": str(paths.QMPLUS_TOKENS_FILE),
    }


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


class QmplusClient:
    def __init__(self) -> None:
        self.data = read_session()
        self._sesskey: str | None = self.data.get("sesskey")

    @property
    def cookie(self) -> str:
        if not self.data.get("MoodleSession"):
            raise QmplusAuthRequired(
                "QMplus is not connected. Open the app and click 'Connect QMplus'."
            )

        return "; ".join(
            f"{k}={v}"
            for k, v in self.data.items()
            if k not in ("saved_at", "source", "sesskey") and v
        )

    def _request(
        self,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str, Any, bytes]:
        h = {"User-Agent": UA, "Cookie": self.cookie, "Referer": QMPLUS_HOME}
        if headers:
            h.update(headers)

        req = urllib.request.Request(
            QMPLUS_BASE + path if path.startswith("/") else path,
            data=data,
            headers=h,
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.geturl(), resp.headers, resp.read()
        except urllib.error.HTTPError as exc:
            exc.read()
            if exc.code in (401, 403):
                raise QmplusAuthRequired(
                    "QMplus session rejected. Reconnect QMplus in the app."
                ) from None
            raise QmplusError(f"HTTP {exc.code} on {path}") from None
        except Exception as exc:
            raise QmplusError(f"{type(exc).__name__}: {exc}") from None

    def _html(self, path: str) -> str:
        _, final, _, raw = self._request(path)
        text = raw.decode("utf-8", "replace")
        if "/login/" in final or "Log in to the site" in text:
            raise QmplusAuthRequired("QMplus session expired. Reconnect QMplus.")
        return text

    def sesskey(self) -> str:
        if self._sesskey:
            return self._sesskey

        match = re.search(r'"sesskey"\s*:\s*"([^"]+)"', self._html("/my/"))
        if not match:
            raise QmplusError("Could not find QMplus sesskey")

        self._sesskey = match.group(1)
        self.data["sesskey"] = self._sesskey
        paths.write_json(paths.QMPLUS_TOKENS_FILE, self.data, mode=0o600)

        return self._sesskey

    def _ajax(self, method: str, args: dict[str, Any]) -> Any:
        body = json.dumps([{"index": 0, "methodname": method, "args": args}]).encode()
        _, _, _, raw = self._request(
            f"/lib/ajax/service.php?sesskey={self.sesskey()}",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        try:
            payload = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise QmplusError("Invalid JSON from QMplus AJAX") from None

        if not payload:
            return None

        first = payload[0]
        if first.get("error"):
            exc = first.get("exception") or {}
            raise QmplusError(exc.get("message") or "QMplus AJAX error")

        return first.get("data")

    def courses(self) -> list[dict[str, Any]]:
        data = self._ajax(
            "core_course_get_enrolled_courses_by_timeline_classification",
            {
                "offset": 0,
                "limit": 0,
                "classification": "all",
                "sort": "fullname",
                "customfieldname": "",
                "customfieldvalue": "",
            },
        )

        return [
            {
                "id": c.get("id"),
                "name": _clean(c.get("fullname")),
                "shortname": _clean(c.get("shortname")),
                "code": _clean(c.get("idnumber")),
                "category": c.get("coursecategory"),
                "url": c.get("viewurl") or f"{QMPLUS_BASE}/course/view.php?id={c.get('id')}",
                "progress": c.get("progress"),
            }
            for c in (data or {}).get("courses", [])
        ]

    def _parse_activity(self, li: Any, section_name: str) -> dict[str, Any]:
        name = unescape(li.get("data-activityname") or "")
        if not name:
            node = li.select_one(".instancename, .activityname")
            name = _clean(node.get_text(" ", strip=True)) if node else ""

        link = li.select_one("a.aalink") or li.select_one('a[href*="/mod/"]')
        url = link.get("href") if link else ""
        if url and url.startswith("/"):
            url = QMPLUS_BASE + url

        desc_node = li.select_one(".summary, .description, .contentafterlink")
        description = _clean(desc_node.get_text(" ", strip=True)) if desc_node else ""
        files = [
            {"name": _clean(a.get_text(" ", strip=True)), "url": a["href"]}
            for a in li.select('a[href*="pluginfile.php"]')
            if a.get("href")
        ]
        mod_match = re.search(r"/mod/([a-z0-9_]+)/", url or "")

        return {
            "name": name,
            "modname": mod_match.group(1) if mod_match else "",
            "url": url,
            "description": description[:400],
            "section": section_name,
            "files": files,
        }

    def course_contents(self, course_id: int) -> dict[str, Any]:
        html = self._html(f"/course/view.php?id={int(course_id)}")
        soup = BeautifulSoup(html, "html.parser")
        title = _clean(soup.title.get_text()) if soup.title else ""
        sections: list[dict[str, Any]] = []
        activities: list[dict[str, Any]] = []
        seen_sections: set[str] = set()
        seen_activities: set[tuple[str, str]] = set()

        for sec in soup.select("li.section, div.section"):
            sec_id = sec.get("id") or ""
            node = sec.select_one("h3.sectionname, h3, [data-sectionname]")
            if node and node.get("data-sectionname"):
                sec_name = unescape(node["data-sectionname"])
            elif node:
                sec_name = _clean(node.get_text(" ", strip=True))
            else:
                sec_name = _clean(sec.get("data-sectionname") or "")

            if not sec_name:
                sec_name = sec_id.replace("section-", "Section ") if sec_id else "General"

            key = sec_id or sec_name
            if key in seen_sections:
                continue
            seen_sections.add(key)

            sec_activities: list[dict[str, Any]] = []
            for li in sec.select("li.activity"):
                act = self._parse_activity(li, sec_name)
                if not (act["name"] or act["url"]):
                    continue

                akey = (act["name"], act["url"])
                if akey in seen_activities:
                    continue
                seen_activities.add(akey)

                sec_activities.append(act)
                activities.append(act)

            sections.append(
                {
                    "id": sec_id.replace("section-", "") if sec_id else None,
                    "name": sec_name[:140],
                    "activities": sec_activities,
                }
            )

        if not activities:
            # Fallback for unusual course formats.
            for li in soup.select("li.activity"):
                act = self._parse_activity(li, "General")
                if act["name"] or act["url"]:
                    activities.append(act)
            if activities:
                sections = [{"id": None, "name": "General", "activities": activities}]

        return {
            "course_id": int(course_id),
            "title": title,
            "sections": sections,
            "activities": activities,
            "url": f"{QMPLUS_BASE}/course/view.php?id={int(course_id)}",
        }

    def _extract_links(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        out = [
            {"name": _clean(a.get_text(" ", strip=True)), "url": a["href"]}
            for a in soup.select('a[href*="pluginfile.php"]')
            if a.get("href")
        ]

        for tag, attr in (("iframe", "src"), ("object", "data"), ("embed", "src")):
            for node in soup.select(f"{tag}[{attr}*='pluginfile.php']"):
                val = node.get(attr)
                if val:
                    out.append({"name": "", "url": str(val)})

        return out

    def activity_files(self, activity: dict[str, Any]) -> list[dict[str, Any]]:
        files = list(activity.get("files") or [])
        url = activity.get("url")
        modname = activity.get("modname")

        if not url or modname not in ("resource", "folder", "page", "book", "url"):
            return files

        if modname == "url":
            return files + [{"name": activity.get("name", ""), "url": url, "link": True}]

        try:
            _, final, headers, raw = self._request(url)
        except QmplusError:
            return files

        ctype = (headers.get("Content-Type") or "").lower()
        if "html" not in ctype:
            name = _filename_from_headers(headers) or activity.get("name", "")
            return files + [{"name": name, "url": final, "file": True}]

        soup = BeautifulSoup(raw.decode("utf-8", "replace"), "html.parser")
        seen = {f.get("url") for f in files}
        for f in self._extract_links(soup):
            if f["url"] not in seen:
                files.append(f)
                seen.add(f["url"])

        return files

    def download(self, url: str) -> dict[str, Any]:
        _, final, headers, raw = self._request(url)
        name = _filename_from_headers(headers) or urllib.parse.unquote(
            url.split("?")[0].rsplit("/", 1)[-1]
        )

        return {
            "filename": name,
            "content_type": headers.get("Content-Type"),
            "size": len(raw),
            "data": raw,
            "url": final,
        }

    def fetch_url(self, url: str) -> dict[str, Any]:
        if url and url.startswith("/"):
            url = QMPLUS_BASE + url
        if not url:
            raise QmplusError("No URL supplied")

        _, final, headers, raw = self._request(url)
        ctype = (headers.get("Content-Type") or "").lower()
        if "html" not in ctype:
            name = _filename_from_headers(headers) or final.rsplit("/", 1)[-1]
            return {
                "ok": True,
                "type": "file",
                "filename": name,
                "url": final,
                "content_type": ctype,
                "size": len(raw),
                "text": extract_text(raw, name, ctype),
            }

        soup = BeautifulSoup(raw.decode("utf-8", "replace"), "html.parser")
        files: list[dict[str, Any]] = []
        for f in self._extract_links(soup)[:8]:
            try:
                got = self.download(f["url"])
            except QmplusError:
                continue

            files.append(
                {
                    "name": f.get("name") or got["filename"],
                    "url": got["url"],
                    "content_type": got["content_type"],
                    "size": got["size"],
                    "text": extract_text(got["data"], got["filename"], got["content_type"]),
                }
            )

        title = _clean(soup.title.get_text()) if soup.title else ""
        return {
            "ok": True,
            "type": "page",
            "title": title[:160],
            "url": url,
            "text": _clean(soup.get_text(" ", strip=True))[:20000],
            "files": files,
        }

    def search(
        self,
        course_id: int,
        query: str,
        deep: bool = False,
        limit: int = 25,
    ) -> dict[str, Any]:
        q = (query or "").strip().lower()
        if not q:
            raise QmplusError("Search query is empty")

        contents = self.course_contents(course_id)
        results: list[dict[str, Any]] = []

        for section in contents["sections"]:
            if q in section["name"].lower():
                results.append(
                    {
                        "type": "section",
                        "section": section["name"],
                        "name": section["name"],
                        "snippet": "",
                    }
                )

            for act in section["activities"]:
                hay = f'{act["name"]} {act.get("description", "")}'.lower()
                if q in hay:
                    results.append(
                        {
                            "type": "activity",
                            "section": section["name"],
                            "name": act["name"],
                            "modname": act.get("modname"),
                            "url": act.get("url"),
                            "snippet": act.get("description", "")[:300],
                        }
                    )

        if deep:
            checked = 0
            for section in contents["sections"]:
                for act in section["activities"]:
                    if checked >= 12 or len(results) >= limit:
                        break

                    for f in self.activity_files(act):
                        if checked >= 12 or len(results) >= limit:
                            break
                        if f.get("link"):
                            continue

                        try:
                            got = self.download(f["url"])
                        except QmplusError:
                            continue

                        text = extract_text(got["data"], got["filename"], got["content_type"])
                        checked += 1

                        if text and q in text.lower():
                            idx = text.lower().find(q)
                            results.append(
                                {
                                    "type": "file",
                                    "section": section["name"],
                                    "name": f.get("name") or got["filename"],
                                    "url": got["url"],
                                    "snippet": _clean(text[max(0, idx - 120):idx + 240]),
                                }
                            )

        return {"course_id": int(course_id), "query": query, "results": results[:limit]}

    def calendar_events(
        self,
        year: int | None = None,
        month: int | None = None,
        course_id: int = 1,
    ) -> list[dict[str, Any]]:
        today = dt.date.today()
        data = self._ajax(
            "core_calendar_get_calendar_monthly_view",
            {
                "year": int(year or today.year),
                "month": int(month or today.month),
                "courseid": int(course_id),
                "categoryid": 0,
                "includenavigation": False,
                "mini": False,
            },
        )

        return [
            {
                "name": _clean(ev.get("name")),
                "url": ev.get("url"),
                "timesort": ev.get("timesort"),
                "start": dt.datetime.fromtimestamp(ev.get("timesort", 0)).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),
                "course": (ev.get("course") or {}).get("fullname"),
                "eventtype": ev.get("eventtype"),
            }
            for week in (data or {}).get("weeks", [])
            for day in week.get("days", [])
            for ev in day.get("events", [])
        ]

    def current_lecture(self) -> dict[str, Any]:
        from timelog.server.modules import calendar as ombiel_calendar

        today = dt.date.today()
        try:
            events = ombiel_calendar.CalendarClient().range_events(
                today.isoformat(), today.isoformat()
            )
        except Exception:
            events = []

        now = dt.datetime.now().astimezone()
        current: dict[str, Any] | None = None
        upcoming: dict[str, Any] | None = None

        for e in events:
            try:
                start = dt.datetime.fromisoformat(e["start"])
                end = dt.datetime.fromisoformat(e["end"]) if e.get("end") else start
            except Exception:
                continue

            if start <= now <= end:
                current = e
                break
            if start > now and (
                upcoming is None or start < dt.datetime.fromisoformat(upcoming["start"])
            ):
                upcoming = e

        event = current or upcoming
        if not event:
            return {"ok": False, "error": "No current or upcoming class found in CampusM today."}

        code_match = re.search(r"\b([A-Z]{2,4}\d{3,4}[A-Z]?)\b", event.get("title", ""))
        code = code_match.group(1) if code_match else ""
        courses = self.courses()

        course = next(
            (
                c
                for c in courses
                if code
                and code.upper()
                in f'{c.get("code", "")} {c.get("shortname", "")} {c.get("name", "")}'.upper()
            ),
            None,
        )
        if course is None:
            words = [w for w in re.split(r"\W+", event.get("title", "")) if len(w) > 4][:4]
            course = next(
                (
                    c
                    for c in courses
                    if all(
                        w.lower() in (c.get("name", "") + c.get("shortname", "")).lower()
                        for w in words
                    )
                ),
                None,
            )

        out: dict[str, Any] = {
            "ok": True,
            "event": event,
            "course_code": code,
            "course": course,
            "section": None,
            "activities": [],
            "files": [],
        }
        if not course:
            return out

        contents = self.course_contents(course["id"])
        week = None

        try:
            event_day = (event.get("start") or "")[:10]
            if event_day:
                day = dt.date.fromisoformat(event_day)
                for qe in self.calendar_events(day.year, day.month, course["id"]):
                    if (qe.get("start") or "")[:10] == event_day:
                        match = re.search(r"Week\s+([0-9A-Za-z]+)", qe.get("name", ""), re.I)
                        if match:
                            week = match.group(1)
                            break
        except Exception:
            pass

        title = event.get("title", "").lower()
        keywords = [
            w
            for w in re.split(r"\W+", title)
            if w in ("lab", "lecture", "seminar", "workshop") or w.isdigit()
        ]

        best = None
        if week:
            best = next(
                (
                    s
                    for s in contents["sections"]
                    if re.search(rf"Week\s+{re.escape(week)}\b", s["name"], re.I)
                ),
                None,
            )
        if best is None:
            best = next(
                (
                    s
                    for s in contents["sections"]
                    if any(k in s["name"].lower() for k in keywords if len(k) > 3)
                ),
                None,
            )
        if best is None:
            best = next((s for s in reversed(contents["sections"]) if s["activities"]), None)

        if best:
            out["section"] = best
            acts = best["activities"]
            out["activities"] = [
                a for a in acts if any(k in a["name"].lower() for k in keywords if len(k) > 3)
            ] or acts[:8]

            for act in out["activities"][:5]:
                for f in self.activity_files(act)[:4]:
                    out["files"].append({"activity": act["name"], **f})

        out["course_url"] = contents["url"]
        out["section_count"] = len(contents["sections"])
        out["week"] = week

        return out


def _filename_from_headers(headers: Any) -> str:
    disposition = headers.get("Content-Disposition") or ""
    match = re.search(r"filename\*?=(?:UTF-8''|)([^;]+)", disposition, re.I)
    return urllib.parse.unquote(match.group(1).strip().strip('"')) if match else ""


def extract_text(data: bytes, filename: str, content_type: str = "") -> str | None:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    try:
        if name.endswith(".pdf") or "pdf" in ctype:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages[:100])[:60000]

        if name.endswith(".pptx") or "presentation" in ctype:
            from pptx import Presentation

            prs = Presentation(io.BytesIO(data))
            parts = [
                shape.text
                for slide in prs.slides
                for shape in slide.shapes
                if hasattr(shape, "text") and shape.text
            ]
            return "\n".join(parts)[:60000]

        if name.endswith((".txt", ".md", ".csv", ".json")):
            return data.decode("utf-8", "replace")[:60000]
    except Exception:
        return None

    return None
