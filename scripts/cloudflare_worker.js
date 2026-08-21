// TXO-GEX Cloud Relay Worker (Public Open Source Relay Version)
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

      // Check staleness (> 45 seconds -> fallback to TAIFEX MIS Serverless Polling)
      if (!currentTick || currentTick.price === 0 || (Date.now() - (currentTick.timestamp || currentTick.time || 0) > 45000)) {
        try {
          const dateUtc8 = new Date(Date.now() + 8 * 3600 * 1000);
          const h8 = dateUtc8.getUTCHours();
          const isNightSession = (h8 >= 15 || h8 < 5);
          const mType = isNightSession ? '1' : '0';

          const taifexRes = await fetch('https://mis.taifex.com.tw/futures/api/getQuoteList', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
              'Referer': 'https://mis.taifex.com.tw/futures/'
            },
            body: JSON.stringify({ MarketType: mType, SymbolType: 'F' })
          });

          if (taifexRes.ok) {
            const misData = await taifexRes.json();
            const quoteList = (misData.RtData && misData.RtData.QuoteList) ? misData.RtData.QuoteList : [];
            const txItems = quoteList.filter(q => q.SymbolID && q.SymbolID.startsWith('TX') && q.CLastPrice && parseFloat(q.CLastPrice) > 0);
            if (txItems.length > 0) {
              const liveP = parseFloat(txItems[0].CLastPrice);
              const refP = parseFloat(txItems[0].CRefPrice || liveP);
              const chg = Math.round((liveP - refP) * 100) / 100;
              const pct = refP > 0 ? Math.round((chg / refP * 10000)) / 100 : 0;
              currentTick = {
                ticker: "TXF",
                price: liveP,
                change: chg,
                pct: pct,
                provider: "TAIFEX_MIS",
                provider_name: isNightSession ? "🌐 期交所 MIS 夜盤行情" : "🌐 期交所 MIS 日盤行情",
                timestamp: Date.now(),
                time: Date.now()
              };
              return new Response(JSON.stringify(currentTick), { headers: corsHeaders });
            }
          }
        } catch(e){}

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
