import { describe, expect, test } from "vitest";
import { fetchClient, $api } from "./client";

describe("API client", () => {
  test("fetchClient is defined", () => {
    expect(fetchClient).toBeDefined();
  });

  test("$api query client is defined", () => {
    expect($api).toBeDefined();
  });
});
