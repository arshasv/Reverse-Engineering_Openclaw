// Simple Playwright-based OpenClaw-like analysis harness
// Usage: node scripts/analyze.js <startUrl> [--dry-run]

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const argv = require("minimist")(process.argv.slice(2));
const startUrl = argv._[0];
const dryRun = argv["dry-run"] || argv["dryrun"] || true;

if (!startUrl) {
  console.error("Usage: node scripts/analyze.js <startUrl> [--dry-run=false]");
  process.exit(1);
}

(async () => {
  const outDir = path.resolve(process.cwd(), "openclaw-output");
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Basic rate limit
  const delayBetweenActionsMs = 2000;
  const jitterMs = 500;
  const avoidSelectors = [
    "button.delete",
    "a.delete",
    "form[action*='delete']",
    "input[type='submit'].danger",
  ];

  function sleep(ms) {
    return new Promise((res) => setTimeout(res, ms));
  }

  function randJitter() {
    return Math.floor(Math.random() * (jitterMs * 2 + 1)) - jitterMs;
  }

  const visited = new Set();
  const screenshots = [];
  const domMap = [];
  const logs = [];

  async function analyzeUrl(url, depth = 0) {
    if (visited.has(url) || depth > 3) return;
    visited.add(url);
    logs.push({ event: "navigate", url, timestamp: Date.now() });
    await page.goto(url, { waitUntil: "networkidle" });

    const screenshotPath = path.join(
      outDir,
      `screenshot_${screenshots.length + 1}.png`,
    );
    await page.screenshot({ path: screenshotPath, fullPage: true });
    screenshots.push(screenshotPath);

    // Map actionable elements
    const actions = await page.$$eval(
      "button, a, input, select, textarea",
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
      },
    );

    domMap.push({ url, actions });

    // Click primary buttons (non-destructive) - open modals if present
    for (let i = 0; i < actions.length; i++) {
      const a = actions[i];
      if (!a.text || a.text.trim().length === 0) continue;
      const lower = a.text.toLowerCase();
      if (
        lower.includes("delete") ||
        lower.includes("remove") ||
        lower.includes("pay") ||
        lower.includes("confirm")
      )
        continue;
      // avoid by selector
      if (avoidSelectors.some((s) => a.selector.includes(s.replace(/\./g, ""))))
        continue;

      try {
        logs.push({
          event: "click_attempt",
          selector: a.selector,
          text: a.text,
          timestamp: Date.now(),
        });
        await sleep(delayBetweenActionsMs + randJitter());
        const handle = await page.$(a.selector);
        if (!handle) continue;
        await handle.scrollIntoViewIfNeeded();
        // Try to click but if dryRun, just hover and capture modal changes
        if (!dryRun) {
          await handle.click({ timeout: 5000 });
        } else {
          await handle.hover();
        }
        await sleep(800 + randJitter());
        const modalShot = path.join(
          outDir,
          `modal_${screenshots.length + 1}.png`,
        );
        await page.screenshot({ path: modalShot, fullPage: true });
        screenshots.push(modalShot);
        logs.push({
          event: "click_success",
          selector: a.selector,
          text: a.text,
          timestamp: Date.now(),
        });
      } catch (err) {
        logs.push({
          event: "click_error",
          selector: a.selector,
          text: a.text,
          error: err.message,
          timestamp: Date.now(),
        });
      }
    }

    // Follow internal links shallowly
    const links = await page.$$eval("a[href]", (els) =>
      els.map((a) => a.href).filter(Boolean),
    );
    for (const link of links) {
      if (new URL(link).origin === new URL(url).origin) {
        await analyzeUrl(link, depth + 1);
      }
    }
  }

  try {
    await analyzeUrl(startUrl, 0);
  } catch (err) {
    console.error("Error during analysis", err);
  } finally {
    await browser.close();
    fs.writeFileSync(
      path.join(outDir, "domMap.json"),
      JSON.stringify(domMap, null, 2),
    );
    fs.writeFileSync(
      path.join(outDir, "logs.json"),
      JSON.stringify(logs, null, 2),
    );
    console.log("Analysis complete. Output in:", outDir);
  }
})();
