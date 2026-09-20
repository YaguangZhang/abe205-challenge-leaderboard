/* Run with: node --test tests/test_themes.cjs (Node 18+; no packages).
   Exercises the actual early-loading controller with a strict browser fixture. */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const site = path.join(__dirname, "..", "site");
const source = fs.readFileSync(path.join(site, "themes.js"), "utf8");
const html = fs.readFileSync(path.join(site, "index.html"), "utf8");
const options = [...html.matchAll(/<option value="([a-z]+)"[^>]*>([^<]+)<\/option>/g)]
  .map((match) => ({ value: match[1], textContent: match[2] }));
const expected = ["arcade", "festival", "glass", "minimal", "neon", "purdue", "retro", "sports"];

function visit(randomValues = [0]) {
  const documentEvents = new Map();
  const windowEvents = new Map();
  const selectEvents = new Map();
  let ready = false;
  let randomCalls = 0;
  const root = { dataset: { theme: "purdue" } };
  const meta = { content: "#101110", setAttribute(name, value) { assert.equal(name, "content"); this.content = value; } };
  const status = { textContent: "" };
  const selector = {
    value: "purdue", disabled: true,
    get selectedOptions() { return options.filter((option) => option.value === this.value); },
    addEventListener(name, callback) { selectEvents.set(name, callback); },
  };
  const document = {
    documentElement: root,
    querySelector(selector) {
      assert.equal(selector, 'meta[name="theme-color"]', "must not query leaderboard content");
      return meta;
    },
    getElementById(id) {
      assert.ok(["theme-select", "theme-status"].includes(id), "must not access leaderboard state");
      if (!ready) return null;
      return id === "theme-select" ? selector : status;
    },
    addEventListener(name, callback) { documentEvents.set(name, callback); },
  };
  const window = { addEventListener(name, callback) { windowEvents.set(name, callback); } };
  const context = {
    document, window,
    Math: { floor: Math.floor, random() {
      assert.ok(randomCalls < randomValues.length, "must not reroll during a visit");
      return randomValues[randomCalls++];
    } },
    setTimeout() { assert.fail("theme must not change on a timer"); },
    setInterval() { assert.fail("theme must not change on a timer"); },
    fetch() { assert.fail("theme must not load or change participant data"); },
  };
  for (const target of [context, window]) {
    for (const key of ["localStorage", "sessionStorage", "indexedDB", "caches", "location", "history"]) {
      Object.defineProperty(target, key, { get() { assert.fail(`must not use ${key} for theme state`); } });
    }
  }
  Object.defineProperty(document, "cookie", {
    get() { assert.fail("must not read cookies"); },
    set() { assert.fail("must not write cookies"); },
  });
  vm.runInNewContext(source, context, { filename: "themes.js" });
  return {
    root, meta, selector, status,
    randomCalls: () => randomCalls,
    ready() { ready = true; documentEvents.get("DOMContentLoaded")(); },
    select(theme) { selector.value = theme; selectEvents.get("change")(); },
    pageShow(persisted) { windowEvents.get("pageshow")({ persisted }); },
    tabSwitch() { documentEvents.get("visibilitychange")?.(); windowEvents.get("focus")?.(); },
  };
}

test("dropdown exposes all eight requested themes and has an accessible label", () => {
  assert.deepEqual(options.map((option) => option.value), expected);
  assert.equal(options.find((option) => option.value === "glass").textContent, "Glass / Futuristic");
  assert.match(html, /<label for="theme-select">Theme<\/label>/);
  assert.match(html, /ABE 205: Computations for Engineering Systems/);
  assert.ok(html.indexOf('src="./themes.js"') < html.indexOf('href="./styles.css"'));
});

test("each equal random interval selects its theme before the body is ready", () => {
  expected.forEach((theme, index) => {
    const page = visit([(index + 0.5) / expected.length]);
    assert.equal(page.root.dataset.theme, theme);
    assert.equal(page.selector.disabled, true);
    page.ready();
    assert.equal(page.selector.value, theme);
    assert.equal(page.selector.disabled, false);
    assert.match(page.meta.content, /^#[0-9a-f]{6}$/);
    assert.equal(page.randomCalls(), 1);
  });
});

test("random interval boundaries include the first and last themes", () => {
  assert.equal(visit([0]).root.dataset.theme, "arcade");
  assert.equal(visit([0.999999999]).root.dataset.theme, "sports");
});

test("initial pageshow and tab switches preserve the automatically selected theme", () => {
  const page = visit([0.56]);
  page.ready();
  page.pageShow(false);
  page.tabSwitch();
  assert.equal(page.root.dataset.theme, "neon");
  assert.equal(page.randomCalls(), 1);
});

test("manual selection applies and announces every theme without another random draw", () => {
  const page = visit([0]);
  page.ready();
  for (const option of options) {
    page.select(option.value);
    assert.equal(page.root.dataset.theme, option.value);
    assert.equal(page.selector.value, option.value);
    assert.equal(page.status.textContent, `${option.textContent} theme selected.`);
    page.pageShow(false);
    page.tabSwitch();
    assert.equal(page.root.dataset.theme, option.value);
  }
  assert.equal(page.randomCalls(), 1);
});

test("a reload starts an independent random visit after a manual selection", () => {
  const first = visit([0]);
  first.ready();
  first.select("purdue");
  const reloaded = visit([0.99]);
  reloaded.ready();
  assert.equal(reloaded.root.dataset.theme, "sports");
  assert.equal(reloaded.selector.value, "sports");
});

test("a browser-restored dropdown value cannot override the new visit's theme", () => {
  const page = visit([0]);
  page.ready();
  page.selector.value = "purdue"; // Browser form restoration, not a change event.
  page.pageShow(false);
  assert.equal(page.root.dataset.theme, "arcade");
  assert.equal(page.selector.value, "arcade");
  assert.equal(page.randomCalls(), 1);
});

test("returning through the back/forward cache rerolls and synchronizes the dropdown", () => {
  const page = visit([0, 0.4]);
  page.ready();
  page.select("neon");
  page.pageShow(true);
  assert.equal(page.root.dataset.theme, "minimal");
  assert.equal(page.selector.value, "minimal");
  assert.equal(page.status.textContent, "");
  assert.equal(page.randomCalls(), 2);
  page.select("festival");
  page.tabSwitch();
  assert.equal(page.root.dataset.theme, "festival");
});

test("unrecognized themes do not change the active styling", () => {
  const page = visit([0.7]);
  page.ready();
  page.select("not-a-theme");
  assert.equal(page.root.dataset.theme, "purdue");
});
