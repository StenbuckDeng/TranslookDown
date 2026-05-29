// backend/license_worker.js
// 部署到 Cloudflare Workers
//
// 环境变量（在 wrangler.toml 或 CF 控制台中配置）：
//   LICENSE_KV  →  KV namespace binding（存储所有 license 数据）
//
// KV 数据格式（key: "license:<KEY_STRING>"）：
//   {
//     "plan": "pro",                 // "pro" | "team"
//     "expires_at": 1893456000,      // Unix timestamp（秒），0 = 永不过期
//     "devices": [],                 // 已绑定设备指纹列表
//     "ttl": 31536000                // KV 自动过期秒数（可选）
//   }

export default {
  async fetch(request, env) {
    // CORS 预检
    if (request.method === "OPTIONS") {
      return corsResponse(new Response(null, { status: 204 }));
    }

    if (request.method !== "POST") {
      return corsResponse(new Response("Method not allowed", { status: 405 }));
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return corsResponse(json({ valid: false, message: "请求体解析失败" }, 400));
    }

    const { key, fingerprint, action } = body;

    if (!key || !fingerprint) {
      return corsResponse(json({ valid: false, message: "参数缺失：需要 key 和 fingerprint" }, 400));
    }

    // 从 KV 查询 License
    const licenseData = await env.LICENSE_KV.get(`license:${key}`, "json");

    if (!licenseData) {
      return corsResponse(json({ valid: false, message: "License 不存在或已被吊销" }));
    }

    // 检查是否过期（expires_at = 0 表示永不过期）
    if (licenseData.expires_at && licenseData.expires_at > 0) {
      if (Date.now() / 1000 > licenseData.expires_at) {
        return corsResponse(json({ valid: false, message: "License 已过期，请续费后重新激活" }));
      }
    }

    // 激活操作：绑定设备指纹
    if (action === "activate") {
      const maxDevices = licenseData.plan === "team" ? 5 : 1;
      const devices = licenseData.devices || [];

      if (!devices.includes(fingerprint)) {
        if (devices.length >= maxDevices) {
          return corsResponse(json({
            valid: false,
            message: `设备数已达上限（最多 ${maxDevices} 台）。请先在其他设备上取消激活，或联系支持。`,
          }));
        }
        // 绑定新设备
        devices.push(fingerprint);
        const updated = { ...licenseData, devices };
        const putOptions = licenseData.ttl ? { expirationTtl: licenseData.ttl } : {};
        await env.LICENSE_KV.put(`license:${key}`, JSON.stringify(updated), putOptions);
      }
    }

    return corsResponse(json({
      valid: true,
      plan: licenseData.plan,
      expires_at: licenseData.expires_at || null,
    }));
  },
};

// ─── Helpers ─────────────────────────────────────────────────

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function corsResponse(response) {
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  return new Response(response.body, {
    status: response.status,
    headers,
  });
}
