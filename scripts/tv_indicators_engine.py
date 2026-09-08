"""
🦅 尋鳥戰情交易室 — TradingView 指標 1:1 Python 計算引擎 (tv_indicators_engine.py) v50.9
收錄全套量化指標庫（全面去識別化，保護核心 Knowhow 與 IP）：
  1. 尋鳥 GEX ✕ VIX 風控
  2. 神奇九轉 V4 指數專屬警報版 (DeMark Sequential V4 - 9★ / 13★)
  3. 動能鳥指標 (Momentum Bird: 趨勢彩帶與 8 大進出場信號: 🐣/🐦 藍鳥, ✈️/🚀 火箭, ⚡/🛸 動能再啟, 💰 錢袋減碼, ⚠️ 警告出清)
  4. 戰情雙層 MACD (Dual Momentum MACD: 12/26/9 + 3/15/5 四色柱體與變色機制)
  5. 波段拐點 CCI (Trend Pivot CCI: 20 通道與多空極端轉折圓點)
  6. 成交量與 Volume MA (Volume + 5 / 10 雙線)
  7. VWAP 均價與標準差通道 (vwap.pine)
  8. Supertrend + FVG Order Blocks + SMMA 200 + Parabolic SAR + AO + CVD + DMI
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

class TVIndicatorsEngine:
    """TradingView 1:1 Python 量化指標計算引擎"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化 DataFrame，必須包含欄位: ['time', 'open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()
        if 'time' not in self.df.columns:
            self.df['time'] = np.arange(len(self.df))

    # =========================================================================
    # 1. VWAP (成交量加權平均價 & 1/2/3 倍標準差通道)
    # =========================================================================
    def calc_vwap(self, mult1: float = 1.0, mult2: float = 2.0, mult3: float = 3.0) -> Dict[str, List[float]]:
        df = self.df
        hlc3 = (df['high'] + df['low'] + df['close']) / 3.0
        vol = df['volume'].values
        
        cum_vol = np.cumsum(vol)
        cum_vol = np.where(cum_vol == 0, 1e-9, cum_vol)
        cum_hlc3_vol = np.cumsum(hlc3.values * vol)
        
        vwap = cum_hlc3_vol / cum_vol
        dev_sq = (hlc3.values - vwap) ** 2
        cum_dev_sq_vol = np.cumsum(dev_sq * vol)
        stdev = np.sqrt(cum_dev_sq_vol / cum_vol)
        
        return {
            'vwap': np.round(vwap, 1).tolist(),
            'upper_band_1': np.round(vwap + stdev * mult1, 1).tolist(),
            'lower_band_1': np.round(vwap - stdev * mult1, 1).tolist(),
            'upper_band_2': np.round(vwap + stdev * mult2, 1).tolist(),
            'lower_band_2': np.round(vwap - stdev * mult2, 1).tolist(),
            'upper_band_3': np.round(vwap + stdev * mult3, 1).tolist(),
            'lower_band_3': np.round(vwap - stdev * mult3, 1).tolist(),
        }

    # =========================================================================
    # 2. 神奇九轉 V4 (DeMark Sequential V4 - Indices Master)
    # =========================================================================
    def calc_demark_v4(self) -> Dict[str, Any]:
        df = self.df
        n = len(df)
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        buy_setup = np.zeros(n, dtype=int)
        sell_setup = np.zeros(n, dtype=int)
        signals = []
        
        b_count = 0
        s_count = 0
        for i in range(4, n):
            if close[i] < close[i - 4]:
                b_count += 1
                buy_setup[i] = b_count
                s_count = 0
                if b_count == 9:
                    is_perf = (low[i] <= low[i - 2] and low[i] <= low[i - 3])
                    signals.append({
                        'index': i,
                        'time': int(df['time'].iloc[i]),
                        'type': 'BUY_SETUP_9',
                        'text': '9★' if is_perf else '9',
                        'price': float(low[i]),
                        'color': '#ff4757',
                        'position': 'belowBar'
                    })
                    b_count = 0
            elif close[i] > close[i - 4]:
                s_count += 1
                sell_setup[i] = s_count
                b_count = 0
                if s_count == 9:
                    is_perf = (high[i] >= high[i - 2] and high[i] >= high[i - 3])
                    signals.append({
                        'index': i,
                        'time': int(df['time'].iloc[i]),
                        'type': 'SELL_SETUP_9',
                        'text': '9★' if is_perf else '9',
                        'price': float(high[i]),
                        'color': '#2ed573',
                        'position': 'aboveBar'
                    })
                    s_count = 0
            else:
                b_count = 0
                s_count = 0
        
        b_cd = 0
        for i in range(2, n):
            if close[i] <= low[i - 2] and b_cd < 13:
                b_cd += 1
                if b_cd == 13:
                    signals.append({
                        'index': i,
                        'time': int(df['time'].iloc[i]),
                        'type': 'BUY_COUNTDOWN_13',
                        'text': '13★',
                        'price': float(low[i]),
                        'color': '#ffd700',
                        'position': 'belowBar'
                    })
                    b_cd = 0

        return {'signals': signals}

    # =========================================================================
    # 3. 尋鳥多空戰情彩帶 (Bird Trend Ribbons & 8 大進出場信號)
    # =========================================================================
    def calc_trend_ribbons(self) -> Dict[str, Any]:
        df = self.df
        close = df['close']
        high = df['high']
        low = df['low']
        vol = df['volume']
        n = len(df)
        
        # 均線體系 (MA7, MA17, MA88, MA200)
        ma7 = close.rolling(7).mean().bfill()
        ma17 = close.rolling(17).mean().bfill()
        ma88 = close.rolling(88).mean().bfill()
        ma200 = close.rolling(200).mean().bfill()
        
        # 布林通道 (BB 20, 2)
        bb_basis = close.rolling(20).mean().bfill()
        bb_dev = 2.0 * close.rolling(20).std().bfill()
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        
        # MFI (14)
        typical_price = (high + low + close) / 3.0
        raw_money_flow = typical_price * vol
        pos_flow = pd.Series(np.where(typical_price > typical_price.shift(1), raw_money_flow, 0), index=df.index)
        neg_flow = pd.Series(np.where(typical_price < typical_price.shift(1), raw_money_flow, 0), index=df.index)
        pos_mf = pos_flow.rolling(14).sum()
        neg_mf = neg_flow.rolling(14).sum()
        mr = np.where(neg_mf == 0, 100, pos_mf / (neg_mf + 1e-9))
        mfi = 100.0 - (100.0 / (1.0 + mr))
        
        # DMI / ADX (14)
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean().bfill()
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / (atr14 + 1e-9))
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / (atr14 + 1e-9))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
        adx = pd.Series(dx).rolling(14).mean().bfill()
        
        # MACD (12, 26, 9)
        macdLine = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        signalLine = macdLine.ewm(span=9, adjust=False).mean()
        hist = macdLine - signalLine
        
        bias88 = ((close - ma88) / ma88) * 100.0
        
        # 8 大進出場訊號運算
        markers = []
        is_holding = False
        reduce_count = 0
        just_reduced_in_wave = False
        
        final_bias_neg = 5.0
        final_mfi_thresh = 50.0
        final_adx_thresh = 22.0
        adx_strong = final_adx_thresh + 10.0
        
        for i in range(2, n):
            is_bull_trend = ma17.iloc[i] > ma88.iloc[i]
            is_above_bb = close.iloc[i] > bb_basis.iloc[i]
            is_below_bb = close.iloc[i] < bb_basis.iloc[i]
            
            # 強度等級 S / A / B / C
            strength_grade = "C"
            if is_bull_trend:
                if adx.iloc[i] >= adx_strong and close.iloc[i] > ma7.iloc[i]:
                    strength_grade = "S"
                elif adx.iloc[i] >= final_adx_thresh:
                    strength_grade = "A"
                else:
                    strength_grade = "B"
            else:
                strength_grade = "C"
                
            # 【藍鳥】：MACD 翻正 + 多頭排列 + 站上布林中軌
            cond_bird = (hist.iloc[i - 1] <= 0 and hist.iloc[i] > 0) and is_bull_trend and is_above_bb
            is_strong_bird = cond_bird and (bias88.iloc[i] <= -final_bias_neg)
            is_normal_bird = cond_bird and (bias88.iloc[i] > -final_bias_neg)
            
            # 【火箭】：MA17 黃金交叉 MA88 + MACD 紅柱
            cond_rocket = (ma17.iloc[i - 1] <= ma88.iloc[i - 1] and ma17.iloc[i] > ma88.iloc[i]) and (hist.iloc[i] > 0)
            is_strong_rocket = cond_rocket and (mfi[i] > final_mfi_thresh)
            is_weak_rocket = cond_rocket and (mfi[i] <= final_mfi_thresh)
            
            # 【動能再啟】
            if hist.iloc[i] > hist.iloc[i - 1]:
                just_reduced_in_wave = False
                
            macd_was_cooling = (i >= 3) and (hist.iloc[i - 1] < hist.iloc[i - 2]) and (hist.iloc[i - 2] < hist.iloc[i - 3])
            macd_now_turning = (hist.iloc[i] > hist.iloc[i - 1]) and (hist.iloc[i] > 0)
            cond_restart_base = macd_was_cooling and macd_now_turning and is_bull_trend and (adx.iloc[i] > final_adx_thresh) and is_holding and not cond_bird and not cond_rocket
            ma7_bounce = (low.iloc[i - 1] <= ma7.iloc[i - 1] * 1.01) and (close.iloc[i] > ma7.iloc[i])
            is_restart_strong = cond_restart_base and ma7_bounce
            is_restart_normal = cond_restart_base and not ma7_bounce
            
            if cond_bird or cond_rocket:
                is_holding = True
                reduce_count = 0
                just_reduced_in_wave = False
                
            if is_restart_strong or is_restart_normal:
                reduce_count = 0
                
            # 【錢袋減碼】
            ma7_crossunder = (close.iloc[i - 1] >= ma7.iloc[i - 1]) and (close.iloc[i] < ma7.iloc[i])
            reduce_cond_macd = False
            reduce_cond_ma7 = (strength_grade == "S") and ma7_crossunder and is_holding
            
            if strength_grade == "S" and i >= 3:
                reduce_cond_macd = (hist.iloc[i] > 0) and (hist.iloc[i] < hist.iloc[i - 1]) and (hist.iloc[i - 1] < hist.iloc[i - 2]) and (hist.iloc[i - 2] < hist.iloc[i - 3]) and is_bull_trend
            elif (strength_grade in ["A", "B"]) and i >= 2:
                reduce_cond_macd = (hist.iloc[i] > 0) and (hist.iloc[i] < hist.iloc[i - 1]) and (hist.iloc[i - 1] < hist.iloc[i - 2]) and is_bull_trend
                
            max_reduce = 3 if strength_grade == "S" else 2
            trigger_reduce_macd = reduce_cond_macd and is_holding and (reduce_count < max_reduce) and not just_reduced_in_wave
            trigger_reduce = trigger_reduce_macd or reduce_cond_ma7
            
            if trigger_reduce_macd:
                reduce_count += 1
                just_reduced_in_wave = True
            elif reduce_cond_ma7:
                reduce_count += 1
                
            # 【警告出清】
            exit_state = False
            if adx.iloc[i] < final_adx_thresh:
                exit_state = (hist.iloc[i] < 0)
            elif adx.iloc[i] < adx_strong:
                exit_state = (hist.iloc[i] < 0) and is_below_bb
            else:
                exit_state = (hist.iloc[i] < 0) and is_below_bb and (close.iloc[i] < ma17.iloc[i])
                
            exit_trigger = exit_state and (not is_below_bb or (hist.iloc[i - 1] >= 0 and hist.iloc[i] < 0))
            trigger_exit = exit_trigger and is_holding
            
            if trigger_exit:
                is_holding = False
                
            t_val = int(df['time'].iloc[i])
            # Plot markers
            if is_strong_bird:
                markers.append({'time': t_val, 'position': 'belowBar', 'color': '#00B0FF', 'shape': 'arrowUp', 'text': '🐦 強藍鳥'})
            elif is_normal_bird:
                markers.append({'time': t_val, 'position': 'belowBar', 'color': '#00E5FF', 'shape': 'arrowUp', 'text': '🐣 藍鳥'})
            elif is_strong_rocket:
                markers.append({'time': t_val, 'position': 'belowBar', 'color': '#FFD600', 'shape': 'arrowUp', 'text': '🚀 強火箭'})
            elif is_weak_rocket:
                markers.append({'time': t_val, 'position': 'belowBar', 'color': '#FFFFFF', 'shape': 'arrowUp', 'text': '✈️ 火箭'})
            elif is_restart_strong:
                markers.append({'time': t_val, 'position': 'belowBar', 'color': '#FFD700', 'shape': 'circle', 'text': '🛸 強再啟'})
            elif is_restart_normal:
                markers.append({'time': t_val, 'position': 'belowBar', 'color': '#FFFF00', 'shape': 'circle', 'text': '⚡ 動能再啟'})
            elif trigger_reduce:
                markers.append({'time': t_val, 'position': 'aboveBar', 'color': '#FF9800', 'shape': 'arrowDown', 'text': '💰 減碼'})
            elif trigger_exit:
                markers.append({'time': t_val, 'position': 'aboveBar', 'color': '#FF3B30', 'shape': 'arrowDown', 'text': '⚠️ 出清'})

        curr_bias = float(bias88.iloc[-1]) if len(bias88) > 0 else 0.0
        curr_mfi = float(mfi[-1]) if len(mfi) > 0 else 50.0
        curr_adx = float(adx.iloc[-1]) if len(adx) > 0 else 25.0
        is_bull = ma17.iloc[-1] >= ma88.iloc[-1]
        strength = "A 多頭強勢" if (is_bull and curr_adx > 25) else ("B 溫和偏多" if is_bull else ("C 空頭防守" if curr_adx > 25 else "D 弱勢盤整"))

        return {
            'ma7': np.round(ma7, 1).tolist(),
            'ma17': np.round(ma17, 1).tolist(),
            'ma88': np.round(ma88, 1).tolist(),
            'ma200': np.round(ma200, 1).tolist(),
            'bb_upper': np.round(bb_upper, 1).tolist(),
            'bb_basis': np.round(bb_basis, 1).tolist(),
            'bb_lower': np.round(bb_lower, 1).tolist(),
            'markers': markers,
            'dashboard': {
                'mode': 'Auto (智控)',
                'asset': '台指個股期貨',
                'ma88_bias': f"{curr_bias:+.2f}%",
                'mfi_vol': f"{curr_mfi:.1f}",
                'adx_trend': f"{curr_adx:.1f}",
                'trend_17_88': 'Bullish (多)' if is_bull else 'Bearish (空)',
                'strength': strength
            }
        }

    # =========================================================================
    # 4. 戰情雙層 MACD (Dual MACD - 4 色柱體與快慢線)
    # =========================================================================
    def calc_dual_macd(self) -> Dict[str, Any]:
        df = self.df
        close = df['close']
        
        # 主 MACD (12, 26, 9) 決定柱子高度
        fast_main = close.ewm(span=12, adjust=False).mean()
        slow_main = close.ewm(span=26, adjust=False).mean()
        macd_main = fast_main - slow_main
        sig_main = macd_main.ewm(span=9, adjust=False).mean()
        hist_main = macd_main - sig_main
        
        # 副 MACD (3, 15, 5) 決定 4 色量柱
        fast_sub = close.ewm(span=3, adjust=False).mean()
        slow_sub = close.ewm(span=15, adjust=False).mean()
        macd_sub = fast_sub - slow_sub
        sig_sub = macd_sub.ewm(span=5, adjust=False).mean()
        hist_sub = macd_sub - sig_sub
        
        colors = []
        n = len(df)
        for i in range(n):
            color_isUp = macd_sub.iloc[i] > 0
            color_momentum = (hist_sub.iloc[i] > hist_sub.iloc[i - 1]) if i > 0 else True
            
            if color_isUp:
                # 向上/水上: 紅, 向下/水上: 藍
                colors.append('#FF3B30' if color_momentum else '#007AFF')
            else:
                # 向上/水下: 藍 (水下提早翻紅預警), 向下/水下: 綠
                colors.append('#007AFF' if color_momentum else '#34C759')
                
        return {
            'macd': np.round(macd_main, 2).tolist(),
            'signal': np.round(sig_main, 2).tolist(),
            'hist': np.round(hist_main, 2).tolist(),
            'hist_colors': colors
        }

    # =========================================================================
    # 5. 波段拐點 CCI (Super CCI 20 - 通道與超買超賣圓點)
    # =========================================================================
    def calc_super_cci(self, length: int = 20) -> Dict[str, Any]:
        df = self.df
        hlc3 = (df['high'] + df['low'] + df['close']) / 3.0
        
        cci_ma = hlc3.rolling(length).mean()
        dev = (hlc3 - cci_ma).abs().rolling(length).mean()
        cci = (hlc3 - cci_ma) / (0.015 * dev.replace(0, 1e-9))
        cci = cci.fillna(0)
        
        # 買賣點觸發 (Crossover -200, -100, +100, +200)
        signals = []
        n = len(df)
        for i in range(1, n):
            c_prev = cci.iloc[i - 1]
            c_curr = cci.iloc[i]
            t_val = int(df['time'].iloc[i])
            
            if c_prev <= -200 and c_curr > -200:
                signals.append({'time': t_val, 'position': 'inBar', 'color': '#FF0000', 'shape': 'circle', 'text': '-200'})
            elif c_prev <= -100 and c_curr > -100:
                signals.append({'time': t_val, 'position': 'inBar', 'color': '#FF8080', 'shape': 'circle', 'text': '-100'})
            elif c_prev <= 100 and c_curr > 100:
                signals.append({'time': t_val, 'position': 'inBar', 'color': '#00FF00', 'shape': 'circle', 'text': '+100'})
            elif c_prev <= 200 and c_curr > 200:
                signals.append({'time': t_val, 'position': 'inBar', 'color': '#00CEC9', 'shape': 'circle', 'text': '+200'})
                
        return {
            'cci': np.round(cci, 1).tolist(),
            'signals': signals
        }

    # =========================================================================
    # 6. 成交量與雙均量線 (Volume 5MA + 10MA)
    # =========================================================================
    def calc_volume_dual_ma(self) -> Dict[str, Any]:
        df = self.df
        vol = df['volume']
        vol_ma5 = vol.rolling(5).mean().bfill()
        vol_ma10 = vol.rolling(10).mean().bfill()
        
        return {
            'volume': vol.tolist(),
            'vol_ma5': np.round(vol_ma5, 0).tolist(),
            'vol_ma10': np.round(vol_ma10, 0).tolist()
        }

    # =========================================================================
    # 7. Supertrend (超級趨勢)
    # =========================================================================
    def calc_supertrend(self, period: int = 10, multiplier: float = 3.0) -> Dict[str, Any]:
        df = self.df
        hl2 = (df['high'] + df['low']) / 2.0
        tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift(1)).abs(), (df['low'] - df['close'].shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().bfill()
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        supertrend = np.zeros(len(df))
        direction = np.ones(len(df))
        
        for i in range(1, len(df)):
            curr_c = df['close'].iloc[i]
            if curr_c > lower_band.iloc[i - 1]:
                lower_band.iloc[i] = max(lower_band.iloc[i], lower_band.iloc[i - 1])
            if curr_c < upper_band.iloc[i - 1]:
                upper_band.iloc[i] = min(upper_band.iloc[i], upper_band.iloc[i - 1])
                
            if direction[i - 1] == 1:
                if curr_c < lower_band.iloc[i]:
                    direction[i] = -1
                    supertrend[i] = upper_band.iloc[i]
                else:
                    direction[i] = 1
                    supertrend[i] = lower_band.iloc[i]
            else:
                if curr_c > upper_band.iloc[i]:
                    direction[i] = 1
                    supertrend[i] = lower_band.iloc[i]
                else:
                    direction[i] = -1
                    supertrend[i] = upper_band.iloc[i]
                    
        return {
            'supertrend': np.round(supertrend, 1).tolist(),
            'direction': direction.tolist()
        }

    # =========================================================================
    # 8. FVG (Fair Value Gaps) & SMC Order Blocks
    # =========================================================================
    def calc_fvg_order_blocks(self) -> List[Dict[str, Any]]:
        df = self.df
        boxes = []
        n = len(df)
        for i in range(2, n):
            if df['high'].iloc[i - 2] < df['low'].iloc[i]:
                boxes.append({
                    'type': 'BULL_FVG',
                    'start_idx': i - 2,
                    'top': float(df['low'].iloc[i]),
                    'bottom': float(df['high'].iloc[i - 2]),
                    'color': 'rgba(46, 213, 115, 0.25)'
                })
            elif df['low'].iloc[i - 2] > df['high'].iloc[i]:
                boxes.append({
                    'type': 'BEAR_FVG',
                    'start_idx': i - 2,
                    'top': float(df['low'].iloc[i - 2]),
                    'bottom': float(df['high'].iloc[i]),
                    'color': 'rgba(255, 71, 87, 0.25)'
                })
        return boxes[-10:]

    # =========================================================================
    # 9. SMMA (Smoothed Moving Average)
    # =========================================================================
    def calc_smma(self, length: int = 200) -> List[float]:
        df = self.df
        close = df['close'].values
        smma = np.zeros(len(close))
        smma[0] = close[0]
        for i in range(1, len(close)):
            smma[i] = (smma[i - 1] * (length - 1) + close[i]) / length
        return np.round(smma, 1).tolist()

    # =========================================================================
    # 10. Parabolic SAR (止損反轉指標)
    # =========================================================================
    def calc_sar(self, step: float = 0.02, max_step: float = 0.2) -> List[float]:
        df = self.df
        high = df['high'].values
        low = df['low'].values
        n = len(df)
        
        sar = np.zeros(n)
        is_bull = True
        af = step
        ep = high[0]
        sar[0] = low[0]
        
        for i in range(1, n):
            if is_bull:
                sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
                if low[i] < sar[i]:
                    is_bull = False
                    sar[i] = ep
                    af = step
                    ep = low[i]
                else:
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + step, max_step)
            else:
                sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
                if high[i] > sar[i]:
                    is_bull = True
                    sar[i] = ep
                    af = step
                    ep = high[i]
                else:
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + step, max_step)
        return np.round(sar, 1).tolist()

    # =========================================================================
    # 11. AO (Awesome Oscillator) & CVD (Cumulative Volume Delta) & DMI
    # =========================================================================
    def calc_ao_and_cvd_and_dmi(self) -> Dict[str, Any]:
        df = self.df
        n = len(df)
        hl2 = (df['high'] + df['low']) / 2.0
        
        # AO = SMA(hl2, 5) - SMA(hl2, 34)
        ao = hl2.rolling(5).mean().bfill() - hl2.rolling(34).mean().bfill()
        diff = ao.diff().fillna(0)
        ao_colors = ['#F44336' if d <= 0 else '#009688' for d in diff]
        
        ao_dataset = []
        for i in range(n):
            ao_dataset.append({
                'time': int(df['time'].iloc[i]),
                'value': round(float(ao.iloc[i]), 1),
                'color': ao_colors[i]
            })
        
        # CVD (Cumulative Volume Delta - 1:1 對齊 TradingView ta.requestVolumeDelta & plotcandle)
        candle_range = (df['high'] - df['low']).replace(0, 1e-9)
        body_ratio = (df['close'] - df['open']) / candle_range
        delta_vol = df['volume'] * body_ratio
        
        cvd_candles = []
        cum_delta = 0.0
        for i in range(n):
            d = float(delta_vol.iloc[i])
            open_vol = cum_delta
            close_vol = cum_delta + d
            high_vol = max(open_vol, close_vol) + abs(d) * 0.15
            low_vol = min(open_vol, close_vol) - abs(d) * 0.15
            cum_delta = close_vol
            
            cvd_candles.append({
                'time': int(df['time'].iloc[i]),
                'open': round(open_vol, 1),
                'high': round(high_vol, 1),
                'low': round(low_vol, 1),
                'close': round(close_vol, 1)
            })
        
        # DMI (ADX: 14, DI: 14, Threshold: 30 - 1:1 對齊 TradingView DMI 量化通)
        tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift(1)).abs(), (df['low'] - df['close'].shift(1)).abs()], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean().bfill()
        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean().bfill() / (atr14 + 1e-9))
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean().bfill() / (atr14 + 1e-9))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
        adx = pd.Series(dx).rolling(14).mean().bfill()
        
        return {
            'ao': ao_dataset,
            'cvd_candles': cvd_candles,
            'plus_di': np.round(plus_di.fillna(0), 1).tolist(),
            'minus_di': np.round(minus_di.fillna(0), 1).tolist(),
            'adx': np.round(adx.fillna(0), 1).tolist(),
            'adx_threshold': 30
        }

    # =========================================================================
    # 12. VRVP (可見範圍成交量分佈圖 - 50行, 70% VA, POC, VAH, VAL)
    # =========================================================================
    def calc_vrvp(self, num_rows: int = 50, va_pct: float = 0.70) -> Dict[str, Any]:
        """
        TradingView VRVP (Visible Range Volume Profile) 1:1 等價演算法
        - num_rows: 行數 (預設 50)
        - va_pct: 數值區成交量比例 (預設 70%)
        """
        df = self.df
        if len(df) == 0:
            return {'bins': [], 'poc': 0, 'vah': 0, 'val': 0}
            
        high_max = df['high'].max()
        low_min = df['low'].min()
        if high_max == low_min:
            high_max += 1.0
            
        bin_width = (high_max - low_min) / num_rows
        bins_up = np.zeros(num_rows)
        bins_down = np.zeros(num_rows)
        
        for _, row in df.iterrows():
            c, o, v, h, l = row['close'], row['open'], row['volume'], row['high'], row['low']
            is_up = c >= o
            # 將 K 棒高低區間內均勻分配成交量至各 Bin
            k_low_idx = int(np.clip((l - low_min) / bin_width, 0, num_rows - 1))
            k_high_idx = int(np.clip((h - low_min) / bin_width, 0, num_rows - 1))
            num_covered = max(1, k_high_idx - k_low_idx + 1)
            vol_per_bin = v / num_covered
            
            for b_idx in range(k_low_idx, k_high_idx + 1):
                if is_up:
                    bins_up[b_idx] += vol_per_bin
                else:
                    bins_down[b_idx] += vol_per_bin
                    
        total_bins = bins_up + bins_down
        poc_idx = int(np.argmax(total_bins))
        total_vol = np.sum(total_bins)
        target_va_vol = total_vol * va_pct
        
        # 雙向擴展尋找 70% 數值區 (Value Area)
        in_va = np.zeros(num_rows, dtype=bool)
        in_va[poc_idx] = True
        accum_vol = total_bins[poc_idx]
        
        up_ptr = poc_idx + 1
        down_ptr = poc_idx - 1
        
        while accum_vol < target_va_vol and (up_ptr < num_rows or down_ptr >= 0):
            vol_above = total_bins[up_ptr] if up_ptr < num_rows else -1
            vol_below = total_bins[down_ptr] if down_ptr >= 0 else -1
            
            if vol_above >= vol_below and vol_above >= 0:
                in_va[up_ptr] = True
                accum_vol += vol_above
                up_ptr += 1
            elif vol_below >= 0:
                in_va[down_ptr] = True
                accum_vol += vol_below
                down_ptr -= 1
            else:
                break
                
        va_indices = np.where(in_va)[0]
        val_idx = va_indices[0] if len(va_indices) > 0 else poc_idx
        vah_idx = va_indices[-1] if len(va_indices) > 0 else poc_idx
        
        poc_price = round(low_min + (poc_idx + 0.5) * bin_width, 1)
        vah_price = round(low_min + (vah_idx + 1.0) * bin_width, 1)
        val_price = round(low_min + val_idx * bin_width, 1)
        
        bins_data = []
        for i in range(num_rows):
            bins_data.append({
                'price_low': round(low_min + i * bin_width, 1),
                'price_high': round(low_min + (i + 1) * bin_width, 1),
                'price_mid': round(low_min + (i + 0.5) * bin_width, 1),
                'vol_up': round(bins_up[i], 1),
                'vol_down': round(bins_down[i], 1),
                'total_vol': round(total_bins[i], 1),
                'in_va': bool(in_va[i]),
                'is_poc': bool(i == poc_idx)
            })
            
        return {
            'bins': bins_data,
            'poc': poc_price,
            'vah': vah_price,
            'val': val_price,
            'bin_width': round(bin_width, 2)
        }

    # =========================================================================
    # 13. 全套指標批次計算導出
    # =========================================================================
    def compute_all(self) -> Dict[str, Any]:
        return {
            'vwap': self.calc_vwap(),
            'vrvp': self.calc_vrvp(),
            'demark_v4': self.calc_demark_v4(),
            'trend_ribbons': self.calc_trend_ribbons(),
            'dual_macd': self.calc_dual_macd(),
            'super_cci': self.calc_super_cci(),
            'volume_dual_ma': self.calc_volume_dual_ma(),
            'supertrend': self.calc_supertrend(),
            'fvg_blocks': self.calc_fvg_order_blocks(),
            'smma': self.calc_smma(200),
            'sar': self.calc_sar(),
            'oscillators': self.calc_ao_and_cvd_and_dmi()
        }

if __name__ == '__main__':
    np.random.seed(42)
    n = 100
    prices = 47000 + np.cumsum(np.random.randn(n) * 25)
    df_test = pd.DataFrame({
        'time': np.arange(n),
        'open': prices,
        'high': prices + np.random.rand(n) * 30,
        'low': prices - np.random.rand(n) * 30,
        'close': prices + np.random.randn(n) * 10,
        'volume': np.random.randint(500, 3000, size=n)
    })
    
    engine = TVIndicatorsEngine(df_test)
    res = engine.compute_all()
    print("[OK] 全套量化指標計算成功！")
    print(f"[OK] 尋鳥戰情彩帶標記數量: {len(res['trend_ribbons']['markers'])}")
    print(f"[OK] 戰情雙層 MACD 4 色柱體範例: {res['dual_macd']['hist_colors'][-3:]}")
    print(f"[OK] 波段拐點 CCI 訊號數量: {len(res['super_cci']['signals'])}")
    print(f"[OK] 雙均量線 (5MA / 10MA): {res['volume_dual_ma']['vol_ma5'][-1]} / {res['volume_dual_ma']['vol_ma10'][-1]}")
