-- Conversational Survey Engine — Seed Data for Development

-- Sample surveys
INSERT INTO surveys (id, title, context, goal, constraints, max_questions, completion_criteria, goal_coverage_threshold, context_similarity_threshold, is_active, created_at, updated_at)
VALUES
(
    'survey-001',
    'Customer Satisfaction Survey',
    'We are a SaaS company that provides project management tools. We recently launched a major redesign of our dashboard. We want to understand how users feel about the changes.',
    'Understand user satisfaction with the new dashboard redesign, identify pain points, and gather suggestions for improvement.',
    '["Do not ask about pricing", "Focus on UI/UX aspects only", "Keep questions conversational"]',
    8,
    'We have sufficient understanding of the user''s experience with the redesign, including likes, dislikes, and specific feature feedback.',
    0.85,
    0.7,
    1,
    '2026-01-15T10:00:00Z',
    '2026-01-15T10:00:00Z'
),
(
    'survey-002',
    'Employee Engagement Pulse',
    'We are a mid-size tech company (~200 employees). This is a quarterly pulse survey to gauge team morale and engagement. Teams are currently adapting to a hybrid work model.',
    'Assess employee engagement levels, identify factors affecting morale, understand hybrid work challenges.',
    '["Avoid questions about specific managers by name", "Keep it anonymous-friendly", "Do not ask about salary"]',
    10,
    'We have captured the employee''s overall sentiment, specific engagement drivers, and hybrid work experience.',
    0.80,
    0.65,
    1,
    '2026-02-01T09:00:00Z',
    '2026-02-01T09:00:00Z'
),
(
    'survey-003',
    'Product Feature Discovery',
    'We are building a fitness tracking mobile app. We are in the ideation phase and want to discover which features users value most. Target audience: health-conscious adults aged 25-45.',
    'Discover the most desired features for a fitness tracking app and understand user priorities.',
    '["Do not suggest features - let users describe needs", "Avoid leading questions", "Explore both exercise and nutrition tracking"]',
    12,
    'We have a clear picture of the user''s fitness tracking needs, feature preferences, and daily health habits.',
    0.85,
    0.7,
    0,
    '2026-02-10T14:00:00Z',
    '2026-02-10T14:00:00Z'
);

-- Sample users
INSERT INTO users (id, participant_name, metadata, created_at)
VALUES
('user-001', 'Alice Johnson', '{"source": "email_invite"}', '2026-01-20T08:30:00Z'),
('user-002', 'Bob Smith', '{"source": "link_share"}', '2026-01-21T14:15:00Z'),
('user-003', NULL, '{}', '2026-02-05T11:00:00Z');

-- Sample sessions
INSERT INTO sessions (id, survey_id, user_id, status, completion_reason, question_count, created_at, completed_at)
VALUES
('session-001', 'survey-001', 'user-001', 'completed', 'goal_coverage_met', 6, '2026-01-20T08:30:00Z', '2026-01-20T08:45:00Z'),
('session-002', 'survey-001', 'user-002', 'completed', 'max_questions_reached', 8, '2026-01-21T14:15:00Z', '2026-01-21T14:35:00Z'),
('session-003', 'survey-002', 'user-003', 'active', NULL, 3, '2026-02-05T11:00:00Z', NULL);

-- Sample responses for session-001
INSERT INTO responses (id, session_id, survey_id, user_id, question_id, question_text, answer_text, question_number, question_embedding, created_at)
VALUES
('resp-001', 'session-001', 'survey-001', 'user-001', 'q-001', 'What was your first impression when you saw the new dashboard?', 'I was a bit overwhelmed at first. There are a lot more widgets and the layout is quite different from what I was used to.', 1, NULL, '2026-01-20T08:31:00Z'),
('resp-002', 'session-001', 'survey-001', 'user-001', 'q-002', 'Can you tell me which specific changes felt overwhelming?', 'The sidebar navigation moved to the top, and the project overview cards are now much smaller. I had trouble finding the task list at first.', 2, NULL, '2026-01-20T08:33:00Z'),
('resp-003', 'session-001', 'survey-001', 'user-001', 'q-003', 'After using the new dashboard for a while, has your experience improved?', 'Yes, after a couple of days I got used to the top navigation. The drag-and-drop for widgets is actually really nice once you discover it.', 3, NULL, '2026-01-20T08:35:00Z'),
('resp-004', 'session-001', 'survey-001', 'user-001', 'q-004', 'What feature of the redesigned dashboard do you find most useful?', 'The customizable widget layout. I can now put the most important project metrics right at the top of my view.', 4, NULL, '2026-01-20T08:37:00Z'),
('resp-005', 'session-001', 'survey-001', 'user-001', 'q-005', 'Is there anything from the old dashboard that you wish had been kept?', 'The compact task list view. The new card-based view takes up too much space when I have 50+ tasks.', 5, NULL, '2026-01-20T08:39:00Z'),
('resp-006', 'session-001', 'survey-001', 'user-001', 'q-006', 'If you could change one thing about the new dashboard, what would it be?', 'Add a toggle to switch between card view and compact list view for tasks. That would solve my biggest frustration.', 6, NULL, '2026-01-20T08:41:00Z');
