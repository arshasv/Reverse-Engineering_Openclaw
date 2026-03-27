#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "openclaw-output"
DOMMAP_PATH = OUTPUT_DIR / "domMap.json"
LOGS_PATH = OUTPUT_DIR / "logs.json"
MD_OUT = OUTPUT_DIR / "md"
ROOT_FUNCTIONALITY_PATH = ROOT_DIR / "functionality.md"
MD_FUNCTIONALITY_PATH = MD_OUT / "functionality.md"


def read_json(file_path: Path):
    with file_path.open("r", encoding="utf8") as handle:
        return json.load(handle)


def ensure_dir(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)


def write_file(file_path: Path, content: str) -> None:
    with file_path.open("w", encoding="utf8") as handle:
        handle.write(content.rstrip() + "\n")


def normalize_text(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def truncate(text: str, max_length: int = 110) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def join_human(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def sanitize(value: str) -> str:
    sanitized = re.sub(r"^https?://", "", str(value))
    sanitized = re.sub(r"[\\/:?&=#\s]+", "_", sanitized)
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = re.sub(r"^_+|_+$", "", sanitized)
    return sanitized[:80]


def image_exists(file_name: str) -> bool:
    return (OUTPUT_DIR / file_name).exists()


def get_pathname(url: str) -> str:
    try:
        pathname = urlparse(url).path or "/"
    except ValueError:
        return "/"
    if pathname == "/":
        return "/"
    return re.sub(r"/+$", "", pathname) or "/"


def get_page_title(url: str) -> str:
    pathname = get_pathname(url)

    if pathname == "/":
        return "Homepage"
    if pathname == "/demo":
        return "Demo Page"
    if pathname == "/pricing":
        return "Pricing Page"
    if pathname == "/love":
        return "Wall of Love Page"
    if pathname == "/about":
        return "About Page"
    if pathname == "/contact":
        return "Contact Page"

    if pathname.startswith("/compare/"):
        competitor = pathname.strip("/").split("/")[-1] or "competitor"
        return f"Comparison Page ({competitor})"

    return f"Page {pathname}"


def get_page_purpose(url: str) -> str:
    pathname = get_pathname(url)

    if pathname == "/":
        return (
            "Landing page designed to move visitors from product discovery into a free "
            "trial, a demo, supporting resources, or a proof point such as testimonials "
            "and case studies."
        )

    if pathname == "/demo":
        return (
            "Dedicated demo page focused on showing the product in action with video "
            "playback, chapter/audio controls, and conversion paths into signup."
        )

    if pathname == "/pricing":
        return (
            "Pricing page centered on plan discovery, trial prompts, and helping "
            "visitors compare value before starting signup."
        )

    if pathname == "/love":
        return (
            "Social-proof page that highlights customer success stories and "
            "testimonials while still keeping trial and navigation CTAs available."
        )

    if pathname == "/about":
        return (
            "Company information page that introduces the team, brand story, and "
            "related trust-building content."
        )

    if pathname == "/contact":
        return (
            "Contact and community page that routes visitors toward support channels, "
            "educational content, and direct outreach options."
        )

    if pathname == "/compare/jobber":
        return (
            "Competitor comparison page built to position ZenMaid against Jobber and "
            "push comparison shoppers toward a trial or pricing review."
        )

    if pathname == "/compare/bookingkoala":
        return (
            "Competitor comparison page built to position ZenMaid against BookingKoala "
            "and move visitors toward a trial or pricing review."
        )

    if pathname == "/compare/launch27":
        return (
            "Competitor comparison page built to position ZenMaid against Launch27 and "
            "move visitors toward a trial or pricing review."
        )

    return "Content page captured during the OpenClaw dry-run analysis."


def derive_action_label(text: str, selector: str, page_url: str) -> str:
    clean = normalize_text(text)

    if not clean:
        if (selector or "").startswith("input"):
            return "Form input"
        if (selector or "").startswith("button"):
            return "Button"
        return f"Unlabeled control on {get_page_title(page_url)}"

    label = clean
    cut_patterns = [
        re.compile(r"\s+Read article", re.IGNORECASE),
        re.compile(r"\s+Read case study", re.IGNORECASE),
        re.compile(r"\s+Learn more", re.IGNORECASE),
        re.compile(r"\s+See pricing", re.IGNORECASE),
        re.compile(r"\s+Start your free trial", re.IGNORECASE),
        re.compile(r"\s+Get started for free", re.IGNORECASE),
    ]

    for pattern in cut_patterns:
        match = pattern.search(label)
        if match and match.start() > 0:
            label = label[: match.start()].strip()
            break

    if re.fullmatch(r"\d+", label) and get_pathname(page_url) == "/pricing":
        return f"Pricing control ({label})"

    return truncate(label, 100)


def infer_action_function(action: dict, page_url: str) -> dict[str, str]:
    label = derive_action_label(action.get("text"), action.get("selector"), page_url)
    text = normalize_text(action.get("text")).lower()
    selector = str(action.get("selector") or "").lower()
    tag = str(action.get("tag") or "").upper()
    pathname = get_pathname(page_url)

    if re.search(r"features", text):
        return {
            "label": label,
            "category": "feature discovery",
            "description": "opens or highlights the product features navigation.",
        }

    if re.search(r"how it works", text):
        return {
            "label": label,
            "category": "workflow guidance",
            "description": "explains the product workflow and onboarding journey.",
        }

    if re.search(r"pricing", text):
        return {
            "label": label,
            "category": "pricing discovery",
            "description": "takes visitors toward plan and pricing information.",
        }

    if re.search(
        r"resources|magazine|read article|keywords every maid service|ads to increase|free tools",
        text,
        re.IGNORECASE,
    ):
        return {
            "label": label,
            "category": "resource discovery",
            "description": "opens educational content, articles, or growth resources.",
        }

    if re.search(r"log in|login", text):
        return {
            "label": label,
            "category": "account access",
            "description": "routes existing customers into the authentication flow.",
        }

    if re.search(
        r"get started|start your free trial|free trial|try zenmaid|try free|automate your back office today",
        text,
    ):
        return {
            "label": label,
            "category": "trial signup",
            "description": "starts or promotes the free-trial signup flow.",
        }

    if re.search(r"watch a demo|demo", text):
        return {
            "label": label,
            "category": "demo access",
            "description": "opens or promotes the product demo experience.",
        }

    if re.search(r"play video|click for sound|mute|fullscreen|chapter", text):
        return {
            "label": label,
            "category": "video controls",
            "description": (
                "controls demo video playback, audio, fullscreen mode, or chapter "
                "navigation."
            ),
        }

    if re.search(r"wall of love|testimonials|testimonial", text):
        return {
            "label": label,
            "category": "customer proof",
            "description": "opens testimonial and social-proof content.",
        }

    if re.search(r"case study", text):
        return {
            "label": label,
            "category": "case studies",
            "description": "opens a case study about customer outcomes.",
        }

    if re.search(r"jobber|bookingkoala|launch27|compare zenmaid to", text):
        return {
            "label": label,
            "category": "competitor comparison",
            "description": "takes visitors to a competitor comparison experience.",
        }

    if re.search(r"contact us|talk to our team|contact", text):
        return {
            "label": label,
            "category": "contact routing",
            "description": "routes visitors toward contact or sales conversations.",
        }

    if re.search(r"about us|about\b", text):
        return {
            "label": label,
            "category": "company information",
            "description": "opens company background and team information.",
        }

    if re.search(r"get the free pdf|get free access|free pdf", text):
        return {
            "label": label,
            "category": "lead capture",
            "description": (
                "collects lead information for a downloadable resource or gated content."
            ),
        }

    if re.search(r"mastermind|chat with 5000", text):
        return {
            "label": label,
            "category": "community access",
            "description": "opens the ZenMaid community or mastermind destination.",
        }

    if pathname == "/about" and re.search(
        r"chris schwab|amar ghaghada|team|founder", text
    ):
        return {
            "label": label,
            "category": "team profiles",
            "description": "opens a team member or founder profile.",
        }

    if pathname == "/love" and re.search(
        r"mindy|lashanda|tripled|business owner|maid service", text
    ):
        return {
            "label": label,
            "category": "customer stories",
            "description": "opens a detailed customer success story.",
        }

    if re.fullmatch(r"\d+", normalize_text(action.get("text"))) and pathname == "/pricing":
        return {
            "label": label,
            "category": "pricing controls",
            "description": (
                "appears to be part of an interactive pricing control or calculator."
            ),
        }

    if tag == "BUTTON":
        return {
            "label": label,
            "category": "form submission",
            "description": "submits a form or advances a conversion flow.",
        }

    if tag == "INPUT":
        return {
            "label": label,
            "category": "form input",
            "description": "collects visitor information for signup or lead capture.",
        }

    if tag == "SELECT" or re.search(r"english|spanish|portuguese", text):
        return {
            "label": label,
            "category": "language switching",
            "description": "changes the visible site language or localization.",
        }

    if re.search(r"linkedin|facebook|instagram|youtube|x\.com|twitter", text):
        return {
            "label": label,
            "category": "social links",
            "description": "opens a social or community destination.",
        }

    if not normalize_text(action.get("text")) and re.match(r"^a\.", selector):
        return {
            "label": label,
            "category": "linked asset",
            "description": f"opens linked content from the {get_page_title(page_url)}.",
        }

    return {
        "label": label,
        "category": "navigation or linked content",
        "description": f"opens related content from the {get_page_title(page_url)}.",
    }


def match_action(actions: list[dict], event: dict) -> dict | None:
    target_text = normalize_text(event.get("text"))
    target_selector = event.get("selector") or ""

    for action in actions:
        if (
            normalize_text(action.get("text")) == target_text
            and str(action.get("selector") or "") == target_selector
        ):
            return action
    for action in actions:
        if normalize_text(action.get("text")) == target_text:
            return action
    for action in actions:
        if str(action.get("selector") or "") == target_selector:
            return action
    return None


def collect_page_capabilities(page: dict) -> list[str]:
    capabilities: list[str] = []
    seen: set[str] = set()
    source_actions = (
        page["captures"] if page.get("captures") else page.get("actions") or []
    )

    for action in source_actions:
        capability = infer_action_function(action, page["url"])["category"]
        if capability not in seen:
            seen.add(capability)
            capabilities.append(capability)

    return capabilities[:6]


def build_pages(dom_map: list[dict], logs: list[dict]) -> tuple[list[dict], int]:
    pages: list[dict] = []
    capture_index = 0
    dom_index = 0
    current_page = None

    for event in logs:
        if event.get("event") == "navigate":
            capture_index += 1
            dom_entry = dom_map[dom_index] if dom_index < len(dom_map) else {
                "url": event.get("url"),
                "actions": [],
            }
            current_page = {
                "index": len(pages) + 1,
                "url": event.get("url"),
                "title": get_page_title(event.get("url")),
                "actions": dom_entry["actions"] if isinstance(dom_entry.get("actions"), list) else [],
                "screenshotFile": f"screenshot_{capture_index}.png",
                "captures": [],
            }
            pages.append(current_page)
            dom_index += 1
            continue

        if event.get("event") == "click_success" and current_page:
            capture_index += 1
            matched_action = match_action(current_page["actions"], event) or {}
            current_page["captures"].append(
                {
                    "index": capture_index,
                    "file": f"modal_{capture_index}.png",
                    "text": normalize_text(event.get("text")),
                    "selector": event.get("selector") or "",
                    "tag": matched_action.get("tag") or "",
                    "classes": matched_action.get("classes") or "",
                }
            )

    return pages, capture_index


def append_image(lines: list[str], label: str, image_path: str) -> None:
    if image_exists(Path(image_path).name):
        lines.append(f"![{label}]({image_path})")
    else:
        lines.append(f"_Missing image: {Path(image_path).name}_")


def render_interaction(capture: dict, page: dict, image_prefix: str, heading_level: int) -> str:
    meta = infer_action_function(capture, page["url"])
    heading = "#" * heading_level
    lines: list[str] = []

    lines.append(f"{heading} {capture['file']} - {meta['label']}")
    lines.append("")
    append_image(lines, meta["label"], f"{image_prefix}{capture['file']}")
    lines.append("")
    lines.append(f"- Triggered by: `{meta['label']}`")
    if capture.get("selector"):
        lines.append(f"- Selector: `{capture['selector']}`")
    lines.append(f"- Functionality: {meta['description']}")

    return "\n".join(lines)


def render_page_section(page: dict, image_prefix: str, heading_level: int = 2) -> str:
    heading = "#" * heading_level
    capabilities = collect_page_capabilities(page)
    lines: list[str] = []

    lines.append(f"{heading} Page {page['index']} - {page['title']}")
    lines.append("")
    lines.append(f"- URL: {page['url']}")
    lines.append(f"- Full-page screenshot: `{page['screenshotFile']}`")
    lines.append(f"- Interaction captures: {len(page['captures'])}")
    lines.append(f"- Page purpose: {get_page_purpose(page['url'])}")
    if capabilities:
        lines.append(f"- Key functionality: {join_human(capabilities)}.")
    lines.append("")
    append_image(lines, page["title"], f"{image_prefix}{page['screenshotFile']}")
    lines.append("")
    lines.append(
        f"This full-page screenshot captures the {page['title']}. It represents the "
        "main screen visitors see before interacting with the linked controls below."
    )
    lines.append("")

    if not page["captures"]:
        lines.append("_No successful interaction captures were recorded for this page._")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"{heading}# Interaction Screenshots")
    lines.append("")
    for capture in page["captures"]:
        lines.append(render_interaction(capture, page, image_prefix, heading_level + 2))
        lines.append("")

    return "\n".join(lines)


def slugify_title(title: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", title.lower()))


def render_combined_doc(pages: list[dict], total_capture_count: int, image_prefix: str) -> str:
    lines: list[str] = []

    lines.append("# ZenMaid Functionality Map")
    lines.append("")
    lines.append(
        "This document maps every screenshot produced by `scripts/analyze.js` to the "
        "page or UI element it represents."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Pages captured: {len(pages)}")
    lines.append(f"- Total screenshot files referenced: {total_capture_count}")
    lines.append(
        "- `modal_*.png` captures come from dry-run hover/focus interactions, so they "
        "show UI states around an interaction rather than a completed navigation."
    )
    lines.append("")
    lines.append("## Pages")
    lines.append("")

    for page in pages:
        lines.append(
            f"- [Page {page['index']} - {page['title']}]"
            f"(#page-{page['index']}---{slugify_title(page['title'])})"
        )

    lines.append("")

    for page in pages:
        lines.append(render_page_section(page, image_prefix, 2))
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    if not DOMMAP_PATH.exists() or not LOGS_PATH.exists():
        print(
            "Missing analysis output. Expected both domMap.json and logs.json in "
            "openclaw-output.",
            file=sys.stderr,
        )
        return 1

    ensure_dir(MD_OUT)

    dom_map = read_json(DOMMAP_PATH)
    logs = read_json(LOGS_PATH)
    pages, total_capture_count = build_pages(dom_map, logs)

    for page in pages:
        file_name = (
            f"page_{str(page['index']).zfill(3)}_{sanitize(page['url'])}.md"
        )
        page_doc = render_page_section(page, "../", 1)
        write_file(MD_OUT / file_name, page_doc)

    md_functionality = render_combined_doc(pages, total_capture_count, "../")
    root_functionality = render_combined_doc(
        pages, total_capture_count, "openclaw-output/"
    )

    write_file(MD_FUNCTIONALITY_PATH, md_functionality)
    write_file(ROOT_FUNCTIONALITY_PATH, root_functionality)

    print("Wrote", MD_FUNCTIONALITY_PATH)
    print("Wrote", ROOT_FUNCTIONALITY_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
