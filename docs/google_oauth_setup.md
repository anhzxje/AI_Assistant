# Google OAuth Setup

Use one real Google account for local smoke testing. Do not create many fake Google accounts; use the mock scenario fixtures for Gmail/Calendar coverage.

## Google Cloud Console

1. Create or select a Google Cloud project.
2. Configure the OAuth consent screen.
3. Keep the app in Testing mode for local development.
4. Add your Google account as a test user.
5. Create an OAuth Client ID with application type `Web application`.

Authorized JavaScript origins:

- `http://127.0.0.1:3002`
- `http://localhost:3002`

Authorized redirect URIs:

- `http://127.0.0.1:8000/api/auth/google/callback`
- `http://127.0.0.1:8000/api/integrations/google/gmail/callback`
- `http://127.0.0.1:8000/api/integrations/google/calendar/callback`
- `http://localhost:8000/api/auth/google/callback`
- `http://localhost:8000/api/integrations/google/gmail/callback`
- `http://localhost:8000/api/integrations/google/calendar/callback`

If Google shows an unverified-app warning, use the configured test user account.

## Environment

Set these in `.env`. Do not commit `.env`.

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/auth/google/callback
GOOGLE_GMAIL_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/google/gmail/callback
GOOGLE_CALENDAR_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/google/calendar/callback
FRONTEND_URL=http://127.0.0.1:3002
```

## Scopes

Login requests only identity scopes:

- `openid`
- `email`
- `profile`

Gmail connect requests only:

- `https://www.googleapis.com/auth/gmail.readonly`

Calendar connect requests only:

- `https://www.googleapis.com/auth/calendar.readonly`

Do not request broad scopes. Do not request Gmail send/modify scopes. Do not request Calendar write scopes.

## Token Storage

Local integration tokens are stored under:

```text
data/personal_memory/google_tokens/{user_id}/
```

This path is gitignored. Token values must not be logged or copied into reports.

## Mock Scenario Testing

Use these fixtures for rich QA without real Google data:

- `backend/app/services/connectors/fixtures/scenarios/users.json`
- `backend/app/services/connectors/fixtures/scenarios/gmail/*.json`
- `backend/app/services/connectors/fixtures/scenarios/calendar/*.json`

If a real inbox variety test is needed, use one Gmail test account and plus addressing:

- `yourname+school@gmail.com`
- `yourname+spam@gmail.com`
- `yourname+deadline@gmail.com`

These aliases route to the same inbox, so they are useful for labeling test messages but not for separate-account isolation.
