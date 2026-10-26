
const isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

window.LOCAL_GUIDE_CONFIG = {
  USE_MOCK: false,

  API_BASE: isLocal
    ? "http://127.0.0.1:8000"
    : window.location.origin,

  TOKEN_KEY: "localguide_token"
};
