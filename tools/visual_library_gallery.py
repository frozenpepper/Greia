"""Offline visual gallery over Greia's existing semantic authoring library.

This is developer tooling, not an Activity, remote service, or second catalogue.
All resource paths are checked against the permitted source tree before emitting
relative URLs. Browser rendering is only on the authoring workstation, never
inside Greia's low-resource child runtime.
"""
from __future__ import annotations

from html import escape
import os
from pathlib import Path
from urllib.parse import quote


class VisualGalleryError(ValueError):
    pass


def _source_url(source_path: object, *, repository: Path, output: Path) -> str:
    if not isinstance(source_path, str):
        raise VisualGalleryError("art resource needs a source_path")
    source_root = (repository / "assets" / "visual").resolve(strict=True)
    source = (repository / source_path).resolve(strict=True)
    if not source.is_file() or not source.is_relative_to(source_root):
        raise VisualGalleryError(f"art source outside reviewed visual tree: {source_path}")
    relative = Path(os.path.relpath(source, output.parent.resolve()))
    return quote(relative.as_posix(), safe="/-._~")


def render_gallery(items: list[dict[str, object]], *, repository: Path, output: Path) -> str:
    """Produce deterministic browser-only HTML, without modifying any art asset."""
    seen: set[str] = set()
    cards: list[str] = []
    counts = {"preferred": 0, "candidate_reference": 0}
    for item in sorted(items, key=lambda value: str(value.get("id", ""))):
        asset_id = item.get("id")
        status = item.get("library_status")
        if not isinstance(asset_id, str) or not asset_id or asset_id in seen:
            raise VisualGalleryError(f"missing/duplicate visual id: {asset_id!r}")
        if status not in counts:
            raise VisualGalleryError(f"unknown visual status for {asset_id}: {status!r}")
        seen.add(asset_id)
        counts[status] += 1
        path = _source_url(item.get("source_path"), repository=repository, output=output)
        category = str(item.get("collection_name", "Uncategorized"))
        search = " ".join(str(item.get(key, "")) for key in
                          ("id", "role", "family", "notes", "collection_name", "source_pack"))
        tags = item.get("tags", [])
        if isinstance(tags, list):
            search += " " + " ".join(map(str, tags))
        label = "Preferred" if status == "preferred" else "Candidate reference"
        kind = str(item.get("item_type", "finished"))
        cards.append(
            '<article class="asset" data-status="' + escape(status, quote=True) +
            '" data-collection="' + escape(category, quote=True) +
            '" data-search="' + escape(search.casefold(), quote=True) + '">' +
            '<div class="preview"><img src="' + escape(path, quote=True) +
            '" alt="' + escape(asset_id, quote=True) + '" loading="lazy"></div>' +
            '<div class="details"><span class="state">' + label + "</span>" +
            '<span class="kind">' + escape(kind) + "</span>" +
            "<h2>" + escape(asset_id) + "</h2>" +
            "<p>" + escape(str(item.get("notes", item.get("role", "")))) + "</p>" +
            '<div class="foot"><span>' + escape(category) + '</span>' +
            '<a href="' + escape(path, quote=True) + '" target="_blank" rel="noopener">Open source ↗</a></div>' +
            "</div></article>"
        )
    note = (f"{len(items)} source resources · {counts['preferred']} preferred · "
            f"{counts['candidate_reference']} candidate references")
    # A single self-contained document: no CDN, backend, or collection mutation.
    markup = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Greia · Visual Library</title>
<style>
:root{color-scheme:light;--paper:#f7f4ec;--white:#fffdfa;--ink:#23313a;--muted:#596974;--line:#e3ddd0;--accent:#2b7e78}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 "Nunito Sans",system-ui,sans-serif}
header{max-width:1440px;margin:auto;padding:36px 28px 16px}h1{font-size:clamp(29px,4vw,48px);letter-spacing:-.045em;margin:0}
.subtitle{max-width:760px;color:var(--muted);font-size:17px;margin:8px 0 24px}
.controls{display:flex;gap:12px;flex-wrap:wrap;padding-bottom:20px}
input,select{border:1px solid #bcb7aa;border-radius:15px;background:var(--white);font:inherit;padding:12px 16px;color:var(--ink)}
input{flex:2;min-width:240px}select{flex:1;min-width:170px}
main{max-width:1440px;margin:auto;padding:0 28px 70px}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:20px}
.asset{background:var(--white);border:1px solid var(--line);border-radius:20px;overflow:hidden;box-shadow:0 5px 21px #23313a0a}
.preview{height:248px;display:grid;place-items:center;background:linear-gradient(140deg,#f8f0df,#edf3ee);padding:20px}
.preview img{max-width:100%;max-height:100%;object-fit:contain}
.details{padding:18px 19px 20px}.state,.kind{font-size:12px;font-weight:750;letter-spacing:.04em;text-transform:uppercase}
.state{color:var(--accent)}.kind{color:var(--muted);float:right}
h2{font-size:15px;line-height:1.35;overflow-wrap:anywhere;margin:12px 0 7px}
.details p{font-size:14px;color:var(--muted);margin:0 0 16px;min-height:40px}
.foot{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.foot a{font-size:12px;color:#09665e;text-decoration:underline}
.asset[hidden]{display:none}#results{margin:0 0 17px;color:var(--muted)}
@media(prefers-reduced-motion:no-preference){.asset{transition:box-shadow .14s}.asset:hover{box-shadow:0 8px 29px #23313a17}}
</style></head>
<body><header><h1>Greia Visual Library</h1><p class="subtitle">Explore our reusable artwork source masters. Search by object, meaning or role. Preferred assets are reviewed for reuse; candidates are references for adaptation—not automatically approved finished art.</p>
<div class="controls"><input id="search" aria-label="Search visuals" placeholder="Try tree, lamp, book, shadow…" type="search">
<select id="collection" aria-label="Collection"><option value="">All collections</option></select>
<select id="status" aria-label="Review status"><option value="">All statuses</option><option value="preferred">Preferred</option><option value="candidate_reference">Candidate reference</option></select></div>
</header><main><p id="results" aria-live="polite"></p><div id="grid">__CARDS__</div></main>
<script>
"use strict";
const cards=Array.from(document.querySelectorAll(".asset"));
const search=document.getElementById("search"),collection=document.getElementById("collection"),status=document.getElementById("status");
[...new Set(cards.map(el=>el.dataset.collection))].sort().forEach(label=>{const option=document.createElement("option");option.value=label;option.textContent=label;collection.append(option)});
function update(){const q=search.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
let count=0;for(const card of cards){const ok=q.every(word=>card.dataset.search.includes(word))&&(!collection.value||card.dataset.collection===collection.value)&&(!status.value||card.dataset.status===status.value);card.hidden=!ok;if(ok)count++}
document.getElementById("results").textContent=count+" of "+cards.length+" resources shown";}
for(const control of [search,collection,status])control.addEventListener("input",update);
update();
</script></body></html>"""
    return markup.replace("__CARDS__", "\n".join(cards)).replace(
        "<title>Greia · Visual Library</title>",
        "<title>Greia · Visual Library</title><!-- " + escape(note) + " -->",
    )


def write_gallery(items: list[dict[str, object]], *, repository: Path, output: Path) -> Path:
    """Reject existing paths by default: caller chooses an explicit disposable output."""
    if output.is_symlink() or output.exists():
        raise VisualGalleryError("gallery output already exists; choose a fresh path")
    if not output.parent.is_dir():
        raise VisualGalleryError("gallery output parent does not exist")
    html = render_gallery(items, repository=repository, output=output)
    # Exclusive creation prevents a concurrent authoring job from overwriting
    # a file that did not exist during the initial safety check.
    try:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(html)
    except FileExistsError as exc:
        raise VisualGalleryError("gallery output already exists") from exc
    return output


__all__ = ["VisualGalleryError", "render_gallery", "write_gallery"]
