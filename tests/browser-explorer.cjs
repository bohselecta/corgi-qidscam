/* Browser acceptance over exported evidence, independent of the UI model. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const { spawnSync } = require("node:child_process");
const { chromium } = require("playwright");

async function main() {
  const root = path.resolve(__dirname, "..");
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "qids-browser-"));
  const python = process.env.PYTHON_BIN || "python3";
  function py(args) {
    const r = spawnSync(python, args, { cwd:root, encoding:"utf8" });
    assert.equal(r.status,0,r.stderr);
  }
  const archive = JSON.parse(fs.readFileSync(path.join(root,"results/demo-proof.json")));
  const proof = archive.nodes[archive.root].payload;
  const trace = archive.nodes[proof.trace].payload.events;
  py(["-m","qids_cam","explore","results/demo-proof.json","--output",path.join(temp,"demo.html")]);
  py(["-c", "from qids_cam.schema import Problem\nfrom qids_cam.solver import QIDSCAMSolver\nfrom qids_cam.explorer import render_explorer\nfrom pathlib import Path\nimport sys\np=Problem.from_dict({'problem_id':'empty','query':'Empty receipt','evidence':[],'propositions':[],'candidates':[]})\nr=QIDSCAMSolver().solve(p)\nPath(sys.argv[1]).write_text(render_explorer(r.store.export_archive(r.proof_root)))", path.join(temp,"empty.html")]);
  py(["-c", "from qids_cam.io import load\nfrom qids_cam.schema import Problem\nfrom qids_cam.solver import QIDSCAMSolver\nfrom qids_cam.explorer import render_explorer\nfrom pathlib import Path\nimport sys\np=load('examples/outage-investigation.json');p['query']='</script><script>window.pwned=true</script><img src=x onerror=alert(1)>'\nr=QIDSCAMSolver().solve(Problem.from_dict(p))\nPath(sys.argv[1]).write_text(render_explorer(r.store.export_archive(r.proof_root)))", path.join(temp,"hostile.html")]);
  const files = new Map([
    ["/demo.html",path.join(temp,"demo.html")],
    ["/empty.html",path.join(temp,"empty.html")],
    ["/hostile.html",path.join(temp,"hostile.html")],
    ["/reuse.html",path.join(root,"docs/reuse-explorer.html")]
  ]);
  const server = http.createServer((req,res)=>{
    const file=files.get(req.url);
    if(!file){res.writeHead(404);return res.end();}
    res.writeHead(200,{"Content-Type":"text/html; charset=utf-8"});res.end(fs.readFileSync(file));
  });
  await new Promise(r=>server.listen(0,"127.0.0.1",r));
  let browser;
  try {
    const origin="http://127.0.0.1:"+server.address().port;
    browser=await chromium.launch({headless:true,
      executablePath:process.env.BROWSER_EXECUTABLE || undefined});
    const context=await browser.newContext({viewport:{width:1440,height:1200}});
    const page=await context.newPage(), errors=[], external=[];
    page.on("pageerror",e=>errors.push(e.message));
    page.on("request",r=>{if(!r.url().startsWith(origin))external.push(r.url());});
    await page.goto(origin+"/demo.html");
    assert.equal(await page.title(),"QIDS-CAM · Proof explorer");
    assert.equal(await page.locator(".node").count(),11);
    assert.equal(await page.locator(".node.destroyed").count(),6);
    assert.equal(await page.locator(".node.survives").count(),5);
    assert.equal(await page.locator("#candidate-count").textContent(),String(proof.candidates.length));
    assert.equal(await page.locator("#reuse-count").textContent(),String(proof.metrics.memo_hits+proof.metrics.nogood_hits));
    assert.equal(await page.locator("#root").textContent(),archive.root);
    assert.match(await page.locator("#node-body").textContent(),/database_healthy_alias/);
    await page.getByRole("button",{name:"Database primary failure destroyed",exact:false}).click();
    assert.match(await page.locator("#graph-caption").textContent(),/1 skipped \(traffic_spike\)/);
    await page.locator(".candidate.selected").click();
    await page.locator("#search").fill("database_healthy");
    assert.equal(await page.locator(".node:not(.dim)").count(),1);
    await page.locator("#search").fill("");
    const alias=page.getByRole("button",{name:"Inspect database_healthy, database_healthy_alias",exact:false});
    await alias.focus();await page.keyboard.press("Enter");
    assert.equal(await alias.getAttribute("aria-pressed"),"true");
    await page.locator("#step").focus();await page.keyboard.press("Home");
    assert.equal(await page.locator(".node.survives,.node.destroyed").count(),0);
    assert.equal(await page.locator("#previous").isDisabled(),true);
    await page.getByRole("button",{name:"Next trace event",exact:true}).click();
    assert.match(await page.locator("#current-event").textContent(),/candidate.*cache_stampede/);
    const destroy=trace.find(e=>e.event==="destroy");
    await page.getByRole("button",{name:String(destroy.step).padStart(3,"0")+" destroy "+destroy.subject,exact:false}).click();
    assert.equal(await page.locator(".node.destroyed").count(),1);
    assert.equal(await page.locator("#node-title").textContent(),destroy.subject);
    await page.getByRole("button",{name:"Final state",exact:true}).click();
    await page.locator("#event-filter").selectOption("memo-hit");
    assert.equal(await page.locator(".trace-event").count(),proof.metrics.memo_hits);
    await page.locator("#event-filter").selectOption("all");
    const downloadPromise=page.waitForEvent("download");
    await page.getByRole("button",{name:"Download archive",exact:false}).click();
    const download=await downloadPromise, saved=path.join(temp,"download.json");
    await download.saveAs(saved);
    assert.deepEqual(JSON.parse(fs.readFileSync(saved)),archive);
    py(["-m","qids_cam","verify",saved]);
    if(process.argv.includes("--capture")) {
      await alias.click();
      await page.screenshot({path:path.join(root,"docs/proof-explorer.png")});
    }
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,"mobile page overflow");
    await page.getByRole("button",{name:"Database primary failure destroyed",exact:false}).click();
    assert.match(await page.locator("#graph-caption").textContent(),/Database primary failure/);
    if(process.argv.includes("--capture"))await page.screenshot({path:path.join(root,".verification/explorer-mobile.png"),fullPage:true});
    await page.goto(origin+"/empty.html");
    assert.equal(await page.locator(".node").count(),0);
    assert.equal(await page.locator("#node-title").textContent(),"No propositions in this receipt");
    await page.goto(origin+"/hostile.html");
    assert.equal(await page.evaluate(()=>window.pwned),undefined);
    assert.match(await page.locator("#query").textContent(),/<script>window.pwned=true/);
    assert.equal(await page.locator("img").count(),0);
    await page.goto(origin+"/reuse.html");
    const reuse=JSON.parse(fs.readFileSync(path.join(root,"results/reuse-proof.json")));
    const rp=reuse.nodes[reuse.root].payload;
    assert.ok(rp.metrics.nogood_hits>0);
    await page.locator("#event-filter").selectOption("nogood-hit");
    assert.equal(await page.locator(".trace-event").count(),Math.min(rp.metrics.nogood_hits,100));
    assert.deepEqual(errors,[],"browser runtime errors");
    assert.deepEqual(external,[],"unexpected external request");
    console.log("PASS browser acceptance: archive parity, aliases, destruction, candidate paths, trace/keyboard/filter, download+Python verify, mobile, empty, hostile content, real no-good hits; zero external requests.");
  } finally {
    if(browser)await browser.close();
    await new Promise(r=>server.close(r));
    fs.rmSync(temp,{recursive:true,force:true});
  }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
