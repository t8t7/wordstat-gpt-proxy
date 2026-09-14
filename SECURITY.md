# Security policy

Do not open a public issue containing API keys, Bearer tokens, `.env` files, IP
addresses that are not already public, or other credentials. Revoke a secret
immediately if it is exposed.

The Yandex API key and folder ID must exist only in the server-side `.env` file.
Only `PROXY_API_KEY` is configured in the GPT Action authentication settings.

