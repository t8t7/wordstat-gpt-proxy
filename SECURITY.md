# Security policy

Do not open a public issue containing API keys, Bearer tokens, `.env` files, IP
addresses that are not already public, or other credentials. Revoke a secret
immediately if it is exposed.

The Yandex browser session is stored only in the private Docker volume on the
server. Never publish the browser-screen port; access it through an SSH tunnel.
Only `PROXY_API_KEY` is configured in the GPT Action authentication settings.
