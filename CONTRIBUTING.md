# Contributing

Fingerprint normalization is a community-governed shared rule set. Propose rule
changes in an issue with concrete same-pain and different-pain examples, then
open a pull request with golden tests, documented tradeoffs, a fingerprint
version change, and a migration/compatibility plan. Reviewers should consider
false merges as well as unnecessary identity churn. Schema changes require a
versioned migration, migration tests, and updated schema documentation.

Run `python -m pytest` to test. Never commit real private ledgers or secrets.
