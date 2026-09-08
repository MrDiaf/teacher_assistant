\set ON_ERROR_STOP on

INSERT INTO calendars (
    id, name, description, color, is_visible, is_read_only, is_importing,
    subscription_url, source_type
) VALUES (
    '11111111-1111-4111-8111-111111111111',
    'M14 fixture subscription',
    'Non-private relocation fixture',
    '#29584c', true, true, false,
    'https://example.invalid/m14-fixture.ics',
    'ics_import'
);

INSERT INTO calendars (
    id, name, description, color, is_visible, is_read_only, is_importing,
    source_type
) VALUES (
    '10101010-1010-4010-8010-101010101010',
    'M14 fixture writable calendar',
    'Non-private event fixture',
    '#3f7a69', true, false, false, 'local'
);

INSERT INTO events (
    id, calendar_id, title, start_at, end_at, all_day, timezone, status,
    external_uid
) VALUES (
    '22222222-2222-4222-8222-222222222222',
    '10101010-1010-4010-8010-101010101010',
    'M14 fixture event',
    '2026-08-31T12:00:00Z',
    '2026-08-31T13:00:00Z',
    false, 'UTC', 'confirmed', 'm14-fixture@example.invalid'
);

INSERT INTO courses (
    id, name, course_code, description, term, color, status, source_type
) VALUES (
    '33333333-3333-4333-8333-333333333333',
    'M14 fixture course', 'M14', 'Non-private fixture', '2026',
    '#b98522', 'active', 'manual'
);

INSERT INTO course_sources (
    id, course_id, source_type, display_name, original_filename,
    stored_filename, mime_type, file_size, storage_path, content_hash,
    extraction_status
) VALUES (
    '44444444-4444-4444-8444-444444444444',
    '33333333-3333-4333-8333-333333333333',
    'slides', 'M14 fixture PDF', 'fixture.pdf', 'original.pdf',
    'application/pdf', 27,
    '33333333-3333-4333-8333-333333333333/slides/44444444-4444-4444-8444-444444444444/original.pdf',
    'e0b7c90192df3885822217e31d469bb69f7fd6a5fab39c8ddb24baa3a5ae4845',
    'completed'
);

INSERT INTO course_source_text (
    id, source_id, page_or_slide_number, text, content_hash
) VALUES (
    '55555555-5555-4555-8555-555555555555',
    '44444444-4444-4444-8444-444444444444',
    1, 'M14 non-private extracted fixture text', repeat('5', 64)
);

INSERT INTO notes (id, course_id, title, body) VALUES (
    '66666666-6666-4666-8666-666666666666',
    '33333333-3333-4333-8333-333333333333',
    'M14 fixture note', 'Fixture note body for relocation testing.'
);

INSERT INTO note_source_links (
    id, note_id, source_id, start_slide, end_slide, label
) VALUES (
    '77777777-7777-4777-8777-777777777777',
    '66666666-6666-4666-8666-666666666666',
    '44444444-4444-4444-8444-444444444444',
    1, 1, 'Fixture slide'
);

INSERT INTO note_summaries (
    id, note_id, model, status, summary_json, note_content_hash,
    slide_content_hash
) VALUES (
    '88888888-8888-4888-8888-888888888888',
    '66666666-6666-4666-8666-666666666666',
    'fixture-model', 'completed',
    '{"overview":"Fixture summary","bullets":[{"text":"Durable fixture","provenance":"note"}]}'::jsonb,
    repeat('8', 64), repeat('9', 64)
);

INSERT INTO course_calendar_links (id, course_id, calendar_id) VALUES (
    '99999999-9999-4999-8999-999999999999',
    '33333333-3333-4333-8333-333333333333',
    '10101010-1010-4010-8010-101010101010'
);

INSERT INTO diagnostic_errors (
    id, request_id, code, message, operation, details, exception_type
) VALUES (
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    'abababab-abab-4bab-8bab-abababababab',
    'm14_fixture', 'Non-private fixture diagnostic', 'm14.relocation',
    '{"fixture":true}'::jsonb, 'FixtureError'
);

INSERT INTO diagnostic_audit_records (
    id, error_id, action, details, created_at
) VALUES (
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    'created', '{"fixture":true}'::jsonb, now()
);

INSERT INTO assistant_conversations (id, title) VALUES (
    'cccccccc-cccc-4ccc-8ccc-cccccccccccc', 'M14 fixture conversation'
);

INSERT INTO assistant_messages (
    id, conversation_id, role, content, citations
) VALUES (
    'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
    'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    'owner', 'Create a non-private fixture event.', '[]'::jsonb
);

INSERT INTO assistant_jobs (
    id, conversation_id, owner_message_id, status, model,
    safe_error_details, diagnostic_error_id
) VALUES (
    'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
    'awaiting_confirmation', 'fixture-model', '{}'::jsonb,
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
);

INSERT INTO assistant_messages (
    id, conversation_id, role, content, citations, job_id
) VALUES (
    'ffffffff-ffff-4fff-8fff-ffffffffffff',
    'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    'assistant', 'Fixture proposal is awaiting confirmation.',
    '[{"note_id":"66666666-6666-4666-8666-666666666666"}]'::jsonb,
    'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
);

INSERT INTO assistant_proposals (
    id, job_id, conversation_id, status, summary, batch_position,
    batch_count, actions, baselines, review_items, warnings,
    affected_events, expires_at
) VALUES (
    '12121212-1212-4212-8212-121212121212',
    'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    'awaiting_confirmation', 'M14 fixture proposal', 1, 1,
    '[{"action":"create_event"}]'::jsonb, '[]'::jsonb, '[]'::jsonb,
    '[]'::jsonb, 1, '2099-01-01T00:00:00Z'
);

INSERT INTO assistant_proposal_actions (
    id, proposal_id, position, operation, target_calendar_id, requested_at
) VALUES (
    '13131313-1313-4313-8313-131313131313',
    '12121212-1212-4212-8212-121212121212',
    1, 'create_event', '10101010-1010-4010-8010-101010101010', now()
);

INSERT INTO assistant_context_audits (
    id, job_id, course_ids, note_ids, source_ids, slide_numbers,
    requires_clarification, created_at
) VALUES (
    '14141414-1414-4414-8414-141414141414',
    'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    '["33333333-3333-4333-8333-333333333333"]'::jsonb,
    '["66666666-6666-4666-8666-666666666666"]'::jsonb,
    '["44444444-4444-4444-8444-444444444444"]'::jsonb,
    '[{"source_id":"44444444-4444-4444-8444-444444444444","slides":[1]}]'::jsonb,
    false, now()
);

INSERT INTO document_projects (id, title) VALUES (
    '15151515-1515-4515-8515-151515151515', 'M21 durable document fixture'
);

INSERT INTO document_tags (id, name, name_normalized, color) VALUES (
    '16161616-1616-4616-8616-161616161616', 'Fixture', 'fixture', '#29584c'
);

INSERT INTO document_project_tags (project_id, tag_id) VALUES (
    '15151515-1515-4515-8515-151515151515',
    '16161616-1616-4616-8616-161616161616'
);
