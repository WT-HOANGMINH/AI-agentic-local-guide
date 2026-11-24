(() => {
  const existing = window.LOCAL_GUIDE_CONFIG || {};
  const hostname = window.location.hostname;
  const localHosts = new Set(["localhost", "127.0.0.1"]);
  const isLocalBrowser = localHosts.has(hostname) && window.location.port !== "8000";
  const apiBase = String(
    window.LOCAL_GUIDE_API_BASE ||
    existing.API_BASE ||
    (isLocalBrowser ? `http://${hostname}:8000` : window.location.origin)
  ).replace(/\/+$/, "");

  window.LOCAL_GUIDE_CONFIG = {
    ...existing,
    USE_MOCK: existing.USE_MOCK ?? false,
    API_BASE: apiBase,
    TOKEN_KEY: existing.TOKEN_KEY || "localguide_token",
  };

  window.API_BASE_URL = apiBase;
})();