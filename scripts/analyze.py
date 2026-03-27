#!/usr/bin/env python3
"""Simple Playwright-based OpenClaw-like analysis harness.

Usage:
    python3 scripts/analyze.py <startUrl> [--dry-run=false]
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
import time
from pathlib import Path
from urllib.parse import urlparse


USAGE = "Usage: python3 scripts/analyze.py <startUrl> [--dry-run=false]"


def current_timestamp_ms() -> int:
    return int(time.time() * 1000)


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def parse_args(argv: list[str]) -> tuple[str | None, bool]:
    start_url = None
    dry_run = True

    for arg in argv:
        if arg in {"-h", "--help"}:
            print(USAGE)
            raise SystemExit(0)
        if arg.startswith("--dry-run="):
            dry_run = parse_bool(arg.split("=", 1)[1])
            continue
        if arg.startswith("--dryrun="):
            dry_run = parse_bool(arg.split("=", 1)[1])
            continue
        if arg in {"--dry-run", "--dryrun"}:
            dry_run = True
            continue
        if arg.startswith("-"):
            raise ValueError(f"Unknown argument: {arg}")
        if start_url is not None:
            raise ValueError(f"Unexpected extra argument: {arg}")
        start_url = arg

    return start_url, dry_run


async def run_analysis(start_url: str, dry_run: bool) -> int:
    try:
        from playwright.async_api import async_playwright
    except ModuleNotFoundError:
        print(
            "Missing dependency: playwright. Install it with "
            "`pip install playwright` and then run `playwright install chromium`.",
            file=sys.stderr,
        )
        return 1

    out_dir = Path.cwd() / "openclaw-output"
    out_dir.mkdir(exist_ok=True)

    delay_between_actions_ms = 2000
    jitter_ms = 500
    avoid_selectors = [
        "button.delete",
        "a.delete",
        "form[action*='delete']",
        "input[type='submit'].danger",
    ]

    def rand_jitter() -> int:
        return random.randint(-jitter_ms, jitter_ms)

    async def sleep_ms(ms: int) -> None:
        await asyncio.sleep(ms / 1000)

    visited: set[str] = set()
    dom_map: list[dict] = []
    logs: list[dict] = []
    screenshot_count = 0

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        async def analyze_url(url: str, depth: int = 0) -> None:
            nonlocal screenshot_count

            if url in visited or depth > 3:
                return

            visited.add(url)
            logs.append(
                {"event": "navigate", "url": url, "timestamp": current_timestamp_ms()}
            )
            await page.goto(url, wait_until="networkidle")

            screenshot_count += 1
            screenshot_path = out_dir / f"screenshot_{screenshot_count}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            actions = await page.eval_on_selector_all(
                "button, a, input, select, textarea",
                """
                (els) => {
                  return els.map((el) => {
                    const rect = el.getBoundingClientRect
                      ? el.getBoundingClientRect()
                      : { x: 0, y: 0, width: 0, height: 0 };
                    return {
                      tag: el.tagName,
                      text:
                        el.innerText || el.value || el.getAttribute("aria-label") || "",
                      role: el.getAttribute("role"),
                      id: el.id || null,
                      classes: el.className || null,
                      onclick: el.getAttribute("onclick") || null,
                      selector:
                        el.tagName.toLowerCase() +
                        (el.id
                          ? "#" + el.id
                          : el.className
                            ? "." + el.className.split(" ").join(".")
                            : ""),
                      rect: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                      },
                    };
                  });
                }
                """,
            )

            dom_map.append({"url": url, "actions": actions})

            for action in actions:
                text = action.get("text") or ""
                if not text.strip():
                    continue

                lower = text.lower()
                if any(word in lower for word in ("delete", "remove", "pay", "confirm")):
                    continue

                selector = action.get("selector") or ""
                if any(selector.find(item.replace(".", "")) != -1 for item in avoid_selectors):
                    continue

                try:
                    logs.append(
                        {
                            "event": "click_attempt",
                            "selector": selector,
                            "text": text,
                            "timestamp": current_timestamp_ms(),
                        }
                    )
                    await sleep_ms(delay_between_actions_ms + rand_jitter())
                    handle = await page.query_selector(selector)
                    if handle is None:
                        continue
                    await handle.scroll_into_view_if_needed()
                    if dry_run:
                        await handle.hover()
                    else:
                        await handle.click(timeout=5000)
                    await sleep_ms(800 + rand_jitter())

                    screenshot_count += 1
                    modal_shot = out_dir / f"modal_{screenshot_count}.png"
                    await page.screenshot(path=str(modal_shot), full_page=True)
                    logs.append(
                        {
                            "event": "click_success",
                            "selector": selector,
                            "text": text,
                            "timestamp": current_timestamp_ms(),
                        }
                    )
                except Exception as err:  # noqa: BLE001
                    logs.append(
                        {
                            "event": "click_error",
                            "selector": selector,
                            "text": text,
                            "error": str(err),
                            "timestamp": current_timestamp_ms(),
                        }
                    )

            links = await page.eval_on_selector_all(
                "a[href]",
                "(els) => els.map((anchor) => anchor.href).filter(Boolean)",
            )
            current_origin = urlparse(url).scheme + "://" + urlparse(url).netloc
            for link in links:
                parsed = urlparse(link)
                link_origin = parsed.scheme + "://" + parsed.netloc
                if link_origin == current_origin:
                    await analyze_url(link, depth + 1)

        try:
            await analyze_url(start_url, 0)
        except Exception as err:  # noqa: BLE001
            print("Error during analysis", err, file=sys.stderr)
        finally:
            await browser.close()

    with (out_dir / "domMap.json").open("w", encoding="utf8") as handle:
        json.dump(dom_map, handle, indent=2)
        handle.write("\n")

    with (out_dir / "logs.json").open("w", encoding="utf8") as handle:
        json.dump(logs, handle, indent=2)
        handle.write("\n")

    print("Analysis complete. Output in:", out_dir)
    return 0


def main() -> int:
    try:
        start_url, dry_run = parse_args(sys.argv[1:])
    except ValueError as err:
        print(err, file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    if not start_url:
        print(USAGE, file=sys.stderr)
        return 1

    return asyncio.run(run_analysis(start_url, dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
