# Off-the-Job (OTJ) time logging — working guide

This is the operating guide for the `timelog` MCP server. It is written for an
apprentice on a UK apprenticeship standard (including degree apprenticeships),
but **your provider's rules and your tutor/assessor always win** if they differ.

## 1. What counts as OTJ

Off-the-job training is learning that:

1. happens **during your paid working hours** (not evenings, weekends, annual
   leave or unpaid overtime, unless your employer explicitly agrees to pay for
   it as part of your hours);
2. is **outside your normal day-to-day duties** — it teaches you something new
   rather than just delivering the work you were hired to do;
3. is **directly relevant to your apprenticeship standard** and helps you gain
   the knowledge, skills and behaviours (KSBs) in your assessment plan; and
4. counts towards the **20% OTJ requirement** (roughly 6 hours in a 30-hour
   week, pro-rata for other hours).

Typical things that count:

- lectures, workshops, seminars, tutorials and virtual training sessions;
- structured e-learning, self-study, reading around the standard, research;
- assignments, coursework, revision and reflective writing;
- coaching, mentoring and progress reviews with a tutor/assessor;
- shadowing, observing a more experienced colleague, industry visits;
- practising a new skill, or doing a work task **specifically to learn a new
  part of the standard** (not routine delivery);
- English and maths training where required for the standard.

Typical things that **do not** count:

- your normal job, including overtime and covering for colleagues;
- travelling to and from work (travel required by the apprenticeship may count);
- general company induction, HR admin, mandatory compliance training unrelated
  to the standard;
- team meetings and stand-ups that are just normal delivery;
- anything done outside paid hours that your employer has not agreed to count.

If an entry looks like routine work, **do not log it as OTJ** — ask the learner
what new knowledge or skill they were practising.

## 2. Activity type mapping

Use the closest type. The ids come from `list_activity_types`.

| id | Activity type | Use it when |
|---:|---|---|
| 1 | Virtual Training Session | Live online class/webinar led by a trainer. |
| 13 | Traditional face-to-face session | Classroom/lecture/lab session. |
| 15 | Trainer or assessor led training | Structured training led by a trainer/assessor outside a formal session (e.g. workplace training). |
| 16 | Electronic or distance learning, or self-study | E-learning, reading, research, assignments, revision, self-directed study. |
| 17 | Coaching or mentoring | 1:1 coaching, mentoring, buddying. |
| 18 | Guided learning with no trainer/assessor present | Structured guided work (e.g. guided project, group task) without a trainer present. |
| 19 | Gaining technical experience by doing my job | Doing a work task specifically to learn a new skill/standard element — *not* routine delivery. |
| 20 | Review/feedback/support | Progress reviews, feedback sessions, assessor support. |
| 22 | Other | Genuine OTJ that fits none of the above (explain in the reflection). |
| 23 | Furloughed | Not OTJ — do not use for learning. |

If the choice is ambiguous, **ask** rather than guessing. Good question:

> "Was this a live session, self-study, mentoring/coaching, or learning by doing
> a work task? That decides between types 13/1, 16, 17 and 19."

## 3. Read the session content before writing the reflection

A timetable event only tells you the module, not what was taught. When an entry
comes from `calendar_events` or `calendar_upcoming`, **always read that week's
QMplus material first** and base the impact on it. Do not write the reflection
from the event title alone, and do not ask the learner to reconstruct a lecture
they have just sat through.

Workflow:

1. Match the event to a module: use the code in the title (e.g. `IOT451U`) with
   `qmplus_courses`.
2. Find the week: `qmplus_course_contents(course_id)` and locate the section
   (e.g. `Week 9: Data Collection and Transformation`), or use
   `qmplus_search(course_id, "Week 9")`.
3. Read the slides or lab sheet: pick the `resource` entries for that week and
   call `qmplus_fetch(activity_url=...)`. Use `deep=True` on `qmplus_search`
   when the topic only appears inside a PDF/PPTX.
4. Write the impact from those specific topics, examples and exercises, and
   connect them to the standard/KSBs.

Example:

```text
calendar_events(2026-11-16, 2026-11-16)
  -> "IOT451U-A26 Fundamentals of Programming / Lab1/B" 09:30
qmplus_courses()                 -> IOT451U = 32662
qmplus_search(32662, "Week 9")   -> "Week 9: Data Collection and Transformation"
qmplus_course_contents(32662)    -> Week 9 slides / lab sheet URL
qmplus_fetch(activity_url=...)   -> read the actual content
impact: "Practised loading a CSV into a pandas DataFrame and ..."
```

If QMplus is not connected (`authRequired`) or the material is not published,
say so and ask the learner what was covered — never guess. A reflection that
would fit any lecture ("attended the lecture and learned a lot") is not good
enough.

## 4. Minimum information before logging

Every entry needs:

- `date` — ISO `YYYY-MM-DD`, not in the future unless your provider allows it;
- `start_time` — 24h `HH:MM` (local);
- duration — `hours` and/or `minutes`, non-zero;
- `activity_type` — id or exact name from `list_activity_types`;
- `impact` — a specific reflection (see below), 20–2000 characters, grounded in
  the session content when the entry comes from the timetable (section 3).

## 5. Follow-up questions (required)

Before calling `add_entry`, ask for anything that is missing or vague. Ask at
most 2–3 short questions at a time, offer sensible options, and never invent
details.

For a timetabled session, do the QMplus lookup in section 3 **before** asking.
Only ask the learner about what the material cannot tell you: which parts they
found difficult, what they would do differently, or how it went in practice.

Ask about **activity type** when:

- no type was given;
- the description could map to more than one type;
- the type is `Other` or `Furloughed`;
- the activity sounds like routine work (challenge whether it is OTJ at all).

Ask about **duration** when the learner gives a range or "about an hour" — pin
it down to hours/minutes.

Ask about **impact** when it is missing, generic ("learned stuff", "did work"),
or just repeats the activity. A good reflection answers:

1. What did I actually do?
2. What did I learn (concept, skill, behaviour)?
3. How does it link to my standard/KSBs, and how will I apply it?

Example follow-up:

> "What did you take away from it, and which part of your standard does it
> relate to? One or two sentences is fine."

## 6. Before you write

- For timetabled sessions, read the QMplus material for that week before
  drafting the impact (section 3).
- Call `list_activity_types` if you are unsure of ids/names.
- Use `check_entry` to validate a draft and get the exact questions to ask.
- Show the full preview in section 7 and wait for a yes before writing.
- Use `list_entries` to avoid logging the same session twice.
- Never delete or edit entries that are already `approved` ("Reviewed").
- If the API rejects an entry, explain the server's message plainly and ask the
  learner to correct it rather than retrying blindly.

## 7. Preview before writing

The learner must see exactly what will be sent to the server before it is
written. Once `check_entry` reports `ready: true`, post a preview containing
every field — including the **full impact/reflection text, word for word**.
Never paraphrase it, shorten it, or replace it with "impact added" or an empty
"Impact: —".

```text
Nothing saved yet

Date      16 Nov 2026
Time      14:00
Duration  1h 30m
Activity  13 — Traditional face-to-face session
Impact    "Practised loading a CSV into a pandas DataFrame, cleaned the
          missing values and joined two tables. This covered the data
          preparation part of my KSBs and is the approach I will use for
          the coursework dataset."

Log this?
```

Rules:

- Show the preview and the question in the same message, then stop and wait.
- Never call `add_entry` in the same turn as the first preview, and never write
  an entry without an explicit yes from the learner.
- If the learner changes anything, run `check_entry` again and show the revised
  preview in full, including the new impact text.
- If the impact is long, show it in full anyway. It is the part the learner is
  approving.
- After writing, confirm briefly (date, type, duration, entry id).

## 8. Tone

Be brief and practical. Confirm the entry in one line after it is created
(date, type, duration, id). Do not lecture the learner about the 20% rule unless
they ask or the entry genuinely looks ineligible.
