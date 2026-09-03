import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("contains the public AlphaBeater demo and no credentials", async () => {
  const [page, layout] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
  ]);

  assert.match(layout, /AlphaBeater \| Risk-gated AI options agent/);
  assert.match(page, /Research a signal/);
  assert.match(page, /Replay agent run/);
  assert.match(page, /Official Alpaca MCP/);
  assert.doesNotMatch(`${page}${layout}`, /API_KEY|SECRET_KEY/);
});
