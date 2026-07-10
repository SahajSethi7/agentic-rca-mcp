import assert from "node:assert/strict";
import test from "node:test";

import { parseRouteHash, routeHash } from "../src/routing.ts";

test("route hashes round-trip run keys", () => {
  const hash = routeHash("report", "job/with spaces:1");

  assert.deepEqual(parseRouteHash(hash), {
    surface: "report",
    runKey: "job/with spaces:1",
    matched: true,
  });
});

test("malformed percent encoding is ignored instead of crashing", () => {
  assert.deepEqual(parseRouteHash("#/report/%E0%A4%A"), {
    surface: "new",
    matched: false,
  });
});

test("in-page anchors are not treated as application routes", () => {
  assert.equal(parseRouteHash("#main-content").matched, false);
});
