"""Tests for the soei ledger, verification layer, and harness."""
import copy
import json

from soei.harness import generate_cohort, generate_session
from soei.ledger import GENESIS, Ledger, verify
from soei.run import analyse_session, attack_ledger
from soei.verify import episode_verdicts, todo_verdicts


def _ledger_of(*payloads):
    ledger = Ledger()
    for p in payloads:
        ledger.append(p)
    return ledger


def test_clean_ledger_verifies():
    ledger = _ledger_of({"type": "edit", "episode": "e1"},
                        {"type": "check", "episode": "e1"})
    result = verify(ledger)
    assert result["ok"] and result["problems"] == []


def test_empty_ledger_verifies_with_genesis_head():
    assert verify(Ledger())["ok"]
    assert Ledger().head_hash == GENESIS


def test_tampered_payload_detected():
    ledger = _ledger_of({"type": "edit", "artifact": "a.py"},
                        {"type": "check", "artifact": "a.py"})
    tampered = Ledger(entries=copy.deepcopy(ledger.entries))
    tampered.entries[0].payload["artifact"] = "b.py"
    result = verify(tampered)
    assert not result["ok"]
    assert any("tamper" in p for p in result["problems"])


def test_replayed_entry_detected():
    ledger = _ledger_of({"type": "edit"}, {"type": "check"})
    replayed = Ledger(entries=copy.deepcopy(ledger.entries))
    replayed.entries.append(copy.deepcopy(ledger.entries[0]))
    result = verify(replayed)
    assert not result["ok"]
    assert any("replay" in p for p in result["problems"])


def test_tail_truncation_detected_with_expected_head():
    ledger = _ledger_of({"type": "edit"}, {"type": "check"}, {"type": "edit"})
    truncated = Ledger(entries=copy.deepcopy(ledger.entries[:-1]))
    result = verify(truncated, expected_head=ledger.head_hash)
    assert not result["ok"]
    assert any("truncation" in p for p in result["problems"])


def test_middle_drop_detected_without_expected_head():
    ledger = _ledger_of({"type": "edit"}, {"type": "check"}, {"type": "edit"})
    dropped = Ledger(entries=copy.deepcopy(ledger.entries))
    del dropped.entries[1]
    result = verify(dropped)
    assert not result["ok"]


def test_ledger_serialisation_roundtrip():
    ledger = _ledger_of({"type": "edit", "n": 1}, {"type": "check", "n": 2})
    restored = Ledger.from_json(ledger.to_json())
    assert verify(restored)["ok"]
    assert restored.head_hash == ledger.head_hash


def test_episode_verified_only_with_check_after_last_edit():
    events = [
        {"type": "edit", "episode": "e1", "digest": "d1"},
        {"type": "edit", "episode": "e1", "digest": "d2"},
        {"type": "check", "episode": "e1", "digest": "d1", "kind": "test"},
    ]
    # Check references the superseded digest d1, not the last edit d2.
    assert episode_verdicts(events) == [
        {"episode": "e1", "has_edit": True, "verified": False}]
    events.append({"type": "check", "episode": "e1", "digest": "d2",
                   "kind": "build"})
    assert episode_verdicts(events)[0]["verified"] is True


def test_todo_claim_without_proof_never_verified():
    events = [
        {"type": "edit", "episode": "e1", "todo": "t1", "digest": "d1"},
        {"type": "todo_claim", "episode": "e1", "todo": "t1", "digest": "d1"},
        # A check AFTER the claim must not retroactively verify it.
        {"type": "check", "episode": "e1", "todo": "t1", "digest": "d1",
         "kind": "test"},
    ]
    assert todo_verdicts(events) == [
        {"todo": "t1", "has_edit": True, "verified": False}]


def test_todo_claim_with_proof_before_claim_verified():
    events = [
        {"type": "edit", "episode": "e1", "todo": "t1", "digest": "d1"},
        {"type": "check", "episode": "e1", "todo": "t1", "digest": "d1",
         "kind": "smoke"},
        {"type": "todo_claim", "episode": "e1", "todo": "t1", "digest": "d1"},
    ]
    assert todo_verdicts(events)[0]["verified"] is True


def test_harness_deterministic_same_seed():
    import random
    rng1, rng2 = random.Random(109001), random.Random(109001)
    ev1, _ = generate_session(rng1, "s0000")
    ev2, _ = generate_session(rng2, "s0000")
    assert json.dumps(ev1, sort_keys=True) == json.dumps(ev2, sort_keys=True)


def test_harness_verdicts_match_ground_truth():
    cohort = generate_cohort(109001, 30)
    for sess in cohort:
        res = analyse_session(sess["events"])
        assert res["clean_ok"]
        ep_v = {v["episode"]: v["verified"]
                for v in res["episode_verdicts"]}
        for ep, t in sess["truth"]["episodes"].items():
            assert ep_v[ep] == t["verified"]
        td_v = {v["todo"]: v["verified"] for v in res["todo_verdicts"]}
        for td, t in sess["truth"]["todos"].items():
            assert td_v[td] == t["proof"]


def test_attacks_all_detected_on_real_session_ledger():
    cohort = generate_cohort(109001, 10)
    for sess in cohort:
        res = analyse_session(sess["events"])
        atk = attack_ledger(res["ledger"])
        assert atk["tamper_detected"] and atk["replay_detected"]
        assert atk["truncation_detected"] and atk["middle_drop_detected"]


def test_benign_cohort_fully_verified():
    cohort = generate_cohort(7, 20, profile="benign")
    for sess in cohort:
        res = analyse_session(sess["events"])
        assert all(v["verified"] for v in res["episode_verdicts"])
        assert all(v["verified"] for v in res["todo_verdicts"])
