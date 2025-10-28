from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/panel", response_class=HTMLResponse)
async def panel():
    # HTML served directly to keep it simple; uses Tailwind + Alpine via CDN
    return HTMLResponse(PANEL_HTML)


PANEL_HTML = r"""
<!doctype html>
<html lang="en" x-data="panelApp()" x-init="init()" :class="theme">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Market Scanner - Command Center</title>
  <script src="/static/vendor/alpinejs.min.js" defer></script>
  <script src="/static/vendor/axios.min.js"></script>
  <script src="/static/vendor/tailwind.min.js"></script>
  
  
  <style>
    :root { --bg:#050816; --surface:#0c1224; --tray:#0f172a; --ink:#cbd5e1; --muted:#64748b; --accent:#22d3ee; --danger:#f87171; --success:#34d399; --warn:#facc15; }
    html,body{height:100%; background:var(--bg); color:var(--ink); font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial;}
    body{margin:0;}
    .glass{background:rgba(15,23,42,.7); backdrop-filter:blur(14px); border:1px solid rgba(148,163,184,.16);}
    .card{background:rgba(17,25,40,.72); border:1px solid rgba(148,163,184,.12); border-radius:18px; backdrop-filter:blur(18px); box-shadow:0 20px 36px rgba(2,6,23,.55);}
    .panel{background:rgba(10,17,33,.88); border:1px solid rgba(148,163,184,.12); border-radius:24px;}
    .spot-input::placeholder{color:rgba(148,163,184,.5);}
    .scrollbar::-webkit-scrollbar{width:10px; height:10px}
    .scrollbar::-webkit-scrollbar-thumb{background:rgba(30,41,59,.85); border-radius:999px}
    .progress{height:6px; border-radius:999px; background:rgba(148,163,184,.2); overflow:hidden;}
    .progress span{display:block; height:100%; background:linear-gradient(90deg,#22d3ee,#6366f1);}
    .badge{display:inline-flex; align-items:center; gap:6px; padding:0 12px; border-radius:999px; font-size:12px; letter-spacing:.1em; text-transform:uppercase;}
    .badge-live{background:rgba(52,211,153,.18); color:#34d399; border:1px solid rgba(52,211,153,.4);}
    .badge-error{background:rgba(248,113,113,.18); color:#fb7185; border:1px solid rgba(248,113,113,.4);}
    @keyframes pulse{0%{transform:scale(.8); opacity:.6;}70%{transform:scale(1.4); opacity:0;}100%{transform:scale(.8); opacity:0;}}
    .pulse::after{content:""; position:absolute; inset:-8px; border-radius:999px; border:2px solid rgba(34,211,238,.35); animation:pulse 2s infinite; opacity:0;}
    [x-cloak]{display:none!important;}
  </style>
</head>
<body class="min-h-full flex flex-col">
  <header class="glass sticky top-0 z-40 border-b border-slate-800/60">
    <div class="px-6 py-4 flex flex-wrap items-center gap-4">
      <div class="flex items-center gap-4">
        <div class="relative w-12 h-12 rounded-2xl bg-cyan-500/15 border border-cyan-300/30 flex items-center justify-center text-cyan-200 font-semibold text-lg pulse">MS</div>
        <div>
          <p class="uppercase text-[11px] tracking-[0.42em] text-slate-500">Market Scanner</p>
          <h1 class="text-[1.5rem] font-extrabold tracking-tight">Command Center</h1>
          <p class="text-xs text-slate-500" x-text="subTitle()"></p>
        </div>
      </div>
      <div class="ml-auto flex flex-wrap items-center gap-3">
        <div class="relative badge" :class="connected ? 'badge-live' : 'badge-error'">
          <span class="w-2 h-2 rounded-full" :class="connected ? 'bg-emerald-400 animate-ping' : 'bg-rose-400'"></span>
          <span x-text="connected ? 'Live' : 'Error'"></span>
        </div>
        <div class="text-xs text-slate-400">Updated <span x-text="lastUpdated ? timeAgo(lastUpdated) : 'Waiting...'"></span></div>
        <div class="text-xs text-slate-400">Latency <span x-text="latency ? latency + 'ms' : '-' "></span></div>
        <div class="relative hidden md:block">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21 21-4.35-4.35"/><circle cx="11" cy="11" r="6"/></svg>
          <input class="spot-input w-64 pl-10 pr-4 py-2 rounded-xl bg-slate-900/70 border border-slate-700/60 text-sm focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30" x-model="spot" @keydown.enter.prevent="fetchSpotlight()" placeholder="Spotlight: BTC/USDT:USDT">
        </div>
        <button class="px-3 py-2 rounded-xl bg-slate-900/70 border border-slate-700/60 text-sm hover:border-cyan-300/60" @click="openSettings=true">⚙ Settings</button>
        <button class="px-3 py-2 rounded-xl bg-cyan-500/20 border border-cyan-300/40 text-sm text-cyan-100 font-medium hover:bg-cyan-500/30" @click="manualRefresh()">Refresh</button>
      </div>
    </div>
    <div class="px-6 pb-4">
      <div class="progress"><span :style="'width:' + refreshProgress + '%'" aria-hidden="true"></span></div>
      <p class="text-[11px] text-slate-500 mt-1 tracking-[0.3em] uppercase">Auto refresh in <span x-text="countdown"></span></p>
    </div>
  </header>

  <div class="flex-1 flex flex-col xl:flex-row overflow-hidden">
    <main class="flex-1 px-6 py-6 overflow-y-auto scrollbar space-y-6">
      <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <article class="card p-4 flex flex-col gap-3">
          <p class="text-xs text-slate-400 uppercase tracking-[0.28em]">Pulse</p>
          <p class="text-2xl font-semibold" x-text="rows.length || '-' "></p>
          <p class="text-xs text-slate-500">Markets tracked right now</p>
        </article>
        <article class="card p-4 flex flex-col gap-3">
          <p class="text-xs text-slate-400 uppercase tracking-[0.28em]">Profile</p>
          <p class="text-lg font-semibold" x-text="settings.profile"></p>
          <p class="text-xs text-slate-500">Top <span x-text="settings.top"></span> | Notional <span x-text="settings.notional"></span></p>
        </article>
        <article class="card p-4 flex flex-col gap-3">
          <p class="text-xs text-slate-400 uppercase tracking-[0.28em]">Risk Guard</p>
          <p class="text-lg font-semibold" x-text="avgManip()"></p>
          <p class="text-xs text-slate-500">Minimum manipulation threshold <span x-text="settings.minManip + '%'">0%</span></p>
        </article>
      </section>

      <section class="card overflow-hidden">
        <div class="flex flex-wrap items-center gap-3 px-5 py-4 border-b border-slate-800/60">
          <div>
            <h2 class="text-lg font-semibold">Live rankings</h2>
            <p class="text-xs text-slate-500">Refreshes every <span x-text="refreshInterval/1000"></span>s | click a row to spotlight</p>
          </div>
          <div class="ml-auto flex flex-wrap gap-2 text-xs">
            <button class="px-3 py-1 rounded-lg border border-slate-800/70" :class="quickFilters.liq ? 'bg-emerald-500/10 border-emerald-400/40 text-emerald-300' : 'text-slate-400 hover:text-slate-200'" @click="toggleQuick('liq')">Liquidity</button>
            <button class="px-3 py-1 rounded-lg border border-slate-800/70" :class="quickFilters.mom ? 'bg-sky-500/10 border-sky-400/40 text-sky-200' : 'text-slate-400 hover:text-slate-200'" @click="toggleQuick('mom')">Momentum</button>
            <button class="px-3 py-1 rounded-lg border border-slate-800/70" :class="quickFilters.safe ? 'bg-amber-500/10 border-amber-400/40 text-amber-200' : 'text-slate-400 hover:text-slate-200'" @click="toggleQuick('safe')">Low spread</button>
          </div>
        </div>
        <div class="grid grid-cols-12 text-[11px] uppercase tracking-[0.22em] text-slate-500 px-5 py-3 border-b border-slate-800/60">
          <div class="col-span-2">Symbol</div>
          <div>Score</div>
          <div>Liquidity</div>
          <div>Momentum</div>
          <div>ATR%</div>
          <div>Spread</div>
          <div>Slip</div>
          <div>Vol</div>
          <div>Ret15</div>
          <div>Ret1</div>
          <div>Flags</div>
        </div>
        <div class="divide-y divide-slate-800/60">
          <template x-if="!rows.length">
            <div class="px-5 py-12 text-center text-sm text-slate-500">Waiting for rankings...</div>
          </template>
          <template x-for="row in rows" :key="row.symbol">
            <div class="grid grid-cols-12 items-center px-5 py-4 cursor-pointer hover:bg-slate-800/40 transition" @click="openSymbol(row.symbol)" :class="selectedSymbol===row.symbol ? 'bg-cyan-500/10 border-l border-cyan-400/50' : ''">
              <div class="col-span-2 font-semibold text-slate-100" x-text="row.symbol"></div>
              <div :class="scoreTone(row.score)" x-text="fmt(row.score)"></div>
              <div class="text-slate-300" x-text="fmt(row.liquidity_edge)"></div>
              <div :class="tone(row.momentum_edge)" x-text="fmt(row.momentum_edge)"></div>
              <div :class="row.atr_pct>1.5 ? 'text-amber-300' : 'text-slate-300'" x-text="fmt(row.atr_pct)"></div>
              <div :class="row.spread_bps>8 ? 'text-rose-300' : 'text-slate-300'" x-text="fmt(row.spread_bps)"></div>
              <div :class="row.slip_bps>5 ? 'text-rose-300' : 'text-slate-300'" x-text="fmt(row.slip_bps)"></div>
              <div class="text-slate-300" x-text="num(row.qvol_usdt)"></div>
              <div :class="tone(row.ret15)" x-text="fmt(row.ret15)"></div>
              <div :class="tone(row.ret1)" x-text="fmt(row.ret1)"></div>
              <div class="flex flex-wrap gap-1">
                <template x-for="flag in (row.flags||[])" :key="row.symbol + flag.name">
                  <span class="px-2 py-0.5 rounded-full border text-[11px]" :class="flag.active ? 'border-emerald-400/40 text-emerald-300 bg-emerald-400/10' : 'border-slate-700 text-slate-400'" x-text="flag.name"></span>
                </template>
                <span x-show="!(row.flags && row.flags.length)" class="text-[11px] text-slate-500">-</span>
              </div>
            </div>
          </template>
        </div>
      </section>
    </main>

    <aside class="w-full xl:w-96 2xl:w-[420px] border-t xl:border-t-0 xl:border-l border-slate-800/60 bg-slate-950/70 backdrop-blur-xl px-6 py-6 scrollbar overflow-y-auto">
      <section class="space-y-4">
        <header>
          <p class="uppercase text-[11px] tracking-[0.32em] text-slate-500">Spotlight</p>
          <h2 class="text-xl font-semibold mt-1" x-text="spotCard ? spotCard.symbol : 'No symbol selected'"></h2>
          <p class="text-xs text-slate-500">Use Ctrl+K / Cmd+K or click a row to focus a market.</p>
        </header>
        <template x-if="spotCard">
          <div class="panel p-5 space-y-4">
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div><p class="text-xs text-slate-500">Spread (bps)</p><p :class="spotCard.spread_bps>8 ? 'text-rose-300' : 'text-slate-100'" class="text-lg font-semibold" x-text="fmt(spotCard.spread_bps)"></p></div>
              <div><p class="text-xs text-slate-500">Slip (bps)</p><p :class="spotCard.slip_bps>5 ? 'text-rose-300' : 'text-slate-100'" class="text-lg font-semibold" x-text="fmt(spotCard.slip_bps)"></p></div>
              <div><p class="text-xs text-slate-500">ATR %</p><p :class="spotCard.atr_pct>1.4 ? 'text-amber-300' : 'text-slate-100'" class="text-lg font-semibold" x-text="fmt(spotCard.atr_pct)"></p></div>
              <div><p class="text-xs text-slate-500">Quote Vol</p><p class="text-lg font-semibold text-slate-100" x-text="num(spotCard.qvol_usdt)"></p></div>
            </div>
            <div>
              <p class="text-xs text-slate-500 uppercase tracking-[0.32em]">Flags</p>
              <div class="flex flex-wrap gap-2 mt-2">
                <template x-for="f in (spotCard.flags||[])" :key="f.name">
                  <span class="px-3 py-1 rounded-full border text-xs" :class="f.active ? 'border-emerald-400/40 text-emerald-300 bg-emerald-400/10' : 'border-slate-700 text-slate-300'" x-text="f.name"></span>
                </template>
                <span x-show="!(spotCard.flags && spotCard.flags.length)" class="text-xs text-slate-600">No flags raised.</span>
              </div>
            </div>
            <button class="w-full px-4 py-2 rounded-xl bg-cyan-500/20 border border-cyan-300/30 text-cyan-100 hover:bg-cyan-500/30" @click="openSymbol(spotCard.symbol)">Sync with rankings</button>
          </div>
        </template>
        <template x-if="!spotCard">
          <div class="panel p-5 text-sm text-slate-500">Spotlight a market to see its liquidity, risk, and momentum profile in detail.</div>
        </template>
        <section class="space-y-3">
          <p class="uppercase text-[11px] tracking-[0.32em] text-slate-500">Activity</p>
          <template x-for="item in activity" :key="item.id">
            <div class="card px-4 py-3 text-xs flex items-start gap-3">
              <span class="w-2 h-2 rounded-full mt-1" :class="item.variant==='positive' ? 'bg-emerald-400' : item.variant==='warning' ? 'bg-amber-300' : 'bg-slate-500'"></span>
              <div>
                <p class="text-slate-300" x-text="item.message"></p>
                <p class="text-[10px] text-slate-500" x-text="item.time"></p>
              </div>
            </div>
          </template>
          <template x-if="!activity.length">
            <div class="card px-4 py-3 text-xs text-slate-500">No alerts yet - they will show up as the scanner refreshes.</div>
          </template>
        </section>
      </section>
    </aside>
  </div>

  <div x-show="openSettings" x-transition.opacity x-cloak class="fixed inset-0 z-50 flex">
    <div class="flex-1 bg-black/50" @click="openSettings=false"></div>
    <div class="w-full max-w-md bg-slate-950/95 border-l border-slate-800/70 backdrop-blur-xl p-6 overflow-y-auto scrollbar" x-transition>
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold">Control Deck</h3>
        <button class="text-slate-400 hover:text-slate-200" @click="openSettings=false">✕</button>
      </div>
      <p class="text-xs text-slate-500 mt-1">Settings persist in localStorage. Wire to an API later for synced profiles.</p>
      <div class="mt-6 space-y-5">
        <div>
          <label class="text-xs text-slate-400 uppercase tracking-[0.3em]">Profile</label>
          <select class="w-full rounded-lg bg-slate-900/80 border border-slate-700/70 px-3 py-2 text-sm mt-1" x-model="settings.profile" @change="saveSettings(); manualRefresh();">
            <option value="scalp">Scalp</option>
            <option value="swing">Swing</option>
            <option value="news">News</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-xs text-slate-400 uppercase tracking-[0.3em]">Top N</label>
            <select class="w-full rounded-lg bg-slate-900/80 border border-slate-700/70 px-3 py-2 text-sm mt-1" x-model.number="settings.top" @change="saveSettings(); manualRefresh();">
              <template x-for="n in [12,20,40,100]" :key="n"><option :value="n" x-text="n"></option></template>
            </select>
          </div>
          <div>
            <label class="text-xs text-slate-400 uppercase tracking-[0.3em]">Notional (USDT)</label>
            <input type="number" min="100" step="100" class="w-full rounded-lg bg-slate-900/80 border border-slate-700/70 px-3 py-2 text-sm mt-1" x-model.number="settings.notional" @change="saveSettings(); manualRefresh();">
          </div>
        </div>
        <div class="space-y-3">
          <template x-for="item in weightSliders" :key="item.key">
            <div>
              <div class="flex items-center justify-between text-xs text-slate-400">
                <span x-text="item.label"></span>
                <span class="text-slate-500" x-text="settings.weights[item.key] + '%'">0%</span>
              </div>
              <input type="range" min="0" max="100" class="w-full" x-model.number="settings.weights[item.key]" @input="saveSettings()">
            </div>
          </template>
        </div>
        <div class="space-y-3">
          <div>
            <label class="text-xs text-slate-400 uppercase tracking-[0.3em]">Whitelist</label>
            <input class="w-full rounded-lg bg-slate-900/80 border border-slate-700/70 px-3 py-2 text-sm mt-1" x-model="settings.whitelist" @blur="saveSettings()" placeholder="BTC/USDT:USDT, ETH/USDT:USDT">
          </div>
          <div>
            <label class="text-xs text-slate-400 uppercase tracking-[0.3em]">Blacklist</label>
            <input class="w-full rounded-lg bg-slate-900/80 border border-slate-700/70 px-3 py-2 text-sm mt-1" x-model="settings.blacklist" @blur="saveSettings()" placeholder="HIFI/USDT:USDT">
          </div>
        </div>
        <div>
          <div class="flex items-center justify-between text-xs text-slate-400">
            <span>Min manipulation risk</span>
            <span class="text-slate-500" x-text="settings.minManip + '%'">0%</span>
          </div>
          <input type="range" min="0" max="100" class="w-full" x-model.number="settings.minManip" @input="saveSettings()">
        </div>
        <div class="flex gap-2">
          <button class="flex-1 px-3 py-2 rounded-lg border border-slate-700/70" :class="theme==='dark' ? 'bg-cyan-500/20 border-cyan-400/40 text-cyan-100' : 'text-slate-400'" @click="setTheme('dark')">Matrix dark</button>
          <button class="flex-1 px-3 py-2 rounded-lg border border-slate-700/70" :class="theme==='light' ? 'bg-slate-200 text-slate-900 border-slate-300' : 'text-slate-400'" @click="setTheme('light')">Light</button>
        </div>
        <button class="w-full px-4 py-2 rounded-xl bg-cyan-500/20 border border-cyan-300/30 text-cyan-100 hover:bg-cyan-500/30" @click="manualRefresh()">Apply & refresh</button>
      </div>
      <p class="text-[11px] text-slate-600 mt-6">Need persistence across devices? Add CRUD endpoints and replace the localStorage helper.</p>
    </div>
  </div>

  <div x-show="toast" x-transition.opacity x-cloak class="fixed bottom-6 right-6 z-50 glass px-4 py-3 rounded-xl border border-slate-700/70 text-sm" :class="toastType==='error' ? 'text-rose-200 border-rose-500/40 bg-rose-500/10' : 'text-emerald-200 border-emerald-400/40 bg-emerald-500/10'">
    <span x-text="toast"></span>
  </div>

  <script>
  function panelApp(){
    return {
      theme: localStorage.getItem('theme') || 'dark',
      rows: [],
      connected: false,
      latency: null,
      lastUpdated: null,
      refreshInterval: 5000,
      refreshProgress: 100,
      countdown: '-',
      openSettings: false,
      spot: '',
      spotCard: null,
      selectedSymbol: null,
      toast: '', toastType: 'info', toastTimer: null,
      activity: [],
      quickFilters: { liq:false, mom:false, safe:false },
      weightSliders: [
        { key: 'liq', label: 'Liquidity weight' },
        { key: 'mom', label: 'Momentum weight' },
        { key: 'spread', label: 'Spread penalty' },
        { key: 'bias', label: 'MeanRev <-> Breakout' }
      ],
      settings: {},
      init(){
        this.settings = Object.assign({
          profile: 'scalp',
          top: 12,
          notional: 5000,
          weights: { liq: 60, mom: 25, spread: 15, bias: 50 },
          whitelist: '',
          blacklist: '',
          minManip: 0
        }, JSON.parse(localStorage.getItem('scanner_settings') || '{}'));
        this.applyTheme();
        this.manualRefresh();
        this.refreshLoop();
        this.progressTicker();
        window.addEventListener('keydown', (e) => {
          if((e.metaKey || e.ctrlKey) && e.key.toLowerCase()==='k'){
            e.preventDefault();
            const el = document.querySelector('.spot-input');
            if(el){ el.focus(); el.select(); }
          }
        });
      },
      applyTheme(){ localStorage.setItem('theme', this.theme); document.documentElement.setAttribute('data-theme', this.theme); },
      setTheme(mode){ this.theme = mode; this.applyTheme(); },
      saveSettings(){ localStorage.setItem('scanner_settings', JSON.stringify(this.settings)); },
      async refreshLoop(){
        while(true){
          await new Promise(r => setTimeout(r, this.refreshInterval));
          await this.fetchRankings();
        }
      },
      progressTicker(){
        setInterval(() => {
          if(!this.lastUpdated){ return; }
          const elapsed = Date.now() - this.lastUpdated;
          const remain = Math.max(this.refreshInterval - elapsed, 0);
          this.countdown = Math.ceil(remain/1000) + 's';
          const pct = Math.min(100, (elapsed/this.refreshInterval)*100);
          this.refreshProgress = 100 - pct;
        }, 180);
      },
      params(){
        const params = new URLSearchParams({
          top: this.settings.top,
          profile: this.settings.profile,
          notional: this.settings.notional
        });
        if(this.settings.whitelist.trim()) params.append('whitelist', this.settings.whitelist);
        if(this.settings.blacklist.trim()) params.append('blacklist', this.settings.blacklist);
        if(this.settings.minManip>0) params.append('min_manip', this.settings.minManip);
        if(this.quickFilters.safe) params.append('max_spread_bps', '5');
        return params;
      },
      async manualRefresh(){ await this.fetchRankings(true); },
      async fetchRankings(force=false){
        const started = performance.now();
        try{
          const res = await axios.get('/rankings?' + this.params().toString(), { timeout: 10000 });
          let items = res.data.items || res.data || [];
          if(!Array.isArray(items)) items = [];
          const normalizeRow = (row) => {
            const fallback = (...values) => {
              for (const val of values) {
                if (val !== undefined && val !== null) {
                  return val;
                }
              }
              return 0;
            };
            const liquidityEdge = fallback(row.liquidity_edge, row.liq_edge, row.liquidity, row.liq);
            const momentumEdge = fallback(row.momentum_edge, row.mom_edge, row.momentum);
            return { ...row, liquidity_edge: Number(liquidityEdge) || 0, momentum_edge: Number(momentumEdge) || 0 };
          };
          items = items.map(normalizeRow);
          if(this.quickFilters.liq){
            items = items.filter((r) => {
              const value = r.liquidity_edge !== undefined && r.liquidity_edge !== null ? r.liquidity_edge : (r.qvol_usdt || 0);
              return Number(value) > 0;
            });
          }
          if(this.quickFilters.mom){
            items = items.filter((r) => Number(r.momentum_edge || 0) > 0);
          }
          this.rows = items;
          this.connected = true;
          this.lastUpdated = Date.now();
          this.latency = Math.round(performance.now() - started);
          if(force) this.toastShow('Ranks refreshed');
          this.activity.unshift({ id: Date.now(), message: 'Ranks updated (' + items.length + ')', variant: 'positive', time: new Date().toLocaleTimeString() });
          if(this.activity.length > 12) this.activity.pop();
        }catch(e){
          this.connected = false;
          const msg = (e.response && e.response.status) ? 'Request failed with status ' + e.response.status : 'Network error';
          this.toastShow(msg, 'error');
          this.activity.unshift({ id: Date.now(), message: 'Refresh failed - ' + msg, variant: 'warning', time: new Date().toLocaleTimeString() });
        }
      },
      async fetchSpotlight(){
        if(!this.spot) return;
        try{
          const res = await axios.get('/opportunities?symbol=' + encodeURIComponent(this.spot));
          const items = Array.isArray(res.data && res.data.items) ? res.data.items : [];
          const card = (res.data && res.data.card) || items.find((x) => x.symbol === this.spot) || res.data;
          if(card){
            this.spotCard = card;
            this.selectedSymbol = card.symbol;
            this.toastShow('Spotlight updated');
          }else{
            this.toastShow('No data for symbol', 'error');
          }
        }catch(err){
          this.toastShow('Spotlight failed', 'error');
        }
      },
      openSymbol(sym){ this.selectedSymbol = sym; this.spot = sym; this.fetchSpotlight(); },
      toggleQuick(key){ this.quickFilters[key] = !this.quickFilters[key]; this.manualRefresh(); },
      tone(v){ const n = Number(v || 0); if(n>0) return 'text-emerald-300'; if(n<0) return 'text-rose-300'; return 'text-slate-300'; },
      scoreTone(v){ const n = Number(v || 0); if(n>40) return 'text-emerald-200'; if(n<-10) return 'text-rose-300'; return 'text-slate-200'; },
      fmt(v){ if(v===null || v===undefined || isNaN(v)) return '-'; return (+v).toFixed(2); },
      num(v){ const n = Number(v || 0); if(n>=1e9) return (n/1e9).toFixed(2)+'B'; if(n>=1e6) return (n/1e6).toFixed(2)+'M'; if(n>=1e3) return (n/1e3).toFixed(1)+'K'; return n ? n.toLocaleString() : '-'; },
      timeAgo(ts){ const s=Math.floor((Date.now()-ts)/1000); if(s<60) return s+'s ago'; const m=Math.floor(s/60); if(m<60) return m+'m ago'; return Math.floor(m/60)+'h ago'; },
      toastShow(msg,type='info'){ clearTimeout(this.toastTimer); this.toast=msg; this.toastType=type; this.toastTimer=setTimeout(() => this.toast='', 2400); },
      avgManip(){
        if(!this.rows.length) return '-';
        const vals = this.rows.map((r) => Number(r.manip || r.manip_score)).filter((n) => !Number.isNaN(n));
        if(!vals.length) return '-';
        return (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1);
      }
    }
  }
  </script>
</body>
</html>
"""

