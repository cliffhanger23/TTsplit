# SplitScope — Streamlit Private Edition

A dark, invite-only table tennis first-two-set split dashboard. Supports completed match history, player split rates, H2H rates, upcoming matchup rankings, on-screen alerts, admin member approvals/revocations and CSV imports. **No automatic live sports API feed or outbound email alerts yet.**

## Deployment checklist (free tiers, subject to provider limits)

1. Create a **private** GitHub repository and upload `app.py`, `requirements.txt`, `schema.sql`, `.gitignore` and this README (do not upload credentials).
2. Create a free Supabase project, open **SQL Editor**, paste `schema.sql`, and run it. In Project Settings > API, copy the project URL and the **service role** secret key. The service-role key bypasses RLS: **keep it server-side and private**.
3. Set up Google OAuth for Streamlit's built-in authentication: in Google Cloud Console configure an OAuth consent screen and a Web application OAuth client. For redirect URI use `https://YOUR-APP.streamlit.app/oauth2callback` (replace with the deployed app's actual URL). Add your Google account as a test user if your OAuth app is in testing mode. Streamlit authentication uses `st.login()` and `st.user`; it does not send invitations.
4. In Streamlit Community Cloud create an app using the GitHub repo and entrypoint `app.py`. In the app's **Advanced settings > Secrets**, configure the following (replace placeholders):

```toml
SUPABASE_URL = "https://YOURPROJECT.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
ADMIN_EMAIL = "you@example.com"

[auth]
redirect_uri = "https://YOUR-APP.streamlit.app/oauth2callback"
cookie_secret = "A_LONG_RANDOM_SECRET_AT_LEAST_32_CHARACTERS"
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

5. Restart the app. Sign in with the Google account whose verified email equals `ADMIN_EMAIL`. Under **Admin**, approve a member's verified Google email, then privately send them the Streamlit app URL. Members cannot invite others through the application. To revoke, open Admin > Revoke access. Revocation takes effect on their next app rerun/request; it does not forcibly disconnect an already-open browser tab.
6. Use Admin > Import match data to upload completed and upcoming CSV files. The app shows ranked matchups and alerts. Import is manual until a sports-data feed is connected.

### Important privacy and operations notes

- Streamlit Community Cloud's **platform-level viewer permissions** are separate from this app's login. If Streamlit's sharing model conflicts with your invite-only requirements, choose another host. Do not rely on the GitHub repo's privacy alone. Check a denied/uninvited account before sharing.
- A Supabase **service-role key** grants privileged database access. Never commit it to GitHub or put it in a public URL. Only put it in Streamlit server-side Secrets.
- The administrator is identified by the `ADMIN_EMAIL` secret; other users must be approved in `members`. The app checks email verification.
- This starter limits the history query to 10,000 records and upcoming query to 2,000. For larger datasets, implement pagination and server-side aggregation.
- Importing rows without stable `id` values creates new records on repeated imports. Deduplicate at source or include UUID IDs.
- Google OAuth setup and third-party provider free tiers can change. You must complete account configuration; this package cannot configure those accounts automatically.
- The rankings are descriptive scores, **not** probabilities or guaranteed wagering outcomes.

## CSV examples

Completed: `league,played_at,player_a,player_b,set1_a,set1_b,set2_a,set2_b`

Upcoming: `league,starts_at,player_a,player_b`

Use ISO 8601 UTC timestamps such as `2026-11-17T20:00:00Z`.

## Local development

Install `pip install -r requirements.txt`, create `.streamlit/secrets.toml` with the above secrets and a local redirect URI, then run `streamlit run app.py`.
