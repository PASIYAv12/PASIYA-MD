// ./commands/signals.js
const axios = require("axios")
const fs = require("fs")
const path = require("path")

const statePath = path.join(__dirname, "../signals_state.json")
function loadState() {
  if (!fs.existsSync(statePath)) return { date: "", count: 0 }
  return JSON.parse(fs.readFileSync(statePath))
}
function saveState(s) { fs.writeFileSync(statePath, JSON.stringify(s, null, 2)) }

async function getKlines(symbol, interval="15m", limit=200) {
  const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`
  const { data } = await axios.get(url)
  // map to OHLC array of numbers
  return data.map(k => ({
    time: k[0],
    open: +k[1], high: +k[2], low: +k[3], close: +k[4]
  }))
}

// helpers
function ema(values, p) {
  const k = 2 / (p + 1)
  let emaArr = []
  let prev = values.slice(0, p).reduce((a,b)=>a+b,0)/p
  emaArr[p-1] = prev
  for (let i=p; i<values.length; i++){
    prev = values[i]*k + prev*(1-k)
    emaArr[i] = prev
  }
  return emaArr
}
function rsi(closes, period=14) {
  let gains = [], losses = []
  for (let i=1;i<closes.length;i++){
    const ch = closes[i]-closes[i-1]
    gains.push(Math.max(ch,0))
    losses.push(Math.max(-ch,0))
  }
  let avgG = gains.slice(0,period).reduce((a,b)=>a+b,0)/period
  let avgL = losses.slice(0,period).reduce((a,b)=>a+b,0)/period
  let out = new Array(closes.length).fill(null)
  out[period] = 100 - (100/(1+(avgG/(avgL||1e-9))))
  for (let i=period+1;i<closes.length;i++){
    avgG = (avgG*(period-1)+gains[i-1]) / period
    avgL = (avgL*(period-1)+losses[i-1]) / period
    out[i] = 100 - (100/(1+(avgG/(avgL||1e-9))))
  }
  return out
}
function atr(data, period=14) {
  let trs = []
  for (let i=0;i<data.length;i++){
    if (i===0){ trs.push(data[i].high - data[i].low); continue }
    const h = data[i].high, l = data[i].low, pc = data[i-1].close
    trs.push(Math.max(h-l, Math.abs(h-pc), Math.abs(l-pc)))
  }
  let out = new Array(data.length).fill(null)
  let avg = trs.slice(0,period).reduce((a,b)=>a+b,0)/period
  out[period] = avg
  for (let i=period+1;i<trs.length;i++){
    avg = (avg*(period-1) + trs[i]) / period
    out[i] = avg
  }
  return out
}

function buildSignal(symbol, side, price, atrVal, riskMulSL=1.5, rr=2.0) {
  const sl = side==="LONG" ? +(price - atrVal*riskMulSL).toFixed(2) : +(price + atrVal*riskMulSL).toFixed(2)
  const tp = side==="LONG" ? +(price + (price-sl)*rr).toFixed(2) : +(price - (sl-price)*rr).toFixed(2)
  return { symbol, side, entry:+price.toFixed(2), sl, tp, rr }
}

async function scanSymbols(symbols) {
  let picks = []
  for (const s of symbols) {
    const kl = await getKlines(s, "15m", 200)
    const closes = kl.map(k=>k.close)
    const ema20 = ema(closes, 20)
    const ema50 = ema(closes, 50)
    const r = rsi(closes, 14)
    const a = atr(kl, 14)

    const i = closes.length - 1
    const c = closes[i]
    const e20 = ema20[i], e50 = ema50[i]
    const rnow = r[i]
    const atrNow = a[i]

    if (!e20 || !e50 || !rnow || !atrNow) continue

    // LONG setup
    if (e20 > e50 && rnow >= 45 && rnow <= 65 && c > e20) {
      picks.push({ score: (e20-e50)/c, ...buildSignal(s,"LONG",c,atrNow) })
      continue
    }
    // SHORT setup
    if (e20 < e50 && rnow >= 35 && rnow <= 55 && c < e20) {
      picks.push({ score: (e50-e20)/c, ...buildSignal(s,"SHORT",c,atrNow) })
      continue
    }
  }
  // sort by score desc (strength)
  picks.sort((a,b)=>b.score-a.score)
  return picks
}

function formatMessage(sig) {
  return `🚨 *PASIYA-MD Binance Signal*  
${sig.side} *${sig.symbol}*  
🎯 Entry: ${sig.entry}  
🛑 SL: ${sig.sl}  
🎁 TP: ${sig.tp}  (RR ${sig.rr}x)

⏱ Timeframe: 15m | Indicators: EMA20/50, RSI14, ATR14
⚠️ Risk-managed educational signal.`
}

async function generateSignals(maxCount=4) {
  const symbols = ["BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","SOLUSDT"]
  const state = loadState()
  const today = new Date().toISOString().slice(0,10) // UTC date

  // reset daily counter
  if (state.date !== today) { state.date = today; state.count = 0; saveState(state) }

  if (state.count >= maxCount) return [] // already sent today

  const picks = await scanSymbols(symbols)
  const available = Math.min(maxCount - state.count, picks.length)
  const chosen = picks.slice(0, available)

  state.count += chosen.length
  saveState(state)

  const msgs = chosen.map(formatMessage)
  return msgs
}

module.exports = { generateSignals }
