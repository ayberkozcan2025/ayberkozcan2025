"""Blue dimensional README badges; dynamic values are daily snapshots.

The README retains the original Komarev image request to keep counting hits.
Komarev counts requests, including this generator's request, not unique people.
SVG images embedded by GitHub cannot react to mouse hover or run JavaScript.
"""

import argparse
from datetime import datetime, timezone
from html import escape
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET


def parse_views(svg):
    root = ET.fromstring(svg)
    label = root.get("aria-label", "")
    match = re.search(r":\s*([\d, ]+)\s*$", label)
    if not match:
        # Shields-compatible responses may only include a title or SVG text.
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1] in {"title", "text"}:
                label = "".join(node.itertext()).strip()
                match = re.fullmatch(r"(?:Profile views:\s*)?([\d, ]+)", label)
                if match:
                    break
    if not match:
        raise ValueError("The counter did not return a numeric value")
    return str(int(match.group(1).replace(",", "").replace(" ", "")))


def views(username):
    query = urlencode({"username": username, "label": "Profile views", "color": "64748b", "style": "flat"})
    with urlopen("https://komarev.com/ghpvc/?" + query, timeout=20) as response:
        return parse_views(response.read())


ICONS = {
    "views": '<path d="M-10 0s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/><circle r="3"/>',
    "status": '<path d="m-8-5-5 5 5 5M8-5l5 5-5 5M3-9l-6 18"/>',
}


def badge(kind, label, value, width, updated):
    status = kind == "status"
    size = 15 if status else 22
    value = escape(value)
    subtitle = ("Actively Learning & Building" if status else "Günlük özet · " + updated)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="90" viewBox="0 0 {width} 90" role="img" aria-labelledby="title desc">
<title id="title">{escape(label)}: {value}</title>
<desc id="desc">{escape(subtitle)}. Mavi gradient ve hafif otomatik yaylanma animasyonu.</desc>
<defs>
  <linearGradient id="face" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#173a78"/><stop offset=".52" stop-color="#1769aa"/><stop offset="1" stop-color="#168fc5"/></linearGradient>
  <linearGradient id="rim" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#b5eeff" stop-opacity=".85"/><stop offset="1" stop-color="#349bd1" stop-opacity=".3"/></linearGradient>
  <linearGradient id="shine" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".14"/><stop offset=".65" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <filter id="shadow" x="-15%" y="-30%" width="130%" height="170%"><feDropShadow dx="0" dy="5" stdDeviation="3" flood-color="#020e26" flood-opacity=".3"/></filter>
</defs>
<style>
text{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif}}
.surface{{animation:settle 7s ease-in-out infinite;transform-origin:center;transform-box:fill-box}}
@keyframes settle{{0%,72%,100%{{transform:translateY(0)}}80%{{transform:translateY(-2px)}}87%{{transform:translateY(1px)}}93%{{transform:translateY(-.5px)}}}}
@media(prefers-reduced-motion:reduce){{.surface{{animation:none}}}}
</style>
<g filter="url(#shadow)">
  <rect x="7" y="15" width="{width-14}" height="64" rx="14" fill="#0b2854"/>
  <g class="surface">
    <rect x="7" y="9" width="{width-14}" height="64" rx="14" fill="url(#face)" stroke="url(#rim)"/>
    <rect x="8" y="10" width="{width-16}" height="62" rx="13" fill="url(#shine)"/>
    <path d="M22 11H{width-22}" stroke="#d4f4ff" stroke-opacity=".35" stroke-linecap="round"/>
    <rect x="19" y="24" width="34" height="34" rx="10" fill="#071d46" fill-opacity=".27" stroke="#b9eaff" stroke-opacity=".17"/>
    <g transform="translate(36 41)" fill="none" stroke="#d0f4ff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{ICONS[kind]}</g>
    <text x="65" y="32" fill="#cae9ff" font-size="10" font-weight="600" letter-spacing="1.1">{escape(label.upper())}</text>
    <text x="65" y="55" fill="#ffffff" font-size="{size}" font-weight="600">{value}</text>
  </g>
</g>
</svg>
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.environ.get("PROFILE_USERNAME", "ayberkozcan2025"))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    for kind, label, width, source in [
        ("views", "Profile Views", 192, views),
        ("status", "Status", 320, lambda _: "Actively Learning & Building"),
    ]:
        try:
            value = source(args.username)
            updated = date
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, ET.ParseError) as error:
            # A service outage must not publish invented counts or stop other visuals.
            value, updated = "—", "Veri kaynağına ulaşılamadı"
            print(f"Warning: {kind} is unavailable ({type(error).__name__})")
        (args.output / f"badge-{kind}.svg").write_text(badge(kind, label, value, width, updated))
    print("Generated Profile Views and Status badges. Followers uses a live Shields endpoint.")


if __name__ == "__main__":
    main()
