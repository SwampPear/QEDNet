# tests/test_lean_rpc.py
import shutil
import pytest

from qednet.io.lean_rpc import LeanRPC, LeanState, StepResult


def _has_lean() -> bool:
    return bool(shutil.which("lake") or shutil.which("lean"))


lean_missing = pytest.mark.skipif(
    not _has_lean(), reason="Lean/Lake not found on PATH; skip Lean integration tests."
)


@lean_missing
def test_fetch_goal_nat_add_comm():
    rpc = LeanRPC(imports=["Mathlib"])
    st: LeanState = rpc.fetch_goal("Nat.add_comm")
    # Basic sanity checks: we got a type and it mentions Nat / equality
    assert isinstance(st.pp_goal, str) and len(st.pp_goal) > 0
    assert "Nat" in st.pp_goal
    assert "=" in st.pp_goal or "Eq" in st.pp_goal


@lean_missing
def test_check_tactic_success_against_fetched_goal():
    rpc = LeanRPC(imports=["Mathlib"])
    st: LeanState = rpc.fetch_goal("Nat.add_comm")

    # Prove the fetched goal using the existing lemma via simp.
    # Goal is (∀ m n : Nat, m + n = n + m); we introduce binders then close by simp.
    tactic = """
    intro m n
    simpa [Nat.add_comm]
    """

    res: StepResult = rpc.check_tactic(st.pp_goal, tactic, theorem_name="__qednet_tmp_add_comm")
    assert res.valid, f"Expected tactic to succeed, got error:\n{res.error}\nSTDERR:\n{res.stderr}"


@lean_missing
def test_check_tactic_failure_reports_error():
    rpc = LeanRPC(imports=["Mathlib"])
    st: LeanState = rpc.fetch_goal("Nat.add_comm")

    # Deliberately wrong proof attempt
    bad_tactic = """
    intro m n
    exact rfl
    """

    res: StepResult = rpc.check_tactic(st.pp_goal, bad_tactic, theorem_name="__qednet_tmp_add_comm_fail")
    assert not res.valid, "Expected tactic to fail but it succeeded unexpectedly."
    # Ensure we get a helpful error message back
    assert isinstance(res.error, str) and len(res.error) > 0
