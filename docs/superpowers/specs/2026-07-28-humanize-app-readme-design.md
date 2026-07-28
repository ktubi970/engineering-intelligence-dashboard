# Human-Centered App and README Design

## Context

MergeLens is a portfolio project intended to be understood first by recruiters and engineering
managers, with developers as a secondary audience. Its current dashboard and README lead with
implementation vocabulary, evaluation mechanics, and internal engineering evidence. This makes
the project credible but harder to scan and weakens the value proposition.

The application and README will remain in English for international visibility.

## Goal

Make the project understandable within 60 to 90 seconds while preserving its technical honesty.
A first-time reader should quickly understand:

- what MergeLens helps a team see;
- what the dashboard contains;
- what the prediction does and does not mean;
- how to run the project locally;
- where to find deeper technical and quality evidence.

## Non-goals

- Do not change metrics, model features, model parameters, snapshot data, or calculations.
- Do not remove privacy, non-causality, or developer-scoring safeguards.
- Do not rewrite historical CI or deployment evidence as current proof.
- Do not hide the model's limitations or imply that its estimate is a delivery promise.
- Do not turn the README into exhaustive API or architecture documentation.

## Editorial approach

Use a product-first information hierarchy. Lead with the reader's question, then the answer, then
optional evidence. Prefer short sentences and familiar terms. Introduce unavoidable technical
terms only where they help a decision, and explain them in place.

The voice should be direct, calm, and credible. It should not sound promotional, academic, or
machine-generated. Headings should describe what the reader learns rather than name an internal
discipline. Detailed implementation and engineering-process evidence should live in the existing
documents and be linked from the README.

## Dashboard design

Keep the dashboard focused on exploration rather than implementation:

1. Rename the three product views to `Delivery overview`, `Where work slows down`, and
   `Merge-time estimate`.
2. Remove the `Technical stack` tab and its explanatory content. The stack belongs in the README
   and architecture document, not in the main user journey.
3. Rewrite captions, form labels, empty states, model comparisons, and warnings in plain English.
4. Keep the four existing delivery measures, but explain specialist terms such as P90 and MAE
   close to where they appear.
5. Present the forecast result before its evaluation mechanics. Keep the baseline and error
   visible, using language such as "typical error on recent test data."
6. Preserve concise safeguards: the forecast is experimental, describes merged pull requests,
   and must never be used to score people.

Loading failures and insufficient-data states should tell the reader what happened and what they
can do next. They must not expose secrets or obscure the genuine constraint.

## README design

The README will use progressive disclosure in this order:

1. A one-sentence description of the problem MergeLens solves.
2. A short value summary and the dashboard screenshot.
3. The live-demo link, with any access-status observation dated and stated plainly without
   dominating the page.
4. Three concise descriptions of what the reader can explore.
5. A quick local start.
6. A mathematically explicit `Prediction model` section.
7. A short `How it works` section naming the core stack and data flow.
8. Compact trust, privacy, and limitation notes.
9. Links to the architecture, data card, model card, quality evidence, and agentic-development
   record for readers who want implementation detail.

The long agentic-engineering narrative, exhaustive quality-gate results, exact evidence anchors,
full metric glossary, and repeated model caveats will be removed from the main flow. Existing
specialist documents remain the source for those details.

## Prediction model notation

For pull request \(i\), define the target in hours as:

\[
Y_i =
\frac{\mathrm{merged\_at}_i-\mathrm{created\_at}_i}
     {1\ \mathrm{hour}},
\qquad Y_i \ge 0.
\]

The model applies only to pull requests that eventually merge. Its raw opening-time inputs are
the repository \(r_i\), pull-request number \(n_i\), and UTC opening time \(t_i\). The derived
feature vector is:

\[
X_i =
\left(
r_i,\ n_i,\ \mathrm{year}(t_i),\ \mathrm{month}(t_i),\ \mathrm{day}(t_i),\
\mathrm{weekday}(t_i),\ \mathrm{hour}(t_i)
\right).
\]

No developer identity, pull-request content, change size, merge outcome, or other future
information is included in \(X_i\). Let \(\phi(X_i)\) denote one-hot encoding for the repository
plus the model's configured missing-value imputation. The fitted prediction is:

\[
\widehat{Y}_i = f(X_i) =
\max\left(
\exp\left(
\frac{1}{200}\sum_{b=1}^{200}T_b(\phi(X_i))
\right)-1,\ 0
\right),
\]

where each \(T_b\) is one regression tree in the 200-tree random forest. The trees are trained to
predict \(\log(1+Y_i)\), use maximum depth 8, and require at least 3 training samples per leaf.

The newest 20% of rows forms the chronological test set. Earlier rows may enter training only
when their merge result was already known before the first test opening time. Unavailable labels
are purged. Performance is reported as:

\[
\mathrm{MAE} =
\frac{1}{m}\sum_{i=1}^{m}\left|Y_i-\widehat{Y}_i\right|.
\]

The same test rows are compared with a baseline that predicts the median training-set merge time.
The README will give rounded current-snapshot results and link to the model card for the full
contract, evidence, and limitations.

## Testing and evidence

Implementation will follow the existing test-first workflow:

- update dashboard contract tests before changing visible labels and sections;
- update README contract tests before replacing the document structure;
- add assertions that the README defines \(Y\), \(X\), \(f\), chronological evaluation, MAE, and
  the median baseline;
- retain assertions for privacy, non-causal use, and the prohibition on developer scoring;
- verify that no metric, model result, or snapshot-derived value changes;
- run focused dashboard and project-contract tests, then Ruff and the complete test suite with
  coverage.

All reported evidence must be labeled accurately as local or CI evidence.

## Acceptance criteria

- A recruiter can identify the product's purpose and three main capabilities above the technical
  details.
- The dashboard contains no dedicated technical-stack tab.
- User-facing labels and explanations avoid unexplained statistical or implementation jargon.
- The README remains concise while containing the approved mathematical model definition.
- Detailed engineering evidence is discoverable through links rather than repeated in the main
  narrative.
- Privacy, model limitations, and the no-developer-scoring rule remain visible.
- The implementation changes presentation only; calculations and data remain unchanged.
