import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.models import Note, NoteSourceLink
from tests.helpers import create_course, create_note, upload_course_source


async def test_note_crud_works_without_slide_references(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    note = await create_note(
        client,
        course["id"],
        title="  Normal forms  ",
        body="# BCNF\n\n<script>alert('kept as plain text')</script>",
    )

    assert note["title"] == "Normal forms"
    assert note["body"].startswith("# BCNF")
    assert note["slide_references"] == []

    listed = await client.get(f"/api/v1/courses/{course['id']}/notes")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [note["id"]]

    updated = await client.patch(
        f"/api/v1/notes/{note['id']}",
        json={
            "title": "Database normalization",
            "body": "First, second, and third normal form.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Database normalization"
    assert updated.json()["body"] == "First, second, and third normal form."

    deleted = await client.delete(f"/api/v1/notes/{note['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/notes/{note['id']}")).status_code == 404


async def test_note_markdown_round_trips_exactly_and_enforces_body_limit(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    markdown = (
        "# Serializable transactions\n\n"
        "Keep **write skew**, _dirty reads_, and `locks` visible.  \n"
        "- first item\n2. second item\n\n"
        "> Preserve spacing and punctuation.\n\n"
        "[Reference](https://example.test/path?q=one)\n\n"
        "```sql\nSELECT * FROM notes;\n```\n"
        "<script>alert('stored, not rendered')</script>\n"
    )

    created = await client.post(
        f"/api/v1/courses/{course['id']}/notes",
        json={"title": "Markdown source", "body": markdown, "slide_references": []},
    )
    assert created.status_code == 201
    assert created.json()["body"] == markdown

    fetched = await client.get(f"/api/v1/notes/{created.json()['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["body"] == markdown

    updated_markdown = markdown.replace("**write skew**", "__write skew__")
    updated = await client.patch(
        f"/api/v1/notes/{created.json()['id']}",
        json={"body": updated_markdown},
    )
    assert updated.status_code == 200
    assert updated.json()["body"] == updated_markdown

    at_limit = await client.post(
        f"/api/v1/courses/{course['id']}/notes",
        json={"title": "At the limit", "body": "x" * 100_000},
    )
    assert at_limit.status_code == 201
    assert len(at_limit.json()["body"]) == 100_000

    over_limit = await client.post(
        f"/api/v1/courses/{course['id']}/notes",
        json={"title": "Over the limit", "body": "x" * 100_001},
    )
    assert over_limit.status_code == 422


async def test_note_preserves_multiple_named_slide_ranges(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    course = await create_course(client)
    first_deck = await upload_course_source(
        client,
        course["id"],
        file_name="lecture-one.md",
        content=b"# Transactions",
        source_type="slides",
        display_name="Transactions deck",
    )
    second_deck = await upload_course_source(
        client,
        course["id"],
        file_name="lecture-two.txt",
        content=b"Recovery and logging",
        source_type="slides",
        display_name="Recovery deck",
    )

    note = await create_note(
        client,
        course["id"],
        slide_references=[
            {
                "source_id": first_deck["id"],
                "start_slide": 2,
                "end_slide": 5,
                "label": "ACID overview",
            },
            {
                "source_id": second_deck["id"],
                "start_slide": None,
                "end_slide": None,
                "label": "Whole lecture",
            },
        ],
    )

    assert [
        (
            reference["source_display_name"],
            reference["start_slide"],
            reference["end_slide"],
            reference["label"],
        )
        for reference in note["slide_references"]
    ] == [
        ("Transactions deck", 2, 5, "ACID overview"),
        ("Recovery deck", None, None, "Whole lecture"),
    ]
    assert note["slide_references"][0]["original_filename"] == "lecture-one.md"

    links = list(
        await session.scalars(
            select(NoteSourceLink).where(
                NoteSourceLink.note_id == uuid.UUID(note["id"])
            )
        )
    )
    assert len(links) == 2


async def test_note_references_reject_literature_other_courses_and_unknown_ids(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    other_course = await create_course(client, name="Other course")
    literature = await upload_course_source(
        client,
        course["id"],
        file_name="reading.txt",
        content=b"Literature",
        source_type="literature",
    )
    other_slides = await upload_course_source(
        client,
        other_course["id"],
        file_name="other-slides.txt",
        content=b"Other slides",
        source_type="slides",
    )

    for source_id, message in [
        (literature["id"], "Only course materials in the Slides library"),
        (other_slides["id"], "belongs to another course"),
        (str(uuid.uuid4()), "does not exist"),
    ]:
        response = await client.post(
            f"/api/v1/courses/{course['id']}/notes",
            json={
                "title": "Invalid reference",
                "body": "",
                "slide_references": [
                    {
                        "source_id": source_id,
                        "start_slide": 1,
                        "end_slide": 2,
                    }
                ],
            },
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_note_slide_reference"
        assert message in response.json()["message"]

    assert (await client.get(f"/api/v1/courses/{course['id']}/notes")).json() == []


async def test_note_reference_ranges_and_duplicates_are_rejected(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    slides = await upload_course_source(
        client,
        course["id"],
        file_name="slides.txt",
        content=b"Slides",
        source_type="slides",
    )
    base = {
        "title": "Range validation",
        "body": "",
    }

    for reference in [
        {"source_id": slides["id"], "start_slide": 2, "end_slide": None},
        {"source_id": slides["id"], "start_slide": 4, "end_slide": 3},
        {"source_id": slides["id"], "start_slide": 0, "end_slide": 1},
    ]:
        response = await client.post(
            f"/api/v1/courses/{course['id']}/notes",
            json={**base, "slide_references": [reference]},
        )
        assert response.status_code == 422

    duplicate = {
        "source_id": slides["id"],
        "start_slide": 1,
        "end_slide": 3,
    }
    response = await client.post(
        f"/api/v1/courses/{course['id']}/notes",
        json={**base, "slide_references": [duplicate, duplicate]},
    )
    assert response.status_code == 400
    assert "cannot be linked more than once" in response.json()["message"]


async def test_removing_links_preserves_notes_and_sources_and_source_delete_cascades(
    client: AsyncClient,
) -> None:
    course = await create_course(client)
    first_deck = await upload_course_source(
        client,
        course["id"],
        file_name="first.md",
        content=b"First deck",
        source_type="slides",
    )
    second_deck = await upload_course_source(
        client,
        course["id"],
        file_name="second.md",
        content=b"Second deck",
        source_type="slides",
    )
    note = await create_note(
        client,
        course["id"],
        slide_references=[
            {
                "source_id": first_deck["id"],
                "start_slide": 1,
                "end_slide": 2,
            },
            {
                "source_id": second_deck["id"],
                "start_slide": None,
                "end_slide": None,
            },
        ],
    )

    removed_one = await client.patch(
        f"/api/v1/notes/{note['id']}",
        json={
            "slide_references": [
                {
                    "source_id": second_deck["id"],
                    "start_slide": None,
                    "end_slide": None,
                }
            ]
        },
    )
    assert removed_one.status_code == 200
    assert [
        reference["source_id"]
        for reference in removed_one.json()["slide_references"]
    ] == [second_deck["id"]]
    assert (await client.get(f"/api/v1/course-sources/{first_deck['id']}")).status_code == 200

    deleted_source = await client.delete(
        f"/api/v1/course-sources/{second_deck['id']}"
    )
    assert deleted_source.status_code == 204
    remaining_note = await client.get(f"/api/v1/notes/{note['id']}")
    assert remaining_note.status_code == 200
    assert remaining_note.json()["slide_references"] == []


async def test_course_delete_cascades_notes(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    course = await create_course(client)
    note = await create_note(client, course["id"])

    assert (await client.delete(f"/api/v1/courses/{course['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/notes/{note['id']}")).status_code == 404
    assert list(await session.scalars(select(Note))) == []
