const state = {
  records: [],
  reviews: {},
  filtered: [],
  currentId: null,
  filter: 'all',
  query: '',
};

const $ = (selector) => document.querySelector(selector);
const els = {
  layout: $('#reviewLayout'), empty: $('#emptyState'), emptyMessage: $('#emptyMessage'),
  progressText: $('#progressText'), progressBar: $('#progressBar'), saveState: $('#saveState'),
  search: $('#searchInput'), filters: $('#filters'), position: $('#positionText'),
  prev: $('#prevButton'), next: $('#nextButton'), id: $('#characterId'), name: $('#characterName'),
  organization: $('#organization'), badge: $('#decisionBadge'), meta: $('#metaGrid'),
  sourceFacts: $('#sourceFacts'), assumptions: $('#designAssumptions'), concept: $('#sceneConcept'),
  unknowns: $('#unknowns'), sourceLocator: $('#sourceLocator'), runId: $('#runId'), qa: $('#qaNotes'),
  image: $('#portraitImage'), imageError: $('#imageError'), note: $('#reviewNote'), clear: $('#clearButton'),
};

const decisionLabels = { pass: '已通过', reject: '未通过', pending: '待定', unreviewed: '未审核' };

function currentRecord() {
  return state.records.find((record) => record.id === state.currentId) ?? null;
}

function setSaveState(text, kind = '') {
  els.saveState.textContent = text;
  els.saveState.className = `save-state ${kind}`.trim();
}

function appendList(target, values, fallback) {
  target.replaceChildren();
  const items = values?.length ? values : [fallback];
  for (const value of items) {
    const li = document.createElement('li');
    li.textContent = value;
    target.append(li);
  }
}

function metaCard(label, value) {
  const card = document.createElement('div');
  card.className = 'meta-card';
  const caption = document.createElement('span');
  caption.textContent = label;
  const strong = document.createElement('strong');
  strong.textContent = value || '—';
  card.append(caption, strong);
  return card;
}

function updateProgress() {
  const reviewed = Object.values(state.reviews).filter((item) => ['pass', 'reject', 'pending'].includes(item.decision)).length;
  const passed = Object.values(state.reviews).filter((item) => item.decision === 'pass').length;
  els.progressText.textContent = `已审核 ${reviewed} / ${state.records.length} · 通过 ${passed}`;
  els.progressBar.style.width = `${state.records.length ? reviewed / state.records.length * 100 : 0}%`;
}

function applyFilters({ preserveCurrent = true } = {}) {
  const previousId = preserveCurrent ? state.currentId : null;
  const query = state.query.trim().toLocaleLowerCase('zh-CN');
  state.filtered = state.records.filter((record) => {
    const decision = state.reviews[record.id]?.decision ?? 'unreviewed';
    const statusMatches = state.filter === 'all' || decision === state.filter;
    const haystack = `${record.id} ${record.name} ${record.organization}`.toLocaleLowerCase('zh-CN');
    return statusMatches && (!query || haystack.includes(query));
  });
  state.currentId = state.filtered.some((item) => item.id === previousId)
    ? previousId
    : (state.filtered[0]?.id ?? null);
  render();
}

function render() {
  updateProgress();
  const record = currentRecord();
  if (!record) {
    els.layout.hidden = true;
    els.empty.hidden = false;
    els.emptyMessage.textContent = state.records.length ? '当前筛选条件下没有角色。' : '没有读取到角色资料。';
    els.position.textContent = '0 / 0';
    els.prev.disabled = true;
    els.next.disabled = true;
    return;
  }

  els.layout.hidden = false;
  els.empty.hidden = true;
  const index = state.filtered.findIndex((item) => item.id === record.id);
  els.position.textContent = `${index + 1} / ${state.filtered.length}`;
  els.prev.disabled = index <= 0;
  els.next.disabled = index >= state.filtered.length - 1;

  const review = state.reviews[record.id];
  const decision = review?.decision ?? 'unreviewed';
  els.id.textContent = record.id;
  els.name.textContent = record.name;
  els.organization.textContent = record.organization;
  els.badge.textContent = decisionLabels[decision];
  els.badge.className = `decision-badge ${decision}`;
  els.meta.replaceChildren(
    metaCard('能力标记', record.marker),
    metaCard('设计等级', `${record.grade} · ${record.priority}`),
    metaCard('生产状态', record.productionStatus),
  );
  appendList(els.sourceFacts, record.sourceFacts, '总控未提供结构化事实，请参照来源定位。');
  appendList(els.assumptions, record.designAssumptions, '没有单列本轮视觉假设。');
  els.concept.textContent = record.sceneConcept || '没有单列画面构思。';
  els.unknowns.textContent = record.unknowns || '无';
  els.sourceLocator.textContent = record.sourceLocator || '—';
  els.runId.textContent = record.runId || '—';
  els.qa.textContent = record.qaNotes?.join('；') || '—';
  els.note.value = review?.note ?? '';
  els.clear.disabled = !review;
  document.querySelectorAll('.decision').forEach((button) => {
    button.classList.toggle('selected', button.dataset.decision === decision);
  });

  els.imageError.hidden = true;
  els.image.hidden = false;
  els.image.alt = `${record.name}候选立绘`;
  els.image.src = `${record.imageUrl}?v=${encodeURIComponent(record.runId || '')}`;
}

function move(delta) {
  const index = state.filtered.findIndex((record) => record.id === state.currentId);
  const next = state.filtered[index + delta];
  if (next) {
    state.currentId = next.id;
    render();
    document.querySelector('.profile-panel')?.scrollTo({ top: 0 });
  }
}

async function submitDecision(decision) {
  const record = currentRecord();
  if (!record) return;
  setSaveState('正在保存…', 'saving');
  try {
    const response = await fetch('/api/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: record.id, decision, note: els.note.value.trim() }),
    });
    if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`);
    const payload = await response.json();
    state.reviews = payload.decisions;
    setSaveState('已保存', 'saved');
    applyFilters();
  } catch (error) {
    setSaveState(`保存失败：${error.message}`, 'error');
  }
}

async function clearDecision() {
  const record = currentRecord();
  if (!record || !state.reviews[record.id]) return;
  setSaveState('正在清除…', 'saving');
  try {
    const response = await fetch(`/api/review/${encodeURIComponent(record.id)}`, { method: 'DELETE' });
    if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`);
    const payload = await response.json();
    state.reviews = payload.decisions;
    setSaveState('已清除', 'saved');
    applyFilters();
  } catch (error) {
    setSaveState(`清除失败：${error.message}`, 'error');
  }
}

els.prev.addEventListener('click', () => move(-1));
els.next.addEventListener('click', () => move(1));
els.search.addEventListener('input', () => { state.query = els.search.value; applyFilters(); });
els.filters.addEventListener('click', (event) => {
  const button = event.target.closest('[data-filter]');
  if (!button) return;
  state.filter = button.dataset.filter;
  document.querySelectorAll('.filter').forEach((item) => item.classList.toggle('active', item === button));
  applyFilters({ preserveCurrent: false });
});
document.querySelectorAll('.decision').forEach((button) => button.addEventListener('click', () => submitDecision(button.dataset.decision)));
els.clear.addEventListener('click', clearDecision);
els.image.addEventListener('error', () => { els.image.hidden = true; els.imageError.hidden = false; });
document.addEventListener('keydown', (event) => {
  if (event.target.matches('input, textarea')) return;
  if (event.key === 'ArrowLeft') move(-1);
  if (event.key === 'ArrowRight') move(1);
  if (event.key.toLowerCase() === 'a') submitDecision('pass');
  if (event.key.toLowerCase() === 'r') submitDecision('reject');
  if (event.key.toLowerCase() === 'p') submitDecision('pending');
});

try {
  const response = await fetch('/api/roster');
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = await response.json();
  state.records = payload.records;
  state.reviews = payload.decisions;
  state.filtered = [...state.records];
  state.currentId = state.filtered[0]?.id ?? null;
  setSaveState('审核记录已载入');
  render();
} catch (error) {
  els.emptyMessage.textContent = `无法连接本地审核服务：${error.message}。请运行 start-review.cmd 后访问终端显示的网址。`;
  setSaveState('读取失败', 'error');
}
