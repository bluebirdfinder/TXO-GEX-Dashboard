/**
 * Secure Cloudflare Worker proxy for the TXO dashboard.
 *
 * Important security rule:
 * - Never put Fubon API keys, tokens, or secrets in the browser bundle.
 * - Keep them in Cloudflare Worker secrets / environment variables only.
 */

const DEFAULT_ALLOWED_ORIGIN = 'https://bluebirdfinder.github.io';

function makeCorsHeaders(request, env) {
  const origin = request.headers.get('Origin') || '';
  const allowedOrigin = env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN;
  const allowOrigin = origin && (origin === allowedOrigin || origin.startsWith('https://bluebirdfinder.github.io'))
    ? origin
    : allowedOrigin;

  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400'
  };
}

function buildAuthHeaders(env) {
  const headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
  };

  if (env.FUBON_AUTH_HEADER) {
    headers.Authorization = env.FUBON_AUTH_HEADER;
  } else if (env.FUBON_API_TOKEN) {
    headers.Authorization = `Bearer ${env.FUBON_API_TOKEN}`;
  }

  if (env.FUBON_API_KEY && env.FUBON_API_SECRET) {
    headers['X-API-Key'] = env.FUBON_API_KEY;
    headers['X-API-Secret'] = env.FUBON_API_SECRET;
  }

  return headers;
}

function isAuthorizedPrivateRequest(request, env) {
  const configuredToken = env.PRIVATE_ACCESS_TOKEN;
  if (!configuredToken) {
    return false;
  }

  const headerToken = request.headers.get('X-Private-Token') || '';
  const bearerToken = request.headers.get('Authorization') || '';
  const bearerValue = bearerToken.startsWith('Bearer ') ? bearerToken.replace(/^Bearer\s+/i, '') : '';

  return headerToken === configuredToken || bearerValue === configuredToken;
}

function pickNumber(value) {
  if (value === null || value === undefined) return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function normalizeQuotePayload(data) {
  const payload = data?.data || data?.result || data?.payload || data || {};

  const spot = pickNumber(payload.spot_price ?? payload.spot ?? payload.last ?? payload.price ?? payload.close ?? payload.latestPrice);
  const txf = pickNumber(payload.txf_price ?? payload.txf ?? payload.futuresPrice ?? payload.futurePrice ?? payload.quote ?? spot);
  const ts = payload.timestamp || payload.time || payload.updatedAt || new Date().toISOString();

  return {
    status: 'success',
    symbol: payload.symbol || 'TXF1',
    spot_price: spot,
    txf_price: txf ?? spot,
    timestamp: ts
  };
}

export default {
  async fetch(request, env, ctx) {
    const corsHeaders = makeCorsHeaders(request, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return new Response(JSON.stringify({ status: 'ok', message: 'Private proxy heartbeat is healthy.' }), {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    if (url.pathname !== '/quote') {
      return new Response(JSON.stringify({ status: 'ok', message: 'Use /quote to fetch a server-side live quote.' }), {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    if (!isAuthorizedPrivateRequest(request, env)) {
      return new Response(JSON.stringify({
        status: 'error',
        message: 'Private access denied. Add X-Private-Token or Authorization Bearer token.'
      }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    const baseUrl = env.FUBON_API_BASE_URL;
    const quotePath = env.FUBON_QUOTE_PATH || '/quote';

    if (!baseUrl) {
      return new Response(JSON.stringify({
        status: 'error',
        message: 'Missing FUBON_API_BASE_URL in Cloudflare Worker secrets.'
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    try {
      const upstreamUrl = `${baseUrl.replace(/\/$/, '')}${quotePath}`;
      const authHeaders = buildAuthHeaders(env);
      const upstreamResponse = await fetch(upstreamUrl, {
        method: 'GET',
        headers: authHeaders
      });

      if (!upstreamResponse.ok) {
        return new Response(JSON.stringify({
          status: 'error',
          message: 'Upstream quote provider returned an error.'
        }), {
          status: upstreamResponse.status,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      const data = await upstreamResponse.json();
      const payload = normalizeQuotePayload(data);

      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
          'Cache-Control': 'public, max-age=5'
        }
      });
    } catch (err) {
      return new Response(JSON.stringify({
        status: 'error',
        message: 'Unable to retrieve live quote from the secure proxy.'
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
