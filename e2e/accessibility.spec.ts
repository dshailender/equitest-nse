import { expect, test } from "@playwright/test";
import path from "path";

const pages = [
  { name: "home", path: "/" },
  { name: "data", path: "/data" },
  { name: "indicators", path: "/indicators" },
  { name: "signals", path: "/signals" },
  { name: "risk", path: "/risk" },
  { name: "backtest", path: "/backtest" },
  { name: "sweep", path: "/sweep" },
  { name: "reports", path: "/reports/test-run-123" },
  { name: "reports-index", path: "/reports" },
  { name: "validation", path: "/validation" },
  { name: "docs", path: "/docs" },
  { name: "api-health", path: "/api-health" },
];

test.describe("AUD-D-002 Axe Accessibility Verification", () => {
  for (const pageInfo of pages) {
    test(`${pageInfo.name} (${pageInfo.path}) has 0 critical or serious accessibility violations`, async ({
      page,
    }) => {
      await page.goto(pageInfo.path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(500);

      const axePath = path.resolve(
        __dirname,
        "../frontend/node_modules/axe-core/axe.min.js"
      );
      await page.addScriptTag({ path: axePath });

      const results = await page.evaluate(async () => {
        // @ts-ignore
        return await window.axe.run(document, {
          runOnly: {
            type: "tag",
            values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
          },
        });
      });

      const criticalOrSerious = results.violations.filter(
        (v: any) => v.impact === "critical" || v.impact === "serious"
      );

      if (criticalOrSerious.length > 0) {
        const summary = criticalOrSerious.map((v: any) => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          nodes: v.nodes.map((n: any) => n.target),
        }));
        console.error(
          `Violations on ${pageInfo.name}:`,
          JSON.stringify(summary, null, 2)
        );
      }

      expect(
        criticalOrSerious,
        `Expected 0 critical or serious axe violations on ${pageInfo.name} (${pageInfo.path})`
      ).toEqual([]);
    });
  }
});
