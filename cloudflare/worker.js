/**
 * Cloudflare Worker Proxy for TAIEX Real-time Index & Futures Quotes
 * Uses open Yahoo Finance API (^TWII) to bypass TAIFEX WAF IP blocks.
 */

export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Yahoo Finance Open API for TAIEX (^TWII)
    const targetUrl = 'https://query1.finance.yahoo.com/v8/finance/chart/^TWII?interval=1m&range=1d';

    try {
      const cache = caches.default;
      let response = await cache.match(request);

      if (!response) {
        const fetchResponse = await fetch(targetUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
          }
        });

        const data = await fetchResponse.json();
        
        let price = null;
        if (data.chart && data.chart.result && data.chart.result[0]) {
          const meta = data.chart.result[0].meta;
          price = meta.regularMarketPrice || meta.chartPreviousClose;
        }

        const payload = JSON.stringify({
          status: 'success',
          symbol: '^TWII',
          spot_price: price,
          timestamp: new Date().toISOString(),
          raw: data
        }, null, 2);

        response = new Response(payload, {
          status: 200,
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=5'
          }
        });

        ctx.waitUntil(cache.put(request, response.clone()));
      }

      return response;
    } catch (err) {
      return new Response(JSON.stringify({ status: 'error', message: err.message }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
