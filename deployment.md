# Pre-launch Checklist

The dashboard is local only. Do not deploy or publish it until the owner has connected a custom domain and reviewed the privacy policy, terms, hosting logs, and applicable legal requirements. No custom domain or hosting account was provided for this project.

## Requirements before any public release

1. Register and connect a domain controlled by the project owner.
2. Have the privacy policy and terms reviewed for the actual host, jurisdiction, provider, and data handling.
3. Configure HTTPS and host-level authentication before allowing remote access. Add authorization if users have different permissions.
4. Put the app behind a maintained reverse proxy or managed platform. Do not expose Streamlit directly to the public internet.
5. Configure and test security headers at the proxy, including an app-compatible Content Security Policy, frame protection, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy. Add HSTS only after HTTPS is working.
6. Configure request limits and provider-call quotas. Review host logs, session handling, and data-retention behavior.
7. Scan the source, dependencies, release files, and Git history for secrets; verify that logs and private files are not publicly served.
8. Review the release build and all dashboard flows. Only then authorize a public repository and deployment.

The app does not require an API key. Yahoo Finance's public chart endpoint is unofficial and may delay, change, rate-limit, or block requests. Verify provider terms and availability before release.

## Recommended remote-access setup

For private sharing without uploading the project source, use [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/) with [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/) and GitHub as the identity provider ([setup guide](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/github/)). The app can remain bound to `127.0.0.1`; the tunnel creates an outbound connection, so do not open port 8501 on the router or change the app to listen on all network interfaces.

This requires an owner-controlled domain active in Cloudflare. Configure an Access application for the chosen hostname with a default-deny policy, then allow only the specific GitHub accounts or organization that should use the dashboard. Require multifactor authentication on those GitHub accounts. All authorized users currently receive the same read-only dashboard; there are no separate admin or user roles.

Configure and test security headers at the edge, including frame protection, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy. Add a Content Security Policy only after testing Streamlit scripts and WebSocket connections; enable HSTS only after HTTPS is confirmed. Rate-limit rules must also be tested against Streamlit's WebSocket paths so they do not prevent normal dashboard use. Never put a tunnel token or GitHub OAuth client secret in project files or Git history.

The tunnel keeps the app on the owner's computer, so that computer must remain on for remote access. No domain or Cloudflare account was provided, so this setup has not been configured or launched.

## Local preview

On Windows, double-click `run_dashboard.bat` and leave its console window open while using the local app.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Enter tickers such as `AAPL, MSFT`, choose a history range, and select **Fetch market history**. Review the Market analysis, Portfolio backtest, Methodology, Privacy policy, and Terms and conditions tabs. Do not present example metrics; all displayed market values should come from the selected provider response.
