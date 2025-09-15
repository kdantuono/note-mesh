"""Quick debug for tag search - simple approach."""

import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from notemesh.core.repositories.note_repository import NoteRepository


async def debug_tag_search():
    """Debug tag search functionality directly."""

    # Create mock session
    mock_session = Mock()

    # Create repository
    repo = NoteRepository(mock_session)

    # Mock data - note with tags
    mock_note = Mock()
    mock_note.id = uuid4()
    mock_note.title = "Work Meeting"
    mock_note.content = "Important meeting notes"
    mock_note.owner_id = uuid4()

    mock_tag = Mock()
    mock_tag.name = "work"
    mock_note.tags = [mock_tag]

    # Mock SQL result
    mock_result = Mock()
    mock_result.scalars.return_value = [mock_note]

    # Mock session execute
    mock_session.execute = AsyncMock(return_value=mock_result)

    print("=== DEBUGGING TAG SEARCH ===")

    user_id = uuid4()

    # Test 1: No tag filter
    print("\n1. Testing without tag filter...")
    results1 = await repo.search_notes(user_id, "meeting", tag_filter=None)
    print(f"Results: {len(results1)}")
    print(f"Session execute called: {mock_session.execute.called}")

    # Reset mock
    mock_session.execute.reset_mock()

    # Test 2: With tag filter
    print("\n2. Testing with tag filter ['work']...")
    results2 = await repo.search_notes(user_id, "meeting", tag_filter=["work"])
    print(f"Results: {len(results2)}")
    print(f"Session execute called: {mock_session.execute.called}")

    # Reset mock
    mock_session.execute.reset_mock()

    # Test 3: With empty tag filter
    print("\n3. Testing with empty tag filter []...")
    results3 = await repo.search_notes(user_id, "meeting", tag_filter=[])
    print(f"Results: {len(results3)}")
    print(f"Session execute called: {mock_session.execute.called}")

    # Check if SQL statements are being built correctly
    # Let's check what SQL would be generated
    from sqlalchemy import select, or_, and_
    from sqlalchemy.orm import selectinload
    from notemesh.core.models.note import Note
    from notemesh.core.models.tag import Tag

    print("\n=== SQL STATEMENT ANALYSIS ===")

    # Base statement
    stmt = select(Note).options(selectinload(Note.tags)).where(Note.owner_id == user_id)
    search_condition = or_(Note.title.ilike("%meeting%"), Note.content.ilike("%meeting%"))
    stmt = stmt.where(search_condition)

    print("1. Base SQL (no tag filter):")
    print(str(stmt.compile(compile_kwargs={"literal_binds": True})))

    # With tag filter
    stmt_with_tags = stmt.join(Note.tags).where(Tag.name.in_(["work"]))
    stmt_with_tags = stmt_with_tags.distinct()

    print("\n2. SQL with tag filter:")
    print(str(stmt_with_tags.compile(compile_kwargs={"literal_binds": True})))

    # Test NEW implementation with shared notes
    print("\n=== NEW IMPLEMENTATION WITH SHARED NOTES ===")

    from notemesh.core.models.share import Share, ShareStatus

    # New access condition: owned OR shared
    access_condition = or_(
        Note.owner_id == user_id,  # Notes owned by user
        and_(  # Notes shared with user
            Share.shared_with_user_id == user_id,
            Share.status == ShareStatus.ACTIVE,
            Note.id == Share.note_id
        )
    )

    stmt_new = select(Note).options(selectinload(Note.tags)).where(access_condition)
    stmt_new = stmt_new.where(search_condition)

    print("\n3. NEW SQL (includes shared notes, no tag filter):")
    print(str(stmt_new.compile(compile_kwargs={"literal_binds": True})))

    # With tag filter
    stmt_new_with_tags = stmt_new.join(Note.tags).where(Tag.name.in_(["work"]))
    stmt_new_with_tags = stmt_new_with_tags.distinct()

    print("\n4. NEW SQL (includes shared notes + tag filter):")
    print(str(stmt_new_with_tags.compile(compile_kwargs={"literal_binds": True})))

    # Test CURRENT implementation in repository
    print("\n=== TESTING CURRENT REPOSITORY IMPLEMENTATION ===")

    # Current implementation combines LEFT JOIN shares + JOIN tags
    from sqlalchemy import outerjoin

    # Step 1: Start with Note + LEFT JOIN shares
    current_stmt = select(Note).options(selectinload(Note.tags))
    current_stmt = current_stmt.outerjoin(Share, Note.id == Share.note_id)

    # Step 2: Add access condition
    current_access_condition = or_(
        Note.owner_id == user_id,
        and_(
            Share.shared_with_user_id == user_id,
            Share.status == ShareStatus.ACTIVE
        )
    )
    current_stmt = current_stmt.where(current_access_condition)

    # Step 3: Add search condition
    current_stmt = current_stmt.where(search_condition)

    print("\n5. CURRENT SQL (no tag filter):")
    print(str(current_stmt.compile(compile_kwargs={"literal_binds": True})))

    # Step 4: Add tag filter (this might be problematic)
    current_stmt_with_tags = current_stmt.join(Note.tags).where(Tag.name.in_(["work"]))
    current_stmt_with_tags = current_stmt_with_tags.distinct()

    print("\n6. CURRENT SQL (with tag filter - potential issue):")
    print(str(current_stmt_with_tags.compile(compile_kwargs={"literal_binds": True})))


if __name__ == "__main__":
    asyncio.run(debug_tag_search())