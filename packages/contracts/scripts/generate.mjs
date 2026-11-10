import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../../..");
const openApiPath = resolve(repoRoot, "services/backend/openapi.yaml");
const outPath = resolve(here, "../src/generated/openapi.ts");

if (!existsSync(openApiPath)) {
  console.error(`Missing OpenAPI schema at ${openApiPath}. Run 'make openapi' or export schema first.`);
  process.exit(1);
}

const ast = await openapiTS(pathToFileURL(openApiPath));
const contents = `/* Auto-generated from services/backend/openapi.yaml — do not edit manually. */\n${astToString(ast)}`;

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, contents, "utf8");
console.log(`Generated ${outPath}`);

