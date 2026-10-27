const INDUSTRIES = {
  manufacturing: "制造业",
  technology: "互联网与软件",
  retail_logistics_service: "零售物流服务",
};

const state = { data: null, industry: "all", query: "", archetype: "all", compare: [] };
const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

function latest(company) { return company.years.find((item) => item.year === 2025); }
function valueOrDash(value, formatter = String) { return value === null || value === undefined ? '<span class="missing">暂无数据</span>' : formatter(value); }
function money(value) {
  if (value === null || value === undefined) return "暂无数据";
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(1)}亿元`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(1)}万元`;
  return `${Math.round(value).toLocaleString("zh-CN")}元`;
}
function percent(value) { return value === null || value === undefined ? "暂无数据" : `${(value * 100).toFixed(1)}%`; }
function score(value) { return value === null || value === undefined ? "—" : Number(value).toFixed(1); }
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char])); }

async function init() {
  const response = await fetch("./data.json");
  state.data = await response.json();
  renderHero();
  fillArchetypes();
  renderRanking();
  bindEvents();
}

function eligibleCompanies() {
  return state.data.companies.filter((company) => latest(company).score.ranking_eligible === true);
}

function sortedEligible() {
  return eligibleCompanies().sort((a, b) => latest(b).score.overall_score_raw - latest(a).score.overall_score_raw);
}

function renderHero() {
  const companies = sortedEligible();
  $("#eligibleCount").textContent = companies.length;
  $("#heroTopThree").innerHTML = companies.slice(0, 3).map((company, index) => {
    const item = latest(company);
    return `<div class="top-row"><span class="rank">${index + 1}</span><div><strong>${escapeHtml(company.display_name)}</strong><small>${INDUSTRIES[company.industry]} · ${escapeHtml(company.primary_archetype)}</small></div><span class="score">${score(item.score.overall_score)}<i>/100</i></span></div>`;
  }).join("");
}

function fillArchetypes() {
  const archetypes = [...new Set(state.data.companies.map((company) => company.primary_archetype))].sort();
  $("#archetypeFilter").insertAdjacentHTML("beforeend", archetypes.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join(""));
}

function filteredCompanies() {
  const query = state.query.trim().toLowerCase();
  return sortedEligible().filter((company) => {
    const industryMatch = state.industry === "all" || company.industry === state.industry;
    const archetypeMatch = state.archetype === "all" || company.primary_archetype === state.archetype;
    const queryMatch = !query || company.display_name.toLowerCase().includes(query) || company.primary_archetype.toLowerCase().includes(query);
    return industryMatch && archetypeMatch && queryMatch;
  });
}

function renderRanking() {
  const companies = filteredCompanies();
  $("#emptyState").hidden = companies.length !== 0;
  $("#rankingBody").innerHTML = companies.map((company) => {
    const item = latest(company);
    const selected = state.compare.includes(company.company_id);
    const rank = state.industry === "all" ? item.score.overall_rank : item.score.industry_rank;
    return `<tr>
      <td class="rank-cell">${rank}</td>
      <td><button class="company-button" data-detail="${company.company_id}">${escapeHtml(company.display_name)}</button><span class="company-meta">${INDUSTRIES[company.industry]} · ${escapeHtml(company.primary_archetype)}</span></td>
      <td class="score-cell">${score(item.score.overall_score)}</td>
      <td><span class="score-pill">${score(item.score.wealth_creation_score)}</span></td>
      <td><span class="score-pill">${score(item.score.employee_welfare_score)}</span></td>
      <td><span class="score-pill">${score(item.score.responsible_governance_score)}</span></td>
      <td><span class="completeness"><span class="mini-meter"><i style="width:${item.score.data_completeness * 100}%"></i></span>${percent(item.score.data_completeness)}</span></td>
      <td><button class="compare-add ${selected ? "selected" : ""}" data-compare="${company.company_id}">${selected ? "已选择" : "+ 比较"}</button></td>
    </tr>`;
  }).join("");
}

function bindEvents() {
  $("#searchInput").addEventListener("input", (event) => { state.query = event.target.value; renderRanking(); });
  $("#archetypeFilter").addEventListener("change", (event) => { state.archetype = event.target.value; renderRanking(); });
  $$(".filter").forEach((button) => button.addEventListener("click", () => {
    $$(".filter").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.industry = button.dataset.industry;
    renderRanking();
  }));
  $("#rankingBody").addEventListener("click", (event) => {
    const detail = event.target.closest("[data-detail]");
    const compare = event.target.closest("[data-compare]");
    if (detail) openCompany(detail.dataset.detail);
    if (compare) toggleCompare(compare.dataset.compare);
  });
  $("#clearCompare").addEventListener("click", () => { state.compare = []; updateCompare(); });
  $(".dialog-close").addEventListener("click", () => $("#companyDialog").close());
  $("#companyDialog").addEventListener("click", (event) => { if (event.target === $("#companyDialog")) $("#companyDialog").close(); });
  $("#openMethod").addEventListener("click", () => $("#method").scrollIntoView({behavior: "smooth"}));
}

function toggleCompare(companyId) {
  if (state.compare.includes(companyId)) state.compare = state.compare.filter((id) => id !== companyId);
  else if (state.compare.length < 3) state.compare.push(companyId);
  else alert("最多比较三家企业，请先移除一家。");
  updateCompare();
}

function updateCompare() {
  const companies = state.compare.map((id) => state.data.companies.find((company) => company.company_id === id));
  $("#compareTray").hidden = companies.length === 0;
  $("#compareCount").textContent = companies.length;
  $("#compareNames").textContent = companies.map((company) => company.display_name).join("、");
  $("#compareEmpty").hidden = companies.length !== 0;
  $("#compareGrid").hidden = companies.length === 0;
  renderRanking();
  if (!companies.length) return;
  const rows = [
    ["道财指数", (company) => score(latest(company).score.overall_score), (company) => latest(company).score.overall_score],
    ["基层收入/生活工资", (company) => valueOrDash(latest(company).derived.living_wage_ratio, (v) => `${Number(v).toFixed(2)}倍`), (company) => Math.min(100, (latest(company).derived.living_wage_ratio || 0) / 1.5 * 100)],
    ["人均劳动投入", (company) => valueOrDash(latest(company).derived.per_employee_cash_investment, money), (company) => Math.min(100, (latest(company).derived.per_employee_cash_investment || 0) / 350000 * 100)],
    ["劳动分配代理值", (company) => valueOrDash(latest(company).derived.labor_distribution_proxy, percent), (company) => (latest(company).derived.labor_distribution_proxy || 0) * 100],
    ["平均周工时", (company) => valueOrDash(latest(company).welfare.average_weekly_hours, (v) => `${v}小时`), (company) => Math.min(100, (latest(company).welfare.average_weekly_hours || 0) / 60 * 100)],
    ["社保覆盖率", (company) => valueOrDash(latest(company).welfare.social_insurance_coverage, percent), (company) => (latest(company).welfare.social_insurance_coverage || 0) * 100],
    ["外包待遇比例", (company) => valueOrDash(latest(company).welfare.contractor_welfare_ratio, percent), (company) => (latest(company).welfare.contractor_welfare_ratio || 0) * 100],
    ["数据完整度", (company) => percent(latest(company).score.data_completeness), (company) => latest(company).score.data_completeness * 100],
  ];
  const header = `<div class="compare-label">指标</div>${companies.map((company) => `<div class="compare-value company-head"><strong>${escapeHtml(company.display_name)}</strong><small>${INDUSTRIES[company.industry]}</small></div>`).join("")}`;
  const body = rows.map(([label, format, width]) => `<div class="compare-label">${label}</div>${companies.map((company) => `<div class="compare-value">${format(company)}<div class="compare-bar"><i style="width:${clampWidth(width(company))}%"></i></div></div>`).join("")}`).join("");
  $("#compareGrid").style.gridTemplateColumns = `160px repeat(${companies.length}, minmax(220px, 1fr))`;
  $("#compareGrid").innerHTML = header + body;
}

function clampWidth(value) { return Math.max(0, Math.min(100, Number(value) || 0)); }

function openCompany(companyId) {
  const company = state.data.companies.find((item) => item.company_id === companyId);
  const item = latest(company);
  const financial = item.financial;
  const welfare = item.welfare;
  const derived = item.derived;
  $("#dialogContent").innerHTML = `
    <div class="dialog-hero">
      <div><p class="eyebrow">模拟企业 · ${INDUSTRIES[company.industry]}</p><h2>${escapeHtml(company.display_name)}</h2><p>${escapeHtml(company.description)} · ${escapeHtml(company.primary_archetype)} · 数据完整度${percent(item.score.data_completeness)}</p></div>
      <div class="score-ring" style="--score:${item.score.overall_score}"><div><span>${score(item.score.overall_score)}</span><small>道财指数</small></div></div>
    </div>
    <div class="dialog-body">
      <div class="score-cards">
        <div class="score-card"><span>财富创造质量 / 25</span><strong>${score(item.score.wealth_creation_score)}</strong></div>
        <div class="score-card"><span>员工福祉与分享 / 60</span><strong>${score(item.score.employee_welfare_score)}</strong></div>
        <div class="score-card"><span>责任治理 / 15</span><strong>${score(item.score.responsible_governance_score)}</strong></div>
      </div>
      <div class="detail-grid">
        <section class="detail-panel"><h3>2025核心指标</h3><dl class="metric-list">
          ${metric("营业收入", money(financial.revenue))}
          ${metric("员工人数", `${Number(financial.employee_count_end).toLocaleString("zh-CN")}人`)}
          ${metric("人均劳动现金投入", valueOrDash(derived.per_employee_cash_investment, money))}
          ${metric("基层收入/生活工资", valueOrDash(derived.living_wage_ratio, (v) => `${Number(v).toFixed(2)}倍`))}
          ${metric("高管员工差距代理", valueOrDash(derived.executive_worker_gap_proxy, (v) => `${Number(v).toFixed(1)}倍`))}
          ${metric("平均周工时", valueOrDash(welfare.average_weekly_hours, (v) => `${v}小时`))}
          ${metric("社保覆盖率", valueOrDash(welfare.social_insurance_coverage, percent))}
          ${metric("外包劳动者比例", valueOrDash(derived.contractor_ratio, percent))}
        </dl></section>
        <section class="detail-panel"><h3>三年道财指数趋势</h3>${trendChart(company.years)}</section>
      </div>
    </div>`;
  $("#companyDialog").showModal();
}

function metric(label, value) { return `<div class="metric-row"><dt>${label}</dt><dd>${value}</dd></div>`; }

function trendChart(years) {
  const points = years.map((item, index) => ({ x: 32 + index * 130, y: 130 - item.score.overall_score * .9, score: item.score.overall_score, year: item.year }));
  const path = points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ");
  return `<svg class="trend-chart" viewBox="0 0 330 165" role="img" aria-label="2023至2025道财指数趋势">
    <line class="grid" x1="25" x2="305" y1="40" y2="40"/><line class="grid" x1="25" x2="305" y1="85" y2="85"/><line class="grid" x1="25" x2="305" y1="130" y2="130"/>
    <path class="line" d="${path}"/>${points.map((point) => `<circle class="dot" cx="${point.x}" cy="${point.y}" r="5"/><text x="${point.x}" y="${point.y - 12}" text-anchor="middle">${score(point.score)}</text><text x="${point.x}" y="153" text-anchor="middle">${point.year}</text>`).join("")}
  </svg>`;
}

init().catch((error) => {
  console.error(error);
  $("#rankingBody").innerHTML = '<tr><td colspan="8">数据加载失败，请刷新页面。</td></tr>';
});
