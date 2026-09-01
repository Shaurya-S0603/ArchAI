import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"];

async function generateConcepts(page, { accessibility = true } = {}) {
  await page.goto("/");
  if (accessibility) {
    await page.getByLabel(/Accessibility priority/i).check();
  }
  await page.getByRole("button", { name: /Generate five concepts/i }).click();
  await expect(page.locator("#form-status")).toHaveText("Generated 5 concepts successfully.");
  await expect(page.getByRole("tab")).toHaveCount(5);
  await expect(page.locator("#plan-svg .room")).not.toHaveCount(0);
}

function formatViolations(violations) {
  return violations
    .map((violation) => `${violation.id}: ${violation.help} (${violation.nodes.length} node(s))`)
    .join("\n");
}

test.describe("ArchAI Phase 1 browser workflow", () => {
  test("generates, edits, persists, previews, and exports a concept", async ({ page }) => {
    await generateConcepts(page);

    const activeTab = page.getByRole("tab", { selected: true });
    await activeTab.press("ArrowRight");
    await expect(page.getByRole("tab", { selected: true })).toContainText("Option 2");

    const firstRoom = page.locator("#plan-svg .room").first();
    await firstRoom.focus();
    await firstRoom.press("Enter");
    await expect(page.locator("#room-editor")).toBeVisible();

    const widthInput = page.locator("#room-width");
    const originalWidth = Number(await widthInput.inputValue());
    await widthInput.fill(String(originalWidth - 0.25));
    await page.getByRole("button", { name: "Apply room edit" }).click();
    await expect(page.locator("#form-status")).toHaveText("Edited concept rechecked.");
    await expect(page.locator("#undo-button")).toBeEnabled();

    await page.locator("#undo-button").click();
    await expect(page.locator("#form-status")).toHaveText("Edited concept rechecked.");

    await page.getByRole("button", { name: "3D massing" }).click();
    await expect(page.locator("#model-wrap")).toBeVisible();
    await page.getByRole("button", { name: "2D plan" }).click();
    await expect(page.locator("#plan-wrap")).toBeVisible();

    await page.locator("#project-name").fill("ArchAI Phase 1 browser test");
    await page.locator("#save-project-button").click();
    await expect(page.locator("#project-status")).toContainText("Saved");

    const pdfDownload = page.waitForEvent("download");
    await page.getByRole("button", { name: "PDF", exact: true }).click();
    await expect((await pdfDownload).suggestedFilename()).toMatch(/concept-plan\.pdf$/);

    await page.reload();
    const savedProjects = page.locator("#saved-projects");
    await expect(savedProjects.locator("option")).not.toHaveCount(1);
    const savedId = await savedProjects.locator("option").nth(1).getAttribute("value");
    await savedProjects.selectOption(savedId);
    await page.locator("#load-project-button").click();
    await expect(page.locator("#project-status")).toContainText("Loaded");
    await expect(page.getByRole("tab")).toHaveCount(5);
  });

  test("supports keyboard navigation and has no automated WCAG A/AA violations", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    await expect(page.locator(".skip-link")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();

    const initialAudit = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(initialAudit.violations, formatViolations(initialAudit.violations)).toEqual([]);

    await generateConcepts(page);
    const generatedAudit = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(generatedAudit.violations, formatViolations(generatedAudit.violations)).toEqual([]);
  });
});
