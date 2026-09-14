# Wordstat Proxy API

Authenticated proxy for the official Yandex Search API Wordstat `GetTop` method.
Yandex credentials never leave the server.

The service is designed for a GPT Action: deploy it behind HTTPS, import
`https://YOUR_PUBLIC_HOST/openapi.json` into the GPT configuration, select API
key authentication with `Bearer` auth, and enter the value of `PROXY_API_KEY`.

## Server setup

1. Copy `.env.example` to `.env` on the VPS and replace every placeholder. Never
   commit `.env`.
2. Ensure the Yandex service account has the `search-api.webSearch.user` role and
   its API key has the `yc.search-api.execute` scope.
3. Start the isolated stack:

   ```bash
   docker compose up -d --build
   docker compose ps
   ```

4. Merge one block from `deploy/Caddyfile.example` into the current Caddyfile,
   validate it, and only then reload Caddy. Do not replace the existing file.

The API port is bound to `127.0.0.1:8087`; it is not directly internet-facing.
Redis has no published port.

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

Successful responses use numeric counts:

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

These numbers are illustrative. Capture the final example from the live Yandex
response after deployment.

## GPT Action

After deployment:

1. Open the GPT editor and create an Action.
2. Import `https://YOUR_PUBLIC_HOST/openapi.json`.
3. Configure authentication as an API key using the `Authorization` header and
   the `Bearer` authentication type.
4. Store the server-side `PROXY_API_KEY` value in the GPT Action authentication
   settings. Do not place `YANDEX_API_KEY` in GPT.

The Action operation is named `getWordstatTop` and accepts the required query
parameter `q`.
