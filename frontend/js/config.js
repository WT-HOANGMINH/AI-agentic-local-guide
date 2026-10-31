
const config = window.LOCAL_GUIDE_CONFIG || {};
const localHosts = ["localhost", "127.0.0.1"];
const isLocalFrontend =
  localHosts.includes(window.location.hostname) &&
  window.location.port !== "8000";

window.LOCAL_GUIDE_CONFIG = {
  ...config,
  USE_MOCK: config.USE_MOCK ?? false,
  API_BASE:
    window.LOCAL_GUIDE_API_BASE ||
    config.API_BASE ||
    (isLocalFrontend
      ? "http://127.0.0.1:8000"
      : window.location.origin),
  TOKEN_KEY: config.TOKEN_KEY || "localguide_token"
};
