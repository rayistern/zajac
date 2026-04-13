#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { parseArgs } from "node:util";

function fail(message) {
  console.error(message);
  process.exit(1);
}

const validMetrics = new Set(["lines", "statements", "functions", "branches"]);
let parsedArgs;

try {
  parsedArgs = parseArgs({
    args: process.argv.slice(2),
    options: {
      threshold: { type: "string" },
      file: { type: "string" },
      metrics: { type: "string" },
    },
    allowPositionals: false,
  });
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}

const args = {
  threshold: Number(parsedArgs.values.threshold ?? process.env.COVERAGE_THRESHOLD ?? 80),
  file: parsedArgs.values.file ?? process.env.COVERAGE_SUMMARY_FILE ?? "coverage/coverage-summary.json",
  metrics: (parsedArgs.values.metrics ?? "lines")
    .split(",")
    .map((metric) => metric.trim())
    .filter(Boolean),
};

if (!Number.isFinite(args.threshold)) {
  fail("Coverage threshold must be a number.");
}

const invalidMetrics = args.metrics.filter((metric) => !validMetrics.has(metric));
if (invalidMetrics.length > 0) {
  fail(
    `Unsupported coverage metric(s): ${invalidMetrics.join(", ")}. Valid values: lines, statements, functions, branches.`,
  );
}

const coverageFile = path.resolve(process.cwd(), args.file);
if (!fs.existsSync(coverageFile)) {
  fail(`Coverage summary file not found: ${coverageFile}`);
}

const parsed = JSON.parse(fs.readFileSync(coverageFile, "utf8"));
if (!parsed.total) {
  fail(`Coverage summary file is missing the 'total' section: ${coverageFile}`);
}

const failedMetrics = [];

for (const metric of args.metrics) {
  const coverage = parsed.total[metric]?.pct;

  if (!Number.isFinite(coverage)) {
    failedMetrics.push(`${metric}: missing`);
    continue;
  }

  if (coverage < args.threshold) {
    failedMetrics.push(`${metric}: ${coverage.toFixed(2)}% < ${args.threshold}%`);
  }
}

if (failedMetrics.length > 0) {
  fail(`Coverage check failed (${failedMetrics.join(", ")}).`);
}

const report = args.metrics
  .map((metric) => `${metric}: ${Number(parsed.total[metric].pct).toFixed(2)}%`)
  .join(", ");

console.log(`Coverage check passed (threshold ${args.threshold}%): ${report}`);
