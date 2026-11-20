/* Read-only, dependency-free replay of exported trace evidence. No fetch/LLM. */
(() => {
  'use strict';
  const bundle = window.MAM_DEMO_DATA;
  if (!bundle || bundle.schema !== 1) {
    document.body.textContent = 'Demo data is unavailable. Generate it with: python3 scripts/build_visual_demo.py';
    return;
  }

  const cases = Object.fromEntries(bundle.cases.map(item => [item.id, item]));
  const stages = [
    { title: 'What was available and what was read', note: 'source_note' },
    { title: 'What actually reached memory', note: 'memory_note' },
    { title: 'How the agent acted', note: 'agent_note' },
    { title: 'How the answer was graded', note: 'result_note' },
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
  const plural = (n, one, many) => (n === 1 ? one : many);
  const statusName = status => ({ ok: 'ok', agent: 'agent', memory: 'memory', model: 'model', refusal: 'refusal' })[status] || status;
  const rel = path => '../../' + path;

  function renderSources(container, scenario, system) {
    for (const event of scenario.focus_events) {
      const evidence = system.sources[event.id];
      const isTool = event.type === 'tool_data';
      const label = evidence.written ? 'written' : 'not read';
      const tone = evidence.written ? 'good' : 'bad';
      const title = `${event.id} · session ${event.session}`;
      const item = card(title, { label, kind: tone });
      const firstLine = event.text.split('\n').slice(0, 2).join(' · ');
      item.append(para(firstLine));
      const meta = element('div', 'field-row');
      append(meta, element('span', 'field-caption', 'TYPE'), element('span', 'field-value', isTool ? event.tool : event.type),
        element('span', 'field-caption', 'TRUST'), element('span', 'field-value', evidence.trust || (isTool ? 'no record' : '—')));
      item.append(meta, detail('Show full text of the source event', event.text));
      container.append(item);
    }
    if (scenario.focus_events.some(evt => !system.sources[evt.id].written)) {
      container.append(notice('The event is in the scenario, but the selected trace has no write operation with this entry_id. Tool availability is not the same as reading.', 'warning'));
    } else {
      container.append(notice('The write operation confirms the record. This does not yet mean the needed fact ended up in the checkpoint context.'));
    }
  }

  function renderMemory(container, scenario, system, systemName) {
    const context = system.context;
    for (const event of scenario.focus_events) {
      const observed = system.sources[event.id];
      const item = card(event.id + ' · path through memory', {
        label: observed.written ? 'write found' : 'no write',
        kind: observed.written ? 'good' : 'bad',
      });
      item.append(row('Record', observed.written ? 'Yes' : 'No'));
      if (systemName === 'ours') {
        item.append(row('Extraction', observed.facts.length ? `${observed.facts.length} ${plural(observed.facts.length, 'fact', 'facts')}` : 'no confirmed facts'));
        for (const fact of observed.facts) {
          const validFrom = fact.valid_from === -1 ? 'no date' : `valid_from=${fact.valid_from}`;
          item.append(code(`${fact.entity} / ${fact.attribute} = ${fact.value}\nsource=${fact.source} · ${validFrom}`));
        }
      } else {
        item.append(row('Format', 'Raw records (no extractor)'));
      }
      item.append(row('IDs in context()', observed.context_ids.length ? observed.context_ids.length : 'none'));
      if (observed.context_ids.length) item.append(detail('Which IDs context() returned', observed.context_ids.join('\n')));
      container.append(item);
    }
    if (system.resolution.length) {
      for (const resolved of system.resolution) {
        const item = card('Version resolution · resolve', { label: resolved.rule, kind: 'good' });
        append(item, row('Current', resolved.winner), row('Superseded', resolved.loser));
        container.append(item);
      }
    }
    const stats = card('Checkpoint read snapshot', null);
    append(stats, row('Role', scenario.question.role), row('Passed to agent', `${context.tokens} tokens`),
      row('Number of item_ids', context.total_ids));
    if (context.sample_ids.length) stats.append(detail('First 8 IDs (reference, not text)', context.sample_ids.join('\n')));
    container.append(stats);
    container.append(notice('A source ID may refer to a document fragment rather than the original fact. The live trace has no full context() text; the IDs do not show which exact values the agent saw.', 'warning'));
  }

  function renderAgent(container, scenario, system) {
    const tools = card(`Worker · session ${scenario.worker_session}`);
    tools.append(para('Two Worker model calls from agent_action. The first chooses an action, and the runner executes it. The second receives the tool result; the runner executes its action only if it is update_record, so no repeat read is started (live.py).'));
    const executed = (idx, tool) => idx === 0 ? tool !== 'none' : tool === 'update_record';
    for (const [idx, action] of system.worker_actions.entries()) {
      const line = element('div', 'field-row');
      const name = idx === 0 ? 'CALL 1 · CHOICE' : 'CALL 2 · AFTER RESULT';
      const status = executed(idx, action.tool) ? 'executed' : 'not executed';
      append(line, element('span', 'field-caption', `${name} · ${status}`), element('span', 'field-value', action.tool),
        element('span', 'field-caption', 'ARGS'), element('span', 'field-value', JSON.stringify(action.args)));
      tools.append(line);
    }
    container.append(tools);
    const answer = element('div', `answer-card${system.checkpoint.passed ? '' : ' bad'}`);
    append(answer, element('h4', '', `${scenario.question.role.toUpperCase()} · SESSION ${scenario.question.session} · ${scenario.checkpoint}`),
      para(scenario.question.text), element('blockquote', 'answer-text', system.checkpoint.answer));
    container.append(answer);
    const read = card('What is known about the answer context');
    append(read, row('Token count', system.context.tokens), row('Context quality', system.checkpoint.context_passed ? 'context_passed = true' : 'context_passed = false'));
    container.append(read);
  }

  function renderResults(container, scenario, system, systemName) {
    const grade = system.checkpoint;
    const grid = element('div', 'result-grid');
    const outcome = element('div', 'result-tile');
    append(outcome, element('span', '', 'ANSWER / passed'), element('strong', grade.passed ? '' : 'bad', grade.passed ? 'PASS' : 'FAIL'));
    const context = element('div', 'result-tile');
    append(context, element('span', '', 'CONTEXT / context_passed'), element('strong', grade.context_passed ? '' : 'bad', grade.context_passed ? 'PASS' : 'FAIL'));
    append(grid, outcome, context);
    container.append(grid);
    const item = card(`Evaluator label · ${statusName(grade.label)}`, { label: grade.passed ? 'ok' : 'failed', kind: grade.passed ? 'good' : 'bad' });
    append(item, row('Expected', scenario.question.expected), row('Label', grade.label), row('Source reachable', grade.reachable ? 'Yes' : 'No'));
    if (scenario.question.stale.length) item.append(row('Forbidden values', scenario.question.stale.join(', ')));
    item.append(row('Violations', grade.violations.length ? grade.violations.join(' · ') : 'none'));
    container.append(item);

    const comparison = element('div', 'comparison');
    for (const sys of ['ours', 'full_history']) {
      const other = scenario.systems[sys].checkpoint;
      const tile = element('div', 'compare-item' + (sys === systemName ? ' selected' : ''));
      append(tile, element('strong', '', sys), element('span', '', `${other.passed ? 'PASS' : 'FAIL'} · ${other.label}`));
      comparison.append(tile);
    }
    container.append(comparison);
    container.append(notice("This is one specific run (r0). The labels follow the benchmark rules; they do not explain causality and do not measure the model's overall accuracy.", grade.passed ? '' : 'warning'));
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
    $('metric-source-desc').textContent = `${plural(written, 'record', 'records')} of ${count} key events`;
    $('metric-tokens').textContent = system.context.tokens.toLocaleString('en-US');
    $('metric-outcome').textContent = system.checkpoint.passed ? 'PASS' : 'FAIL';
    $('metric-outcome').className = system.checkpoint.passed ? 'good' : 'bad';
    $('metric-label').textContent = `label: ${system.checkpoint.label}`;
    $('step-counter').textContent = `STEP 0${state.step + 1} / 04`;
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
    for (const [name, path] of [['Scenario', scenario.files.scenario], ['Trace · JSONL', scenario.files[state.system].trace], ['Grade · JSON', scenario.files[state.system].unit]]) {
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
    $('play').querySelector('span').textContent = 'Show step by step';
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
    $('play').querySelector('span').textContent = 'Stop';
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
