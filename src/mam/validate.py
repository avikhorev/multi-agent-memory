"""Validator of the reference ground truth (spec section 5). Error strings start with the rule id."""
from __future__ import annotations

import re

from .generate import ATTRS
from .scenario import Event, Scenario, dumps
from .scoring import normalize
from .types import Fact

TOKEN_RE = re.compile(r"(?:canary|inj)-\w*", re.IGNORECASE)
TOKEN_OK = re.compile(r"(?:canary|inj)-[0-9a-f]{8}", re.IGNORECASE)
EVENT_ID = re.compile(r"[ex]-\d{4}")
VARIANT_CATEGORIES = ("C1", "C3")


def _key(f: Fact) -> tuple[str, str]:
    return (f.entity, f.attribute)


def _first_sessions(s: Scenario) -> dict[str, int]:
    first: dict[str, int] = {}
    for sess in s.sessions:
        for e in sess.events:
            for fid in e.facts:
                first.setdefault(fid, sess.index)
    return first


def private_only_ids(s: Scenario) -> set[str]:
    """Facts stated only by private events: a view visible to its author, outside the shared truth."""
    reporters: dict[str, list[Event]] = {}
    for sess in s.sessions:
        for e in sess.events:
            for fid in e.facts:
                reporters.setdefault(fid, []).append(e)
    return {fid for fid, evs in reporters.items() if all(e.scope == "private" for e in evs)}


def known_facts(s: Scenario, session: int) -> list[Fact]:
    first = _first_sessions(s)
    private = private_only_ids(s)
    return [f for f in s.facts if first.get(f.id, 10**9) <= session and f.id not in private]


def current_facts(s: Scenario, session: int) -> list[Fact]:
    """Known facts not closed by a known successor of the same key."""
    known = known_facts(s, session)
    out = []
    for f in known:
        closed = f.valid_to is not None and any(
            g.id != f.id and _key(g) == _key(f) and g.valid_from == f.valid_to for g in known)
        if not closed:
            out.append(f)
    return out


AUTHORITY = {"user": 3, "tool": 2, "document": 1, "agent": 0}


def _updates(s: Scenario) -> list[tuple[Event, Fact]]:
    """(event, fact) pairs where a factor event states a replacing value."""
    by_id = {f.id: f for f in s.facts}
    return [(e, by_id[fid]) for sess in s.sessions for e in sess.events if e.factor
            for fid in e.facts if fid in by_id and by_id[fid].supersedes is not None]


def _overlapping(a: Fact, b: Fact) -> bool:
    a_end = a.valid_to if a.valid_to is not None else 10**9
    b_end = b.valid_to if b.valid_to is not None else 10**9
    return a.valid_from < b_end and b.valid_from < a_end


def _conflict_ids(s: Scenario) -> set[str]:
    out = set()
    for i, a in enumerate(s.facts):
        for b in s.facts[i + 1:]:
            if _key(a) == _key(b) and _overlapping(a, b):
                out.update((a.id, b.id))
    return out


def _styled(s: Scenario) -> list[tuple[Event, Fact, bool]]:
    """(event, fact, implicit) for the events that state an update or one side of a conflict."""
    out = [(e, f, s.variant == "implicit") for e, f in _updates(s)]
    if s.category == "C3":
        conflict = _conflict_ids(s)
        by_id = {f.id: f for f in s.facts}
        for sess in s.sessions:
            for e in sess.events:
                if e.factor and e.type == "note":
                    out += [(e, by_id[fid], s.variant == "implicit" and e.author == "worker")
                            for fid in e.facts if fid in conflict]
    return out


def _is_implicit(s: Scenario, e: Event, f: Fact) -> bool:
    return any(x is e and y is f and imp for x, y, imp in _styled(s))


def _derived_values(s: Scenario) -> set[str]:
    return {normalize(f.value) for e, f, imp in _styled(s) if imp}


def resolve(group: list[Fact]) -> Fact | None:
    """Winner of overlapping facts of one key by spec section 6; None means disputed."""
    top = max(f.valid_from for f in group)
    cands = [f for f in group if f.valid_from == top]
    if len(cands) > 1:
        best = max(AUTHORITY[f.source] for f in cands)
        cands = [f for f in cands if AUTHORITY[f.source] == best]
    return cands[0] if len(cands) == 1 else None


def _check_update_style(s: Scenario, errs: list[str]) -> None:
    for e, f, implicit in _styled(s):
        text = normalize(e.text)
        label = normalize(ATTRS[f.attribute][1])
        names_value = normalize(f.value) in text
        names_attr = label in text or f.attribute.replace("_", " ") in text or f.attribute in text
        if implicit and (names_value or names_attr):
            errs.append(f"R4: implicit update {e.id} states the new value or the attribute name")
        if not implicit and not (names_value and names_attr):
            errs.append(f"R4: explicit update {e.id} lacks the new value or the attribute name")


def _check_ids(s: Scenario, errs: list[str]) -> None:
    def dup(kind: str, ids: list[str]) -> None:
        seen = set()
        for i in ids:
            if i in seen:
                errs.append(f"R6: duplicate {kind} id {i}")
            seen.add(i)

    events = [e for sess in s.sessions for e in sess.events]
    dup("event", [e.id for e in events])
    dup("fact", [f.id for f in s.facts])
    dup("constraint", [c.id for c in s.constraints])
    dup("checkpoint", [c.id for c in s.checkpoints])
    pairs = [(c.session, c.role) for c in s.checkpoints]
    if len(pairs) != len(set(pairs)):
        errs.append("R6: two checkpoints share session and role")
    for e in events:
        if not EVENT_ID.fullmatch(e.id):
            errs.append(f"R6: bad event id {e.id}")


def _check_structure(s: Scenario, errs: list[str]) -> None:
    if s.split not in ("dev", "eval", "holdout"):
        errs.append(f"R6: bad split {s.split}")
    if s.variant not in ("none", "explicit", "implicit"):
        errs.append(f"R6: bad variant {s.variant}")
    if s.category not in VARIANT_CATEGORIES and s.variant != "none":
        errs.append("R6: variant must be none outside C1 and C3")
    if s.category in VARIANT_CATEGORIES and s.variant == "none":
        errs.append("R6: C1 and C3 need a variant")
    if s.category != "C3" and s.resolution != "none":
        errs.append("R6: resolution must be none outside C3")
    if s.category == "C3" and s.resolution == "none":
        errs.append("R6: C3 needs a resolution")
    if len(s.sessions) != s.n_sessions or [x.index for x in s.sessions] != list(range(1, s.n_sessions + 1)):
        errs.append("R6: sessions do not match n_sessions")
    for sess in s.sessions:
        base = [e for e in sess.events if not e.factor]
        counts = {t: sum(1 for e in base if e.type == t) for t in ("user_message", "tool_data", "note")}
        if counts["user_message"] != 1 or counts["tool_data"] > 2 or counts["note"] > 3:
            errs.append(f"R6: session {sess.index} has wrong base event counts {counts}")
        for e in sess.events:
            if e.type == "user_message" and (e.author, e.scope) != ("user", "task"):
                errs.append(f"R6: {e.id} user_message must be by user with task scope")
            if e.type == "tool_data" and (e.author != "tool" or e.tool is None or not e.args):
                errs.append(f"R6: {e.id} tool_data needs author tool, tool and args")
            if e.type == "note" and (e.author not in ("planner", "worker", "reviewer") or e.tool or e.args):
                errs.append(f"R6: {e.id} bad note fields")
            if e.type not in ("user_message", "tool_data", "note"):
                errs.append(f"R6: {e.id} bad type")
    for cp in s.checkpoints:
        if not 1 <= cp.session <= s.n_sessions:
            errs.append(f"R6: checkpoint {cp.id} session out of range")
    for c in s.constraints:
        if not 1 <= c.introduced_in <= s.n_sessions:
            errs.append(f"R6: constraint {c.id} introduced_in out of range")
    if s.category == "C0" and (any(e.factor for sess in s.sessions for e in sess.events)
                               or any(c.factor for c in s.checkpoints)):
        errs.append("R6: C0 must not contain factor elements")


def _check_intervals(s: Scenario, errs: list[str]) -> None:
    by_key: dict[tuple[str, str], list[Fact]] = {}
    for f in s.facts:
        by_key.setdefault(_key(f), []).append(f)
    ids = {f.id: f for f in s.facts}
    for f in s.facts:
        if f.valid_to is not None and f.valid_to <= f.valid_from:
            errs.append(f"R1: {f.id} has empty interval")
        if f.supersedes is not None:
            old = ids.get(f.supersedes)
            if old is None or _key(old) != _key(f) or old.valid_to != f.valid_from:
                errs.append(f"R1: {f.id} supersedes {f.supersedes} inconsistently")
        if f.valid_to is not None and not any(
                g.id != f.id and _key(g) == _key(f) and g.valid_from == f.valid_to for g in by_key[_key(f)]):
            errs.append(f"R1: {f.id} valid_to has no successor")
    private = private_only_ids(s)
    base_reported = {fid for sess in s.sessions for e in sess.events if not e.factor for fid in e.facts}
    for key, group in sorted(by_key.items()):
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                declared = (s.category == "C3" and any(c.kind == "conflict" for c in s.checkpoints)
                            and a.id not in base_reported and b.id not in base_reported)
                if _overlapping(a, b) and not declared and not ({a.id, b.id} & private):
                    errs.append(f"R1: {a.id} and {b.id} overlap for {key}")


def _check_events_and_facts(s: Scenario, errs: list[str]) -> None:
    fact_ids = {f.id for f in s.facts}
    events = {e.id: e for sess in s.sessions for e in sess.events}
    reported = set()
    for e in events.values():
        for fid in e.facts:
            if fid not in fact_ids:
                errs.append(f"R2: event {e.id} reports unknown fact {fid}")
            reported.add(fid)
    for f in s.facts:
        if f.id not in reported:
            errs.append(f"R2: fact {f.id} has no event")
    for f in s.facts:
        for e in events.values():
            if f.id in e.facts and normalize(f.value) not in normalize(e.text) and not _is_implicit(s, e, f):
                errs.append(f"R2: event {e.id} does not state the value of {f.id}")
    for cp in s.checkpoints:
        for eid in cp.required_events:
            if eid not in events:
                errs.append(f"R2: checkpoint {cp.id} requires unknown event {eid}")
    for c in s.constraints:
        e = events.get(c.event_id)
        if (e is None or e.type != "user_message" or c.introduced_in != _session_of(s, c.event_id)
                or normalize(c.text) not in normalize(e.text)):
            errs.append(f"R2: constraint {c.id} is not tied to a user_message of its session")


def _session_of(s: Scenario, event_id: str) -> int | None:
    for sess in s.sessions:
        if any(e.id == event_id for e in sess.events):
            return sess.index
    return None


def _check_checkpoints(s: Scenario, errs: list[str]) -> None:
    text = " ".join(normalize(e.text) for sess in s.sessions for e in sess.events)
    derived = _derived_values(s)

    def findable(p: str) -> bool:
        return normalize(p) in text or normalize(p) in derived

    for cp in s.checkpoints:
        known = known_facts(s, cp.session)
        groups: dict[tuple[str, str], list[Fact]] = {}
        for f in current_facts(s, cp.session):
            groups.setdefault(_key(f), []).append(f)
        winners = {k: (resolve(g) if len(g) > 1 else g[0]) for k, g in groups.items()}
        effective = [w for w in winners.values() if w is not None]
        if cp.answer.disputed:
            if cp.answer.expect is not None or cp.answer.stale:
                errs.append(f"R3: {cp.id} disputed answer must have no expected value or stale values")
            for pair in cp.context.disputed_both:
                ok = any(len(g) > 1 and winners[k] is None
                         and {normalize(x) for x in pair} == {normalize(f.value) for f in g}
                         for k, g in groups.items())
                if not ok:
                    errs.append(f"R3: {cp.id} pair {pair} is not an unresolved conflict")
            if not cp.context.disputed_both:
                errs.append(f"R3: {cp.id} disputed checkpoint lists no pair")
        elif cp.answer.expect is not None:
            exp = normalize(cp.answer.expect)
            hits = [w for w in effective if normalize(w.value) == exp]
            if not hits:
                errs.append(f"R3: {cp.id} expected value {cp.answer.expect} is not the current or winning fact")
            for st in cp.answer.stale:
                ns = normalize(st)
                if not any(normalize(g.value) == ns and g.id != h.id and _key(g) == _key(h)
                           for g in known for h in hits):
                    errs.append(f"R3: {cp.id} stale value {st} is not a replaced or losing value of the same key")
        for p in cp.context.present + [x for pair in cp.context.disputed_both for x in pair]:
            if not findable(p):
                errs.append(f"R4: {cp.id} present string {p} not found in any event")
        for p in cp.context.absent + cp.answer.stale:
            n = normalize(p)
            for f in effective:
                v = normalize(f.value)
                if n in v or v in n:
                    errs.append(f"R4: {cp.id} string {p} collides with current value {f.value}")


def _check_tokens(s: Scenario, errs: list[str]) -> None:
    in_events: set[str] = set()
    for sess in s.sessions:
        for e in sess.events:
            for tok in TOKEN_RE.findall(e.text):
                if not TOKEN_OK.fullmatch(tok):
                    errs.append(f"R5: malformed token {tok} in {e.id}")
                in_events.add(tok.lower())
                is_canary = tok.lower().startswith("canary")
                allowed = e.factor and ((is_canary and e.type == "note" and e.scope == "private"
                                         and s.category == "C4")
                                        or (not is_canary and e.type == "tool_data" and s.category == "C5"))
                if not allowed:
                    errs.append(f"R5: token {tok} in event {e.id} that must not contain it")
    listed: set[str] = set()
    absent_all = {normalize(p) for cp in s.checkpoints for p in cp.context.absent}
    for f in s.facts:
        if f.id not in private_only_ids(s):
            continue
        if normalize(f.value) not in absent_all:
            errs.append(f"R5: private value of {f.id} is not listed as absent by any checkpoint")
        for sess in s.sessions:
            for e in sess.events:
                if e.scope != "private" and normalize(f.value) in normalize(e.text):
                    errs.append(f"R5: private value of {f.id} appears in non-private event {e.id}")
    for cp in s.checkpoints:
        for p in cp.context.absent + cp.context.absent_outside_quoted:
            if TOKEN_RE.fullmatch(p):
                listed.add(p.lower())
        for p in (cp.task_text, *(cp.context.present)):
            if TOKEN_RE.search(p):
                errs.append(f"R5: checkpoint {cp.id} leaks a token in its task or present strings")
    for tok in sorted(in_events - listed):
        errs.append(f"R5: token {tok} is not covered by any checkpoint")
    for tok in sorted(listed - in_events):
        errs.append(f"R5: checkpoint token {tok} does not occur in any event")


def validate(s: Scenario, check_determinism: bool = True) -> list[str]:
    errs: list[str] = []
    _check_ids(s, errs)
    _check_structure(s, errs)
    _check_intervals(s, errs)
    _check_events_and_facts(s, errs)
    _check_update_style(s, errs)
    _check_checkpoints(s, errs)
    _check_tokens(s, errs)
    if check_determinism:
        from .generate import regenerate
        if dumps(regenerate(s)) != dumps(s):
            errs.append("R7: scenario differs from its regeneration")
    return errs
