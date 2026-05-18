# Google/Gmail/Calendar Mock Scenarios

These fixtures support local QA without creating real Google accounts or requesting Gmail/Calendar OAuth scopes.

- `users.json` maps local seeded users to scenarios.
- `gmail/*.json` contains readable Gmail-like test messages with category, priority, and expected task hints.
- `calendar/*.json` contains local calendar events. Calendar dates are aligned to the current local day by the mock ingestion service.

Use `scenario` in sync requests, for example:

```json
{ "user_id": "student-noisy-test", "use_mock": true, "scenario": "student_noisy" }
```

If `scenario` is omitted, the backend tries to map `user_id` or seeded account id to a scenario and then falls back to the original default mock fixture.
