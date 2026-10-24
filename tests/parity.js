// Runs the dashboard's probability model (taken straight from docs/index.html) on the cases in a JSON file.
// usage: node tests/parity.js <export-dir> <cases.json>
const fs = require("fs"), path = require("path");
const [dir, casesFile] = process.argv.slice(2);
const html = fs.readFileSync(path.join(__dirname, "..", "docs", "index.html"), "utf8");
const idx = html.match(/const IDX = \{[\s\S]*?\};/)[0] + "\n" + html.match(/const BOOST_STATS = [^\n]*;/)[0];
const a = html.indexOf("// ---------------------------------------------------------------- model");
const b = html.indexOf("// ---------------------------------------------------------------- players");
if (a < 0 || b < 0 || !idx) throw new Error("could not locate the model code in docs/index.html");
const players = JSON.parse(fs.readFileSync(path.join(dir, "players.json"), "utf8"));
const OPP = JSON.parse(fs.readFileSync(path.join(dir, "opp.json"), "utf8"));
const META = JSON.parse(fs.readFileSync(path.join(dir, "meta.json"), "utf8"));
const CTXJ = JSON.parse(fs.readFileSync(path.join(dir, "ctx.json"), "utf8"));
const BOOST = JSON.parse(fs.readFileSync(path.join(dir, "boost.json"), "utf8"));
const BY_ID = new Map(players.map(p => [p.id, p]));
const CTX = CTXJ && CTXJ.min ? CTXJ : null;
const lib = new Function("OPP", "META", "CTX", "BOOST", "BY_ID", idx + "\n" + html.slice(a, b) + "\nreturn { predict };")(OPP, META, CTX, BOOST, BY_ID);
const cases = JSON.parse(fs.readFileSync(casesFile, "utf8"));
const out = cases.map(c => {
  const p = players.find(x => x.id === c.player_id);
  const r = lib.predict(p, c.stat, c.line, c.side, c.opp || "", c.exp_min || null, c.spread ?? null, c.total ?? null, c.outs ?? null, c.on_date ?? null);
  return r && { pWin: r.pWin, pPush: r.pPush, mu: r.mu, sd: r.sd, avgMin: r.avgMin };
});
console.log(JSON.stringify(out));
