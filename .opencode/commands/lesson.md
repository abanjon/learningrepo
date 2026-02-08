---
description: Start or continue your next data engineering lesson
agent: tutor
---

Read `progress.md` to determine where the student is in the curriculum.

Current progress state:
!`cat progress.md`

Based on the progress state above:

1. **If status is `ready`**: Determine the next session from Current Week and Current Session fields.
2. **If status is `awaiting_quiz_retry`**: The student failed the last quiz. Serve a remediation session for the same topic with different examples and quiz questions.
3. **If status is `in_progress`**: The student left mid-session. Resume from where they left off.

Then:

1. Read the lesson file at `lesson-plan/week-{WEEK_NUMBER}/session-{SESSION_NUMBER}.md` where the numbers come from progress.md. Use zero-padded two-digit week numbers (e.g., `week-01`).
2. For sessions 1-4: Create and checkout a new git branch named `week-{WEEK}-session-{SESSION}` from main.
3. For session 5: Checkout the `cumulative` branch.
4. Update progress.md status to `in_progress`.
5. Begin the session following the phase structure defined in AGENTS.md and the lesson file.

At session end:
1. Update progress.md with completion data (date, score, pass/fail, branch, notes).
2. If the student passed (sessions 1-4) or completed acceptance criteria (session 5): advance Current Session (or Current Week if session 5). Set status to `ready`.
3. If the student failed the quiz: set status to `awaiting_quiz_retry`, increment retry count.

IMPORTANT: Follow AGENTS.md rules exactly. Never generate code during the INDEPENDENT phase. Grade quizzes strictly.
