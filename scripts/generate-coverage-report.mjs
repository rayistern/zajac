#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { parseArgs } from "node:util";

function normalizePath(filePath) {
  return filePath.replace(/\\/g, "/").replace(/^\.\//, "");
}

function parseThresholds(rawThresholds) {
  if (!rawThresholds || rawThresholds.trim() === "") {
    return {};
  }

  return rawThresholds
    .split(",")
    .map((pair) => pair.trim())
    .filter(Boolean)
    .reduce((result, pair) => {
      const [metric, rawValue] = pair.split("=").map((part) => part.trim());
      const value = Number(rawValue);

      if (!metric || !Number.isFinite(value)) {
        throw new Error(
          `Invalid threshold '${pair}'. Use metric=value, for example: statements=80`,
        );
      }

      result[metric] = value;
      return result;
    }, {});
}

function formatPercent(value) {
  if (!Number.isFinite(value)) {
    return "n/a";
  }

  return `${value.toFixed(2)}%`;
}

function formatOverallPercent(metric, value, thresholds) {
  if (!Number.isFinite(value)) {
    return "n/a";
  }

  const threshold = thresholds[metric];
  const statusIcon = threshold === undefined ? "🔵" : value >= threshold ? "✅" : "❌";
  return `${statusIcon} ${formatPercent(value)}`;
}

function getChangedFiles(baseSha) {
  if (!baseSha) {
    return [];
  }

  const output = execSync(`git diff --name-only ${baseSha}...HEAD`, {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });

  return output
    .split("\n")
    .map((line) => normalizePath(line.trim()))
    .filter(Boolean);
}

const parsedArgs = parseArgs({
  args: process.argv.slice(2),
  options: {
    package: { type: "string" },
    coverageFile: { type: "string" },
    thresholds: { type: "string" },
    output: { type: "string" },
    baseSha: { type: "string" },
  },
  allowPositionals: false,
});

const options = {
  packageName: parsedArgs.values.package ?? "api",
  coverageFile: parsedArgs.values.coverageFile ?? "api/coverage/coverage-summary.json",
  thresholds: parseThresholds(parsedArgs.values.thresholds ?? "statements=80"),
  output: parsedArgs.values.output ?? "coverage-report.md",
  baseSha: parsedArgs.values.baseSha ?? process.env.BASE_SHA,
};

const metrics = ["lines", "statements", "branches", "functions"];
const repoRoot = process.cwd();
const coverageFilePath = path.resolve(repoRoot, options.coverageFile);

if (!fs.existsSync(coverageFilePath)) {
  throw new Error(`Coverage summary file not found: ${coverageFilePath}`);
}

const summary = JSON.parse(fs.readFileSync(coverageFilePath, "utf8"));
if (!summary.total) {
  throw new Error(`Coverage summary file is missing total section: ${coverageFilePath}`);
}

const changedFiles = getChangedFiles(options.baseSha);
const coverageByFile = new Map(
  Object.entries(summary)
    .filter(([filePath]) => filePath !== "total")
    .map(([filePath, fileMetrics]) => {
      const absolutePath = path.isAbsolute(filePath) ? filePath : path.resolve(repoRoot, filePath);
      const relativePath = normalizePath(path.relative(repoRoot, absolutePath));
      return [relativePath, fileMetrics];
    }),
);

const changedCoverageRows = changedFiles
  .filter((filePath) => coverageByFile.has(filePath))
  .map((filePath) => ({
    filePath,
    metrics: coverageByFile.get(filePath),
  }));

const overallRow = `| ${options.packageName} | ${metrics
  .map((metric) => formatOverallPercent(metric, Number(summary.total[metric]?.pct), options.thresholds))
  .join(" | ")} |`;

const thresholdDetails = Object.entries(options.thresholds)
  .map(([metric, value]) => `${options.packageName} ${metric} >= ${value}%`)
  .join(" · ");

const lines = [
  "## Coverage Report",
  "",
  "### Overall Coverage",
  "| Package | Lines | Statements | Branches | Functions |",
  "| --- | --- | --- | --- | --- |",
  overallRow,
  "",
  "### Changed Files",
];

if (changedCoverageRows.length === 0) {
  lines.push("_No changed files with coverage data found in this PR._");
} else {
  lines.push("| File | Lines | Statements | Branches | Functions |", "| --- | --- | --- | --- | --- |");

  for (const row of changedCoverageRows) {
    const values = metrics.map((metric) => formatPercent(Number(row.metrics[metric]?.pct)));
    lines.push(`| ${row.filePath} | ${values.join(" | ")} |`);
  }
}

lines.push("", "✅ above threshold · ❌ below threshold · 🔵 no threshold");

if (thresholdDetails) {
  lines.push("", `Thresholds: ${thresholdDetails}`);
}

const report = `${lines.join("\n")}\n`;
const outputPath = path.resolve(repoRoot, options.output);
fs.writeFileSync(outputPath, report, "utf8");

console.log(report);
