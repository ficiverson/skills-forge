# Scoring Anchors and Cap Conditions

## What gets scored — and what does not

Only score competencies that are **directly verifiable from code and documentation artifacts**.
Seven competencies are permanently skipped (shown as "N/A" in the PDF):
Stakeholder Relations, Mentoring, Ambassador/Advocate, Collaboration,
Emotional Intelligence, People Impact.

**The 14 scored competencies are:**

- Creation/Mastery (9-level): code_quality, documentation, conv_tooling, ai_tooling,
  learning, shaping, ways_of_working, teaching
- Integrity/Autonomy (3-level): task_complexity, ownership, planning
- Curiosity/Evangelism (3-level): business_impact
- Collaboration/Humanity (3-level): communication, company_match, proactivity

---

## 9-level competencies — Creation / Mastery

Level index: 0=Junior-1, 1=Junior-2, 2=Junior-3, 3=Medior-1, 4=Medior-2,
5=Medior-3, 6=Senior-1, 7=Senior-2, 8=Senior-3

### code_quality

What to look for: Naming, structure, DRY, SOLID, test coverage, anti-patterns
Anchors: <=3 inconsistent style or missing tests | 4-5 clean TDD consistent | 6+ drives quality culture telemetry
Cap conditions (score CANNOT exceed 5 if ANY of these are true):
  - Public functions have no type hints
  - No separation of dev/prod dependencies
  - God functions > 100 lines with no decomposition

### documentation

What to look for: Docstrings, README quality, architecture docs, ADRs
Anchors: <=3 minimal docs | 4-5 module docstrings plus architecture diagram | 6+ full sub-system docs before implementation
Cap conditions (score CANNOT exceed 5 if ANY of these are true):
  - Public functions/classes have no docstrings
  - README is missing an architecture overview or system diagram
  - No explanation of how to run the project

### conv_tooling

What to look for: Docker quality, CI/CD, linting, pre-commit, test tooling
Anchors: <=3 no Docker | 4 Docker+compose present no CI | 5 full CI pipeline | 6+ multi-stage builds observability

### ai_tooling

What to look for: Frameworks, agent patterns, structured output, tool calling, RAG, eval
Anchors: <=3 basic API calls | 4 multi-step pipeline | 5 tool calling present (@tool + bind_tools + execution loop) | 6+ RAG or eval framework present
IMPORTANT: Tool calling is the decisive signal between level 4 and level 5.

### learning

What to look for: Bonus features, novel approaches, going beyond requirements
Anchors: <=3 met requirements only | 4-5 bonus features implemented | 6+ novel architecture published research

### shaping

What to look for: Spec/planning docs, contracts, user story awareness, scope management
Anchors: <=2 no specs | 3 basic spec files | 4-5 numbered specs with plan + tasks + requirements checklist | 6+ contracts + research.md + quickstart per spec
Cap conditions (score CANNOT exceed 5 if ANY of these are true):
  - AI workflow tooling detected AND spec content reads as AI-generated boilerplate
  - Spec documents contain no evidence of personal engineering judgment

### ways_of_working

What to look for: Commit conventions, branching, PR flow, task breakdown
Anchors: <=2 no evidence | 3 basic branching | 4-5 feature branches aligned to numbered specs with tasks.md | 6+ CHANGELOG PR templates contribution guide

### teaching

What to look for: Tutorial README, code examples, quickstart docs per feature
Anchors: <=2 minimal | 3 clear README | 4-5 quickstart per feature and docstring examples | 6+ wikis recorded demos
Cap conditions (score CANNOT exceed 5 if ANY of these are true):
  - Stale tests that assert values the current code never produces
  - AI workflow tooling detected AND quickstart/tutorial content appears auto-generated

---

## 3-level competencies

Level index: 0=Junior, 1=Medior, 2=Senior

- task_complexity (Integrity): Complexity of system built relative to the brief
- ownership (Integrity): All requirements met + bonus, error handling, edge cases
- planning (Integrity): Folder organisation, specs, phased approach evidence
- business_impact (Curiosity): Business context in README/comments, cost/value framing
- communication (Collaboration): README clarity, commit messages, variable names
- company_match (Collaboration): Professionalism, security practices, code of conduct signals
- proactivity (Collaboration): Bonus features beyond spec, self-initiated improvements

---

## Self-consistency check (do this before writing the JSON)

- AI Tooling: If score >= 5 but no @tool/bind_tools found — re-read. If score < 5 but full tool-calling loop found — raise to at least 5.
- Shaping undercount: If score <= 3 but spec subdirectories not opened — open them now.
- Teaching undercount: If score <= 3 but quickstart.md files exist in specs — raise to at least 4.
- Evidence mismatch: Each evidence string must match the assigned level in the anchors above.
- AI-generated artifact inflation: If AI workflow tooling was flagged, calibrate learning, shaping, and teaching accordingly. AI-assisted spec generation is infrastructure, not personal innovation.
