import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/"),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("renders the AlphaBeater demo", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /AlphaBeater/);
  assert.match(html, /Research a signal/);
  assert.match(html, /Replay agent run/);
  assert.match(html, /Risk sandbox/i);
  assert.match(html, /Alpaca MCP/);
  assert.doesNotMatch(html, /API_KEY|SECRET_KEY/);
});
