"""Generate profile SVG cards from public GitHub data using only the stdlib."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


THEMES = {
    "light": ("#ffffff", "#e2e8f0", "#0f172a", "#64748b", "#0284c7", "#f1f5f9"),
    "dark": ("#0d1117", "#30363d", "#e2e8f0", "#94a3b8", "#38bdf8", "#161b22"),
}
COLORS = ["#0ea5e9", "#6366f1", "#14b8a6", "#f59e0b", "#a78bfa", "#64748b"]


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-cards"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
        return json.load(response)


def public_data(username):
    user = quote(username, safe="")
    profile = api(f"/users/{user}")
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{user}/repos?type=owner&per_page=100&page={page}")
        repos.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            break
        page += 1
    originals = [repo for repo in repos if not repo["fork"]]
    languages = Counter()
    for repo in originals:
        languages.update(api(f"/repos/{user}/{quote(repo['name'], safe='')}/languages"))
    return profile, originals, languages


def text(x, y, value, size=13, color="muted", weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" class="{color}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def card(theme, title, subtitle, body, width=410, height=250):
    bg, border, fg, muted, accent, track = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)} — {escape(subtitle)}</title>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif}}.fg{{fill:{fg}}}.muted{{fill:{muted}}}.accent{{fill:{accent}}}.track{{fill:{track}}}</style>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="16" fill="{bg}" stroke="{border}"/>
<rect x="24" y="26" width="3" height="19" rx="1.5" fill="{accent}"/>
{text(38, 41, title, 17, 'fg', 600)}
{text(24, 65, subtitle, 11)}
{body}
</svg>'''


def stats(theme, profile, repos, languages, date):
    values = [(len(repos), "Açık kaynak depo"),
              (sum(repo["stargazers_count"] for repo in repos), "Kazanılan yıldız"),
              (profile["followers"], "Takipçi"),
              (len(languages), "Kullanılan dil")]
    body = []
    for index, (value, label) in enumerate(values):
        x, y = 24 + (index % 2) * 190, 110 + (index // 2) * 68
        body += [text(x, y, value, 28, "fg", 600), text(x, y + 21, label, 12)]
    body.append(text(24, 230, f"Fork hariç · Güncellendi: {date}", 10))
    return card(theme, "GitHub’a genel bakış", "Açık projeler ve topluluk", "".join(body))


def language_card(theme, languages):
    total = sum(languages.values())
    if not total:
        return card(theme, "Kodun dili", "Açık depolardaki kod dağılımı · Fork hariç",
                    text(205, 130, "</>", 32, "accent", 500, "middle")
                    + text(205, 163, "Henüz dil verisi bulunmuyor", 13, "fg", 500, "middle")
                    + text(205, 186, "Açık kod depoları eklendikçe burada görünür.", 11, anchor="middle"))
    entries = languages.most_common(5)
    remaining = total - sum(value for _, value in entries)
    if remaining:
        entries.append(("Diğer", remaining))
    body = ['<defs><clipPath id="bar"><rect x="24" y="88" width="362" height="10" rx="5"/></clipPath></defs><g clip-path="url(#bar)">']
    x = 24
    for index, (_, value) in enumerate(entries):
        width = value / total * 362
        body.append(f'<rect x="{x:.3f}" y="88" width="{width:.3f}" height="10" fill="{COLORS[index]}"/>')
        x += width
    body.append('</g>')
    for index, (name, value) in enumerate(entries):
        x, y = 24 + (index % 2) * 190, 130 + (index // 2) * 31
        body.append(f'<circle cx="{x+4}" cy="{y-4}" r="4" fill="{COLORS[index]}"/>')
        label = name if len(name) <= 15 else name[:14] + "…"
        body += [text(x + 15, y, label, 12, "fg"),
                 text(x + 171, y, f"{value / total:.1%}", 11, anchor="end")]
    body.append(text(24, 230, "GitHub Linguist · Kod baytı oranı", 10))
    return card(theme, "Kodun dili", "Açık depolardaki kod dağılımı · Fork hariç", "".join(body))


def frame_snake(directory, theme):
    suffix = "-dark" if theme == "dark" else ""
    path = directory / f"github-contribution-grid-snake{suffix}.svg"
    if not path.exists():
        return
    # Preserve the generated animation and its viewBox; only add a card around it.
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.fromstring(path.read_text())
    root.set("x", "16")
    root.set("y", "82")
    root.set("width", "848")
    root.set("height", "185")
    body = ET.tostring(root, encoding="unicode")
    dots = (["#eff6ff", "#bae6fd", "#7dd3fc", "#38bdf8", "#0284c7"]
            if theme == "light" else ["#161b22", "#0c4a6e", "#0369a1", "#0ea5e9", "#7dd3fc"])
    body += text(24, 287, "Her kare bir gün · Katkı yoğunluğu", 11)
    body += text(680, 287, "Az", 11)
    for index, color in enumerate(dots):
        body += f'<rect x="{704+index*20}" y="276" width="13" height="13" rx="3" fill="{color}"/>'
    body += text(815, 287, "Çok", 11)
    output = card(theme, "Bir yıl, gün gün", "Son 12 ayın GitHub katkıları · Her gün güncellenir", body, 880, 310)
    (directory / f"contributions{suffix}.svg").write_text(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.environ.get("PROFILE_USERNAME", "ayberkozcan2025"))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    profile, repos, languages = public_data(args.username)
    args.output.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    for theme in THEMES:
        suffix = "-dark" if theme == "dark" else ""
        (args.output / f"stats{suffix}.svg").write_text(stats(theme, profile, repos, languages, date))
        (args.output / f"languages{suffix}.svg").write_text(language_card(theme, languages))
        frame_snake(args.output, theme)
    print(f"Generated cards for {args.username}: {len(repos)} public non-fork repositories.")


if __name__ == "__main__":
    main()
