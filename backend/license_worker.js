// TranslookDown License Worker
// è·¯ç±ï¼
//   POST /verify          â å®¢æ·ç«¯ License éªè¯ï¼ååè½ï¼
//   GET  /admin           â ç®¡çåå°ï¼å¯ç ä¿æ¤ï¼
//   POST /admin/generate  â çæ License
//   GET  /admin/list      â ååºææ License
//   POST /admin/revoke    â åé License

// ââ å·¥å·å½æ° ââââââââââââââââââââââââââââââââââââââââââââââââââ
function jsonResp(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function genKey() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const seg = () =>
    Array.from({ length: 5 }, () =>
      chars[Math.floor(Math.random() * chars.length)]
    ).join("");
  return `TLD-${seg()}-${seg()}-${seg()}`;
}

// ââ ä¸»å¥å£ ââââââââââââââââââââââââââââââââââââââââââââââââââââ
export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    // ââ Admin è·¯ç± âââââââââââââââââââââââââââââââââââââââââââ
    if (path === "/admin" || path.startsWith("/admin/")) {
      return handleAdmin(request, url, env);
    }

    // ââ License éªè¯è·¯ç±ï¼å®¢æ·ç«¯ä½¿ç¨ï¼ââââââââââââââââââââââââ
    return handleVerify(request, env);
  },
};

// ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
// License éªè¯é»è¾ï¼å odd-base-e5e3 åè½ï¼
// ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async function handleVerify(request, env) {
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }
  let body;
  try { body = await request.json(); } catch {
    return jsonResp({ valid: false, message: "è¯·æ±ä½è§£æå¤±è´¥" }, 400);
  }
  const { key, fingerprint, action } = body;
  if (!key || !fingerprint) {
    return jsonResp({ valid: false, message: "åæ°ç¼ºå¤±" }, 400);
  }
  const licenseData = await env.LICENSE_KV.get(`license:${key}`, "json");
  if (!licenseData) {
    return jsonResp({ valid: false, message: "License ä¸å­å¨æå·²è¢«åé" });
  }
  if (licenseData.expires_at && licenseData.expires_at > 0) {
    if (Date.now() / 1000 > licenseData.expires_at) {
      return jsonResp({ valid: false, message: "License å·²è¿æ" });
    }
  }
  if (action === "activate") {
    const maxDevices = licenseData.plan === "team" ? 5 : 1;
    const devices = licenseData.devices || [];
    if (!devices.includes(fingerprint)) {
      if (devices.length >= maxDevices) {
        return jsonResp({
          valid: false,
          message: `è®¾å¤æ°å·²è¾¾ä¸éï¼${maxDevices} å°ï¼`,
        });
      }
      devices.push(fingerprint);
      const putOpts = licenseData.ttl ? { expirationTtl: licenseData.ttl } : {};
      await env.LICENSE_KV.put(
        `license:${key}`,
        JSON.stringify({ ...licenseData, devices }),
        putOpts
      );
    }
  }
  return jsonResp({
    valid: true,
    plan: licenseData.plan,
    expires_at: licenseData.expires_at || null,
  });
}

// ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
// Admin é¢æ¿
// ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
async function handleAdmin(request, url, env) {
  const adminPwd = env.ADMIN_PASSWORD || "Zhlcc1026@@@";
  const pwd = url.searchParams.get("pwd");
  const path = url.pathname;

  // å¯ç éªè¯
  if (pwd !== adminPwd) {
    return new Response(LOGIN_HTML, {
      headers: { "Content-Type": "text/html;charset=UTF-8" },
    });
  }

  // GET /admin â ä¸»é¡µé¢
  if (path === "/admin" && request.method === "GET") {
    return new Response(ADMIN_HTML, {
      headers: { "Content-Type": "text/html;charset=UTF-8" },
    });
  }

  // POST /admin/generate
  if (path === "/admin/generate" && request.method === "POST") {
    const { plan, years, email } = await request.json();
    const key = genKey();
    const now = Math.floor(Date.now() / 1000);
    const expiresAt = years >= 99 ? 0 : now + years * 365 * 86400;
    const expiresStr =
      expiresAt === 0
        ? "æ°¸ä¹"
        : new Date(expiresAt * 1000).toISOString().slice(0, 10);
    const value = {
      plan: plan || "pro",
      expires_at: expiresAt,
      devices: [],
      ttl: years >= 99 ? 0 : years * 365 * 86400,
      buyer_email: email || "",
      created_at: now,
    };
    const putOpts = value.ttl > 0 ? { expirationTtl: value.ttl } : {};
    await env.LICENSE_KV.put(`license:${key}`, JSON.stringify(value), putOpts);
    return jsonResp({ key, plan: value.plan, expires_str: expiresStr, email: value.buyer_email });
  }

  // GET /admin/list
  if (path === "/admin/list" && request.method === "GET") {
    const list = await env.LICENSE_KV.list({ prefix: "license:" });
    const licenses = await Promise.all(
      list.keys.map(async ({ name }) => {
        const raw = await env.LICENSE_KV.get(name, "json");
        if (!raw) return null;
        const key = name.replace("license:", "");
        return {
          key,
          plan: raw.plan,
          expires_str: raw.expires_at
            ? new Date(raw.expires_at * 1000).toISOString().slice(0, 10)
            : "æ°¸ä¹",
          devices: (raw.devices || []).length,
          max_devices: raw.plan === "team" ? 5 : 1,
          email: raw.buyer_email || "",
        };
      })
    );
    return jsonResp({
      licenses: licenses
        .filter(Boolean)
        .sort((a, b) => b.key.localeCompare(a.key)),
    });
  }

  // POST /admin/revoke
  if (path === "/admin/revoke" && request.method === "POST") {
    const { key } = await request.json();
    await env.LICENSE_KV.delete(`license:${key.replace("license:", "")}`);
    return jsonResp({ ok: true });
  }

  return new Response("Not Found", { status: 404 });
}

// ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
// HTML æ¨¡æ¿
// ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
const LOGIN_HTML = `<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>License ç®¡ç</title><style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#f0f2f5;display:flex;align-items:center;justify-content:center;min-height:100vh}.box{background:#fff;border-radius:16px;padding:40px;width:340px;box-shadow:0 4px 24px rgba(0,0,0,.1);text-align:center}h2{margin-bottom:8px;color:#1a1a2e;font-size:22px}p{color:#999;font-size:13px;margin-bottom:24px}input{width:100%;padding:12px;border:1.5px solid #e0e0e0;border-radius:10px;font-size:14px;margin-bottom:12px;outline:none}input:focus{border-color:#4f46e5}button{width:100%;padding:12px;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer}</style></head><body><div class="box"><h2>ð License ç®¡çåå°</h2><p>TranslookDown Admin Panel</p><input type="password" id="p" placeholder="ç®¡çå¯ç " onkeydown="if(event.key==='Enter')go()"><button onclick="go()">è¿å¥</button></div><script>function go(){var p=document.getElementById('p').value;if(p)location.href='/admin?pwd='+encodeURIComponent(p);}<\/script></body></html>`;

const ADMIN_HTML = `<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>License ç®¡ç Â· TranslookDown</title><style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f0f2f5;min-height:100vh}.hdr{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:18px 28px;display:flex;align-items:center;gap:10px}.hdr h1{font-size:18px;font-weight:700}.hdr .badge{font-size:11px;background:rgba(255,255,255,.15);padding:3px 10px;border-radius:20px}.hdr .out{margin-left:auto;font-size:12px;color:rgba(255,255,255,.6);cursor:pointer;text-decoration:underline}.wrap{max-width:960px;margin:24px auto;padding:0 16px}.card{background:#fff;border-radius:14px;padding:22px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,.06)}.ctitle{font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:14px}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}label{font-size:12px;color:#666;margin-bottom:4px;display:block}select,input{padding:10px 13px;border:1.5px solid #e0e0e0;border-radius:9px;font-size:14px;outline:none;background:#fafafa}select:focus,input:focus{border-color:#4f46e5}.btn{padding:10px 18px;border:none;border-radius:9px;font-size:14px;font-weight:600;cursor:pointer;transition:all .15s}.btn-p{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff}.btn-p:hover{opacity:.9}.btn-sm{padding:5px 11px;font-size:12px}.btn-d{background:#fee2e2;color:#dc2626}.result{margin-top:14px;padding:14px;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;display:none}.key-big{font-size:22px;font-weight:800;color:#166534;font-family:monospace;letter-spacing:1px}.key-meta{font-size:12px;color:#16a34a;margin-top:3px}.copy{background:#dcfce7;color:#166534;border:none;padding:6px 13px;border-radius:8px;cursor:pointer;font-size:12px;font-weight:600;margin-top:8px}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;padding:9px 11px;background:#f8f9fa;color:#666;font-weight:600;border-bottom:2px solid #eee}td{padding:9px 11px;border-bottom:1px solid #f0f0f0}.tag{display:inline-flex;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700}.pro{background:#ede9fe;color:#7c3aed}.team{background:#fef3c7;color:#b45309}.empty{text-align:center;color:#aaa;padding:36px;font-size:14px}.toast{position:fixed;bottom:22px;right:22px;background:#1a1a2e;color:#fff;padding:11px 18px;border-radius:9px;font-size:13px;opacity:0;transition:opacity .25s;z-index:999}.toast.on{opacity:1}</style></head><body>
<div class="hdr"><h1>ð TranslookDown</h1><span class="badge">License ç®¡ç</span><span class="out" onclick="logout()">éåº</span></div>
<div class="wrap">
<div class="card">
  <div class="ctitle">â¨ çææ° License</div>
  <div class="row">
    <div><label>å¥é¤</label><select id="plan"><option value="pro">Proï¼1å°è®¾å¤ï¼</option><option value="team">Teamï¼5å°è®¾å¤ï¼</option></select></div>
    <div><label>æææ</label><select id="years"><option value="1">1 å¹´</option><option value="2">2 å¹´</option><option value="3">3 å¹´</option><option value="99">æ°¸ä¹</option></select></div>
    <div style="flex:1;min-width:180px"><label>ä¹°å®¶é®ç®±ï¼å¯éï¼</label><input type="email" id="email" placeholder="buyer@example.com" style="width:100%"></div>
    <button class="btn btn-p" id="genBtn" onclick="generate()">çæ License</button>
  </div>
  <div class="result" id="result">
    <div class="key-big" id="keyTxt"></div>
    <div class="key-meta" id="keyMeta"></div>
    <button class="copy" onclick="copyKey()">ð å¤å¶</button>
  </div>
</div>
<div class="card">
  <div style="display:flex;align-items:center;margin-bottom:14px">
    <div class="ctitle" style="margin:0">ð å·²åæ¾ License</div>
    <button class="btn btn-sm" style="margin-left:auto;background:#f0f2f5;color:#333" onclick="loadList()">å·æ°</button>
  </div>
  <div id="list"><div class="empty">å è½½ä¸­...</div></div>
</div>
</div>
<div class="toast" id="toast"></div>
<script>
var pwd=new URLSearchParams(location.search).get('pwd')||sessionStorage.getItem('admpwd');
if(pwd)sessionStorage.setItem('admpwd',pwd);
var lastKey='';
function api(path,opts){return fetch(path+(path.includes('?')?'&':'?')+'pwd='+encodeURIComponent(pwd),opts||{}).then(r=>r.json());}
function generate(){
  var b=document.getElementById('genBtn');
  b.disabled=true;b.textContent='çæä¸­...';
  api('/admin/generate',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({plan:document.getElementById('plan').value,years:parseInt(document.getElementById('years').value),email:document.getElementById('email').value})})
  .then(d=>{b.disabled=false;b.textContent='çæ License';
    if(d.key){lastKey=d.key;document.getElementById('keyTxt').textContent=d.key;
      document.getElementById('keyMeta').textContent=d.plan.toUpperCase()+' Â· å°æï¼'+d.expires_str+(d.email?' Â· '+d.email:'');
      document.getElementById('result').style.display='block';loadList();toast('â License å·²çæ');}
    else toast('â '+(d.error||'å¤±è´¥'));})
  .catch(()=>{b.disabled=false;b.textContent='çæ License';toast('â è¯·æ±å¤±è´¥');});}
function copyKey(){navigator.clipboard.writeText(lastKey).then(()=>toast('â å·²å¤å¶ï¼'+lastKey));}
function loadList(){
  document.getElementById('list').innerHTML='<div class="empty">å è½½ä¸­...</div>';
  api('/admin/list').then(d=>{
    if(!d.licenses||!d.licenses.length){document.getElementById('list').innerHTML='<div class="empty">ææ  License</div>';return;}
    document.getElementById('list').innerHTML='<table><thead><tr><th>License Key</th><th>å¥é¤</th><th>å°æ</th><th>è®¾å¤</th><th>é®ç®±</th><th>æä½</th></tr></thead><tbody>'+
    d.licenses.map(l=>'<tr><td style="font-family:monospace;font-weight:600">'+l.key+'</td><td><span class="tag '+l.plan+'">'+l.plan.toUpperCase()+'</span></td><td>'+l.expires_str+'</td><td>'+l.devices+'/'+l.max_devices+'</td><td>'+(l.email||'â')+'</td><td><button class="btn btn-sm btn-d" onclick="revoke(\''+l.key+'\')">åé</button></td></tr>').join('')+'</tbody></table>';});}
function revoke(key){if(!confirm('ç¡®è®¤åé '+key+'ï¼'))return;
  api('/admin/revoke',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})})
  .then(d=>{if(d.ok){toast('â å·²åé');loadList();}else toast('â å¤±è´¥');});}
function logout(){sessionStorage.removeItem('admpwd');location.href='/admin';}
function toast(msg){var t=document.getElementById('toast');t.textContent=msg;t.classList.add('on');setTimeout(()=>t.classList.remove('on'),3000);}
loadList();
<\/script></body></html>`;
