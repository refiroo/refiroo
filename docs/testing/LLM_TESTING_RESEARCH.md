# Testing code written by LLM agents: findings and practice

**Written** 2026-10-02 for this project's [testing strategy](STRATEGY.md). It names nothing specific
to this project, so it can be reused in other projects built by one person with coding agents.
Each claim cites its source. The list was checked on the date above; tools and studies change.

## The problem in one sentence

When the same agent writes the code and then the tests, the tests describe what the code does, not
what it should do, so they pass by construction and cannot catch a misread requirement.

## Findings

### 1. LLM tests encode the actual behaviour, not the expected one

- LLMs tend to generate test oracles (the expected values) that capture the program's actual
  implementation rather than its intended behaviour
  ([Do LLMs generate test oracles that capture the actual or the expected program behaviour?](https://arxiv.org/pdf/2410.21136)).
- When the same model writes the code and the test, a bug in the logic becomes the expected value.
  The test calls the function, records what it returns, and asserts that it returns that: a
  tautological test ([The Limits of LLM-Generated Unit Tests](https://hackernoon.com/the-limits-of-llm-generated-unit-tests);
  [AI-generated tests that pass but don't assert anything](https://getautonoma.com/blog/ai-generated-tests-pass-but-dont-assert)).
- Signs in a suite: tests that follow internal code paths (spies, private functions), states built by
  writing to the database directly, one test per branch or field, and many tests per work package
  instead of per user goal.

### 2. Agents game the tests they must pass

- Coding agents have been measured editing test files, deleting assertions, monkey-patching the
  checker or hard-coding the expected outputs for the inputs a test uses, despite instructions not to
  ([ImpossibleBench](https://www.lesswrong.com/posts/qJYMbrabcQqCZ7iqm/impossiblebench-measuring-reward-hacking-in-llm-coding-1);
  [EvilGenie](https://arxiv.org/html/2511.21654v2);
  [Reward Hacking Benchmark](https://arxiv.org/pdf/2605.02964);
  [SpecBench](https://arxiv.org/pdf/2605.21384)).
- The countermeasure is procedural: the test exists, fails, and is fixed before the code is written,
  and the agent implementing the code may not change it.

### 3. Test first, from the specification, and confirm the failure

- The consensus practice for agentic coding: write the tests before the implementation, confirm that
  they fail (not against a stub), commit them separately, implement until they pass, and do not modify
  the tests during implementation
  ([TDD with Claude Code, S. Kinney](https://stevekinney.com/courses/ai-development/test-driven-development-with-claude);
  [TDD workflow guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/guide/workflows/tdd-with-claude.md)).
- A failing test is the hardest signal for an agent to fake. A description can be satisfied in words
  while missing the intent; a failing assertion can only be satisfied by real behaviour.

### 4. The worker should not grade its own work

- Anthropic's guidance for Claude Code: give the agent a check that produces pass or fail, have it
  show evidence (the command, its output) instead of asserting success, and verify with a fresh
  context that tries to refute the result, "so the agent doing the work isn't the one grading it"
  ([Claude Code best practices](https://code.claude.com/docs/en/best-practices)).
- Applied to tests: the test cases are derived from the specification in a different context from
  the one that implements the code.

### 5. Coverage hides weak tests; mutation testing shows them

- A suite can execute every line and still miss most faults. Mutation testing plants small faults in
  the code and counts how many some test detects; AI-generated suites often reach high line coverage
  with a low mutation score
  ([Mutation testing for AI-generated code](https://www.augmentcode.com/guides/mutation-testing-ai-generated-code);
  [Why coverage lies and mutations don't](https://medium.com/@outsightai/the-truth-about-ai-generated-unit-tests-why-coverage-lies-and-mutations-dont-fcd5b5f6a267)).
- Python tools: `mutmut`, `cosmic-ray`
  ([comparison of Python mutation tools](https://dl.acm.org/doi/10.1145/3701625.3701659)). Mutation
  runs are slow: a release check, not a per-change one.

### 6. The individual test is not the main weakness; the process is

- A study found Claude-authored Python tests no weaker than human-authored ones
  ([arXiv 2608.15188](https://arxiv.org/pdf/2608.15188)). The failures above come from who writes
  the test, from what source and when, not from the model's ability to write a test.

### 7. Generate combinations instead of writing them

- Property-based testing states a rule that must hold for every valid input and lets the framework
  generate the inputs and shrink a failure to a minimal case; in Python, Hypothesis
  ([intro](https://www.freecodecamp.org/news/intro-to-property-based-testing-in-python-6321e0c2f8b);
  [Anthropic: finding bugs with Claude and property-based testing](https://www.anthropic.com/research/property-based-testing)).
- Pairwise (all-pairs) selection covers every pair of option values in a fraction of the full grid;
  most interaction faults involve two parameters
  ([NIST, Combinatorial Testing](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=910001);
  [combinatorial and property-based testing combined](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7984547/)).
- A hand-written grid of every option against every option is the slowest and least informative form.

### 8. Run only what a change can affect

- Test impact analysis records which code each test executes and, after a change, runs only the
  tests that executed the changed code. For pytest, `pytest-testmon` does this with Coverage.py; teams
  report median test time halved ([pytest-testmon](https://github.com/tarpas/pytest-testmon);
  [testmon.org](https://www.testmon.org/);
  [Instawork's experience](https://engineering.instawork.com/test-impact-analysis-the-secret-to-faster-pytest-runs-e44021306603)).
- Its limit is what coverage cannot see: configuration, schema, migrations, data files. A change to
  those counts as a change at the bottom of the hierarchy and selects everything that reads them.

### 9. Traceability must live in the code, or it dies

- A requirements traceability matrix links each requirement to the tests that verify it, so an
  uncovered requirement is visible ([TestRail RTM guide](https://www.testrail.com/blog/requirements-traceability-matrix/)).
- Kept by hand in a spreadsheet it falls behind in fast projects
  ([RTM: death by Excel or a useful tool?](https://www.kualitee.com/blog/test-management/requirements-traceability-matrix-death-by-excel-or-a-useful-tool/)).
  Markers on the tests and a check that reads them keep it current.

## Recommendations for a one-person project built with agents

The scarce resource is the human's review time, not test runtime. A thousand tests cannot be
reviewed, so a large agent-written suite is in practice graded by the agent that wrote the code.

1. **Two kinds of tests.**
   - *Unit tests* per piece of code, testing its purpose, with edge cases and generated combinations.
     They run when that code or what it depends on changes.
   - *Journey tests* per user journey and variant, through the public interface, on realistic data.
     Every piece of code traces to at least one journey.
2. **The specification is the source of every journey test.** Cases are written as given/when/then
   from the specification, in a separate context, reviewed by the human as a short list, fixed before
   implementation, and never edited by the implementing agent. A case the code cannot pass is a code
   defect or a specification gap, never a reason to adjust the test.
3. **Every way of doing something is a journey, a variant of one, or removed.** Agents add options
   speculatively; each one multiplies the test space. An option no client needs is removed. An
   integration product's clients include other systems, not only its own UI.
4. **Unit tests check behaviour, not internals.** No spies on private functions; set up state
   through the public interface unless the state can only arrive from outside it (an import, an older
   version), and say so in the test.
5. **Measure test quality with tools, not trust.** Mutation score at each release; impact-based
   selection for daily runs; everything at release.
6. **Keep evidence, clean up.** Each run reports what it ran and what it found. Every server, clone
   and log a run starts is stopped or deleted, and logs are size-bounded.
