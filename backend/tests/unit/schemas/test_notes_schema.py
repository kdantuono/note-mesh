"""
Unit tests for Note schemas (NoteCreate, NoteUpdate) validators.
"""

import pytest

from src.notemesh.core.schemas.notes import NoteCreate, NoteUpdate


class TestNoteSchemas:
    def test_note_create_valid_tags_normalized(self):
        data = {
            "title": "Valid Note",
            "content": "Some content",
            "tags": ["Work", "project-1", "TAG_2"],
            "hyperlinks": ["https://example.com"],
            "is_public": False,
        }
        note = NoteCreate(**data)
        assert note.tags == ["work", "project-1", "tag_2"]

    def test_note_create_duplicate_tags_error(self):
        data = {
            "title": "Dup Tags",
            "content": "content",
            "tags": ["work", "work"],
        }
        with pytest.raises(ValueError, match="Duplicate tags are not allowed"):
            NoteCreate(**data)

    def test_note_create_invalid_tag_format_error(self):
        data = {
            "title": "Bad Tag",
            "content": "content",
            "tags": ["bad tag"],
        }
        with pytest.raises(ValueError, match="Tags can only contain"):
            NoteCreate(**data)

    def test_note_create_empty_content_error(self):
        data = {
            "title": "No Content",
            "content": "   ",
            "tags": [],
        }
        with pytest.raises(ValueError, match="Content cannot be empty"):
            NoteCreate(**data)

    def test_note_create_too_many_tags(self):
        tags = [f"t{i}" for i in range(21)]  # max_length is 20
        data = {"title": "Too many tags", "content": "c", "tags": tags}
        with pytest.raises(Exception):
            NoteCreate(**data)

    def test_note_create_invalid_hyperlink(self):
        data = {
            "title": "Bad Link",
            "content": "content",
            "hyperlinks": ["not-a-url"],
        }
        with pytest.raises(Exception):
            NoteCreate(**data)

    def test_note_update_none_values_pass(self):
        # None values indicate no change; should not raise
        upd = NoteUpdate()
        assert upd.tags is None
        assert upd.content is None

    def test_note_update_duplicate_tags_error(self):
        with pytest.raises(ValueError, match="Duplicate tags are not allowed"):
            NoteUpdate(tags=["a", "a"])  # type: ignore[arg-type]

    def test_note_update_empty_content_error(self):
        with pytest.raises(ValueError, match="Content cannot be empty"):
            NoteUpdate(content="   ")
