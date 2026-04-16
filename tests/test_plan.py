"""Tests for change plan module."""

import json
from pathlib import Path

from llm_tag_sanitizer.plan import ChangePlan
from llm_tag_sanitizer.tags.models import ProposedChange


def _change(
    field: str = "artist",
    old: str = "old",
    new: str = "new",
    optimizer: str = "test",
    path: str = "/a.mp3",
) -> ProposedChange:
    return ProposedChange(
        file_path=Path(path),
        field_name=field,
        old_value=old,
        new_value=new,
        optimizer_name=optimizer,
    )


class TestChangePlan:
    def test_empty_plan(self):
        plan = ChangePlan()
        assert plan.is_empty()

    def test_add_changes(self):
        plan = ChangePlan()
        plan.add(_change())
        assert not plan.is_empty()
        assert len(plan.changes) == 1

    def test_extend(self):
        plan = ChangePlan()
        plan.extend([_change(), _change()])
        assert len(plan.changes) == 2

    def test_filter_by_optimizer(self):
        plan = ChangePlan(
            [
                _change(optimizer="artist_normalizer"),
                _change(optimizer="disc_merger"),
                _change(optimizer="artist_normalizer"),
            ]
        )
        filtered = plan.filter(optimizer_name="artist_normalizer")
        assert len(filtered.changes) == 2

    def test_filter_by_field(self):
        plan = ChangePlan(
            [
                _change(field="artist"),
                _change(field="album"),
                _change(field="artist"),
            ]
        )
        filtered = plan.filter(field="artist")
        assert len(filtered.changes) == 2

    def test_to_json(self):
        plan = ChangePlan([_change()])
        data = json.loads(plan.to_json())
        assert len(data) == 1
        assert data[0]["field_name"] == "artist"

    def test_display_no_crash(self, capsys):
        plan = ChangePlan([_change()])
        plan.display()  # Should not crash

    def test_summary_no_crash(self, capsys):
        plan = ChangePlan([_change()])
        plan.summary()
