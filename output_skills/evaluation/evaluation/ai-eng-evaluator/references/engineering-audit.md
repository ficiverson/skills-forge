# Engineering Practices Audit

After scoring competencies, perform a structured audit across **13 engineering practice categories**.
For every finding, record only **real evidence backed by actual files and line numbers**.

---

## Category 1 — Clean Architecture & Code Quality

| Check | What to look for |
|---|---|
| SRP | Functions/classes doing more than one conceptual job |
| OCP | Long if/elif chains requiring editing to add new behaviour |
| DIP | Concrete classes instantiated directly inside business logic |
| DRY | Identical or near-identical blocks copy-pasted in 2+ places |
| Long Function | Any function > ~30 lines mixing multiple abstraction levels |
| Magic Numbers | Literal values without named constants repeated across files |
| Deep Nesting | More than 3 levels of indentation |
| Error Swallowing | `except Exception: pass` or bare excepts |

Rating: PASS = 0-2 minor issues | WARN = 3-5 issues | FAIL = 6+ or any God Class/Function

## Category 2 — Testing Practices

| Check | What to look for |
|---|---|
| Unit tests | Tests for individual functions/agents in isolation |
| Integration tests | Tests for component interactions |
| E2E tests | Full pipeline runs tested end-to-end |
| Test coverage | Coverage config, CI coverage thresholds |
| TDD evidence | Tests committed alongside or before feature code |
| Test quality | Meaningful assertions, not just "it ran" |
| Mock/fixture usage | External APIs mocked; test isolation maintained |

Rating: PASS = unit + at least one higher level | WARN = only unit tests | FAIL = no tests

## Category 3 — Static Code Analysis

| Check | What to look for |
|---|---|
| Linter config | ruff, flake8, eslint configured |
| Type checking | mypy, pyright, TypeScript strict mode |
| Pre-commit hooks | .pre-commit-config.yaml enforcing lint/format |
| Formatter | black, prettier configured |

Rating: PASS = linter + type checker | WARN = only linter | FAIL = no static analysis

## Category 4 — Pipeline & DevOps Quality

| Check | What to look for |
|---|---|
| Dockerfile quality | Multi-stage builds, minimal base, .dockerignore |
| docker-compose | Proper services, env vars, health checks |
| CI/CD pipeline | GitHub Actions/GitLab CI present and working |
| Pipeline steps | Lint, test, build, deploy steps defined |
| Secrets management | No hardcoded secrets; .env.example provided |
| Observability | Logging, tracing, metrics hooks |

Rating: PASS = Docker + CI/CD with lint and test | WARN = Docker only | FAIL = no containerisation

## Category 5 — AI Framework Maturity

| Check | What to look for |
|---|---|
| Framework depth | LangGraph, CrewAI, etc. beyond basic API calls |
| Agent architecture | Multi-agent graph, routing, state management |
| Tool calling | @tool/bind_tools/function_call pattern implemented |
| Guardrails | Input validation, output filtering, PII redaction |
| Structured output | Pydantic models, TypedDict state |
| Evaluation harness | LangSmith, RAGAS, golden-set tests |
| Prompt management | Prompts in dedicated files, not inline strings |

Rating: PASS = multi-agent + tool calling + 2 additional | WARN = basic pipeline | FAIL = simple API calls only

## Category 6 — Security Vulnerabilities

| Check | What to look for |
|---|---|
| SAST tooling | bandit, semgrep, CodeQL configured |
| DAST signals | OWASP ZAP or equivalent referenced |
| SCA | pip-audit, safety, Dependabot |
| Hardcoded secrets | API keys, passwords in source files |
| Injection risks | Unsanitised user input in shell/SQL/file paths |
| Insecure defaults | Debug mode in prod, CORS wildcard, no rate limiting |
| Auth/access control | Authentication present where expected |

Rating: PASS = SAST + SCA + no critical findings | WARN = no tooling but no obvious vulns | FAIL = hardcoded secrets or injection risks

## Category 7 — Dependency Management

| Check | What to look for |
|---|---|
| Version pinning | Strategy and automated update tooling |
| Outdated packages | Compare pinned vs latest stable |
| Dev vs prod separation | Dev deps separated from runtime |
| Lock file | poetry.lock, pdm.lock for reproducibility |
| CVE exposure | Known vulnerabilities in pinned versions |

Rating: PASS = deps current + audit tooling | WARN = outdated but no CVEs | FAIL = vulnerable versions pinned

## Category 8 — Observability & Monitoring

| Check | What to look for |
|---|---|
| Structured logging | JSON logs with level, timestamp, correlation ID |
| LLM call logging | Token usage, latency, model name logged |
| Tracing | LangSmith, OpenTelemetry, Datadog traces |
| Health endpoints | /health or /readiness endpoint |
| Metrics | Request count, latency, error rate exposed |

Rating: PASS = structured logging + LLM logging + tracing | WARN = basic logging only | FAIL = only print()

## Category 9 — Error Handling & Resilience

| Check | What to look for |
|---|---|
| Retry logic | Exponential backoff on rate limits/timeouts |
| Timeout handling | Request timeouts set on all external calls |
| Graceful degradation | Fallback responses when LLM unavailable |
| Tool call error handling | Individual failures caught in agent loop |
| Circuit breaker | Mechanism to stop hammering failing services |

Rating: PASS = retry + timeout + graceful degradation | WARN = basic try/except | FAIL = bare excepts

## Category 10 — Prompt Engineering Quality

| Check | What to look for |
|---|---|
| Prompt organisation | Dedicated files/templates vs inline strings |
| Role separation | System/human/AI roles used correctly |
| Few-shot examples | Examples for complex tasks |
| Persona and scope | Agent role and boundaries defined |
| Injection prevention | User input sanitised before prompt insertion |

Rating: PASS = dedicated files + role separation + scope | WARN = inline but role separation correct | FAIL = raw strings, no roles

## Category 11 — API Design & Contract Quality

| Check | What to look for |
|---|---|
| OpenAPI/Swagger | Spec present and accurate |
| Input validation | Pydantic models or equivalent |
| Error response format | Structured errors, not bare 500s |
| HTTP status codes | Correct usage (not everything 200) |
| Authentication | Endpoints requiring auth actually protected |

Rating: PASS = OpenAPI + validation + structured errors + auth | WARN = auto-generated OpenAPI but gaps | FAIL = no validation

## Category 12 — Configuration Management

| Check | What to look for |
|---|---|
| 12-factor compliance | All config from environment variables |
| .env.example | Present and up to date |
| Startup validation | App fails fast on missing env vars |
| Config class | Centralised settings object |
| Secret separation | Secrets never in source; .env in .gitignore |

Rating: PASS = .env.example + startup validation + config class | WARN = scattered os.getenv() | FAIL = hardcoded config

## Category 13 — Code Complexity

| Check | What to look for |
|---|---|
| Cyclomatic complexity | Target < 10 per function |
| Function length | What % exceeds 30 lines; any > 100 lines |
| File length | Files > 500 lines = risk; > 1000 = red flag |
| Dead code | Commented-out blocks, unused imports |
| Duplication | Estimated % of copy-pasted code |

Rating: PASS = no function > 50 lines, no file > 500 | WARN = a few long functions | FAIL = god files > 1000

---

## Evidence checklist — complete BEFORE assigning impacts

**static_analysis evidence:**
- ruff or flake8 present: [YES/NO] — quote config key
- mypy or pyright present: [YES/NO] — quote config key
- pre-commit hooks: [YES/NO]
- Write: `static_analysis: linter=[present/absent at path], type_checker=[present/absent at path]`

**testing evidence:**
- Test files present (list by name): [ ]
- Unit: [YES/NO]; Integration/E2E: [YES/NO]
- Stale tests (list any): [ ]
- Write: `testing: unit=[yes/no], integration=[yes/no], stale_tests=[none/list]`

**ai_frameworks evidence:**
- Multi-agent graph: [YES/NO] — note file and line
- @tool/bind_tools: [YES/NO] — note file and line
- Guardrails: [YES/NO]; Structured output: [YES/NO]; Eval harness: [YES/NO]
- Write: `ai_frameworks: routing=[yes/no], tool_calling=[yes/no], guardrails=[yes/no], eval=[yes/no]`

---

## Impact assignment

Each category independently contributes an impact of -1, 0, or +1:
- +1: Exceeds expectations (must name a specific feature exceeding the candidate's level)
- 0: Meets baseline expectations (PASS = 0, not +1)
- -1: Fails to meet minimum bar

The score_adjustment is the sum of all impacts, capped to -2 … +1.

### Anti-inflation rules

1. **PASS != +1** — PASS = baseline met = impact 0
2. **Bug in core mechanism = 0 or -1, never +1**
3. **The +1 justification sentence** — "The +1 for [category] is justified because [specific feature] goes beyond what a [scored level] candidate is expected to implement."
4. **No offset laundering** — each +1 must survive rules 1-3 independently
5. **Final impact tally self-check** — write out all impacts, sum, and capped value before JSON

---

## Cross-reference: Audit results → Competency scores

| Practice category result | Linked competency | Rule |
|---|---|---|
| clean_architecture FAIL | code_quality | Cannot exceed 5 |
| code_complexity FAIL | code_quality | Cannot exceed 5 |
| testing FAIL with stale tests | teaching | Cannot exceed 5 |
| testing FAIL with no tests | code_quality + teaching | Cannot exceed 4 |
| static_analysis FAIL | conv_tooling | Re-examine if >= 5 |
| pipeline FAIL | conv_tooling | Cannot exceed 4 |
| error_handling FAIL | code_quality | Lower toward 3-4 |
| security FAIL | company_match | Cannot exceed 1 (Medior) |
| prompt_engineering FAIL | ai_tooling | Re-examine if >= 5 |
| observability FAIL | conv_tooling + ai_tooling | Stay <= 4 |
| api_design FAIL | code_quality | Lower by 1 if >= 5 |
| dependency_management FAIL | code_quality + conv_tooling | Lower by 1 if >= 5 |
| ai_frameworks PASS with eval+guardrails+structured | ai_tooling | Upward check: if < 5, re-examine |

For each FAIL/WARN row, write:
> "[category] is [FAIL/WARN] → [competency]: was [old_score], now [new_score]"
