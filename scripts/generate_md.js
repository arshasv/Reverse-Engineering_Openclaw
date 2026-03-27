const fs = require("fs");
const path = require("path");

const ROOT_DIR = path.join(__dirname, "..");
const OUTPUT_DIR = path.join(ROOT_DIR, "openclaw-output");
const DOMMAP_PATH = path.join(OUTPUT_DIR, "domMap.json");
const LOGS_PATH = path.join(OUTPUT_DIR, "logs.json");
const MD_OUT = path.join(OUTPUT_DIR, "md");
const ROOT_FUNCTIONALITY_PATH = path.join(ROOT_DIR, "functionality.md");
const MD_FUNCTIONALITY_PATH = path.join(MD_OUT, "functionality.md");

function readJSON(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeFile(filePath, content) {
  fs.writeFileSync(filePath, content.trimEnd() + "\n", "utf8");
}

function normalizeText(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function truncate(text, max = 110) {
  if (text.length <= max) return text;
  return text.slice(0, max - 3).trimEnd() + "...";
}

function joinHuman(items) {
  if (!items.length) return "";
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

function sanitize(value) {
  return value
    .replace(/^https?:\/\//, "")
    .replace(/[\\/:?&=#\s]+/g, "_")
    .replace(/[^a-zA-Z0-9_.-]/g, "")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
}

function imageExists(fileName) {
  return fs.existsSync(path.join(OUTPUT_DIR, fileName));
}

function getPathname(url) {
  try {
    const pathname = new URL(url).pathname || "/";
    if (pathname === "/") return "/";
    return pathname.replace(/\/+$/, "") || "/";
  } catch {
    return "/";
  }
}

function getPageTitle(url) {
  const pathname = getPathname(url);

  if (pathname === "/") return "Homepage";
  if (pathname === "/demo") return "Demo Page";
  if (pathname === "/pricing") return "Pricing Page";
  if (pathname === "/love") return "Wall of Love Page";
  if (pathname === "/about") return "About Page";
  if (pathname === "/contact") return "Contact Page";

  if (pathname.startsWith("/compare/")) {
    const competitor = pathname.split("/").filter(Boolean).pop() || "competitor";
    return `Comparison Page (${competitor})`;
  }

  return `Page ${pathname}`;
}

function getPagePurpose(url) {
  const pathname = getPathname(url);

  if (pathname === "/") {
    return "Landing page designed to move visitors from product discovery into a free trial, a demo, supporting resources, or a proof point such as testimonials and case studies.";
  }

  if (pathname === "/demo") {
    return "Dedicated demo page focused on showing the product in action with video playback, chapter/audio controls, and conversion paths into signup.";
  }

  if (pathname === "/pricing") {
    return "Pricing page centered on plan discovery, trial prompts, and helping visitors compare value before starting signup.";
  }

  if (pathname === "/love") {
    return "Social-proof page that highlights customer success stories and testimonials while still keeping trial and navigation CTAs available.";
  }

  if (pathname === "/about") {
    return "Company information page that introduces the team, brand story, and related trust-building content.";
  }

  if (pathname === "/contact") {
    return "Contact and community page that routes visitors toward support channels, educational content, and direct outreach options.";
  }

  if (pathname === "/compare/jobber") {
    return "Competitor comparison page built to position ZenMaid against Jobber and push comparison shoppers toward a trial or pricing review.";
  }

  if (pathname === "/compare/bookingkoala") {
    return "Competitor comparison page built to position ZenMaid against BookingKoala and move visitors toward a trial or pricing review.";
  }

  if (pathname === "/compare/launch27") {
    return "Competitor comparison page built to position ZenMaid against Launch27 and move visitors toward a trial or pricing review.";
  }

  return "Content page captured during the OpenClaw dry-run analysis.";
}

function deriveActionLabel(text, selector, pageUrl) {
  const clean = normalizeText(text);

  if (!clean) {
    if ((selector || "").startsWith("input")) return "Form input";
    if ((selector || "").startsWith("button")) return "Button";
    return `Unlabeled control on ${getPageTitle(pageUrl)}`;
  }

  let label = clean;
  const cutPatterns = [
    /\s+Read article/i,
    /\s+Read case study/i,
    /\s+Learn more/i,
    /\s+See pricing/i,
    /\s+Start your free trial/i,
    /\s+Get started for free/i,
  ];

  for (const pattern of cutPatterns) {
    const match = label.match(pattern);
    if (match && match.index > 0) {
      label = label.slice(0, match.index).trim();
      break;
    }
  }

  if (/^\d+$/.test(label) && getPathname(pageUrl) === "/pricing") {
    return `Pricing control (${label})`;
  }

  return truncate(label, 100);
}

function inferActionFunction(action, pageUrl) {
  const label = deriveActionLabel(action.text, action.selector, pageUrl);
  const text = normalizeText(action.text).toLowerCase();
  const selector = String(action.selector || "").toLowerCase();
  const tag = String(action.tag || "").toUpperCase();
  const pathname = getPathname(pageUrl);

  if (/features/.test(text)) {
    return {
      label,
      category: "feature discovery",
      description: "opens or highlights the product features navigation.",
    };
  }

  if (/how it works/.test(text)) {
    return {
      label,
      category: "workflow guidance",
      description: "explains the product workflow and onboarding journey.",
    };
  }

  if (/pricing/.test(text)) {
    return {
      label,
      category: "pricing discovery",
      description: "takes visitors toward plan and pricing information.",
    };
  }

  if (/resources|magazine|read article|keywords every maid service|ads to increase|free tools/i.test(text)) {
    return {
      label,
      category: "resource discovery",
      description: "opens educational content, articles, or growth resources.",
    };
  }

  if (/log in|login/.test(text)) {
    return {
      label,
      category: "account access",
      description: "routes existing customers into the authentication flow.",
    };
  }

  if (/get started|start your free trial|free trial|try zenmaid|try free|automate your back office today/.test(text)) {
    return {
      label,
      category: "trial signup",
      description: "starts or promotes the free-trial signup flow.",
    };
  }

  if (/watch a demo|demo/.test(text)) {
    return {
      label,
      category: "demo access",
      description: "opens or promotes the product demo experience.",
    };
  }

  if (/play video|click for sound|mute|fullscreen|chapter/.test(text)) {
    return {
      label,
      category: "video controls",
      description: "controls demo video playback, audio, fullscreen mode, or chapter navigation.",
    };
  }

  if (/wall of love|testimonials|testimonial/.test(text)) {
    return {
      label,
      category: "customer proof",
      description: "opens testimonial and social-proof content.",
    };
  }

  if (/case study/.test(text)) {
    return {
      label,
      category: "case studies",
      description: "opens a case study about customer outcomes.",
    };
  }

  if (/jobber|bookingkoala|launch27|compare zenmaid to/.test(text)) {
    return {
      label,
      category: "competitor comparison",
      description: "takes visitors to a competitor comparison experience.",
    };
  }

  if (/contact us|talk to our team|contact/.test(text)) {
    return {
      label,
      category: "contact routing",
      description: "routes visitors toward contact or sales conversations.",
    };
  }

  if (/about us|about\b/.test(text)) {
    return {
      label,
      category: "company information",
      description: "opens company background and team information.",
    };
  }

  if (/get the free pdf|get free access|free pdf/.test(text)) {
    return {
      label,
      category: "lead capture",
      description: "collects lead information for a downloadable resource or gated content.",
    };
  }

  if (/mastermind|chat with 5000/.test(text)) {
    return {
      label,
      category: "community access",
      description: "opens the ZenMaid community or mastermind destination.",
    };
  }

  if (pathname === "/about" && /chris schwab|amar ghaghada|team|founder/.test(text)) {
    return {
      label,
      category: "team profiles",
      description: "opens a team member or founder profile.",
    };
  }

  if (pathname === "/love" && /mindy|lashanda|tripled|business owner|maid service/.test(text)) {
    return {
      label,
      category: "customer stories",
      description: "opens a detailed customer success story.",
    };
  }

  if (/^\d+$/.test(normalizeText(action.text)) && pathname === "/pricing") {
    return {
      label,
      category: "pricing controls",
      description: "appears to be part of an interactive pricing control or calculator.",
    };
  }

  if (tag === "BUTTON") {
    return {
      label,
      category: "form submission",
      description: "submits a form or advances a conversion flow.",
    };
  }

  if (tag === "INPUT") {
    return {
      label,
      category: "form input",
      description: "collects visitor information for signup or lead capture.",
    };
  }

  if (tag === "SELECT" || /english|spanish|portuguese/.test(text)) {
    return {
      label,
      category: "language switching",
      description: "changes the visible site language or localization.",
    };
  }

  if (/linkedin|facebook|instagram|youtube|x\.com|twitter/.test(text)) {
    return {
      label,
      category: "social links",
      description: "opens a social or community destination.",
    };
  }

  if (!normalizeText(action.text) && /^a\./.test(selector)) {
    return {
      label,
      category: "linked asset",
      description: `opens linked content from the ${getPageTitle(pageUrl)}.`,
    };
  }

  return {
    label,
    category: "navigation or linked content",
    description: `opens related content from the ${getPageTitle(pageUrl)}.`,
  };
}

function matchAction(actions, event) {
  const targetText = normalizeText(event.text);
  const targetSelector = event.selector || "";

  return (
    actions.find(
      (action) =>
        normalizeText(action.text) === targetText &&
        String(action.selector || "") === targetSelector,
    ) ||
    actions.find((action) => normalizeText(action.text) === targetText) ||
    actions.find((action) => String(action.selector || "") === targetSelector) ||
    null
  );
}

function collectPageCapabilities(page) {
  const capabilities = [];
  const seen = new Set();
  const sourceActions = page.captures.length
    ? page.captures
    : Array.isArray(page.actions)
      ? page.actions
      : [];

  for (const action of sourceActions) {
    const capability = inferActionFunction(action, page.url).category;
    if (!seen.has(capability)) {
      seen.add(capability);
      capabilities.push(capability);
    }
  }

  return capabilities.slice(0, 6);
}

function buildPages(domMap, logs) {
  const pages = [];
  let captureIndex = 0;
  let domIndex = 0;
  let currentPage = null;

  for (const event of logs) {
    if (event.event === "navigate") {
      captureIndex += 1;
      const domEntry = domMap[domIndex] || { url: event.url, actions: [] };
      currentPage = {
        index: pages.length + 1,
        url: event.url,
        title: getPageTitle(event.url),
        actions: Array.isArray(domEntry.actions) ? domEntry.actions : [],
        screenshotFile: `screenshot_${captureIndex}.png`,
        captures: [],
      };
      pages.push(currentPage);
      domIndex += 1;
      continue;
    }

    if (event.event === "click_success" && currentPage) {
      captureIndex += 1;
      const matchedAction = matchAction(currentPage.actions, event) || {};

      currentPage.captures.push({
        index: captureIndex,
        file: `modal_${captureIndex}.png`,
        text: normalizeText(event.text),
        selector: event.selector || "",
        tag: matchedAction.tag || "",
        classes: matchedAction.classes || "",
      });
    }
  }

  return { pages, totalCaptureCount: captureIndex };
}

function appendImage(lines, label, imagePath) {
  if (imageExists(path.basename(imagePath))) {
    lines.push(`![${label}](${imagePath})`);
  } else {
    lines.push(`_Missing image: ${path.basename(imagePath)}_`);
  }
}

function renderInteraction(capture, page, imagePrefix, headingLevel) {
  const meta = inferActionFunction(capture, page.url);
  const heading = "#".repeat(headingLevel);
  const lines = [];

  lines.push(`${heading} ${capture.file} - ${meta.label}`);
  lines.push("");
  appendImage(lines, meta.label, `${imagePrefix}${capture.file}`);
  lines.push("");
  lines.push(`- Triggered by: \`${meta.label}\``);
  if (capture.selector) {
    lines.push(`- Selector: \`${capture.selector}\``);
  }
  lines.push(`- Functionality: ${meta.description}`);

  return lines.join("\n");
}

function renderPageSection(page, imagePrefix, headingLevel = 2) {
  const heading = "#".repeat(headingLevel);
  const capabilities = collectPageCapabilities(page);
  const lines = [];

  lines.push(`${heading} Page ${page.index} - ${page.title}`);
  lines.push("");
  lines.push(`- URL: ${page.url}`);
  lines.push(`- Full-page screenshot: \`${page.screenshotFile}\``);
  lines.push(`- Interaction captures: ${page.captures.length}`);
  lines.push(`- Page purpose: ${getPagePurpose(page.url)}`);
  if (capabilities.length) {
    lines.push(`- Key functionality: ${joinHuman(capabilities)}.`);
  }
  lines.push("");
  appendImage(lines, page.title, `${imagePrefix}${page.screenshotFile}`);
  lines.push("");
  lines.push(
    `This full-page screenshot captures the ${page.title}. It represents the main screen visitors see before interacting with the linked controls below.`,
  );
  lines.push("");

  if (!page.captures.length) {
    lines.push("_No successful interaction captures were recorded for this page._");
    lines.push("");
    return lines.join("\n");
  }

  lines.push(`${heading}# Interaction Screenshots`);
  lines.push("");
  for (const capture of page.captures) {
    lines.push(renderInteraction(capture, page, imagePrefix, headingLevel + 2));
    lines.push("");
  }

  return lines.join("\n");
}

function renderCombinedDoc(pages, totalCaptureCount, imagePrefix) {
  const lines = [];

  lines.push("# ZenMaid Functionality Map");
  lines.push("");
  lines.push(
    "This document maps every screenshot produced by `scripts/analyze.js` to the page or UI element it represents.",
  );
  lines.push("");
  lines.push("## Summary");
  lines.push("");
  lines.push(`- Pages captured: ${pages.length}`);
  lines.push(`- Total screenshot files referenced: ${totalCaptureCount}`);
  lines.push(
    "- `modal_*.png` captures come from dry-run hover/focus interactions, so they show UI states around an interaction rather than a completed navigation.",
  );
  lines.push("");
  lines.push("## Pages");
  lines.push("");

  for (const page of pages) {
    lines.push(`- [Page ${page.index} - ${page.title}](#page-${page.index}---${page.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")})`);
  }

  lines.push("");

  for (const page of pages) {
    lines.push(renderPageSection(page, imagePrefix, 2));
    lines.push("");
  }

  return lines.join("\n");
}

function main() {
  if (!fs.existsSync(DOMMAP_PATH) || !fs.existsSync(LOGS_PATH)) {
    console.error(
      "Missing analysis output. Expected both domMap.json and logs.json in openclaw-output.",
    );
    process.exit(1);
  }

  ensureDir(MD_OUT);

  const domMap = readJSON(DOMMAP_PATH);
  const logs = readJSON(LOGS_PATH);
  const { pages, totalCaptureCount } = buildPages(domMap, logs);

  for (const page of pages) {
    const fileName = `page_${String(page.index).padStart(3, "0")}_${sanitize(page.url)}.md`;
    const pageDoc = renderPageSection(page, "../", 1);
    writeFile(path.join(MD_OUT, fileName), pageDoc);
  }

  const mdFunctionality = renderCombinedDoc(pages, totalCaptureCount, "../");
  const rootFunctionality = renderCombinedDoc(
    pages,
    totalCaptureCount,
    "openclaw-output/",
  );

  writeFile(MD_FUNCTIONALITY_PATH, mdFunctionality);
  writeFile(ROOT_FUNCTIONALITY_PATH, rootFunctionality);

  console.log("Wrote", MD_FUNCTIONALITY_PATH);
  console.log("Wrote", ROOT_FUNCTIONALITY_PATH);
}

if (require.main === module) {
  main();
}

module.exports = { main };
