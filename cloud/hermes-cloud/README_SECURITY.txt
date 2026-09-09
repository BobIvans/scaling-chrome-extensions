SECRETS POLICY

Never commit:
- API_SERVER_KEY / HERMES_API_SERVER_KEY
- provider API keys/tokens
- Chrome cookies/passwords/profile data
- OAuth refresh/access tokens
- seed/recovery phrases/private keys

Use Google Secret Manager (Hermes) and Supabase project secrets (broker). The extension may keep a direct provider key only in volatile side-panel memory for the current session; production broker mode should avoid exposing the Hermes master key to Chrome entirely.
