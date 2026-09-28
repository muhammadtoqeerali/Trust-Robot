"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const playwrightModule = process.env.TRUST_ROBOT_PLAYWRIGHT_MODULE;
const baseURL = process.env.TRUST_ROBOT_DASHBOARD_URL;
const screenshotRoot =
  process.env.TRUST_ROBOT_BROWSER_SCREENSHOT_ROOT || "/tmp";

if (!playwrightModule) {
  throw new Error(
    "TRUST_ROBOT_PLAYWRIGHT_MODULE is required",
  );
}

if (!baseURL) {
  throw new Error(
    "TRUST_ROBOT_DASHBOARD_URL is required",
  );
}

const { chromium } = require(playwrightModule);

const expectedViews = [
  "overview",
  "dataset",
  "features",
  "operations",
  "evidence",
  "health",
];

const normalizedBaseURL = baseURL.replace(/\/+$/, "");

const screenshotPath = (name) =>
  path.join(
    screenshotRoot,
    name,
  );

const waitForDashboard = async (page) => {
  await page.waitForFunction(
    () =>
      document.querySelector("#metric-train")
        ?.textContent
        ?.trim() === "22",
    null,
    {
      timeout: 15000,
    },
  );
};

const assertNoHorizontalPageOverflow = async (page) => {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));

  assert.ok(
    dimensions.scrollWidth <= dimensions.clientWidth + 1,
    `horizontal page overflow: scroll=${dimensions.scrollWidth} client=${dimensions.clientWidth}`,
  );
};

const assertVisibleText = async (
  page,
  selector,
  expected,
) => {
  const locator = page.locator(selector);

  await locator.waitFor({
    state: "visible",
  });

  const text = (
    await locator.textContent()
  )?.trim();

  assert.equal(
    text,
    expected,
    `${selector} text mismatch`,
  );
};

const openView = async (
  page,
  view,
) => {
  await page.locator(
    `[data-view="${view}"]`,
  ).click();

  await page.locator(
    `[data-panel="${view}"].is-active`,
  ).waitFor({
    state: "visible",
  });

  assert.equal(
    await page.locator(
      `[data-view="${view}"]`,
    ).getAttribute("aria-current"),
    "page",
  );
};

(async () => {
  fs.mkdirSync(
    screenshotRoot,
    {
      recursive: true,
    },
  );

  const browser = await chromium.launch({
    headless: true,
  });

  try {
    console.log(
      `browser_name=chromium`,
    );

    console.log(
      `browser_version=${browser.version()}`,
    );

    console.log(
      "=== DESKTOP QUALIFICATION ===",
    );

    const desktopContext = await browser.newContext({
      viewport: {
        width: 1440,
        height: 900,
      },
      reducedMotion: "reduce",
    });

    const desktopPage = await desktopContext.newPage();

    const consoleErrors = [];

    desktopPage.on(
      "console",
      (message) => {
        if (message.type() === "error") {
          consoleErrors.push(
            message.text(),
          );
        }
      },
    );

    let snapshotRequestCount = 0;
    let eventRequestCount = 0;

    desktopPage.on(
      "request",
      (request) => {
        const requestURL = request.url();

        if (
          request.method() === "GET"
          && requestURL.endsWith("/api/v1/snapshot")
        ) {
          snapshotRequestCount += 1;
        }

        if (
          request.method() === "GET"
          && requestURL.endsWith("/api/v1/events")
        ) {
          eventRequestCount += 1;
        }
      },
    );

    const rootResponse = await desktopPage.goto(
      `${normalizedBaseURL}/`,
      {
        waitUntil: "domcontentloaded",
        timeout: 20000,
      },
    );

    assert.ok(rootResponse);
    assert.equal(rootResponse.status(), 200);

    const rootHeaders = await rootResponse.allHeaders();

    assert.equal(
      rootHeaders["cache-control"],
      "no-store, max-age=0",
    );

    assert.equal(
      rootHeaders["x-content-type-options"],
      "nosniff",
    );

    assert.equal(
      rootHeaders["x-frame-options"],
      "DENY",
    );

    assert.match(
      rootHeaders["content-security-policy"],
      /default-src 'self'/,
    );

    assert.match(
      rootHeaders["content-security-policy"],
      /connect-src 'self'/,
    );

    console.log(
      "desktop_security_headers=PASS",
    );

    await waitForDashboard(
      desktopPage,
    );

    assert.equal(
      await desktopPage.title(),
      "TRUST-ROBOT Operations",
    );

    await assertVisibleText(
      desktopPage,
      "#metric-train",
      "22",
    );

    await assertVisibleText(
      desktopPage,
      "#metric-streams",
      "4",
    );

    await assertVisibleText(
      desktopPage,
      "#metric-replay",
      "45",
    );

    await assertVisibleText(
      desktopPage,
      "#metric-labels",
      "0",
    );

    await assertVisibleText(
      desktopPage,
      "#software-qualification",
      "Passed",
    );

    console.log(
      "desktop_overview_rendering=PASS",
    );

    await assertNoHorizontalPageOverflow(
      desktopPage,
    );

    console.log(
      "desktop_horizontal_overflow=PASS",
    );

    for (const view of expectedViews) {
      await openView(
        desktopPage,
        view,
      );

      console.log(
        `desktop_navigation_${view}=PASS`,
      );
    }

    await openView(
      desktopPage,
      "dataset",
    );

    await assertVisibleText(
      desktopPage,
      "#dataset-train-count",
      "22",
    );

    await assertVisibleText(
      desktopPage,
      "#dataset-validation-count",
      "7",
    );

    await assertVisibleText(
      desktopPage,
      "#dataset-confirmation-count",
      "7",
    );

    assert.equal(
      await desktopPage.locator(
        "#train-trajectory-list .trajectory-chip",
      ).count(),
      22,
    );

    assert.equal(
      await desktopPage.locator(
        "#validation-trajectory-list .trajectory-chip",
      ).count(),
      7,
    );

    assert.equal(
      await desktopPage.locator(
        "#confirmation-trajectory-list .trajectory-chip",
      ).count(),
      7,
    );

    assert.equal(
      await desktopPage.locator(
        "#train-trajectory-list .trajectory-chip.is-representative",
      ).textContent(),
      "room_02",
    );

    console.log(
      "desktop_dataset_partition_rendering=PASS",
    );

    await openView(
      desktopPage,
      "features",
    );

    assert.ok(
      await desktopPage.locator(
        "#camera-feature-values .feature-value-row",
      ).count() >= 3,
    );

    assert.ok(
      await desktopPage.locator(
        "#d435i-feature-values .feature-value-row",
      ).count() >= 2,
    );

    assert.ok(
      await desktopPage.locator(
        "#handsfree-feature-values .feature-value-row",
      ).count() >= 2,
    );

    assert.ok(
      await desktopPage.locator(
        "#velodyne-feature-values .feature-value-row",
      ).count() >= 3,
    );

    console.log(
      "desktop_feature_rendering=PASS",
    );

    await openView(
      desktopPage,
      "operations",
    );

    await assertVisibleText(
      desktopPage,
      "#operations-binding-readiness",
      "0 / 16",
    );

    await assertVisibleText(
      desktopPage,
      "#operations-session-state",
      "Not started",
    );

    assert.equal(
      await desktopPage.locator(
        "#operations-channel-body tr",
      ).count(),
      5,
    );

    assert.equal(
      await desktopPage.locator(
        "#operations-lifecycle .operations-lifecycle-item",
      ).count(),
      7,
    );

    await assertVisibleText(
      desktopPage,
      "#operations-network",
      "Not executed",
    );

    await assertVisibleText(
      desktopPage,
      "#operations-contact",
      "Not contacted",
    );

    console.log(
      "desktop_operations_fail_closed=PASS",
    );

    await assertVisibleText(
      desktopPage,
      "#real-session-history-count",
      "0",
    );

    assert.equal(
      await desktopPage.locator(
        "#session-history-list .session-history-item",
      ).count(),
      2,
    );

    console.log(
      "desktop_session_history=PASS",
    );

    await openView(
      desktopPage,
      "evidence",
    );

    await assertVisibleText(
      desktopPage,
      "#receipt-count-badge",
      "2 receipts",
    );

    assert.equal(
      await desktopPage.locator(
        "#receipt-registry .receipt-card",
      ).count(),
      2,
    );

    console.log(
      "desktop_receipt_registry=PASS",
    );

    await openView(
      desktopPage,
      "health",
    );

    await assertVisibleText(
      desktopPage,
      "#health-readiness-state",
      "Blocked",
    );

    await assertVisibleText(
      desktopPage,
      "#health-unresolved-count",
      "5",
    );

    await assertVisibleText(
      desktopPage,
      "#boundary-baseline-sources",
      "0",
    );

    await assertVisibleText(
      desktopPage,
      "#boundary-supervision",
      "0",
    );

    await assertVisibleText(
      desktopPage,
      "#boundary-labels",
      "0",
    );

    await assertVisibleText(
      desktopPage,
      "#gate-se4-complete",
      "No",
    );

    await assertVisibleText(
      desktopPage,
      "#gate-se4-training",
      "Blocked",
    );

    await assertVisibleText(
      desktopPage,
      "#gate-se5",
      "Blocked",
    );

    await assertVisibleText(
      desktopPage,
      "#gate-ate",
      "Unavailable",
    );

    console.log(
      "desktop_health_boundary=PASS",
    );

    await desktopPage.waitForFunction(
      () =>
        document.querySelector("#last-update-age")
          ?.textContent
          ?.trim() !== "No update yet",
      null,
      {
        timeout: 10000,
      },
    );

    await desktopPage.waitForFunction(
      () => window.performance
        .getEntriesByType("resource")
        .some(
          (entry) =>
            entry.name.endsWith("/api/v1/events"),
        ),
      null,
      {
        timeout: 10000,
      },
    ).catch(() => {});

    assert.ok(
      eventRequestCount >= 1,
      "EventSource did not request /api/v1/events",
    );

    console.log(
      `desktop_SSE_request_count=${eventRequestCount}`,
    );

    console.log(
      "desktop_SSE_transport=PASS",
    );

    const snapshotCountBeforeRefresh =
      snapshotRequestCount;

    await desktopPage.locator(
      "#refresh-button",
    ).click();

    await desktopPage.waitForFunction(
      (previous) => {
        const button =
          document.querySelector("#refresh-button");

        return (
          button
          && button.disabled === false
          && performance
            .getEntriesByType("resource")
            .filter(
              (entry) =>
                entry.name.endsWith(
                  "/api/v1/snapshot",
                ),
            )
            .length >= previous
        );
      },
      snapshotCountBeforeRefresh,
      {
        timeout: 10000,
      },
    );

    assert.ok(
      snapshotRequestCount
        > snapshotCountBeforeRefresh,
      "manual refresh did not issue a new snapshot request",
    );

    console.log(
      "desktop_manual_refresh=PASS",
    );

    const skipLink = desktopPage.locator(
      ".skip-link",
    );

    assert.equal(
      await skipLink.getAttribute("href"),
      "#main-content",
    );

    assert.equal(
      await desktopPage.locator("main").count(),
      1,
    );

    assert.equal(
      await desktopPage.locator("nav").count(),
      1,
    );

    console.log(
      "desktop_accessibility_structure=PASS",
    );

    const desktopShot = screenshotPath(
      "trust_robot_ui7_desktop_1440x900.png",
    );

    await desktopPage.screenshot({
      path: desktopShot,
      fullPage: true,
    });

    assert.ok(
      fs.statSync(desktopShot).size > 0,
    );

    console.log(
      `desktop_screenshot=${desktopShot}`,
    );

    console.log(
      `desktop_screenshot_bytes=${fs.statSync(desktopShot).size}`,
    );

    assert.deepEqual(
      consoleErrors,
      [],
      `unexpected desktop console errors: ${consoleErrors.join(" | ")}`,
    );

    console.log(
      "desktop_console_errors=0",
    );

    await desktopContext.close();

    console.log(
      "=== MOBILE QUALIFICATION ===",
    );

    const mobileContext = await browser.newContext({
      viewport: {
        width: 390,
        height: 844,
      },
      isMobile: true,
      reducedMotion: "reduce",
    });

    const mobilePage = await mobileContext.newPage();

    await mobilePage.goto(
      `${normalizedBaseURL}/`,
      {
        waitUntil: "domcontentloaded",
        timeout: 20000,
      },
    );

    await waitForDashboard(
      mobilePage,
    );

    const mobileMenuDisplay =
      await mobilePage.locator(
        "#mobile-menu-button",
      ).evaluate(
        (element) =>
          getComputedStyle(element).display,
      );

    assert.notEqual(
      mobileMenuDisplay,
      "none",
    );

    assert.equal(
      await mobilePage.locator(
        "#mobile-menu-button",
      ).getAttribute(
        "aria-expanded",
      ),
      "false",
    );

    await mobilePage.locator(
      "#mobile-menu-button",
    ).click();

    await mobilePage.waitForFunction(
      () =>
        document.body.classList.contains(
          "nav-open",
        ),
    );

    assert.equal(
      await mobilePage.locator(
        "#mobile-menu-button",
      ).getAttribute(
        "aria-expanded",
      ),
      "true",
    );

    console.log(
      "mobile_navigation_open=PASS",
    );

    await mobilePage.locator(
      '[data-view="dataset"]',
    ).click();

    await mobilePage.locator(
      '[data-panel="dataset"].is-active',
    ).waitFor({
      state: "visible",
    });

    assert.equal(
      await mobilePage.evaluate(
        () =>
          document.body.classList.contains(
            "nav-open",
          ),
      ),
      false,
    );

    await assertVisibleText(
      mobilePage,
      "#dataset-train-count",
      "22",
    );

    console.log(
      "mobile_navigation_dataset=PASS",
    );

    await assertNoHorizontalPageOverflow(
      mobilePage,
    );

    console.log(
      "mobile_horizontal_overflow=PASS",
    );

    const mobileShot = screenshotPath(
      "trust_robot_ui7_mobile_390x844.png",
    );

    await mobilePage.screenshot({
      path: mobileShot,
      fullPage: true,
    });

    assert.ok(
      fs.statSync(mobileShot).size > 0,
    );

    console.log(
      `mobile_screenshot=${mobileShot}`,
    );

    console.log(
      `mobile_screenshot_bytes=${fs.statSync(mobileShot).size}`,
    );

    await mobileContext.close();

    console.log(
      "=== FAIL-CLOSED ERROR-STATE QUALIFICATION ===",
    );

    const errorContext = await browser.newContext({
      viewport: {
        width: 1280,
        height: 800,
      },
      reducedMotion: "reduce",
    });

    const errorPage = await errorContext.newPage();

    await errorPage.route(
      "**/api/v1/snapshot",
      async (route) => {
        await route.abort();
      },
    );

    await errorPage.route(
      "**/api/v1/events",
      async (route) => {
        await route.abort();
      },
    );

    await errorPage.goto(
      `${normalizedBaseURL}/`,
      {
        waitUntil: "domcontentloaded",
        timeout: 20000,
      },
    );

    const alert = errorPage.locator(
      "#dashboard-alert",
    );

    await alert.waitFor({
      state: "visible",
      timeout: 10000,
    });

    const alertText = (
      await alert.textContent()
    ) || "";

    assert.match(
      alertText,
      /Dashboard state unavailable/,
    );

    assert.match(
      alertText,
      /No fallback scientific values were invented/,
    );

    await assertVisibleText(
      errorPage,
      "#metric-train",
      "—",
    );

    await assertVisibleText(
      errorPage,
      "#metric-labels",
      "—",
    );

    console.log(
      "browser_fail_closed_error_state=PASS",
    );

    await errorContext.close();

    console.log(
      "======================================================================",
    );

    console.log(
      "TRUST_ROBOT_UI7_REAL_BROWSER_QUALIFICATION=PASS",
    );

    console.log(
      "BROWSER=Chromium",
    );

    console.log(
      "DESKTOP_VIEWPORT=1440x900",
    );

    console.log(
      "MOBILE_VIEWPORT=390x844",
    );

    console.log(
      "VIEW_COUNT=6",
    );

    console.log(
      "SSE_REQUESTED=true",
    );

    console.log(
      "MANUAL_REFRESH_QUALIFIED=true",
    );

    console.log(
      "FAIL_CLOSED_ERROR_STATE=true",
    );

    console.log(
      "REAL_SENSOR_SESSION_COUNT=0",
    );

    console.log(
      "REAL_SENSOR_CONTACT=false",
    );

    console.log(
      "SE4_COMPLETE=false",
    );

    console.log(
      "SE5_MAY_PROCEED=false",
    );

    console.log(
      "======================================================================",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
