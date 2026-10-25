// 실행: node verify-browser.cjs [결과물 폴더] [basic|full|settings|menu|layout]
// 폴더를 비우면 가장 최근 결과물(결과물/ 안 폴더 이름순 마지막)을 연다. 결과물/ 을 주어도 그 안의 마지막 폴더를 연다.
// 이미 설치된 Playwright 사용. 별도 위치는 PLAYWRIGHT_MODULE, CHROMIUM_EXECUTABLE로 지정.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const SCOPES = ['basic', 'full', 'settings', 'menu', 'layout'];
const RESULT_NAME = /^(\d{4}-\d{2}-\d{2}_\d{4})(?:_(\d+))?$/;
function latestResult(base) {
  const names = fs.existsSync(base) ? fs.readdirSync(base).filter(n => RESULT_NAME.test(n) && fs.statSync(path.join(base, n)).isDirectory()) : [];
  assert.ok(names.length, `결과물이 아직 없습니다: ${base}`);
  const key = n => { const m = n.match(RESULT_NAME); return [m[1], Number(m[2] || 1)]; };
  names.sort((x, y) => { const a = key(x), b = key(y); return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] - b[1]; });
  return path.join(base, names[names.length - 1]);
}
function resultsRoot() {
  // 작업 폴더 = .claude 가 있는 가장 가까운 위 폴더. 없으면 지금 폴더. output_directory 는 분석 스킬 config.md 에서 읽는다.
  let dir = __dirname;
  while (dir !== path.dirname(dir) && !fs.existsSync(path.join(dir, '.claude', 'skills'))) dir = path.dirname(dir);
  const root = fs.existsSync(path.join(dir, '.claude', 'skills')) ? dir : process.cwd();
  const cfg = path.join(root, '.claude/skills/coupang-ad-dashboard/config.md');
  const m = fs.existsSync(cfg) && fs.readFileSync(cfg, 'utf8').match(/^output_directory:\s*['"]?([^'"\n]+?)['"]?\s*$/m);
  const rel = m ? m[1] : '결과물';
  return path.isAbsolute(rel) ? rel : path.join(root, rel);
}
let [given, scopeArg] = process.argv.slice(2);
if (SCOPES.includes(given) && scopeArg === undefined) [given, scopeArg] = [undefined, given];
let out = given ? path.resolve(given) : latestResult(resultsRoot());
if (!fs.existsSync(path.join(out, 'index.html'))) out = latestResult(out);
const scope = scopeArg || 'basic';
assert.ok(SCOPES.includes(scope));
const html = fs.readFileSync(path.join(out, 'index.html'), 'utf8');
const hash = createHash('sha256').update(html).digest('hex');
const {config: C, rows} = JSON.parse(html.match(/<script id="report-data" type="application\/json">(.*?)<\/script>/s)[1]);
const fields = ['cost', 'revenue', 'orders', 'clicks', 'i'];
let expected = Object.fromEntries(fields.map(k => [k, rows.reduce((s, r) => s + r[k], 0)]));
for (const [k, a, b, m] of [['roas','revenue','cost',100],['ctr','clicks','i',100],['cpc','cost','clicks',1],['cvr','orders','clicks',100],['cpa','cost','orders',1]]) expected[k] = expected[b] ? expected[a]/expected[b]*m : null;
let evidence;
if (scope === 'full' || scope === 'settings') {
  evidence = JSON.parse(fs.readFileSync(path.join(out, '검산.json'), 'utf8'));
  assert.equal(evidence.html_sha256, hash, '현재 HTML에 대해 verify.py를 먼저 실행하세요.');
  expected = evidence.total;
}
const n = new Intl.NumberFormat('ko-KR', {maximumFractionDigits: 0});
const display = (k, v) => v == null ? '계산 불가' : ['roas','ctr','cvr'].includes(k) ? v.toFixed(1)+'%' : n.format(v)+(k === 'orders' ? '건' : '원');
(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.CHROMIUM_EXECUTABLE ? {executablePath:process.env.CHROMIUM_EXECUTABLE} : {})});
  const start = performance.now();
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];
    page.on('pageerror', e => errors.push(String(e)));
    // 로컬 웹(serve.py)이 떠 있으면 같은 주소(http://localhost:{포트}/{폴더}/)로 연다. 없거나 안 열리면 파일로 연다.
    let opened = false;
    const serveState = path.join(path.dirname(resultsRoot()), '.serve.json');
    if (fs.existsSync(serveState)) {
      try {
        const {port, root} = JSON.parse(fs.readFileSync(serveState, 'utf8'));
        if (path.resolve(root) === path.dirname(out)) {
          const res = await page.goto(`http://localhost:${port}/${encodeURIComponent(path.basename(out))}/`);
          opened = !!res && res.ok();
        }
      } catch (e) { opened = false; }
    }
    if (!opened) await page.goto(pathToFileURL(path.join(out, 'index.html')).href);
    for (const k of C.kpi_order) assert.equal(await page.locator(`[data-kpi=${k}] strong`).innerText(), display(k, expected[k]), k);
    assert.deepEqual(await page.locator('[role=tab]').evaluateAll(bs=>bs.map(b=>b.textContent.replace(/^0\d/,''))), C.menu_items.map(m=>m.label));
    assert.deepEqual(await page.locator('[data-kpi]').evaluateAll(cs=>cs.map(c=>c.dataset.kpi)), C.kpi_order);
    assert.ok((await page.locator('#source-context').innerText()).includes(C.attribution_days+'일 전환 기준'));
    assert.ok((await page.locator('#source-context').innerText()).includes(C.target_roas_pct == null ? '목표 미설정' : '목표 ROAS '+C.target_roas_pct.toFixed(1)+'%'));
    assert.ok((await page.locator('#source-context').innerText()).includes(C.margin_pct == null ? '마진율 미설정' : '마진율 '));
    // 손익분기 칸은 마진율이 있으면 판정, 없으면 안내 한 줄
    const beBox = await page.locator('#breakeven').innerText();
    if (C.margin_pct == null) assert.ok(beBox.includes('마진율을 정하면 이익인지 손해인지 알려 드립니다'));
    else assert.ok(/손익분기 (위|아래)/.test(beBox) || beBox.includes('계산 불가'));
    for (const m of C.menu_items) {
      await page.locator('#tab-'+m.id).click();
      assert.equal(await page.locator('#tab-'+m.id).getAttribute('aria-selected'), 'true');
      assert.ok((await page.locator('#panel').innerText()).trim().length > 20);
    }
    if (scope === 'full') {
      // 실제 화면의 집계 함수와 원본 독립 집계 비교: 숫자 전체, 비율, 0 분모.
      for (const [name, keys] of [['daily',['d']],['campaign',['cid']],['placement',['p']],['keyword',['cid','g','p','k']]]) {
        const actual = await page.evaluate(keys=>group(ALL,keys),keys);
        assert.equal(actual.length,evidence.groups[name].length);
        const byKey = new Map(actual.map(r=>[JSON.stringify(keys.map(k=>r[k])),r]));
        for (const e of evidence.groups[name]) {
          const a=byKey.get(JSON.stringify(keys.map(k=>e[k])));assert.ok(a);
          for (const k of fields) assert.ok(Math.abs(a[k]-e[k])<0.01,k);
          for(const [k,num,den,m] of [['roas','revenue','cost',100],['ctr','clicks','i',100],['cpc','cost','clicks',1],['cvr','orders','clicks',100],['cpa','cost','orders',1]]) {
            if (!e[den]) assert.equal(a[k],null); else assert.ok(Math.abs(a[k]-e[num]/e[den]*m)<0.00001,k);
          }
        }
      }
      await page.locator('#tab-keyword').click();
      let count=0, sums=[0,0,0];
      for (let i=0;i<=Math.ceil(evidence.groups.keyword.length/20);i++) {
        const cells=await page.locator('#keyword-results tbody tr').evaluateAll(rs=>rs.map(r=>[...r.cells].map(c=>c.textContent)));
        count+=cells.length;
        const oc=C.margin_pct==null?6:7;for(const row of cells) [3,4,oc].forEach((col,j)=>sums[j]+=Number(row[col].replace(/[^\d.-]/g,'')));
        if(await page.locator('#next-page').isDisabled())break;
        await page.locator('#next-page').click();
      }
      assert.equal(count,evidence.groups.keyword.length);
      // 금액은 표시 단계에서 반올림하므로 화면 표 합계는 집계별 표시값 합계와 비교.
      for(const [j,k] of ['cost','revenue','orders'].entries()) assert.equal(sums[j],evidence.groups.keyword.reduce((s,r)=>s+Math.round(r[k]),0));
      await page.locator('#keyword-search').fill('__NO_MATCH_검증__');
      assert.equal(await page.locator('#keyword-results tbody td.namecell').count(),0);
      assert.ok((await page.locator('#keyword-results').innerText()).includes('검색 결과 0개'));
      await page.locator('#keyword-search').fill('');
      for(const key of ['cost','k']) {
        const button=page.locator(`[data-sort=${key}]`);
        assert.equal(await button.count(),1);
        {
          await button.click();const first=await button.locator('..').getAttribute('aria-sort');
          await button.click();assert.notEqual(await button.locator('..').getAttribute('aria-sort'),first);
        }
      }
      await page.locator('[data-category="효자"]').click();
      const keyword=evidence.groups.keyword.find(r=>r.k!=='-');
      if(keyword) {
        await page.locator('#keyword-search').fill(keyword.k);
        const matched=await page.locator('#keyword-results tbody tr:has(.namecell)').evaluateAll(rs=>rs.map(r=>[...r.cells].map(c=>c.textContent)));
        for(const row of matched) {assert.ok(row[0].includes(keyword.k));assert.equal(row[2],'효자');}
      }
      await page.locator('#keyword-search').fill('');
      // 판정을 원본에서 다시 센 값(verify.py judgement)과 화면을 맞춘다
      const J=evidence.judgement;
      assert.ok(J,'검산.json 에 judgement 가 없습니다. verify.py 를 다시 돌리세요.');
      const chip=async k=>Number((await page.locator(`[data-category="${k}"]`).innerText()).replace(/[^\d]/g,''));
      assert.equal(await chip('효자'),J.star,'효자 수');
      assert.equal(await chip('낭비검토'),J.waste,'낭비 검토 수');
      const cpaText=await page.locator('#keyword-cpa').innerText();
      assert.equal(cpaText,J.keyword_cpa==null?'계산 불가':n.format(J.keyword_cpa)+'원','키워드 평균 CPA');
      await page.locator('#tab-overview').click();
      const status=await page.locator('#breakeven').getAttribute('data-status');
      assert.equal(status,J.breakeven_status==null?'none':J.breakeven_status,'손익분기 판정');
      await page.locator('#tab-placement').click();
      if(C.margin_pct==null){assert.equal(await page.locator('#placement-judgement').count(),0);}
      else{
        const marked=await page.locator('#placement-judgement tr[data-judge="지면 점검"]').evaluateAll(rs=>rs.map(r=>r.dataset.placement));
        assert.deepEqual(marked,J.placement_check,'지면 점검 지면');
        await page.locator('#tab-actions').click();
        assert.equal(await page.locator('[data-action="placement-check"]').count(),J.placement_check.length,'실행 계획 지면 점검');
      }
    }
    if (['basic','full','layout','menu'].includes(scope)) {
      await page.locator('#tab-overview').click();
      for (const width of [1440,390]) {
        await page.setViewportSize({width,height:900});
        const geometry=await page.evaluate(()=>({w:innerWidth,doc:document.documentElement.scrollWidth,chart:document.querySelector('.grid>.card').getBoundingClientRect().width,panel:document.querySelector('#panel').getBoundingClientRect().width}));
        assert.ok(geometry.doc<=geometry.w,'페이지 가로 넘침');
        if(C.overview_layout==='chart_full_width')assert.ok(Math.abs(geometry.chart-geometry.panel)<2);
      }
    }
    assert.deepEqual(errors,[]);
    const result={scope,passed:true,dir:path.basename(out),html_sha256:hash,seconds:(performance.now()-start)/1000};
    fs.appendFileSync(path.join(out,'검증결과.md'),`\n## 브라우저 확인: ${scope}\n\n- HTML SHA-256: ${hash}\n- 실행 범위 통과, JavaScript 실행 오류 없음.\n- 전체 검색·필터·정렬·집계 확인: ${scope==='full'?'수행':'이번 범위에서는 미수행'}\n`);
    console.log(JSON.stringify(result));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
