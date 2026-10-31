"""Spec section 7, failure labels: refusal > agent > memory > model."""
from builders import make_checkpoint, make_context, make_scenario
from mam.scoring import label_failure

CP = make_checkpoint(present=["2026-04-02"], absent=["2026-03-14"], stale=["2026-03-14"],
                     expect="2026-04-02", required_events=["e-0007", "e-0008"])
SC = make_scenario(CP)
GOOD_CTX = make_context(("fact", "Go-live 2026-04-02"))
BAD_CTX = make_context(("fact", "Go-live 2026-03-14"))
GOOD_OUT = {"tool": "none", "args": {}, "answer": "2026-04-02", "notes": []}
BAD_OUT = {"tool": "none", "args": {}, "answer": "2026-03-14", "notes": []}


def lab(refusal=False, written=("e-0007",), ctx=GOOD_CTX, out=GOOD_OUT):
    return label_failure(SC, CP.id, refusal=refusal, written_event_ids=set(written), context=ctx,
                         agent_output=out)


def test_refusal_wins_over_everything():
    assert lab(refusal=True, written=(), ctx=BAD_CTX, out=None) == "refusal"


def test_passing_checkpoint_is_ok():
    assert lab() == "ok"


def test_agent_skipped_the_tool():
    assert lab(written=(), ctx=BAD_CTX, out=BAD_OUT) == "agent"
    assert lab(written=("e-0099",), ctx=GOOD_CTX, out=BAD_OUT) == "agent"


def test_any_one_required_event_is_enough():
    assert lab(written=("e-0008",), ctx=BAD_CTX, out=BAD_OUT) == "memory"


def test_wrong_context_is_memory():
    assert lab(ctx=BAD_CTX, out=BAD_OUT) == "memory"


def test_right_context_wrong_answer_is_model():
    assert lab(ctx=GOOD_CTX, out=BAD_OUT) == "model"


def test_no_required_events_skips_agent_label():
    cp = make_checkpoint(cp_id="cp-2", present=["x1"], expect="x1")
    sc = make_scenario(cp)
    out = label_failure(sc, "cp-2", refusal=False, written_event_ids=set(),
                        context=make_context(("fact", "nothing")), agent_output=BAD_OUT)
    assert out == "memory"
