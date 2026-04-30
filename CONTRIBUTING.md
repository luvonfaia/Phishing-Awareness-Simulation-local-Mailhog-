# Contributing

## Code style
- Keep changes small and focused.
- Add tests for new behavior.

## Safety review
Any change that affects sending behavior or templates must:
1. Be reviewed by at least one maintainer.
2. Include a safety checklist: target scope, excluded groups, test plan (MailHog), and rollback plan.

## Tests & CI
- Run `pytest` locally.
- Add tests for new features and ensure CI passes before merging.
