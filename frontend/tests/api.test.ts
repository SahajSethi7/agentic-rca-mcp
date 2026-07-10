import assert from "node:assert/strict";
import test, { afterEach } from "node:test";

import { ApiError, setAccessTokenGetter, startAnalyze, subscribe } from "../src/api.ts";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;

function installWindow() {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      setTimeout: (callback: () => void) => globalThis.setTimeout(callback, 0),
      clearTimeout: (id: ReturnType<typeof setTimeout>) => globalThis.clearTimeout(id),
    },
  });
}

afterEach(() => {
  globalThis.fetch = originalFetch;
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
  setAccessTokenGetter(null);
});

test("startAnalyze surfaces the structured backend message", async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({
    detail: { error: "model_not_allowed", message: "Choose an allowlisted writer model." },
  }), { status: 422, headers: { "content-type": "application/json" } });

  await assert.rejects(
    startAnalyze({ problem_statement: "Checkout requests fail after a deployment", method: "five_why" }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, 422);
      assert.equal(error.code, "model_not_allowed");
      assert.equal(error.message, "Choose an allowlisted writer model.");
      return true;
    },
  );
});

test("polling reports a terminal HTTP error instead of pretending the job completed", async () => {
  installWindow();
  setAccessTokenGetter(async () => null);
  globalThis.fetch = async () => new Response(
    JSON.stringify({ error: "unknown job" }),
    { status: 404, headers: { "content-type": "application/json" } },
  );

  let failure: ApiError | null = null;
  let events = 0;
  await new Promise<void>((resolve) => {
    subscribe(
      "missing-job",
      () => { events += 1; },
      resolve,
      (error) => { failure = error; },
    );
  });

  assert.equal(events, 0);
  assert.ok(failure instanceof ApiError);
  assert.equal(failure.status, 404);
});

test("polling retries transient server errors and then completes", async () => {
  installWindow();
  setAccessTokenGetter(async () => null);
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    if (calls === 1) {
      return new Response(JSON.stringify({ message: "temporarily unavailable" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ events: [], cursor: 0, done: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  let failure: ApiError | null = null;
  await new Promise<void>((resolve) => {
    subscribe("recovering-job", () => undefined, resolve, (error) => { failure = error; });
  });

  assert.equal(calls, 2);
  assert.equal(failure, null);
});
