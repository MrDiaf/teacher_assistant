#!/usr/bin/env node
/* Reject new frontend imports across Teacher Assistant module boundaries. */

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import process from "node:process";

const require = createRequire("/app/package.json");
const ts = require("typescript");

function parseArguments() {
  const values = {
    repo: process.cwd(),
    sourceRoot: "frontend/src",
    allowStale: false,
  };
  for (let index = 2; index < process.argv.length; index += 1) {
    const argument = process.argv[index];
    if (argument === "--repo") values.repo = process.argv[(index += 1)];
    else if (argument === "--source-root")
      values.sourceRoot = process.argv[(index += 1)];
    else if (argument === "--allow-stale-exceptions") values.allowStale = true;
    else throw new Error(`Unknown argument: ${argument}`);
  }
  return values;
}

function normalized(value) {
  return value.replaceAll(path.sep, "/").replace(/\.(tsx?|jsx?|css)$/, "");
}

function matches(value, prefix) {
  return value === prefix || value.startsWith(`${prefix}/`);
}

function owner(value, mappings) {
  const match = mappings
    .filter((item) => matches(value, item.prefix))
    .sort((left, right) => right.prefix.length - left.prefix.length)[0];
  return match?.owner;
}

function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? files(target) : [target];
  });
}

function cycles(dependencies) {
  const errors = new Set();
  const visiting = [];
  const visited = new Set();
  function visit(moduleOwner) {
    const cycleStart = visiting.indexOf(moduleOwner);
    if (cycleStart >= 0) {
      errors.add(
        `dependency cycle: ${[...visiting.slice(cycleStart), moduleOwner].join(" -> ")}`,
      );
      return;
    }
    if (visited.has(moduleOwner)) return;
    visiting.push(moduleOwner);
    for (const dependency of dependencies[moduleOwner] ?? []) {
      if (!(dependency in dependencies))
        errors.add(`${moduleOwner} declares unknown dependency ${dependency}`);
      else visit(dependency);
    }
    visiting.pop();
    visited.add(moduleOwner);
  }
  for (const moduleOwner of Object.keys(dependencies)) visit(moduleOwner);
  return [...errors];
}

function importedPaths(file, sourceRoot) {
  const source = fs.readFileSync(file, "utf8");
  const sourceFile = ts.createSourceFile(
    file,
    source,
    ts.ScriptTarget.Latest,
    true,
  );
  const targets = new Set();
  function addSpecifier(specifier) {
    if (!specifier.startsWith(".")) return;
    const target = path.resolve(path.dirname(file), specifier);
    const relative = normalized(path.relative(sourceRoot, target));
    if (!relative.startsWith("../")) targets.add(relative);
  }
  for (const statement of sourceFile.statements) {
    const isStaticImport =
      ts.isImportDeclaration(statement) || ts.isExportDeclaration(statement);
    if (
      isStaticImport &&
      statement.moduleSpecifier &&
      ts.isStringLiteral(statement.moduleSpecifier)
    ) {
      addSpecifier(statement.moduleSpecifier.text);
    }
  }
  function visit(node) {
    if (
      ts.isCallExpression(node) &&
      node.expression.kind === ts.SyntaxKind.ImportKeyword &&
      node.arguments.length === 1 &&
      ts.isStringLiteral(node.arguments[0])
    ) {
      addSpecifier(node.arguments[0].text);
    }
    ts.forEachChild(node, visit);
  }
  visit(sourceFile);
  return targets;
}

function main() {
  const arguments_ = parseArguments();
  const repo = path.resolve(arguments_.repo);
  const sourceRoot = path.resolve(repo, arguments_.sourceRoot);
  const config = JSON.parse(
    fs.readFileSync(
      path.join(repo, "architecture/module-boundaries.json"),
      "utf8",
    ),
  );
  const frontend = config.frontend;
  const publicModuleEntries = frontend.public_module_entries;
  const exceptions = new Map(
    frontend.legacy_exceptions.map((item) => [
      `${item.importer}\0${item.imported}`,
      item.remove_in,
    ]),
  );
  const seen = new Set();
  const errors = cycles(config.declared_dependencies);

  for (const file of files(sourceRoot).filter(
    (item) => /\.(ts|tsx)$/.test(item) && !item.includes(".test."),
  )) {
    const importerRelative = normalized(path.relative(sourceRoot, file));
    const importerOwner = owner(importerRelative, frontend.path_owners);
    const importerPath =
      normalized(path.relative(repo, file)) + path.extname(file);
    if (!importerOwner) {
      errors.push(`unowned frontend file: ${importerPath}`);
      continue;
    }
    for (const imported of [...importedPaths(file, sourceRoot)].sort()) {
      const importedOwner = owner(imported, frontend.path_owners);
      if (!importedOwner) {
        errors.push(`unowned frontend import: ${importerPath} -> ${imported}`);
        continue;
      }
      if (importedOwner === importerOwner) continue;
      if (
        importerOwner === "platform" &&
        publicModuleEntries[importedOwner] === imported
      )
        continue;
      if (
        importedOwner === "platform" &&
        frontend.allowed_platform_paths.some((prefix) =>
          matches(imported, prefix),
        )
      )
        continue;
      const key = `${importerPath}\0${imported}`;
      if (exceptions.has(key)) {
        seen.add(key);
        continue;
      }
      errors.push(
        `forbidden frontend import: ${importerPath} (${importerOwner}) -> ${imported} (${importedOwner})`,
      );
    }
  }

  if (!arguments_.allowStale) {
    for (const key of exceptions.keys()) {
      if (!seen.has(key))
        errors.push(`stale frontend exception: ${key.replace("\0", " -> ")}`);
    }
  }
  if (errors.length > 0) {
    console.error("Frontend module-boundary check failed:");
    for (const error of [...new Set(errors)].sort())
      console.error(`- ${error}`);
    process.exitCode = 1;
    return;
  }
  console.log("Frontend module-boundary check passed.");
}

main();
