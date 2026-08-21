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
    if (request.method === "POST" && url.pathname !== "/webhook/tv-alert") {
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

    // 3. POST /webhook/tv-alert (TradingView Webhook -> GEX Fusion -> Telegram Channel)
    if (request.method === "POST" && url.pathname === "/webhook/tv-alert") {
      try {
        let payload = {};
        const contentType = request.headers.get("content-type") || "";
        
        if (contentType.includes("application/json")) {
          payload = await request.json();
        } else {
          const rawText = await request.text();
          // 純文字解析 (Plain Text Parser)
          const isSell = /做空|空單|賣出|SELL|SHORT|🟢/i.test(rawText);
          const priceMatch = rawText.match(/(?:價位|進場|價格|價|price|@)\s*[:：=]?\s*(\d+(?:\.\d+)?)/i);
          const pVal = priceMatch ? parseFloat(priceMatch[1]) : (rawText.match(/\b\d{4,5}(?:\.\d+)?\b/) ? parseFloat(rawText.match(/\b\d{4,5}(?:\.\d+)?\b/)[0]) : 0);
          
          let tf = "5m";
          if (/4h|240/i.test(rawText)) tf = "4h";
          else if (/1h|60m|60/i.test(rawText)) tf = "1h";
          else if (/30m|30k|30/i.test(rawText)) tf = "30m";
          else if (/15m|15k|15/i.test(rawText)) tf = "15m";

          payload = {
            ticker: "TXF1!",
            timeframe: tf,
            strategy: /5K/i.test(rawText) ? "5K戰法" : "動能鳥指標",
            signal: isSell ? "SELL" : "BUY",
            price: pVal,
            message: rawText.trim()
          };
        }

        const ticker = payload.ticker || "TXF1!";
        const timeframe = (payload.timeframe || "5m").toLowerCase();
        const strategy = payload.strategy || "指標訊號";
        const signal = (payload.signal || "BUY").toUpperCase();
        const price = parseFloat(payload.price || 0);
        const note = payload.message || "指標觸發";

        // 讀取最新 GEX 牆體數據 (先讀 KV，備用讀 GitHub Raw)
        let gex = { txf_price: price, call_wall_strike: 45200, put_wall_strike: 44600, zero_gamma_level: 44783.7 };
        try {
          const ghRes = await fetch("https://raw.githubusercontent.com/bluebirdfinder/TXO-GEX-Dashboard/main/data/gex_data.json");
          if (ghRes.ok) {
            gex = await ghRes.json();
          }
        } catch(e){}

        const putWall = gex.put_wall_strike || 44600;
        const callWall = gex.call_wall_strike || 45200;
        const zeroGamma = gex.zero_gamma_level || 44783.7;

        const distPut = Math.abs(price - putWall);
        const distCall = Math.abs(price - callWall);

        // 🛑 GEX 門檻過濾
        let isGexSatisfied = false;
        let gexReason = "";

        if (signal === "BUY") {
          if (distPut <= 150) {
            isGexSatisfied = true;
            gexReason = `觸發價 <b>$${price.toLocaleString()}</b> 緊貼做市商 Put 護盤牆 (<b>${putWall.toLocaleString()}</b>)，強力防禦支撐彈力！`;
          } else if (price > zeroGamma) {
            isGexSatisfied = true;
            gexReason = `觸發價 <b>$${price.toLocaleString()}</b> 站穩 Zero Gamma 轉折點 (<b>${zeroGamma.toLocaleString()}</b>) 之上，進入正 Gamma 助漲區！`;
          } else {
            gexReason = `價格處於無牆區，離下檔 Put 牆還有 ${distPut.toFixed(0)} 點空間。`;
          }
        } else {
          if (distCall <= 150) {
            isGexSatisfied = true;
            gexReason = `觸發價 <b>$${price.toLocaleString()}</b> 緊貼做市商 Call 壓制牆 (<b>${callWall.toLocaleString()}</b>)，天花板避險賣壓強烈！`;
          } else if (price < zeroGamma) {
            isGexSatisfied = true;
            gexReason = `觸發價 <b>$${price.toLocaleString()}</b> 跌破 Zero Gamma 轉折點 (<b>${zeroGamma.toLocaleString()}</b>)，進入負 Gamma 避險區！`;
          } else {
            gexReason = `價格處於無牆區，離上檔 Call 牆還有 ${distCall.toFixed(0)} 點空間。`;
          }
        }

        // 未達 GEX 門檻，自動攔截過濾
        if (!isGexSatisfied) {
          return new Response(JSON.stringify({ status: "filtered", reason: "GEX 門檻未滿足，防洗盤攔截" }), { headers: corsHeaders });
        }

        // 🎯 時區自動策略路由
        let quantAdvice = "";
        let strategyTag = "";

        if (timeframe.includes("5m") || timeframe.includes("5k") || timeframe.includes("15m") || timeframe.includes("15k")) {
          strategyTag = "⚡【週選買方當沖 / 微台當沖】";
          if (signal === "BUY") {
            quantAdvice = `💡 <b>【露米當沖指引 — 週選擇權買方/微台當沖】</b>\n• 標的選型: 買進 <code>${putWall + 200} Call</code> (當沖抓爆發力)\n• 微台當沖: 可於 <code>$${price.toLocaleString()}</code> 進場建立多單，停損設 <code>${(price - 40).toFixed(0)}</code>\n• 風險控管: 買方當沖速戰速決，獲利 30%~50% 移停走人。`;
          } else {
            quantAdvice = `💡 <b>【露米當沖指引 — 週選擇權買方/微台當沖】</b>\n• 標的選型: 買進 <code>${callWall - 200} Put</code> (當沖抓下殺力)\n• 微台當沖: 可於 <code>$${price.toLocaleString()}</code> 進場建立空單，停損設 <code>${(price + 40).toFixed(0)}</code>\n• 風險控管: 買方當沖速戰速決，獲利 30%~50% 移停走人。`;
          }
        } else if (timeframe.includes("30m") || timeframe.includes("30k") || timeframe.includes("1h") || timeframe.includes("60m")) {
          strategyTag = "🏦【週選擇權賣方價差單 / 微台短波段】";
          if (signal === "BUY") {
            quantAdvice = `💡 <b>【露米下單指引 — 週選擇權 Bull Put Spread】</b>\n• 賣出Put: <code>${putWall} Put</code> (做市商護盤牆)\n• 買進保險: <code>${putWall - 150} Put</code> (下檔防禦腳)\n• 微台波段: 可建倉 1 口微台多單，目標看至天花板 <code>${callWall}</code>`;
          } else {
            quantAdvice = `💡 <b>【露米下單指引 — 週選擇權 Bear Call Spread】</b>\n• 賣出Call: <code>${callWall} Call</code> (做市商天花板牆)\n• 買進保險: <code>${callWall + 150} Call</code> (上檔防禦腳)\n• 微台波段: 可建倉 1 口微台空單，目標看至護盤牆 <code>${putWall}</code>`;
          }
        } else {
          strategyTag = "🛡️【Covered Call 掩護性買權 / 長線避險】";
          quantAdvice = `💡 <b>【露米下單指引 — Covered Call 貼天花板】</b>\n• 現貨/微台部位: 持有微台多單中\n• 掩護賣出: 賣出 <code>${callWall} Call</code> (收取 50~100 點權利金補貼成本)\n• 適合時機: 漲勢推升至 Call 牆天花板且動能趨緩時。`;
        }

        const actionEmoji = signal === "BUY" ? "🔴 多頭 (BUY)" : "🟢 空頭 (SELL)";
        const badge = `⚡⚡ <b>SS 級【${strategy} + GEX 牆體防守】共振發動！</b>`;

        let msg = `🦅 <b>【露米籌碼 & 尋鳥台指 GEX — 多指標即時共振訊號】</b>\n\n`;
        msg += `${badge}\n${strategyTag}\n\n`;
        msg += `📌 <b>觸發標的</b>: <code>${ticker}</code> (${timeframe.toUpperCase()})\n`;
        msg += `📊 <b>當前訊號</b>: ${actionEmoji} @ <b>$${price.toLocaleString()}</b>\n`;
        msg += `🎯 <b>觸發策略</b>: ${strategy}\n`;
        msg += `💬 <b>策略說明</b>: ${note}\n\n`;
        msg += `🧱 <b>【GEX 做市商實時防守陣地】</b>\n`;
        msg += `• Put 護盤牆 (支撐): <code>${putWall.toLocaleString()}</code> (相距 ${(price - putWall).toFixed(0)} 點)\n`;
        msg += `• Call 天花板牆 (壓力): <code>${callWall.toLocaleString()}</code> (相距 ${(callWall - price).toFixed(0)} 點)\n`;
        msg += `• Zero Gamma 轉折線: <code>${zeroGamma.toLocaleString()}</code>\n`;
        msg += `• 🔍 <b>籌碼點評</b>: ${gexReason}\n\n`;
        msg += `${quantAdvice}\n\n`;
        msg += `⏱️ <i>雲端秒回發送時間: ${new Date(Date.now() + 8*3600*1000).toISOString().replace('T', ' ').substring(0, 19)}</i>`;

        // 雲端直發 Telegram
        const botToken = env.TELEGRAM_BOT_TOKEN || "";
        const chatId = env.TELEGRAM_CHAT_ID || "";
        if (botToken && chatId) {
          ctx.waitUntil(fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: chatId, text: msg, parse_mode: "HTML" })
          }));
        }

        return new Response(JSON.stringify({ status: "success", dispatched: true, strategy: strategyTag }), { headers: corsHeaders });
      } catch(e) {
        return new Response(JSON.stringify({ status: "error", message: e.message }), { status: 400, headers: corsHeaders });
      }
    }

    return new Response(JSON.stringify({ status: "not_found" }), { status: 404, headers: corsHeaders });
  }
};
