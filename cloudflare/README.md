# Cloudflare Worker deploy notes

## 1. Install Wrangler

```bash
npm install -g wrangler
wrangler login
```

## 2. Deploy the proxy worker

```bash
wrangler deploy
```

## 3. Add secrets in Cloudflare Dashboard or CLI

```bash
wrangler secret put PRIVATE_ACCESS_TOKEN
wrangler secret put FUBON_AUTH_HEADER
wrangler secret put FUBON_API_TOKEN
wrangler secret put FUBON_API_KEY
wrangler secret put FUBON_API_SECRET
```

## 4. Use the private token when calling the proxy

The Worker now requires a private token to call `/quote`:

```bash
curl -H "X-Private-Token: <your-private-token>" https://taifex-gex-proxy.<your-subdomain>.workers.dev/quote
```

This keeps the quote path private and prevents anonymous public access.

## 5. Replace the placeholder front-end proxy URL

In `app.js`, set:

```js
const LIVE_QUOTE_PROXY_URL = 'https://taifex-gex-proxy.<your-subdomain>.workers.dev/quote';
```

## 6. Keep secrets out of source control

Do not commit API keys or tokens into repo files.
