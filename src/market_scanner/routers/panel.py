from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/panel", response_class=HTMLResponse)
async def panel():
    # HTML served directly to keep it simple; uses Tailwind + Alpine via CDN
    return HTMLResponse(PANEL_HTML)


PANEL_HTML = r"""
<!doctype html>
<html lang="en" x-data="panelApp()" :class="theme">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Market Scanner — Command Center</title>
  <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/axios@1.6.8/dist/axios.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#0b1220; --panel:#0f172a; --ink:#cbd5e1; --accent:#22d3ee; --bad:#ef4444; --good:#22c55e;}
    html,body{height:100%}
    body{background:linear-gradient(180deg,#0a0f1a 0%, #0b1220 40%, #0e1627 100%); color:var(--ink); font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial;}
    .glass{background:rgba(15,23,42,.6); backdrop-filter: blur(10px); border:1px solid rgba(148,163,184,.1);}
    .chip{border:1px solid rgba(148,163,184,.2)}
    .pulse{box-shadow:0 0 0 rgba(34,211,238,0.4); animation:pulse 2s infinite}
    @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(34,211,238,.45)}70%{box-shadow:0 0 0 15px rgba(34,211,238,0)}100%{box-shadow:0 0 0 0 rgba(34,211,238,0)}}
    .status-dot{width:10px;height:10px;border-radius:9999px}
    .scrollbar::-webkit-scrollbar{height:10px}
    .scrollbar::-webkit-scrollbar-thumb{background:#1f2937;border-radius:8px}
    .pill{background:#0b1324;border:1px solid #213049}
    .hdr{background: radial-gradient(50% 60% at 50% -10%, rgba(34,211,238,.2), transparent 60%)}
    .table-header{background:rgba(2,6,23,.6)}
  </style>
</head>
<body class="min-h-full">
  <!-- Top Bar -->
  <header class="hdr sticky top-0 z-30 px-6 py-4 border-b border-slate-800/60 glass">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-cyan-400/20 border border-cyan-300/30 flex items-center justify-center pulse">
        <svg width="22" height="22" viewBox="0 0 24 24" class="text-cyan-300"><path fill="currentColor" d="M11 21v-7H7l6-11v7h4Z"/></svg>
      </div>
      <div>
        <h1 class="text-xl font-extrabold tracking-tight">Market Scanner — <span class="text-cyan-300">Command Center</span></h1>
        <p class="text-sm text-slate-400" x-text="subTitle()"></p>
      </div>

      <div class="ml-auto flex items-center gap-2">
        <!-- Spotlight -->
        <div class="relative">
          <input x-model="spot" @keydown.enter.prevent="fetchSpotlight()" placeholder="Spotlight: BTC/USDT:USDT…" class="pill px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400/40 placeholder:text-slate-500 w-64">
          <div x-show="spotCard" @click.away="spotCard=null" class="absolute mt-2 w-[28rem] p-4 glass rounded-xl z-20">
            <template x-if="spotCard">
              <div>
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold text-cyan-300" x-text="spotCard.symbol"></h3>
                  <button @click="spotCard=null" class="text-slate-400 hover:text-slate-200">✕</button>
                </div>
                <div class="grid grid-cols-2 gap-3 mt-3 text-sm">
                  <div><span class="text-slate-400">Spread (bps):</span> <span x-text="fmt(spotCard.spread_bps)"></span></div>
                  <div><span class="text-slate-400">Slip (bps):</span> <span x-text="fmt(spotCard.slip_bps)"></span></div>
                  <div><span class="text-slate-400">ATR%:</span> <span x-text="fmt(spotCard.atr_pct)"></span></div>
                  <div><span class="text-slate-400">QVol (USDT):</span> <span x-text="num(spotCard.qvol_usdt)"></span></div>
                </div>
                <div class="mt-3">
                  <span class="text-slate-400 text-sm">Flags:</span>
                  <div class="flex gap-2 mt-2 flex-wrap">
                    <template x-for="f in (spotCard.flags||[])">
                      <span class="px-2 py-1 rounded-full text-xs border border-slate-700" :class="f.active ? 'bg-emerald-500/10 text-emerald-300' : 'bg-slate-700/30 text-slate-300'" x-text="f.name"></span>
                    </template>
                    <span x-show="!(spotCard.flags && spotCard.flags.length)" class="text-slate-500 text-xs">None</span>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Settings -->
        <button @click="openSettings=true" class="pill px-3 py-2 rounded-lg text-sm border-cyan-300/20 hover:border-cyan-300/40 hover:text-cyan-200">
          ⚙ Settings
        </button>

        <!-- Refresh -->
        <button @click="manualRefresh()" class="pill px-3 py-2 rounded-lg text-sm bg-cyan-400/10 border border-cyan-300/30 text-cyan-200 hover:bg-cyan-400/20">
          Refresh
        </button>

        <!-- Status -->
        <div class="flex items-center gap-2 pill px-3 py-2 rounded-lg text-xs">
          <div class="status-dot" :style="connected ? 'background: var(--good)' : 'background: var(--bad)'"></div>
          <span x-text="connected ? 'Live' : 'Error'"></span>
          <span class="text-slate-500">·</span>
          <span class="text-slate-400" x-text="lastUpdated ? ('Updated ' + timeAgo(lastUpdated)) : 'Waiting…'"></span>
        </div>
      </div>
    </div>
  </header>

  <!-- Controls row -->
  <section class="px-6 mt-4">
    <div class="flex items-center gap-2 flex-wrap">
      <span class="chip px-2 py-1 rounded-md text-xs">Profile:
        <select x-model="settings.profile" @change="saveSettings(); manualRefresh();" class="bg-transparent focus:outline-none text-cyan-300">
          <option value="scalp">scalp</option>
          <option value="swing">swing</option>
          <option value="news">news</option>
        </select>
      </span>
      <span class="chip px-2 py-1 rounded-md text-xs">Top:
        <select x-model.number="settings.top" @change="saveSettings(); manualRefresh();" class="bg-transparent focus:outline-none text-cyan-300">
          <template x-for="n in [12,20,40,100]"><option :value="n" x-text="n"></option></template>
        </select>
      </span>
      <span class="chip px-2 py-1 rounded-md text-xs">Notional:
        <input type="number" min="100" step="100" x-model.number="settings.notional" @change="saveSettings(); manualRefresh();" class="bg-transparent w-20 focus:outline-none text-cyan-300">
      </span>

      <template x-if="error">
        <span class="ml-2 text-red-400 text-sm">Error: <span x-text="error"></span></span>
      </template>
    </div>
  </section>

  <!-- Table -->
  <main class="px-6 mt-4">
    <div class="glass rounded-xl overflow-hidden border border-slate-800/60">
      <div class="table-header px-4 py-2 text-xs grid grid-cols-10 gap-2 uppercase tracking-wider text-slate-400">
        <div class="col-span-2">Symbol</div>
        <div>Score</div>
        <div>Volume (USDT)</div>
        <div>ATR %</div>
        <div>Spread bps</div>
        <div>Slip bps</div>
        <div>Ret15%</div>
        <div>Ret1%</div>
        <div>Flags</div>
      </div>
      <div class="divide-y divide-slate-800/60" id="rows">
        <template x-for="row in rows" :key="row.symbol">
          <div class="px-4 py-3 grid grid-cols-10 gap-2 items-center hover:bg-slate-800/30 cursor-pointer"
               @click="openSymbol(row.symbol)">
            <div class="col-span-2 font-semibold text-slate-200" x-text="row.symbol"></div>
            <div class="text-slate-200" x-text="fmt(row.score)"></div>
            <div class="text-slate-300" x-text="num(row.qvol_usdt)"></div>
            <div :class="row.atr_pct>1.2 ? 'text-amber-300' : 'text-slate-300'" x-text="fmt(row.atr_pct)"></div>
            <div :class="row.spread_bps>8 ? 'text-red-400' : 'text-slate-300'" x-text="fmt(row.spread_bps)"></div>
            <div :class="row.slip_bps>5 ? 'text-red-400' : 'text-slate-300'" x-text="fmt(row.slip_bps)"></div>
            <div :class="row.ret15>0 ? 'text-emerald-300' : 'text-rose-300'" x-text="fmt(row.ret15)"></div>
            <div :class="row.ret1>0 ? 'text-emerald-300' : 'text-rose-300'" x-text="fmt(row.ret1)"></div>
            <div class="flex gap-1 flex-wrap">
              <template x-for="f in (row.flags||[])">
                <span class="text-[10px] px-2 py-0.5 rounded-full border"
                      :class="f.active ? 'border-emerald-400/40 text-emerald-300 bg-emerald-400/10' : 'border-slate-600 text-slate-300 bg-slate-600/20'"
                      x-text="f.name"></span>
              </template>
            </div>
          </div>
        </template>
      </div>
    </div>
  </main>

  <!-- Slide-over Settings -->
  <div x-show="openSettings" class="fixed inset-0 z-40" x-transition.opacity>
    <div class="absolute inset-0 bg-black/50" @click="openSettings=false"></div>
    <div class="absolute right-0 top-0 bottom-0 w-[420px] glass border-l border-slate-800/60 p-6 overflow-y-auto" x-transition>
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold">Settings</h3>
        <button @click="openSettings=false" class="text-slate-400 hover:text-slate-200">✕</button>
      </div>
      <div class="mt-4 space-y-4">
        <div>
          <label class="text-sm text-slate-400">Theme</label>
          <select x-model="theme" @change="saveTheme()" class="pill px-3 py-2 rounded-lg w-full mt-1">
            <option value="">Matrix Dark</option>
            <option value="light">Light</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-sm text-slate-400">Liquidity Weight</label>
            <input type="range" min="0" max="100" x-model.number="settings.weights.liq" @input="saveSettings()" class="w-full">
          </div>
          <div>
            <label class="text-sm text-slate-400">Momentum Weight</label>
            <input type="range" min="0" max="100" x-model.number="settings.weights.mom" @input="saveSettings()" class="w-full">
          </div>
          <div>
            <label class="text-sm text-slate-400">Spread Penalty</label>
            <input type="range" min="0" max="100" x-model.number="settings.weights.spread" @input="saveSettings()" class="w-full">
          </div>
          <div>
            <label class="text-sm text-slate-400">MeanRev ↔ Breakout</label>
            <input type="range" min="0" max="100" x-model.number="settings.weights.bias" @input="saveSettings()" class="w-full">
          </div>
        </div>
        <div>
          <label class="text-sm text-slate-400">Whitelist (comma separated)</label>
          <input x-model="settings.whitelist" @change="saveSettings()" class="pill px-3 py-2 rounded-lg w-full mt-1" placeholder='BTC/USDT:USDT, ETH/USDT:USDT'>
        </div>
        <div>
          <label class="text-sm text-slate-400">Blacklist (comma separated)</label>
          <input x-model="settings.blacklist" @change="saveSettings()" class="pill px-3 py-2 rounded-lg w-full mt-1" placeholder='HIFI/USDT:USDT'>
        </div>
        <div class="flex items-center justify-between">
          <label class="text-sm text-slate-400">Min Manipulation Risk</label>
          <input type="range" min="0" max="100" x-model.number="settings.minManip" @input="saveSettings()" class="w-48">
          <span class="text-cyan-300 text-sm" x-text="settings.minManip + '%'"></span>
        </div>
        <button @click="manualRefresh()" class="w-full pill px-3 py-2 rounded-lg bg-cyan-400/10 border border-cyan-300/30 text-cyan-200 hover:bg-cyan-400/20">Apply & Refresh</button>
      </div>
      <p class="text-xs text-slate-500 mt-4">Settings persist in localStorage. Hook to backend later if you want user accounts.</p>
    </div>
  </div>

  <!-- Toast -->
  <div x-show="toast" x-transition.opacity class="fixed bottom-6 right-6 z-50 glass px-4 py-3 rounded-lg border border-slate-700 text-sm" :class="toastType==='error' ? 'text-red-300' : 'text-emerald-300'">
    <span x-text="toast"></span>
  </div>

  <script>
  function panelApp(){
    return {
      theme: localStorage.getItem('theme') || '',
      rows: [],
      connected: false,
      lastUpdated: null,
      error: '',
      openSettings: false,
      spot: '',
      spotCard: null,
      toast: '', toastType: 'info', toastTimer: null,
      settings: JSON.parse(localStorage.getItem('scanner_settings') || '{}') || {},
      init(){
        // defaults
        this.settings = Object.assign({
          profile: 'scalp',
          top: 12,
          notional: 5000,
          weights: { liq: 60, mom: 25, spread: 15, bias: 50 },
          whitelist: '',
          blacklist: '',
          minManip: 0
        }, this.settings);
        this.saveSettings();
        this.refreshLoop();
      },
      subTitle(){ return  },
      saveSettings(){ localStorage.setItem('scanner_settings', JSON.stringify(this.settings)); },
      saveTheme(){ localStorage.setItem('theme', this.theme); },
      async refreshLoop(){
        while(true){
          await this.fetchRankings();
          await new Promise(r=>setTimeout(r, 5000));
        }
      },
      async manualRefresh(){ await this.fetchRankings(true); },
      async fetchRankings(force=false){
        try{
          const params = new URLSearchParams({
            top: this.settings.top,
            profile: this.settings.profile,
            notional: this.settings.notional
          });
          if(this.settings.whitelist.trim()) params.append('whitelist', this.settings.whitelist);
          if(this.settings.blacklist.trim()) params.append('blacklist', this.settings.blacklist);
          if(this.settings.minManip>0) params.append('min_manip', this.settings.minManip);

          const res = await axios.get(, {timeout: 10000});
          this.rows = res.data.items || res.data || [];
          this.connected = true;
          this.error = '';
          this.lastUpdated = Date.now();
          if(force) this.toastShow('Refreshed');
        }catch(e){
          this.connected = false;
          this.error = (e.response && e.response.status) ?  : 'Network error';
          this.toastShow(this.error, 'error');
        }
      },
      async fetchSpotlight(){
        if(!this.spot) return;
        try{
          const res = await axios.get();
          this.spotCard = res.data && (res.data.card || res.data.items?.find(x=>x.symbol===this.spot) || res.data);
          if(!this.spotCard) this.toastShow('No data for symbol', 'error');
        }catch(e){
          this.toastShow('Spotlight failed', 'error');
        }
      },
      openSymbol(sym){ this.spot = sym; this.fetchSpotlight(); },
      fmt(v){ if(v===null || v===undefined) return '—'; return (+v).toFixed(2); },
      num(v){
        const n = Number(v||0);
        return n>=1e9 ? (n/1e9).toFixed(2)+'B' : n>=1e6 ? (n/1e6).toFixed(2)+'M' : n>=1e3 ? (n/1e3).toFixed(1)+'K' : ''+n;
      },
      timeAgo(ts){ const s=Math.floor((Date.now()-ts)/1000); if(s<60) return s+'s ago'; const m=Math.floor(s/60); if(m<60) return m+'m ago'; const h=Math.floor(m/60); return h+'h ago'; },
      toastShow(msg,type='info'){ clearTimeout(this.toastTimer); this.toast=msg; this.toastType=type; this.toastTimer=setTimeout(()=>this.toast='', 2500); },
    }
  }
  </script>
</body>
</html>
"""
