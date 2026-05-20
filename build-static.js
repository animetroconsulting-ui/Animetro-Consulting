const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const dist = path.join(root, "dist");
const publicEntries = ["index.html", "en", "zh", "assets"];

fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });

for (const entry of publicEntries) {
  const source = path.join(root, entry);
  const target = path.join(dist, entry);

  if (!fs.existsSync(source)) {
    continue;
  }

  fs.cpSync(source, target, {
    recursive: true,
    filter: (filePath) => !filePath.endsWith(".DS_Store")
  });
}

console.log("Static website copied to dist/");
