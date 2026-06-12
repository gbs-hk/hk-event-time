import fs from "node:fs";

const resultsPath = process.argv[2] || "pa11y-results.json";
const stderrPath = process.argv[3] || "pa11y-stderr.txt";

function escapeAnnotation(value) {
  return String(value)
    .replaceAll("%", "%25")
    .replaceAll("\r", "%0D")
    .replaceAll("\n", "%0A");
}

let issues;
try {
  issues = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
} catch (error) {
  const stderr = fs.existsSync(stderrPath) ? fs.readFileSync(stderrPath, "utf8").trim() : "";
  const detail = stderr ? `${error.message}. pa11y stderr: ${stderr}` : error.message;
  console.error(`::error title=pa11y output::Could not parse ${resultsPath}: ${escapeAnnotation(detail)}`);
  process.exit(1);
}

if (!Array.isArray(issues)) {
  console.error(`::error title=pa11y output::Expected ${resultsPath} to contain an array.`);
  process.exit(1);
}

const blocking = issues.filter((issue) => issue.type === "error");

for (const issue of blocking) {
  const selector = issue.selector ? ` selector=${issue.selector}` : "";
  const code = issue.code ? ` code=${issue.code}` : "";
  const message = escapeAnnotation(`${issue.message || "pa11y error"}${code}${selector}`);
  console.error(`::error title=pa11y accessibility error::${message}`);
}

console.log(`pa11y blocking errors: ${blocking.length}`);
process.exit(blocking.length > 0 ? 1 : 0);
