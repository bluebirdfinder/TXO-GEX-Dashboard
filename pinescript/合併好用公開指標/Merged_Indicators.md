// This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
// Combined by Antigravity: Supertrend(v6) + FVG Order Blocks + Smart Money Concepts

//@version=6
indicator('Merged Supertrend + FVG + SMC', overlay = true, max_labels_count = 500, max_lines_count = 500, max_boxes_count = 500, max_bars_back = 2000)

// =============================================================================
// 1. SUPERTREND (Upgraded to v5)
// =============================================================================
st_Periods = input.int(title="ATR Period", defval=10, group="Supertrend")
st_src = input.source(hl2, title="Source", group="Supertrend")
st_Multiplier = input.float(title="ATR Multiplier", step=0.1, defval=3.0, group="Supertrend")
st_changeATR= input.bool(title="Change ATR Calculation Method ?", defval=true, group="Supertrend")
st_showsignals = input.bool(title="Show Buy/Sell Signals ?", defval=true, group="Supertrend")
st_highlighting = input.bool(title="Highlighter On/Off ?", defval=true, group="Supertrend")

st_atr2 = ta.sma(ta.tr, st_Periods)
st_atr_val = st_changeATR ? ta.atr(st_Periods) : st_atr2
st_up = st_src - (st_Multiplier * st_atr_val)
st_up1 = nz(st_up[1], st_up)
st_up := close[1] > st_up1 ? math.max(st_up, st_up1) : st_up
st_dn = st_src + (st_Multiplier * st_atr_val)
st_dn1 = nz(st_dn[1], st_dn)
st_dn := close[1] < st_dn1 ? math.min(st_dn, st_dn1) : st_dn
st_trend = 1
st_trend := nz(st_trend[1], st_trend)
st_trend := st_trend == -1 and close > st_dn1 ? 1 : st_trend == 1 and close < st_up1 ? -1 : st_trend

st_upPlot = plot(st_trend == 1 ? st_up : na, title="Up Trend", style=plot.style_linebr, linewidth=2, color=color.green)
st_buySignal = st_trend == 1 and st_trend[1] == -1
plotshape(st_buySignal ? st_up : na, title="UpTrend Begins", location=location.absolute, style=shape.circle, size=size.tiny, color=color.green)
plotshape(st_buySignal and st_showsignals ? st_up : na, title="Buy", text="Buy", location=location.absolute, style=shape.labelup, size=size.tiny, color=color.green, textcolor=color.white)

st_dnPlot = plot(st_trend == 1 ? na : st_dn, title="Down Trend", style=plot.style_linebr, linewidth=2, color=color.red)
st_sellSignal = st_trend == -1 and st_trend[1] == 1
plotshape(st_sellSignal ? st_dn : na, title="DownTrend Begins", location=location.absolute, style=shape.circle, size=size.tiny, color=color.red)
plotshape(st_sellSignal and st_showsignals ? st_dn : na, title="Sell", text="Sell", location=location.absolute, style=shape.labeldown, size=size.tiny, color=color.red, textcolor=color.white)

st_mPlot = plot(ohlc4, title="", display=display.none)
st_longFillColor = st_highlighting ? (st_trend == 1 ? color.new(color.green,80) : color.new(color.white, 100)) : color.new(color.white, 100)
st_shortFillColor = st_highlighting ? (st_trend == -1 ? color.new(color.red,80) : color.new(color.white, 100)) : color.new(color.white, 100)
fill(st_mPlot, st_upPlot, title="UpTrend Highligter", color=st_longFillColor)
fill(st_mPlot, st_dnPlot, title="DownTrend Highligter", color=st_shortFillColor)

alertcondition(st_buySignal, title="SuperTrend Buy", message="SuperTrend Buy!")
alertcondition(st_sellSignal, title="SuperTrend Sell", message="SuperTrend Sell!")
alertcondition(st_trend != st_trend[1], title="SuperTrend Direction Change", message="SuperTrend has changed direction!")

// =============================================================================
// 2. FVG ORDER BLOCKS
// =============================================================================
fvg_group = "FVG Order Blocks"
fvg_loockback  = input.int(2000, "Lookback period for detecting imbalances", group=fvg_group)
fvg_filter     = input.float(0.5, "Filter Gaps by %", minval=0, maxval=100, step=0.1, group=fvg_group)
fvg_show_imb   = input.bool(true, "Fair Value Gaps", inline="1", group=fvg_group)
fvg_box_amount = input.int(6, "Blocks Amount", group=fvg_group)
fvg_show_broken= input.bool(false, "Broken Blocks", group=fvg_group)
fvg_show_signal= input.bool(false, "Order Blocks Signals", group=fvg_group)
fvg_col_bull   = input.color(#14be94, "Color +/-", inline="2", group=fvg_group)
fvg_col_bear   = input.color(color.rgb(194, 25, 25), "", inline="2", group=fvg_group)

var fvg_boxes1 = array.new<box>(10, box(na))
var fvg_boxes2 = array.new<box>(10, box(na))
var bool fvg_isBull = false
var bool fvg_isBear = false
var box fvg_box1 = box(na)
var box fvg_box2 = box(na)

fvg_atr = ta.atr(200)
fvg_filt_up = (low-high[2])/low*100
fvg_filt_dn = (low[2]-high) / low[2] *100
fvg_max_up = ta.highest(fvg_filt_up, 200)
fvg_max_dn = ta.highest(fvg_filt_dn, 200)

if barstate.isconfirmed and last_bar_index - bar_index < fvg_loockback
    fvg_isBull := high[2] < low and high[2] < high[1] and low[2] < low and fvg_filt_up > fvg_filter
    fvg_isBear := low[2] > high and low[2] > low[1] and high[2] > high and fvg_filt_dn > fvg_filter

if fvg_isBull
    if fvg_show_imb
        box.new(bar_index-1, low, bar_index + 5, high[2], na, 0, bgcolor=color.from_gradient(fvg_filt_up, 0, fvg_max_up, color.new(chart.fg_color, 90), color.new(chart.fg_color, 70)), text=str.tostring(fvg_filt_up, format.percent), text_color=chart.fg_color)
    fvg_box1 := box.new(bar_index-1, high[2], last_bar_index, high[2] - fvg_atr, fvg_col_bull, 1, bgcolor=color.from_gradient(fvg_filt_up, 0, fvg_max_up, na, color.new(fvg_col_bull, 70)), text=str.tostring(fvg_filt_up, format.percent), text_size=size.small, text_color=chart.fg_color, text_halign=text.align_right)
    fvg_boxes1.push(fvg_box1)

if fvg_isBear
    if fvg_show_imb
        box.new(bar_index-1, low[2], bar_index + 5, high, na, 0, bgcolor=color.from_gradient(fvg_filt_dn, 0, fvg_max_dn, color.new(chart.fg_color, 90), color.new(chart.fg_color, 70)), text="-"+str.tostring(fvg_filt_dn, format.percent), text_color=chart.fg_color)
    fvg_box2 := box.new(bar_index-1, low[2] + fvg_atr, last_bar_index, low[2], fvg_col_bear, 1, bgcolor=color.from_gradient(fvg_filt_dn, 0, fvg_max_dn, na, color.new(fvg_col_bear, 70)), text=str.tostring(fvg_filt_dn, format.percent), text_size=size.small, text_color=chart.fg_color, text_halign=text.align_right)
    fvg_boxes2.push(fvg_box2)

if barstate.islast
    for f_box in fvg_boxes1
        box.set_right(f_box, bar_index + 15)
    for f_box in fvg_boxes2
        box.set_right(f_box, bar_index + 15)

for f_box in fvg_boxes1
    if high < box.get_bottom(f_box)
        box.set_border_width(f_box, 0)
        box.set_bgcolor(f_box, color.new(chart.fg_color, 85))
        if not fvg_show_broken
            box.delete(f_box)
            fvg_boxes1.remove(fvg_boxes1.indexof(f_box))
    if low > box.get_top(f_box) and low[1] <= box.get_top(f_box) and not fvg_isBull and fvg_show_signal
        label.new(bar_index-1, low[1], "︽", color = color(na), textcolor = fvg_col_bull, style = label.style_label_up)
    for f_box1 in fvg_boxes1
        if f_box1.get_top() < f_box.get_top() and f_box1.get_top() > f_box.get_bottom()
            box.delete(f_box)
            fvg_boxes1.remove(fvg_boxes1.indexof(f_box))

for f_box in fvg_boxes2
    if low > box.get_top(f_box)
        box.set_border_width(f_box, 0)
        box.set_bgcolor(f_box, color.new(chart.fg_color, 85))
        if not fvg_show_broken
            box.delete(f_box)
            fvg_boxes2.remove(fvg_boxes2.indexof(f_box))
    if high < box.get_bottom(f_box) and high[1] >= box.get_bottom(f_box) and not fvg_isBear and fvg_show_signal
        label.new(bar_index-1, high[1], "﹀", color = color(na), textcolor = fvg_col_bear, style = label.style_label_down)
    for f_box1 in fvg_boxes2
        if f_box1.get_top() < f_box.get_top() and f_box1.get_top() > f_box.get_bottom()
            box.delete(f_box)
            fvg_boxes2.remove(fvg_boxes2.indexof(f_box))

if fvg_boxes1.size() >= fvg_box_amount
    box.delete(fvg_boxes1.shift())
if fvg_boxes2.size() >= fvg_box_amount
    box.delete(fvg_boxes2.shift())

// =============================================================================
// 3. SMART MONEY CONCEPTS (LuxAlgo)
// =============================================================================
BULLISH = +1
BEARISH = -1
BULLISH_LEG = 1
BEARISH_LEG = 0
GREEN = #089981
RED = #F23645
BLUE = #2157f3
GRAY = #878b94
MONO_BULLISH = #b2b5be
MONO_BEARISH = #5d606b
HISTORICAL = 'Historical'
PRESENT = 'Present'
COLORED = 'Colored'
MONOCHROME = 'Monochrome'
ALL = 'All'
BOS = 'BOS'
CHOCH = 'CHoCH'
TINY = size.tiny
SMALL = size.small
NORMAL = size.normal
ATR = 'Atr'
RANGE = 'Cumulative Mean Range'
CLOSE = 'Close'
HIGHLOW = 'High/Low'
SOLID = '⎯⎯⎯'
DASHED = '----'
DOTTED = '····'

SMART_GROUP = 'Smart Money Concepts'
INTERNAL_GROUP = 'Real Time Internal Structure'
SWING_GROUP = 'Real Time Swing Structure'
BLOCKS_GROUP = 'Order Blocks'
EQUAL_GROUP = 'EQH/EQL'
GAPS_GROUP = 'Fair Value Gaps'
LEVELS_GROUP = 'Highs & Lows MTF'
ZONES_GROUP = 'Premium & Discount Zones'

modeInput = input.string(HISTORICAL, 'Mode', group=SMART_GROUP, options=[HISTORICAL, PRESENT])
styleInput = input.string(COLORED, 'Style', group=SMART_GROUP, options=[COLORED, MONOCHROME])
showTrendInput = input(false, 'Color Candles', group=SMART_GROUP)

showInternalsInput = input(true, 'Show Internal Structure', group=INTERNAL_GROUP)
showInternalBullInput = input.string(ALL, 'Bullish Structure', group=INTERNAL_GROUP, inline='ibull', options=[ALL,BOS,CHOCH])
internalBullColorInput = input(GREEN, '', group=INTERNAL_GROUP, inline='ibull')
showInternalBearInput = input.string(ALL, 'Bearish Structure' , group=INTERNAL_GROUP, inline='ibear', options=[ALL,BOS,CHOCH])
internalBearColorInput = input(RED, '', group=INTERNAL_GROUP, inline='ibear')
internalFilterConfluenceInput = input(false, 'Confluence Filter', group=INTERNAL_GROUP)
internalStructureSize = input.string(TINY, 'Internal Label Size', group=INTERNAL_GROUP, options=[TINY,SMALL,NORMAL])

showStructureInput = input(true, 'Show Swing Structure', group=SWING_GROUP)
showSwingBullInput = input.string(ALL, 'Bullish Structure', group=SWING_GROUP, inline='bull', options=[ALL,BOS,CHOCH])
swingBullColorInput = input(GREEN, '', group=SWING_GROUP, inline='bull')
showSwingBearInput = input.string(ALL, 'Bearish Structure', group=SWING_GROUP, inline='bear', options=[ALL,BOS,CHOCH])
swingBearColorInput = input(RED, '', group=SWING_GROUP, inline='bear')
swingStructureSize = input.string(SMALL, 'Swing Label Size', group=SWING_GROUP, options=[TINY,SMALL,NORMAL])
showSwingsInput = input(false, 'Show Swings Points', group=SWING_GROUP, inline='swings')
swingsLengthInput = input.int(50, '', group=SWING_GROUP, minval=10, inline='swings')
showHighLowSwingsInput = input(true, 'Show Strong/Weak High/Low', group=SWING_GROUP)

showInternalOrderBlocksInput = input(true, 'Internal Order Blocks', group=BLOCKS_GROUP, inline='iob')
internalOrderBlocksSizeInput = input.int(5, '', group=BLOCKS_GROUP, minval=1, maxval=20, inline='iob')
showSwingOrderBlocksInput = input(false, 'Swing Order Blocks', group=BLOCKS_GROUP, inline='ob')
swingOrderBlocksSizeInput = input.int(5, '', group=BLOCKS_GROUP, minval=1, maxval=20, inline='ob') 
orderBlockFilterInput = input.string('Atr', 'Order Block Filter', group=BLOCKS_GROUP, options=[ATR, RANGE])
orderBlockMitigationInput = input.string(HIGHLOW, 'Order Block Mitigation', group=BLOCKS_GROUP, options=[CLOSE,HIGHLOW])
internalBullishOrderBlockColor = input.color(color.new(#3179f5, 80), 'Internal Bullish OB', group=BLOCKS_GROUP)
internalBearishOrderBlockColor = input.color(color.new(#f77c80, 80), 'Internal Bearish OB', group=BLOCKS_GROUP)
swingBullishOrderBlockColor = input.color(color.new(#1848cc, 80), 'Bullish OB', group=BLOCKS_GROUP)
swingBearishOrderBlockColor = input.color(color.new(#b22833, 80), 'Bearish OB', group=BLOCKS_GROUP)

showEqualHighsLowsInput = input(true, 'Equal High/Low', group=EQUAL_GROUP)
equalHighsLowsLengthInput = input.int(3, 'Bars Confirmation', group=EQUAL_GROUP, minval=1)
equalHighsLowsThresholdInput = input.float(0.1, 'Threshold', group=EQUAL_GROUP, minval=0, maxval=0.5, step=0.1)
equalHighsLowsSizeInput = input.string(TINY, 'Label Size', group=EQUAL_GROUP, options=[TINY,SMALL,NORMAL])

showFairValueGapsInput = input(false, 'Fair Value Gaps', group=GAPS_GROUP)
fairValueGapsThresholdInput = input(true, 'Auto Threshold', group=GAPS_GROUP)
fairValueGapsTimeframeInput = input.timeframe('', 'Timeframe', group=GAPS_GROUP)
fairValueGapsBullColorInput = input.color(color.new(#00ff68, 70), 'Bullish FVG' , group=GAPS_GROUP)
fairValueGapsBearColorInput = input.color(color.new(#ff0008, 70), 'Bearish FVG' , group=GAPS_GROUP)
fairValueGapsExtendInput = input.int(1, 'Extend FVG', group=GAPS_GROUP, minval=0)

showDailyLevelsInput = input(false, 'Daily', group=LEVELS_GROUP, inline='daily')
dailyLevelsStyleInput = input.string(SOLID, '', group=LEVELS_GROUP, inline='daily', options=[SOLID,DASHED,DOTTED])
dailyLevelsColorInput = input(BLUE, '', group=LEVELS_GROUP, inline='daily')
showWeeklyLevelsInput = input(false, 'Weekly', group=LEVELS_GROUP, inline='weekly')
weeklyLevelsStyleInput = input.string(SOLID, '', group=LEVELS_GROUP, inline='weekly', options=[SOLID,DASHED,DOTTED])
weeklyLevelsColorInput = input(BLUE, '', group=LEVELS_GROUP, inline='weekly')
showMonthlyLevelsInput = input(false, 'Monthly', group=LEVELS_GROUP, inline='monthly')
monthlyLevelsStyleInput = input.string(SOLID, '', group=LEVELS_GROUP, inline='monthly', options=[SOLID,DASHED,DOTTED])
monthlyLevelsColorInput = input(BLUE, '', group=LEVELS_GROUP, inline='monthly')

showPremiumDiscountZonesInput = input(false, 'Premium/Discount Zones', group=ZONES_GROUP)
premiumZoneColorInput = input.color(RED, 'Premium Zone', group=ZONES_GROUP)
equilibriumZoneColorInput = input.color(GRAY, 'Equilibrium Zone', group=ZONES_GROUP)
discountZoneColorInput = input.color(GREEN, 'Discount Zone', group=ZONES_GROUP)

type alerts
    bool internalBullishBOS = false
    bool internalBearishBOS = false
    bool internalBullishCHoCH = false
    bool internalBearishCHoCH = false
    bool swingBullishBOS = false
    bool swingBearishBOS = false
    bool swingBullishCHoCH = false
    bool swingBearishCHoCH = false
    bool internalBullishOrderBlock = false
    bool internalBearishOrderBlock = false
    bool swingBullishOrderBlock = false
    bool swingBearishOrderBlock = false
    bool equalHighs = false
    bool equalLows = false
    bool bullishFairValueGap = false
    bool bearishFairValueGap = false

type trailingExtremes
    float top
    float bottom
    int barTime
    int barIndex
    int lastTopTime
    int lastBottomTime

type fairValueGap
    float top
    float bottom
    int bias
    box topBox
    box bottomBox

type trend
    int bias    

type equalDisplay
    line l_ine = na
    label l_abel = na

type pivot
    float currentLevel
    float lastLevel
    bool crossed
    int barTime = time
    int barIndex = bar_index

type orderBlock
    float barHigh
    float barLow
    int barTime    
    int bias

var pivot swingHigh = pivot.new(na,na,false)
var pivot swingLow = pivot.new(na,na,false)
var pivot internalHigh = pivot.new(na,na,false)
var pivot internalLow = pivot.new(na,na,false)
var pivot equalHigh = pivot.new(na,na,false)
var pivot equalLow = pivot.new(na,na,false)
var trend swingTrend = trend.new(0)
var trend internalTrend = trend.new(0)
var equalDisplay equalHighDisplay = equalDisplay.new()
var equalDisplay equalLowDisplay = equalDisplay.new()
var array<fairValueGap> fairValueGaps = array.new<fairValueGap>()
var array<float> parsedHighs = array.new<float>()
var array<float> parsedLows = array.new<float>()
var array<float> highs = array.new<float>()
var array<float> lows = array.new<float>()
var array<int> times = array.new<int>()
var trailingExtremes trailing = trailingExtremes.new()
var array<orderBlock> swingOrderBlocks = array.new<orderBlock>()
var array<orderBlock> internalOrderBlocks = array.new<orderBlock>()
var array<box> swingOrderBlocksBoxes = array.new<box>()
var array<box> internalOrderBlocksBoxes = array.new<box>()

var swingBullishColor = styleInput == MONOCHROME ? MONO_BULLISH : swingBullColorInput
var swingBearishColor = styleInput == MONOCHROME ? MONO_BEARISH : swingBearColorInput
var fairValueGapBullishColor = styleInput == MONOCHROME ? color.new(MONO_BULLISH,70) : fairValueGapsBullColorInput
var fairValueGapBearishColor = styleInput == MONOCHROME ? color.new(MONO_BEARISH,70) : fairValueGapsBearColorInput
var premiumZoneColor = styleInput == MONOCHROME ? MONO_BEARISH : premiumZoneColorInput
var discountZoneColor = styleInput == MONOCHROME ? MONO_BULLISH : discountZoneColorInput 

varip int currentBarIndex = bar_index
varip int lastBarIndex = bar_index
alerts currentAlerts = alerts.new()
var initialTime = time

if barstate.isfirst
    if showSwingOrderBlocksInput
        for index = 1 to swingOrderBlocksSizeInput
            swingOrderBlocksBoxes.push(box.new(na,na,na,na,xloc=xloc.bar_time,extend=extend.right))
    if showInternalOrderBlocksInput
        for index = 1 to internalOrderBlocksSizeInput
            internalOrderBlocksBoxes.push(box.new(na,na,na,na,xloc=xloc.bar_time,extend=extend.right))

bearishOrderBlockMitigationSource = orderBlockMitigationInput == CLOSE ? close : high
bullishOrderBlockMitigationSource = orderBlockMitigationInput == CLOSE ? close : low
atrMeasure = ta.atr(200)
volatilityMeasure = orderBlockFilterInput == ATR ? atrMeasure : ta.cum(ta.tr)/bar_index
highVolatilityBar = (high - low) >= (2 * volatilityMeasure)
parsedHigh = highVolatilityBar ? low : high
parsedLow = highVolatilityBar ? high : low

parsedHighs.push(parsedHigh)
parsedLows.push(parsedLow)
highs.push(high)
lows.push(low)
times.push(time)

leg(int size) =>
    var leg = 0    
    newLegHigh = high[size] > ta.highest(size)
    newLegLow = low[size] < ta.lowest(size)
    if newLegHigh
        leg := BEARISH_LEG
    else if newLegLow
        leg := BULLISH_LEG
    leg

startOfNewLeg(int leg) => ta.change(leg) != 0
startOfBearishLeg(int leg) => ta.change(leg) == -1
startOfBullishLeg(int leg) => ta.change(leg) == +1

drawLabel(int labelTime, float labelPrice, string tag, color labelColor, string labelStyle) =>    
    var label l_abel = na
    if modeInput == PRESENT
        l_abel.delete()
    l_abel := label.new(chart.point.new(labelTime,na,labelPrice),tag,xloc.bar_time,color=color(na),textcolor=labelColor,style=labelStyle,size=size.small)

drawEqualHighLow(pivot p_ivot, float level, int size, bool equalHigh) =>
    equalDisplay e_qualDisplay = equalHigh ? equalHighDisplay : equalLowDisplay
    string tag = 'EQL'
    color equalColor = swingBullishColor
    string labelStyle = label.style_label_up
    if equalHigh
        tag := 'EQH'
        equalColor := swingBearishColor
        labelStyle := label.style_label_down
    if modeInput == PRESENT
        line.delete(e_qualDisplay.l_ine)
        label.delete(e_qualDisplay.l_abel)
    e_qualDisplay.l_ine := line.new(chart.point.new(p_ivot.barTime,na,p_ivot.currentLevel), chart.point.new(time[size],na,level), xloc=xloc.bar_time, color=equalColor, style=line.style_dotted)
    labelPosition = math.round(0.5*(p_ivot.barIndex + bar_index - size))
    e_qualDisplay.l_abel := label.new(chart.point.new(na,labelPosition,level), tag, xloc.bar_index, color=color(na), textcolor=equalColor, style=labelStyle, size=equalHighsLowsSizeInput)

getCurrentStructure(int size,bool equalHighLow = false, bool internal = false) =>        
    currentLeg = leg(size)
    newPivot = startOfNewLeg(currentLeg)
    pivotLow = startOfBullishLeg(currentLeg)
    pivotHigh = startOfBearishLeg(currentLeg)
    if newPivot
        if pivotLow
            pivot p_ivot = equalHighLow ? equalLow : internal ? internalLow : swingLow    
            if equalHighLow and math.abs(p_ivot.currentLevel - low[size]) < equalHighsLowsThresholdInput * atrMeasure                
                drawEqualHighLow(p_ivot, low[size], size, false)
                currentAlerts.equalLows := true
            p_ivot.lastLevel := p_ivot.currentLevel
            p_ivot.currentLevel := low[size]
            p_ivot.crossed := false
            p_ivot.barTime := time[size]
            p_ivot.barIndex := bar_index[size]
            if not equalHighLow and not internal
                trailing.bottom := p_ivot.currentLevel
                trailing.barTime := p_ivot.barTime
                trailing.barIndex := p_ivot.barIndex
                trailing.lastBottomTime := p_ivot.barTime
            if showSwingsInput and not internal and not equalHighLow
                drawLabel(time[size], p_ivot.currentLevel, p_ivot.currentLevel < p_ivot.lastLevel ? 'LL' : 'HL', swingBullishColor, label.style_label_up)            
        else
            pivot p_ivot = equalHighLow ? equalHigh : internal ? internalHigh : swingHigh
            if equalHighLow and math.abs(p_ivot.currentLevel - high[size]) < equalHighsLowsThresholdInput * atrMeasure
                drawEqualHighLow(p_ivot,high[size],size,true)
                currentAlerts.equalHighs := true               
            p_ivot.lastLevel := p_ivot.currentLevel
            p_ivot.currentLevel := high[size]
            p_ivot.crossed := false
            p_ivot.barTime := time[size]
            p_ivot.barIndex := bar_index[size]
            if not equalHighLow and not internal
                trailing.top := p_ivot.currentLevel
                trailing.barTime := p_ivot.barTime
                trailing.barIndex := p_ivot.barIndex
                trailing.lastTopTime := p_ivot.barTime
            if showSwingsInput and not internal and not equalHighLow
                drawLabel(time[size], p_ivot.currentLevel, p_ivot.currentLevel > p_ivot.lastLevel ? 'HH' : 'LH', swingBearishColor, label.style_label_down)
                
drawStructure(pivot p_ivot, string tag, color structureColor, string lineStyle, string labelStyle, string labelSize) =>    
    var line l_ine = line.new(na,na,na,na,xloc=xloc.bar_time)
    var label l_abel = label.new(na,na)
    if modeInput == PRESENT
        l_ine.delete()
        l_abel.delete()
    l_ine := line.new(chart.point.new(p_ivot.barTime,na,p_ivot.currentLevel), chart.point.new(time,na,p_ivot.currentLevel), xloc.bar_time, color=structureColor, style=lineStyle)
    l_abel := label.new(chart.point.new(na,math.round(0.5*(p_ivot.barIndex+bar_index)),p_ivot.currentLevel), tag, xloc.bar_index, color=color(na), textcolor=structureColor, style=labelStyle, size=labelSize)

deleteOrderBlocks(bool internal = false) =>
    array<orderBlock> orderBlocks = internal ? internalOrderBlocks : swingOrderBlocks
    for [index,eachOrderBlock] in orderBlocks
        bool crossedOderBlock = false
        if bearishOrderBlockMitigationSource > eachOrderBlock.barHigh and eachOrderBlock.bias == BEARISH
            crossedOderBlock := true
            if internal
                currentAlerts.internalBearishOrderBlock := true
            else
                currentAlerts.swingBearishOrderBlock := true
        else if bullishOrderBlockMitigationSource < eachOrderBlock.barLow and eachOrderBlock.bias == BULLISH
            crossedOderBlock := true
            if internal
                currentAlerts.internalBullishOrderBlock := true
            else
                currentAlerts.swingBullishOrderBlock := true
        if crossedOderBlock                    
            orderBlocks.remove(index)            

storeOrdeBlock(pivot p_ivot,bool internal = false,int bias) =>
    if (not internal and showSwingOrderBlocksInput) or (internal and showInternalOrderBlocksInput)
        array<float> a_rray = na
        int parsedIndex = na
        if bias == BEARISH
            a_rray := parsedHighs.slice(p_ivot.barIndex,bar_index)
            parsedIndex := p_ivot.barIndex + a_rray.indexof(a_rray.max())  
        else
            a_rray := parsedLows.slice(p_ivot.barIndex,bar_index)
            parsedIndex := p_ivot.barIndex + a_rray.indexof(a_rray.min())                        
        orderBlock o_rderBlock = orderBlock.new(parsedHighs.get(parsedIndex), parsedLows.get(parsedIndex), times.get(parsedIndex),bias)
        array<orderBlock> orderBlocks = internal ? internalOrderBlocks : swingOrderBlocks
        if orderBlocks.size() >= 100
            orderBlocks.pop()
        orderBlocks.unshift(o_rderBlock)

drawOrderBlocks(bool internal = false) =>        
    array<orderBlock> orderBlocks = internal ? internalOrderBlocks : swingOrderBlocks
    orderBlocksSize = orderBlocks.size()
    if orderBlocksSize > 0        
        maxOrderBlocks = internal ? internalOrderBlocksSizeInput : swingOrderBlocksSizeInput
        array<orderBlock> parsedOrdeBlocks = orderBlocks.slice(0, math.min(maxOrderBlocks,orderBlocksSize))
        array<box> b_oxes = internal ? internalOrderBlocksBoxes : swingOrderBlocksBoxes        
        for [index,eachOrderBlock] in parsedOrdeBlocks
            orderBlockColor = styleInput == MONOCHROME ? (eachOrderBlock.bias == BEARISH ? color.new(MONO_BEARISH,80) : color.new(MONO_BULLISH,80)) : internal ? (eachOrderBlock.bias == BEARISH ? internalBearishOrderBlockColor : internalBullishOrderBlockColor) : (eachOrderBlock.bias == BEARISH ? swingBearishOrderBlockColor : swingBullishOrderBlockColor)
            box b_ox = b_oxes.get(index)
            b_ox.set_top_left_point(chart.point.new(eachOrderBlock.barTime,na,eachOrderBlock.barHigh))
            b_ox.set_bottom_right_point(chart.point.new(last_bar_time,na,eachOrderBlock.barLow))        
            b_ox.set_border_color(internal ? na : orderBlockColor)
            b_ox.set_bgcolor(orderBlockColor)

displayStructure(bool internal = false) =>
    var bullishBar = true
    var bearishBar = true
    if internalFilterConfluenceInput
        bullishBar := high - math.max(close, open) > math.min(close, open - low)
        bearishBar := high - math.max(close, open) < math.min(close, open - low)
    pivot p_ivot = internal ? internalHigh : swingHigh
    trend t_rend = internal ? internalTrend : swingTrend
    lineStyle = internal ? line.style_dashed : line.style_solid
    labelSize = internal ? internalStructureSize : swingStructureSize
    extraCondition = internal ? internalHigh.currentLevel != swingHigh.currentLevel and bullishBar : true
    bullishColor = styleInput == MONOCHROME ? MONO_BULLISH : internal ? internalBullColorInput : swingBullColorInput
    if ta.crossover(close,p_ivot.currentLevel) and not p_ivot.crossed and extraCondition
        string tag = t_rend.bias == BEARISH ? CHOCH : BOS
        if internal
            currentAlerts.internalBullishCHoCH := tag == CHOCH
            currentAlerts.internalBullishBOS := tag == BOS
        else
            currentAlerts.swingBullishCHoCH := tag == CHOCH
            currentAlerts.swingBullishBOS := tag == BOS
        p_ivot.crossed := true
        t_rend.bias := BULLISH
        displayCondition = internal ? showInternalsInput and (showInternalBullInput == ALL or (showInternalBullInput == BOS and tag != CHOCH) or (showInternalBullInput == CHOCH and tag == CHOCH)) : showStructureInput and (showSwingBullInput == ALL or (showSwingBullInput == BOS and tag != CHOCH) or (showSwingBullInput == CHOCH and tag == CHOCH))
        if displayCondition                        
            drawStructure(p_ivot,tag,bullishColor,lineStyle,label.style_label_down,labelSize)
        if (internal and showInternalOrderBlocksInput) or (not internal and showSwingOrderBlocksInput)
            storeOrdeBlock(p_ivot,internal,BULLISH)
    p_ivot := internal ? internalLow : swingLow    
    extraCondition := internal ? internalLow.currentLevel != swingLow.currentLevel and bearishBar : true
    bearishColor = styleInput == MONOCHROME ? MONO_BEARISH : internal ? internalBearColorInput : swingBearColorInput
    if ta.crossunder(close,p_ivot.currentLevel) and not p_ivot.crossed and extraCondition
        string tag = t_rend.bias == BULLISH ? CHOCH : BOS
        if internal
            currentAlerts.internalBearishCHoCH := tag == CHOCH
            currentAlerts.internalBearishBOS := tag == BOS
        else
            currentAlerts.swingBearishCHoCH := tag == CHOCH
            currentAlerts.swingBearishBOS := tag == BOS
        p_ivot.crossed := true
        t_rend.bias := BEARISH
        displayCondition = internal ? showInternalsInput and (showInternalBearInput == ALL or (showInternalBearInput == BOS and tag != CHOCH) or (showInternalBearInput == CHOCH and tag == CHOCH)) : showStructureInput and (showSwingBearInput == ALL or (showSwingBearInput == BOS and tag != CHOCH) or (showSwingBearInput == CHOCH and tag == CHOCH))
        if displayCondition                        
            drawStructure(p_ivot,tag,bearishColor,lineStyle,label.style_label_up,labelSize)
        if (internal and showInternalOrderBlocksInput) or (not internal and showSwingOrderBlocksInput)
            storeOrdeBlock(p_ivot,internal,BEARISH)

fairValueGapBox(leftTime,rightTime,topPrice,bottomPrice,boxColor) => box.new(chart.point.new(leftTime,na,topPrice),chart.point.new(rightTime + fairValueGapsExtendInput * (time-time[1]),na,bottomPrice), xloc=xloc.bar_time, border_color=boxColor, bgcolor=boxColor)

deleteFairValueGaps() =>
    for [index,eachFairValueGap] in fairValueGaps
        if (low < eachFairValueGap.bottom and eachFairValueGap.bias == BULLISH) or (high > eachFairValueGap.top and eachFairValueGap.bias == BEARISH)
            eachFairValueGap.topBox.delete()
            eachFairValueGap.bottomBox.delete()
            fairValueGaps.remove(index)
    
drawFairValueGaps() => 
    [lastClose, lastOpen, lastTime, currentHigh, currentLow, currentTime, last2High, last2Low] = request.security(syminfo.tickerid, fairValueGapsTimeframeInput, [close[1], open[1], time[1], high[0], low[0], time[0], high[2], low[2]],lookahead=barmerge.lookahead_on)
    barDeltaPercent = (lastClose - lastOpen) / (lastOpen * 100)
    newTimeframe = timeframe.change(fairValueGapsTimeframeInput)
    threshold = fairValueGapsThresholdInput ? ta.cum(math.abs(newTimeframe ? barDeltaPercent : 0)) / bar_index * 2 : 0
    bullishFairValueGap = currentLow > last2High and lastClose > last2High and barDeltaPercent > threshold and newTimeframe
    bearishFairValueGap = currentHigh < last2Low and lastClose < last2Low and -barDeltaPercent > threshold and newTimeframe
    if bullishFairValueGap
        currentAlerts.bullishFairValueGap := true
        fairValueGaps.unshift(fairValueGap.new(currentLow,last2High,BULLISH,fairValueGapBox(lastTime,currentTime,currentLow,math.avg(currentLow,last2High),fairValueGapBullishColor),fairValueGapBox(lastTime,currentTime,math.avg(currentLow,last2High),last2High,fairValueGapBullishColor)))
    if bearishFairValueGap
        currentAlerts.bearishFairValueGap := true
        fairValueGaps.unshift(fairValueGap.new(currentHigh,last2Low,BEARISH,fairValueGapBox(lastTime,currentTime,currentHigh,math.avg(currentHigh,last2Low),fairValueGapBearishColor),fairValueGapBox(lastTime,currentTime,math.avg(currentHigh,last2Low),last2Low,fairValueGapBearishColor)))

getStyle(string style) =>
    switch style
        SOLID => line.style_solid
        DASHED => line.style_dashed
        DOTTED => line.style_dotted

drawLevels(string timeframe, bool sameTimeframe, string style, color levelColor) =>
    [topLevel, bottomLevel, leftTime, rightTime] = request.security(syminfo.tickerid, timeframe, [high[1], low[1], time[1], time],lookahead=barmerge.lookahead_on)
    float parsedTop = sameTimeframe ? high : topLevel
    float parsedBottom = sameTimeframe ? low : bottomLevel    
    int parsedLeftTime = sameTimeframe ? time : leftTime
    int parsedRightTime = sameTimeframe ? time : rightTime
    int parsedTopTime = time
    int parsedBottomTime = time
    if not sameTimeframe
        int leftIndex = times.binary_search_rightmost(parsedLeftTime)
        int rightIndex = times.binary_search_rightmost(parsedRightTime)
        array<int> timeArray = times.slice(leftIndex,rightIndex)
        array<float> topArray = highs.slice(leftIndex,rightIndex)
        array<float> bottomArray = lows.slice(leftIndex,rightIndex)
        parsedTopTime := timeArray.size() > 0 ? timeArray.get(topArray.indexof(topArray.max())) : initialTime
        parsedBottomTime := timeArray.size() > 0 ? timeArray.get(bottomArray.indexof(bottomArray.min())) : initialTime
    var line topLine = line.new(na, na, na, na, xloc=xloc.bar_time, color=levelColor, style=getStyle(style))
    var line bottomLine = line.new(na, na, na, na, xloc=xloc.bar_time, color=levelColor, style=getStyle(style))
    var label topLabel = label.new(na, na, xloc=xloc.bar_time, text=str.format('P{0}H',timeframe), color=color(na), textcolor=levelColor, size=size.small, style=label.style_label_left)
    var label bottomLabel = label.new(na, na, xloc=xloc.bar_time, text=str.format('P{0}L',timeframe), color=color(na), textcolor=levelColor, size=size.small, style=label.style_label_left)
    topLine.set_first_point(chart.point.new(parsedTopTime,na,parsedTop))
    topLine.set_second_point(chart.point.new(last_bar_time + 20 * (time-time[1]),na,parsedTop))   
    topLabel.set_point(chart.point.new(last_bar_time + 20 * (time-time[1]),na,parsedTop))
    bottomLine.set_first_point(chart.point.new(parsedBottomTime,na,parsedBottom))    
    bottomLine.set_second_point(chart.point.new(last_bar_time + 20 * (time-time[1]),na,parsedBottom))
    bottomLabel.set_point(chart.point.new(last_bar_time + 20 * (time-time[1]),na,parsedBottom))

higherTimeframe(string timeframe) => timeframe.in_seconds() > timeframe.in_seconds(timeframe)

updateTrailingExtremes() =>
    trailing.top := math.max(high,trailing.top)
    trailing.lastTopTime := trailing.top == high ? time : trailing.lastTopTime
    trailing.bottom := math.min(low,trailing.bottom)
    trailing.lastBottomTime := trailing.bottom == low ? time : trailing.lastBottomTime

drawHighLowSwings() =>
    var line topLine = line.new(na, na, na, na, color = swingBearishColor, xloc = xloc.bar_time)
    var line bottomLine = line.new(na, na, na, na, color = swingBullishColor, xloc = xloc.bar_time)
    var label topLabel = label.new(na, na, color=color(na), textcolor=swingBearishColor, xloc=xloc.bar_time, style=label.style_label_down, size=size.tiny)
    var label bottomLabel = label.new(na, na, color=color(na), textcolor=swingBullishColor, xloc=xloc.bar_time, style=label.style_label_up, size=size.tiny)
    rightTimeBar = last_bar_time + 20 * (time - time[1])
    topLine.set_first_point(chart.point.new(trailing.lastTopTime, na, trailing.top))
    topLine.set_second_point(chart.point.new(rightTimeBar, na, trailing.top))
    topLabel.set_point(chart.point.new(rightTimeBar, na, trailing.top))
    topLabel.set_text(swingTrend.bias == BEARISH ? 'Strong High' : 'Weak High')
    bottomLine.set_first_point(chart.point.new(trailing.lastBottomTime, na, trailing.bottom))
    bottomLine.set_second_point(chart.point.new(rightTimeBar, na, trailing.bottom))
    bottomLabel.set_point(chart.point.new(rightTimeBar, na, trailing.bottom))
    bottomLabel.set_text(swingTrend.bias == BULLISH ? 'Strong Low' : 'Weak Low')

drawZone(float labelLevel, int labelIndex, float top, float bottom, string tag, color zoneColor, string style) =>
    var label l_abel = label.new(na,na,text=tag, color=color(na),textcolor=zoneColor, style=style, size=size.small)
    var box b_ox = box.new(na,na,na,na,bgcolor=color.new(zoneColor,80),border_color=color(na), xloc=xloc.bar_time)
    b_ox.set_top_left_point(chart.point.new(trailing.barTime,na,top))
    b_ox.set_bottom_right_point(chart.point.new(last_bar_time,na,bottom))
    l_abel.set_point(chart.point.new(na,labelIndex,labelLevel))

drawPremiumDiscountZones() =>
    drawZone(trailing.top, math.round(0.5*(trailing.barIndex + last_bar_index)), trailing.top, 0.95*trailing.top + 0.05*trailing.bottom, 'Premium', premiumZoneColor, label.style_label_down)
    equilibriumLevel = math.avg(trailing.top, trailing.bottom)
    drawZone(equilibriumLevel, last_bar_index, 0.525*trailing.top + 0.475*trailing.bottom, 0.525*trailing.bottom + 0.475*trailing.top, 'Equilibrium', equilibriumZoneColorInput, label.style_label_left)
    drawZone(trailing.bottom, math.round(0.5*(trailing.barIndex + last_bar_index)), 0.95*trailing.bottom + 0.05*trailing.top, trailing.bottom, 'Discount', discountZoneColor, label.style_label_up)

parsedOpen = showTrendInput ? open : na
candleColor = internalTrend.bias == BULLISH ? swingBullishColor : swingBearishColor
plotcandle(parsedOpen,high,low,close,color=candleColor, wickcolor=candleColor, bordercolor=candleColor)

if showHighLowSwingsInput or showPremiumDiscountZonesInput
    updateTrailingExtremes()
    if showHighLowSwingsInput
        drawHighLowSwings()
    if showPremiumDiscountZonesInput
        drawPremiumDiscountZones()

if showFairValueGapsInput
    deleteFairValueGaps()

getCurrentStructure(swingsLengthInput,false)
getCurrentStructure(5,false,true)

if showEqualHighsLowsInput
    getCurrentStructure(equalHighsLowsLengthInput,true)

if showInternalsInput or showInternalOrderBlocksInput or showTrendInput
    displayStructure(true)

if showStructureInput or showSwingOrderBlocksInput or showHighLowSwingsInput
    displayStructure()

if showInternalOrderBlocksInput
    deleteOrderBlocks(true)

if showSwingOrderBlocksInput
    deleteOrderBlocks()

if showFairValueGapsInput
    drawFairValueGaps()

if barstate.islastconfirmedhistory or barstate.islast
    if showInternalOrderBlocksInput        
        drawOrderBlocks(true)
    if showSwingOrderBlocksInput        
        drawOrderBlocks()

lastBarIndex := currentBarIndex
currentBarIndex := bar_index
newBar = currentBarIndex != lastBarIndex

if barstate.islastconfirmedhistory or (barstate.isrealtime and newBar)
    if showDailyLevelsInput and not higherTimeframe('D')
        drawLevels('D',timeframe.isdaily,dailyLevelsStyleInput,dailyLevelsColorInput)
    if showWeeklyLevelsInput and not higherTimeframe('W')
        drawLevels('W',timeframe.isweekly,weeklyLevelsStyleInput,weeklyLevelsColorInput)
    if showMonthlyLevelsInput and not higherTimeframe('M')
        drawLevels('M',timeframe.ismonthly,monthlyLevelsStyleInput,monthlyLevelsColorInput)

alertcondition(currentAlerts.internalBullishBOS, 'Internal Bullish BOS', 'Internal Bullish BOS formed')
alertcondition(currentAlerts.internalBullishCHoCH, 'Internal Bullish CHoCH', 'Internal Bullish CHoCH formed')
alertcondition(currentAlerts.internalBearishBOS, 'Internal Bearish BOS', 'Internal Bearish BOS formed')
alertcondition(currentAlerts.internalBearishCHoCH, 'Internal Bearish CHoCH', 'Internal Bearish CHoCH formed')
alertcondition(currentAlerts.swingBullishBOS, 'Bullish BOS', 'Internal Bullish BOS formed')
alertcondition(currentAlerts.swingBullishCHoCH, 'Bullish CHoCH', 'Internal Bullish CHoCH formed')
alertcondition(currentAlerts.swingBearishBOS, 'Bearish BOS', 'Bearish BOS formed')
alertcondition(currentAlerts.swingBearishCHoCH, 'Bearish CHoCH', 'Bearish CHoCH formed')
alertcondition(currentAlerts.internalBullishOrderBlock, 'Bullish Internal OB Breakout', 'Price broke bullish internal OB')
alertcondition(currentAlerts.internalBearishOrderBlock, 'Bearish Internal OB Breakout', 'Price broke bearish internal OB')
alertcondition(currentAlerts.swingBullishOrderBlock, 'Bullish Swing OB Breakout', 'Price broke bullish swing OB')
alertcondition(currentAlerts.swingBearishOrderBlock, 'Bearish Swing OB Breakout', 'Price broke bearish swing OB')
alertcondition(currentAlerts.equalHighs, 'Equal Highs', 'Equal highs detected')
alertcondition(currentAlerts.equalLows, 'Equal Lows', 'Equal lows detected')
alertcondition(currentAlerts.bullishFairValueGap, 'Bullish FVG', 'Bullish FVG formed')
alertcondition(currentAlerts.bearishFairValueGap, 'Bearish FVG', 'Bearish FVG formed')
