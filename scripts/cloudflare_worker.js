// TXO-GEX Cloud Relay Worker (Cloudflare Workers 24/7 Free Endpoint)
// Serves as an ultra-fast HTTPS cloud bridge for TradingView & Multi-source Live Ticks

let inMemoryTick = {
  ticker: "TXF1!",
  price: 0,
  change: 0,
  pct: 0,
  provider: "NONE",
  provider_name: "⚪ 官方盤後定案 (靜態分析)",
  timestamp: Date.now()
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // CORS Headers for global access from GitHub Pages and TradingView
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Content-Type": "application/json; charset=utf-8"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // 1. GET /api/live_tick (Read current live tick or accept URL query params)
    if (request.method === "GET") {
      const p = url.searchParams.get("price");
      const prov = url.searchParams.get("provider");
      
      if (p && parseFloat(p) > 0) {
        const priceNum = parseFloat(p);
        const tickData = {
          ticker: "TXF1!",
          price: priceNum,
          change: parseFloat(url.searchParams.get("change") || "0"),
          pct: parseFloat(url.searchParams.get("pct") || "0"),
          provider: (prov || "TRADINGVIEW").toUpperCase(),
          provider_name: "🟡 TradingView 實時網關 (雲端中繼)",
          timestamp: Date.now(),
          time: Date.now()
        };
        
        if (env.GEX_KV) {
          await env.GEX_KV.put("GEX_LIVE_TICK", JSON.stringify(tickData), { expirationTtl: 300 });
        }
        inMemoryTick = tickData;
      }

      let currentTick = inMemoryTick;
      if (env.GEX_KV) {
        const kvVal = await env.GEX_KV.get("GEX_LIVE_TICK");
        if (kvVal) {
          try { currentTick = JSON.parse(kvVal); } catch(e){}
        }
      }

      // Check staleness (> 45 seconds -> fallback)
      if (currentTick.price > 0 && (Date.now() - (currentTick.timestamp || currentTick.time || 0) > 45000)) {
        currentTick = {
          price: 0,
          provider: "NONE",
          provider_name: "⚪ 雲端快照已過期",
          timestamp: Date.now()
        };
      }

      return new Response(JSON.stringify(currentTick), { headers: corsHeaders });
    }

    // 2. POST /api/live_tick (Write new tick from TradingView bookmarklet or Python gateway)
    if (request.method === "POST") {
      try {
        const data = await request.json();
        if (data && data.price > 0) {
          const tickData = {
            ticker: data.ticker || "TXF1!",
            price: parseFloat(data.price),
            change: parseFloat(data.change || 0),
            pct: parseFloat(data.pct || 0),
            provider: (data.provider || "TRADINGVIEW").toUpperCase(),
            provider_name: data.provider_name || "🟡 TradingView 實時網關 (雲端中繼)",
            timestamp: Date.now(),
            time: Date.now()
          };

          if (env.GEX_KV) {
            await env.GEX_KV.put("GEX_LIVE_TICK", JSON.stringify(tickData), { expirationTtl: 300 });
          }
          inMemoryTick = tickData;

          return new Response(JSON.stringify({ status: "ok", tick: tickData }), { headers: corsHeaders });
        }
      } catch (e) {
        return new Response(JSON.stringify({ status: "error", message: e.message }), { status: 400, headers: corsHeaders });
      }
    }

    return new Response(JSON.stringify({ status: "not_found" }), { status: 404, headers: corsHeaders });
  }
};
