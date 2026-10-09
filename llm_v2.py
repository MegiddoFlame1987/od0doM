"""Ocena ryzyka z nagłówków dla v2."""
import hashlib
import json
import re
from string import Template

import config_v2 as C
from common import ROOT


def prompt_text() -> str:
    return (ROOT / C.PROMPT_FILE).read_text(encoding="utf-8")


def prompt_sha256() -> str:
    return hashlib.sha256(prompt_text().encode("utf-8")).hexdigest()


def parse_risk(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("brak JSON w odpowiedzi")
    d = json.loads(m.group(0))
    ryzyko = str(d.get("ryzyko", "")).strip().upper()
    if ryzyko not in ("NISKIE", "WYSOKIE"):
        raise ValueError(f"złe ryzyko: {ryzyko!r}")
    powod = str(d.get("powod", "")).strip()
    if not powod:
        raise ValueError("pusty powód")
    return {"ryzyko": ryzyko, "powod": powod}


def build_messages(asset: dict, day: str, headlines: list, direction: str):
    system = Template(prompt_text()).substitute(
        ticker=asset["ticker"], theme_en=asset["theme_en"], date=day, direction=direction)
    if headlines:
        lines = "\n".join(f"- [{h['czas_utc']} UTC] {h['tytul']}" for h in headlines)
    else:
        lines = "(no headlines in the last 24 hours)"
    return system, f"Headlines for {asset['theme_en']}:\n{lines}"


def claude_risk(asset: dict, day: str, headlines: list, direction: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    system, user = build_messages(asset, day, headlines, direction)
    last_err = None
    for _ in range(2):
        msg = client.messages.create(model=C.MODEL, max_tokens=300, system=system,
                                     messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        try:
            return parse_risk(text)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
    raise ValueError(f"niepoprawna odpowiedź modelu: {last_err}")
