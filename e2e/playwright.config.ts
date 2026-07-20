import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  reporter: "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://frontend:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
