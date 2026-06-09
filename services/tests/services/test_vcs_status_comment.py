"""Tests for the pure PR/MR status-comment renderer (#282 phase 6).

Only the framework-agnostic rendering helpers are exercised here — the
DB collection and provider-posting paths are integration concerns. These
functions take plain run-shaped objects and emit deterministic Markdown,
so a SimpleNamespace stand-in is enough.
"""

from types import SimpleNamespace

from terrapod.services.vcs_status_comment import (
    _COMMENT_MARKER,
    _Row,
    _apply_summary,
    _escape,
    _mergeable_summary,
    _plan_summary,
    render_comment,
)


def _run(**attrs):
    """A run-shaped object with the fields the renderer reads."""
    attrs.setdefault("has_changes", None)
    attrs.setdefault("vcs_apply_blocked_reason", None)
    return SimpleNamespace(**attrs)


class TestPlanSummary:
    def test_none_run_is_dash(self):
        assert _plan_summary(None) == "—"

    def test_queued_states(self):
        assert _plan_summary(_run(status="pending")) == "queued"
        assert _plan_summary(_run(status="queued")) == "queued"

    def test_planning_is_running(self):
        assert _plan_summary(_run(status="planning")) == "running"

    def test_terminal_states_pass_through(self):
        assert _plan_summary(_run(status="errored")) == "errored"
        assert _plan_summary(_run(status="discarded")) == "discarded"
        assert _plan_summary(_run(status="canceled")) == "canceled"

    def test_planned_no_changes(self):
        assert _plan_summary(_run(status="planned", has_changes=False)) == "no changes"

    def test_planned_with_changes(self):
        assert _plan_summary(_run(status="planned", has_changes=True)) == "changes"

    def test_planned_unknown_changes_defaults_to_changes(self):
        # has_changes is None (not parsed) — conservative default is "changes".
        assert _plan_summary(_run(status="applied", has_changes=None)) == "changes"


class TestApplySummary:
    def test_none_run_is_dash(self):
        assert _apply_summary(None) == "—"

    def test_applied_and_applying(self):
        assert _apply_summary(_run(status="applied")) == "applied"
        assert _apply_summary(_run(status="applying")) == "applying"

    def test_not_applied_default(self):
        assert _apply_summary(_run(status="planned")) == "not applied"


class TestMergeableSummary:
    def test_none_run_is_dash(self):
        assert _mergeable_summary(None) == "—"

    def test_unblocked_is_yes(self):
        assert _mergeable_summary(_run(status="planned")) == "yes"

    def test_blocked_reason_surfaced_and_truncated(self):
        long_reason = "x" * 200
        out = _mergeable_summary(_run(status="planned", vcs_apply_blocked_reason=long_reason))
        assert out.startswith("blocked: ")
        # Reason is clamped to 60 chars in the cell.
        assert len(out) == len("blocked: ") + 60


class TestEscape:
    def test_pipes_escaped(self):
        assert _escape("a|b") == "a\\|b"

    def test_newlines_collapsed(self):
        assert _escape("line1\nline2") == "line1 line2"

    def test_none_is_empty(self):
        assert _escape("") == ""


class TestRenderComment:
    def test_marker_always_present(self):
        assert render_comment([]).startswith(_COMMENT_MARKER)

    def test_empty_rows_message(self):
        body = render_comment([])
        assert "No Terrapod workspaces affected" in body

    def test_table_header_and_row(self):
        rows = [
            _Row(
                workspace_name="api-prod",
                mode="apply_then_merge",
                plan_summary="changes",
                apply_summary="not applied",
                mergeable_summary="yes",
            )
        ]
        body = render_comment(rows)
        assert "| Workspace | Mode | Plan | Apply | Mergeable |" in body
        assert "`api-prod`" in body
        # Single pending apply prints a per-workspace hint.
        assert "Comment `terrapod apply` to apply `api-prod`." in body

    def test_merge_then_apply_overrides_apply_cell(self):
        rows = [
            _Row(
                workspace_name="db",
                mode="merge_then_apply",
                plan_summary="changes",
                apply_summary="not applied",
                mergeable_summary="yes",
            )
        ]
        body = render_comment(rows)
        assert "will apply on merge" in body
        # merge_then_apply is never "pending apply", so no apply hint.
        assert "terrapod apply" not in body

    def test_multiple_pending_applies_hint(self):
        rows = [
            _Row("a", "apply_then_merge", "changes", "not applied", "yes"),
            _Row("b", "apply_then_merge", "changes", "not applied", "yes"),
        ]
        body = render_comment(rows)
        assert "apply all pending workspaces" in body

    def test_force_merge_hint_appended(self):
        rows = [_Row("a", "apply_then_merge", "changes", "applied", "yes")]
        body = render_comment(rows, force_merge_hint=True)
        assert "Auto-merge is blocked" in body
        assert "terrapod merge" in body

    def test_workspace_name_with_pipe_is_escaped(self):
        rows = [_Row("we|rd", "apply_then_merge", "changes", "applied", "yes")]
        body = render_comment(rows)
        assert "we\\|rd" in body
