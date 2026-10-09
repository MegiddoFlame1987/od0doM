"""Wywołanie Claude i ścisła walidacja odpowiedzi."""
import hashlib
import json
import re
from string import Template

import confload
from common import ROOT

config = confload.load()


def prompt_text() -> str:
    return (ROOT / config.PROMPT_FILE).read_text(encoding="utf-8")


def prompt_sha256() -> str:
    return hashlib.sha256(prompt_text().encode("utf-8")).hexdigest()


def parse_forecast(text: str, allowed=None) -> dict:
    """Zwraca {kierunek, pewnosc, powod} albo rzuca ValueError."""
    allowed = allowed or getattr(config, "DIRECTIONS", ("LONG", "SHORT"))
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("brak JSON w odpowiedzi")
    d = json.loads(m.group(0))
    kierunek = str(d.get("kierunek", "")).strip().upper()
    if kierunek not in allowed:
        raise ValueError(f"zły kierunek: {kierunek!r}")
    pewnosc = d.get("pewnosc")
    if isinstance(pewnosc, bool) or not isinstance(pewnosc, int) or not 1 <= pewnosc <= 5:
        raise ValueError(f"zła pewność: {pewnosc!r}")
    powod = str(d.get("powod", "")).strip()
    if not powod:
        raise ValueError("pusty powód")
    return {"kierunek": kierunek, "pewnosc": pewnosc, "powod": powod}


def build_messages(inst: dict, day: str, headlines: list):
    system = Template(prompt_text()).substitute(
        ticker=inst["ticker"], sector_en=inst["sector_en"], date=day)
    if headlines:
        lines = "\n".join(f"- [{h['czas_utc']} UTC] {h['tytul']}" for h in headlines)
    else:
        lines = "(no headlines in the last 24 hours)"
    user = f"Headlines for {inst['sector_en']}:\n{lines}"
    return system, user


def claude_forecast(inst: dict, day: str, headlines: list) -> dict:
    import anthropic  # import tylko w produkcji
    client = anthropic.Anthropic()
    system, user = build_messages(inst, day, headlines)
    last_err = None
    for _ in range(2):  # jedna ponowna próba przy złym formacie
        msg = client.messages.create(
            model=config.MODEL, max_tokens=400, system=system,
            messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        try:
            return parse_forecast(text)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
    raise ValueError(f"niepoprawna odpowiedź modelu: {last_err}")
