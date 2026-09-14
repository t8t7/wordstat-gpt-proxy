# Wordstat Proxy API

Authenticated browser bridge for the free Yandex Wordstat website. It returns
the visible "Popular" and "Similar" tables as JSON and does not use the paid
Yandex Search API.

The service is designed for a GPT Action: deploy it behind HTTPS, import
`https://YOUR_PUBLIC_HOST/openapi.json` into the GPT configuration, select API
key authentication with `Bearer` auth, and enter the value of `PROXY_API_KEY`.

## Server setup

1. Copy `.env.example` to `.env` on the VPS and replace `PROXY_API_KEY`. Never
   commit `.env`.
2. Start the isolated stack:

   ```bash
   docker compose up -d --build
   docker compose ps
   ```

3. Merge one block from `deploy/Caddyfile.example` into the current Caddyfile,
   validate it, and only then reload Caddy. Do not replace the existing file.
4. Create an SSH tunnel to the browser screen:

   ```bash
   ssh -L 7901:127.0.0.1:7901 goodpapa@YOUR_VPS_IP
   ```

5. Open `http://127.0.0.1:7901/?autoconnect=1&resize=scale`, then sign in to
   Yandex manually. The browser profile is stored in a private Docker volume.

The API and browser-screen ports are bound to loopback only. Redis has no
published port. The browser screen must never be exposed directly through
Caddy; access it only through SSH.

## Verification

On the VPS:

```bash
curl --fail --silent http://127.0.0.1:8087/health
```

Through the subdomain:

```bash
curl --get 'https://wordstat.mydomain.ru/top' \
  --data-urlencode 'q=купить базу клиентов' \
  --header 'Authorization: Bearer YOUR_PROXY_API_KEY'
```

For the path-based Caddy variant, set `PUBLIC_BASE_URL` and use
`https://mydomain.ru/api/wordstat/top` instead.

Successful responses use numeric counts parsed from the visible Wordstat page:

```json
{
  "query": "купить базу клиентов",
  "totalCount": 12345,
  "results": [
    {"phrase": "купить базу клиентов", "count": 12345}
  ],
  "associations": [
    {"phrase": "база потенциальных клиентов", "count": 678}
  ]
}
```

If Yandex expires the session or requests a CAPTCHA, the API returns
`yandex_auth_required` or `yandex_captcha_required`. Open the SSH tunnel and
complete the requested step manually; CAPTCHA bypass is intentionally absent.

## GPT Action

After deployment:

1. Open the GPT editor and create an Action.
2. Import `https://YOUR_PUBLIC_HOST/openapi.json`.
3. Configure authentication as an API key using the `Authorization` header and
   the `Bearer` authentication type.
4. Store the server-side `PROXY_API_KEY` value in the GPT Action authentication
   settings. Never copy the Yandex browser session into GPT.

The Action operation is named `getWordstatTop` and accepts the required query
parameter `q`.
