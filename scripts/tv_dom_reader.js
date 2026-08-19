// ==UserScript==
// @name         TradingView TXF1! Live Price Extractor for GEX Dashboard
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Extracts real-time TXF1! quote from TradingView Watchlist and pushes to local GEX recalculation endpoint.
// @author       Antigravity Quant Team
// @match        https://www.tradingview.com/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function() {
    'use strict';

    const LOCAL_ENDPOINT = "http://localhost:8000/api/live_tick";
    let lastPrice = 0;

    function extractAndPush() {
        // Locate TXF1! in TradingView Right Watchlist DOM
        const symbolElements = document.querySelectorAll('[data-symbol-full="TAIFEX:TXF1!"], [data-symbol="TXF1!"], div[class*="symbol-"]');
        let currentPrice = 0;

        for (let el of symbolElements) {
            const text = el.innerText || el.textContent;
            if (text.includes("TXF1!") || text.includes("台指期")) {
                const parent = el.closest('div[class*="row-"], tr, div[class*="item-"]');
                if (parent) {
                    const priceEl = parent.querySelector('span[class*="last-"], span[class*="price-"]');
                    if (priceEl) {
                        const valStr = priceEl.innerText.replace(',', '').trim();
                        const val = parseFloat(valStr);
                        if (!isNaN(val) && val > 1000) {
                            currentPrice = val;
                            break;
                        }
                    }
                }
            }
        }

        // Fallback: Check Active Chart Title Symbol Price
        if (!currentPrice) {
            const chartPriceEl = document.querySelector('div[class*="js-symbol-last"], span[class*="last-"]');
            if (chartPriceEl) {
                const valStr = chartPriceEl.innerText.replace(',', '').trim();
                const val = parseFloat(valStr);
                if (!isNaN(val) && val > 1000) {
                    currentPrice = val;
                }
            }
        }

        // If price changed, push to GEX endpoint with timestamp
        if (currentPrice && currentPrice !== lastPrice) {
            lastPrice = currentPrice;
            console.log(`[GEX Live Tick] Pushing TXF1! price: ${currentPrice}`);

            GM_xmlhttpRequest({
                method: "POST",
                url: LOCAL_ENDPOINT,
                headers: { "Content-Type": "application/json" },
                data: JSON.stringify({
                    ticker: "TXF1!",
                    price: currentPrice,
                    timestamp: Date.now()
                }),
                onload: function(response) {
                    console.log("[GEX Live Tick] Successfully pushed tick.");
                },
                onerror: function(err) {
                    // Silently ignore if local server is not listening
                }
            });
        }
    }

    // Monitor DOM changes every 1.5 seconds
    setInterval(extractAndPush, 1500);
})();
