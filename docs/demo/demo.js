/* Read-only, dependency-free replay of exported trace evidence. No fetch/LLM. */
(() => {
  'use strict';
  const bundle = window.MAM_DEMO_DATA;
  if (!bundle || bundle.schema !== 1) {
    document.body.textContent = 'Данные демо недоступны. Сгенерируйте их: python3 scripts/build_visual_demo.py';
    return;
  }

  const cases = Object.fromEntries(bundle.cases.map(item => [item.id, item]));
  const stages = [
    { title: 'Что было доступно и что прочитали', note: 'source_note' },
    { title: 'Что действительно попало в память', note: 'memory_note' },
    { title: 'Как действовал агент', note: 'agent_note' },
    { title: 'Как был оценён ответ', note: 'result_note' },
  ];
  const state = { caseId: 'c1-update', system: 'ours', step: 0 };
  const $ = id => document.getElementById(id);
  let timer = null;

  const element = (tag, className, value) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (value !== undefined && value !== null) el.textContent = String(value);
    return el;
  };
  const append = (parent, ...children) => { for (const child of children) parent.append(child); return parent; };
  const chip = (value, tone) => element('span', `chip ${tone}`, value);
  const card = (name, tone, body) => {
    const container = element('div', 'data-card');
    const heading = element('div', 'card-heading');
    append(heading, element('span', 'mono-title', name));
    if (tone) heading.append(chip(tone.label, tone.kind));
    container.append(heading);
    if (body) container.append(body);
    return container;
  };
  const para = (text, cls = '') => element('p', cls, text);
  const row = (key, value) => append(element('div', 'key-value'), element('span', 'k', key), element('span', 'v', value));
  const code = (value) => element('pre', 'code-box', typeof value === 'string' ? value : JSON.stringify(value, null, 2));
  const notice = (text, kind = '') => element('div', `callout ${kind}`, text);
  const detail = (summary, content) => {
    const node = element('details', 'details');
    append(node, element('summary', '', summary), code(content));
    return node;
  };
  const plural = (n, a, b, c) => {
    const x = n % 100;
    if (x >= 11 && x <= 14) return c;
    return n % 10 === 1 ? a : n % 10 >= 2 && n % 10 <= 4 ? b : c;
  };
  const statusName = status => ({ ok: 'ok', agent: 'agent', memory: 'memory', model: 'model', refusal: 'refusal' })[status] || status;
  const rel = path => '../../' + path;

  function renderSources(container, scenario, system) {
    for (const event of scenario.focus_events) {
      const evidence = system.sources[event.id];
      const isTool = event.type === 'tool_data';
      const label = evidence.written ? 'записано' : 'не прочитано';
      const tone = evidence.written ? 'good' : 'bad';
      const title = `${event.id} · сессия ${event.session}`;
      const item = card(title, { label, kind: tone });
      const firstLine = event.text.split('\n').slice(0, 2).join(' · ');
      item.append(para(firstLine));
      const meta = element('div', 'field-row');
      append(meta, element('span', 'field-caption', 'ТИП'), element('span', 'field-value', isTool ? event.tool : event.type),
        element('span', 'field-caption', 'TRUST'), element('span', 'field-value', evidence.trust || (isTool ? 'нет записи' : '—')));
      item.append(meta, detail('Читать полный текст исходного события', event.text));
      container.append(item);
    }
    if (scenario.focus_events.some(evt => !system.sources[evt.id].written)) {
      container.append(notice('Событие есть в сценарии, но отсутствует операция write с этим entry_id в выбранной трассе. Доступность инструмента не равна чтению.', 'warning'));
    } else {
      container.append(notice('Запись подтверждена операцией write. Это ещё не означает, что нужный факт окажется в контексте контрольной точки.'));
    }
  }

  function renderMemory(container, scenario, system, systemName) {
    const context = system.context;
    for (const event of scenario.focus_events) {
      const observed = system.sources[event.id];
      const item = card(event.id + ' · путь через память', {
        label: observed.written ? 'write найден' : 'write нет',
        kind: observed.written ? 'good' : 'bad',
      });
      item.append(row('Запись', observed.written ? 'Да' : 'Нет'));
      if (systemName === 'ours') {
        item.append(row('Извлечение', observed.facts.length ? `${observed.facts.length} ${plural(observed.facts.length, 'факт', 'факта', 'фактов')}` : 'нет подтверждённых фактов'));
        for (const fact of observed.facts) {
          const validFrom = fact.valid_from === -1 ? 'без даты' : `valid_from=${fact.valid_from}`;
          item.append(code(`${fact.entity} / ${fact.attribute} = ${fact.value}\nsource=${fact.source} · ${validFrom}`));
        }
      } else {
        item.append(row('Формат', 'Сырые записи (без экстрактора)'));
      }
      item.append(row('ID в context()', observed.context_ids.length ? observed.context_ids.length : 'нет'));
      if (observed.context_ids.length) item.append(detail('Какие именно ID вернул context()', observed.context_ids.join('\n')));
      container.append(item);
    }
    if (system.resolution.length) {
      for (const resolved of system.resolution) {
        const item = card('Разрешение версий · resolve', { label: resolved.rule, kind: 'good' });
        append(item, row('Текущее', resolved.winner), row('Устарело', resolved.loser));
        container.append(item);
      }
    }
    const stats = card('Снимок чтения контрольной точки', null);
    append(stats, row('Роль', scenario.question.role), row('Передано агенту', `${context.tokens} токенов`),
      row('Количество item_ids', context.total_ids));
    if (context.sample_ids.length) stats.append(detail('Первые 8 ID (ориентир, не текст)', context.sample_ids.join('\n')));
    container.append(stats);
    container.append(notice('ID источника может обозначать фрагменты документа, а не исходный факт. Полного текста context() в живой трассе нет; из ID нельзя выводить, какие именно значения увидел агент.', 'warning'));
  }

  function renderAgent(container, scenario, system) {
    const tools = card(`Worker · сессия ${scenario.worker_session}`);
    tools.append(para('Два вызова модели Worker из agent_action. Первый выбирает действие, и раннер его выполняет. Второй получает результат инструмента; раннер выполняет его действие, только если это update_record, повторное чтение не запускается (live.py).'));
    const executed = (idx, tool) => idx === 0 ? tool !== 'none' : tool === 'update_record';
    for (const [idx, action] of system.worker_actions.entries()) {
      const line = element('div', 'field-row');
      const name = idx === 0 ? 'ВЫЗОВ 1 · ВЫБОР' : 'ВЫЗОВ 2 · ПОСЛЕ РЕЗУЛЬТАТА';
      const status = executed(idx, action.tool) ? 'выполнено' : 'не выполнялось';
      append(line, element('span', 'field-caption', `${name} · ${status}`), element('span', 'field-value', action.tool),
        element('span', 'field-caption', 'ARGS'), element('span', 'field-value', JSON.stringify(action.args)));
      tools.append(line);
    }
    container.append(tools);
    const answer = element('div', `answer-card${system.checkpoint.passed ? '' : ' bad'}`);
    append(answer, element('h4', '', `${scenario.question.role.toUpperCase()} · СЕССИЯ ${scenario.question.session} · ${scenario.checkpoint}`),
      para(scenario.question.text), element('blockquote', 'answer-text', system.checkpoint.answer));
    container.append(answer);
    const read = card('Что известно о контексте ответа');
    append(read, row('Число токенов', system.context.tokens), row('Качество контекста', system.checkpoint.context_passed ? 'context_passed = true' : 'context_passed = false'));
    container.append(read);
  }

  function renderResults(container, scenario, system, systemName) {
    const grade = system.checkpoint;
    const grid = element('div', 'result-grid');
    const outcome = element('div', 'result-tile');
    append(outcome, element('span', '', 'ОТВЕТ / passed'), element('strong', grade.passed ? '' : 'bad', grade.passed ? 'PASS' : 'FAIL'));
    const context = element('div', 'result-tile');
    append(context, element('span', '', 'КОНТЕКСТ / context_passed'), element('strong', grade.context_passed ? '' : 'bad', grade.context_passed ? 'PASS' : 'FAIL'));
    append(grid, outcome, context);
    container.append(grid);
    const item = card(`Метка оценщика · ${statusName(grade.label)}`, { label: grade.passed ? 'ok' : 'не пройдено', kind: grade.passed ? 'good' : 'bad' });
    append(item, row('Ожидается', scenario.question.expected), row('Метка', grade.label), row('Доступен источник', grade.reachable ? 'Да' : 'Нет'));
    if (scenario.question.stale.length) item.append(row('Запрещённые значения', scenario.question.stale.join(', ')));
    item.append(row('Нарушения', grade.violations.length ? grade.violations.join(' · ') : 'нет'));
    container.append(item);

    const comparison = element('div', 'comparison');
    for (const sys of ['ours', 'full_history']) {
      const other = scenario.systems[sys].checkpoint;
      const tile = element('div', 'compare-item' + (sys === systemName ? ' selected' : ''));
      append(tile, element('strong', '', sys), element('span', '', `${other.passed ? 'PASS' : 'FAIL'} · ${other.label}`));
      comparison.append(tile);
    }
    container.append(comparison);
    container.append(notice('Это один конкретный прогон (r0). Метки следуют правилам бенчмарка, не объясняют причинность и не измеряют общую точность модели.', grade.passed ? '' : 'warning'));
  }

  function render() {
    const scenario = cases[state.caseId];
    const system = scenario.systems[state.system];
    $('case-select').value = state.caseId;
    $('case-description').textContent = scenario.description;
    for (const button of document.querySelectorAll('[data-system]')) {
      button.setAttribute('aria-pressed', String(button.dataset.system === state.system));
    }
    for (const button of document.querySelectorAll('[data-step]')) {
      if (Number(button.dataset.step) === state.step) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    }
    for (const node of document.querySelectorAll('[data-node]')) {
      const idx = Number(node.dataset.node);
      node.classList.toggle('active', idx === state.step);
      node.classList.toggle('done', idx < state.step);
    }
    for (const edge of document.querySelectorAll('[data-edge]')) {
      edge.classList.toggle('done', Number(edge.dataset.edge) < state.step);
    }
    for (const [idx, dot] of document.querySelectorAll('.progress-dots span').entries()) {
      dot.classList.toggle('active', idx === state.step);
    }
    const written = Object.values(system.sources).filter(item => item.written).length;
    const count = scenario.focus_events.length;
    $('metric-source').textContent = `${written}/${count}`;
    $('metric-source').className = written === count ? 'good' : 'bad';
    $('metric-source-desc').textContent = `${plural(written, 'запись', 'записи', 'записей')} из ${count} ключевых событий`;
    $('metric-tokens').textContent = system.context.tokens.toLocaleString('ru-RU');
    $('metric-outcome').textContent = system.checkpoint.passed ? 'PASS' : 'FAIL';
    $('metric-outcome').className = system.checkpoint.passed ? 'good' : 'bad';
    $('metric-label').textContent = `метка: ${system.checkpoint.label}`;
    $('step-counter').textContent = `ШАГ 0${state.step + 1} / 04`;
    $('story-path').textContent = `${scenario.scenario} / ${scenario.checkpoint}`;
    $('step-title').textContent = stages[state.step].title;
    $('step-lead').textContent = scenario[stages[state.step].note];
    const body = $('step-content');
    body.replaceChildren();
    if (state.step === 0) renderSources(body, scenario, system);
    if (state.step === 1) renderMemory(body, scenario, system, state.system);
    if (state.step === 2) renderAgent(body, scenario, system);
    if (state.step === 3) renderResults(body, scenario, system, state.system);
    $('previous').disabled = state.step === 0;
    $('next').disabled = state.step === 3;
    $('checkpoint-id').textContent = `${scenario.checkpoint} · ${scenario.question.role}`;
    $('checkpoint-question').textContent = scenario.question.text;
    const files = $('file-links');
    files.replaceChildren();
    for (const [name, path] of [['Сценарий', scenario.files.scenario], ['Трасса · JSONL', scenario.files[state.system].trace], ['Оценка · JSON', scenario.files[state.system].unit]]) {
      const link = element('a', '', name);
      link.href = rel(path);
      link.title = path;
      append(link, element('span', '', '↗'));
      files.append(link);
    }
    // Hashes are optional: a file:// URL still works without a server.
    const hash = `#${state.caseId}/${state.system}/${state.step + 1}`;
    if (location.hash !== hash) {
      try { history.replaceState(null, '', hash); } catch (_) { /* Some file:// browsers restrict history. */ }
    }
  }

  function stop() {
    if (timer !== null) clearInterval(timer);
    timer = null;
    $('play').setAttribute('aria-pressed', 'false');
    $('play').querySelector('span').textContent = 'Показать по шагам';
    $('play').firstChild.textContent = '▶ ';
  }
  function change(step) {
    stop();
    state.step = Math.min(3, Math.max(0, step));
    render();
  }
  function play() {
    if (timer !== null) { stop(); return; }
    if (state.step === 3) { state.step = 0; render(); }
    $('play').setAttribute('aria-pressed', 'true');
    $('play').querySelector('span').textContent = 'Остановить';
    $('play').firstChild.textContent = 'Ⅱ ';
    timer = setInterval(() => {
      if (document.hidden) return;
      if (state.step === 3) { stop(); return; }
      state.step += 1;
      render();
      if (state.step === 3) stop();
    }, 4300);
  }

  function readHash() {
    const [caseId, system, step] = location.hash.slice(1).split('/');
    if (cases[caseId]) state.caseId = caseId;
    if (system === 'ours' || system === 'full_history') state.system = system;
    if (['1', '2', '3', '4'].includes(step)) state.step = Number(step) - 1;
  }
  readHash();
  $('case-select').addEventListener('change', event => { stop(); state.caseId = event.target.value; state.step = 0; render(); });
  document.querySelectorAll('[data-system]').forEach(button => button.addEventListener('click', () => {
    stop(); state.system = button.dataset.system; render();
  }));
  document.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => change(Number(button.dataset.step))));
  $('previous').addEventListener('click', () => change(state.step - 1));
  $('next').addEventListener('click', () => change(state.step + 1));
  $('play').addEventListener('click', play);
  window.addEventListener('hashchange', () => { stop(); readHash(); render(); });
  document.querySelector('.step-navigation').addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const next = Math.min(3, Math.max(0, state.step + (event.key === 'ArrowRight' ? 1 : -1)));
    change(next);
    document.querySelector(`[data-step="${next}"]`).focus();
  });
  render();
})();
