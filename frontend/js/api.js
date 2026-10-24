/* =========================================================
   DA NANG GUIDE - API CLIENT
   - USE_MOCK:true  -> dung data.js + localStorage (demo)
   - USE_MOCK:false -> goi FastAPI that
   - Chat AI luon goi backend /agent/chat (ke ca khi USE_MOCK:true)
   - Yeu thich / lich trinh nhap: luu localStorage theo tung user
     (backend chua co route /favorites)
   ========================================================= */

const CFG = window.LOCAL_GUIDE_CONFIG;

const store = {
  get(k, fallback = null) {
    try {
      const v = localStorage.getItem(k);
      return v === null ? fallback : JSON.parse(v);
    } catch {
      return fallback;
    }
  },
  set(k, v) {
    localStorage.setItem(k, JSON.stringify(v));
  }
};

const delay = () => new Promise(r => setTimeout(r, 220));
const cleanUser = u => ({ id: u.id, name: u.name, email: u.email });

const normalizePlaces = x =>
  Array.isArray(x) ? x : (x?.places || x?.items || x?.results || []);

/* ---------- Vi tri GPS (de AI tim "gan toi") ---------- */
let userPos = {};
if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(
    p => {
      userPos = {
        latitude: p.coords.latitude,
        longitude: p.coords.longitude
      };
    },
    () => {},
    { timeout: 8000 }
  );
}

/* ---------- Anh xa danh muc: giao dien (tieng Viet) -> DB ---------- */
const CATEGORY_TO_DB = {
  'Tham quan': 'tourist_attraction',
  'Biển': 'tourist_attraction',
  'Thiên nhiên': 'tourist_attraction',
  'Văn hóa': 'tourist_attraction',
  'Ẩm thực': 'restaurant',
  'Quán ăn': 'restaurant',
  'Cà phê': 'cafe',
  'Mua sắm': 'shopping'
};

const CATEGORY_LABEL = {
  tourist_attraction: 'Tham quan',
  restaurant: 'Ẩm thực',
  cafe: 'Cà phê',
  shopping: 'Mua sắm'
};

const CATEGORY_EMOJI = {
  tourist_attraction: '📍',
  restaurant: '🍜',
  cafe: '☕',
  shopping: '🛍️'
};

/* Chuyen 1 ban ghi tu backend sang dang giao dien dang dung */
function mapPlace(p) {
  if (!p || p.category === undefined || p.district !== undefined) return p;

  const addr = p.address || '';
  const parts = addr.split(',').map(s => s.trim()).filter(Boolean);

  return {
    ...p,
    category: CATEGORY_LABEL[p.category] || p.category,
    rawCategory: p.category,
    district: parts.length >= 2 ? parts[parts.length - 2] : 'Đà Nẵng',
    emoji: CATEGORY_EMOJI[p.category] || '📍',
    rating: p.rating ?? null
  };
}

/* Lay thong bao loi tu nhieu dinh dang tra ve cua backend */
function extractError(payload, status) {
  if (!payload) return `HTTP ${status}`;
  if (Array.isArray(payload.details) && payload.details.length) {
    return payload.details.map(d => `${d.field}: ${d.message}`).join('; ');
  }
  return (
    payload.error ||
    payload.detail ||
    payload.message ||
    `HTTP ${status}`
  );
}

const API = {

  /* ---------------- Ham goi API chung ---------------- */
  async request(path, { method = 'GET', body, auth = false } = {}) {
    const headers = { 'Content-Type': 'application/json' };

    if (auth) {
      const token = localStorage.getItem(CFG.TOKEN_KEY);
      if (token) headers.Authorization = `Bearer ${token}`;
    }

    let response;
    try {
      response = await fetch(CFG.API_BASE + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body)
      });
    } catch {
      throw new Error(
        'Không kết nối được Backend. Kiểm tra FastAPI (cổng 8000), CORS và API_BASE.'
      );
    }

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401 && auth) {
        localStorage.removeItem(CFG.TOKEN_KEY);
        localStorage.removeItem('lg_current_user');
      }
      throw new Error(extractError(payload, response.status));
    }

    return payload;
  },

  /* ---------------- Dang ky ---------------- */
  async register(name, email, password) {
    if (!CFG.USE_MOCK) {
      // Backend yeu cau truong "username"
      return this.request('/auth/register', {
        method: 'POST',
        body: { username: name, email, password }
      });
    }

    await delay();
    const users = store.get('lg_users', []);

    if (users.some(x => x.email === email.toLowerCase())) {
      throw new Error('Email đã tồn tại trong dữ liệu demo.');
    }

    users.push({ id: Date.now(), name, email: email.toLowerCase(), password });
    store.set('lg_users', users);
    return { message: 'Đăng ký thành công' };
  },

  /* ---------------- Dang nhap ---------------- */
  async login(email, password) {
    if (!CFG.USE_MOCK) {
      const res = await this.request('/auth/login', {
        method: 'POST',
        body: { email, password }
      });

      localStorage.setItem(CFG.TOKEN_KEY, res.access_token);

      // Backend tra username/email/role o cap ngoai, khong co res.user
      const user = {
        id: res.user_id,
        name: res.username || email.split('@')[0],
        email: res.email || email,
        role: res.role
      };

      store.set('lg_current_user', user);
      return user;
    }

    await delay();
    const user = store
      .get('lg_users', [])
      .find(x => x.email === email.toLowerCase() && x.password === password);

    if (!user) throw new Error('Email hoặc mật khẩu không đúng.');

    const safe = cleanUser(user);
    store.set('lg_current_user', safe);
    localStorage.setItem(CFG.TOKEN_KEY, 'demo-token');
    return safe;
  },

  logout() {
    localStorage.removeItem(CFG.TOKEN_KEY);
    localStorage.removeItem('lg_current_user');
    location.href = 'login.html';
  },

  user() {
    return store.get('lg_current_user');
  },

  isLogged() {
    return !!localStorage.getItem(CFG.TOKEN_KEY);
  },

  /* ---------------- Danh sach dia diem ---------------- */
  async places(params = {}) {
    if (!CFG.USE_MOCK) {
      const query = {};

      if (params.q) query.keyword = params.q;
      if (params.keyword) query.keyword = params.keyword;

      if (params.category && params.category !== 'all') {
        query.category = CATEGORY_TO_DB[params.category] || params.category;
      }

      if (params.max_price) query.max_price = params.max_price;
      let list;
      if (params.allPages) {
        const pageSize = 100;
        let skip = 0;
        let total = Infinity;
        list = [];

        while (skip < total) {
          const qs = new URLSearchParams({
            ...query,
            skip: String(skip),
            limit: String(pageSize)
          });
          const data = await this.request('/places/?' + qs);
          const page = normalizePlaces(data).map(mapPlace);
          list.push(...page);
          skip += page.length;
          total = Number(data.total ?? skip);
          if (!page.length) break;
        }
      } else {
        query.limit = params.limit || 100;
        const qs = new URLSearchParams(query);
        const data = await this.request('/places/?' + qs);
        list = normalizePlaces(data).map(mapPlace);
      }

      // Cac nhan nhu "Biển", "Thiên nhiên" cung la tourist_attraction trong DB,
      // nen loc them theo ten/mo ta cho dung chu de.
      const topicWords = {
        'Biển': ['biển', 'bãi'],
        'Thiên nhiên': ['rừng', 'núi', 'đèo', 'bán đảo', 'thiên nhiên'],
        'Văn hóa': ['phố cổ', 'chùa', 'bảo tàng', 'nhà thờ', 'thánh địa', 'làng']
      };

      const words = topicWords[params.category];
      if (words) {
        const filtered = list.filter(p => {
          const text = `${p.name} ${p.description || ''}`.toLocaleLowerCase('vi');
          return words.some(w => text.includes(w));
        });
        list = filtered.length ? filtered : list;
      }

      return list;
    }

    await delay();
    const q = (params.q || '').toLocaleLowerCase('vi');

    return window.DEMO_PLACES.filter(p =>
      (!q ||
        (
          p.name + ' ' + p.description + ' ' + p.district + ' ' +
          (p.area || '') + ' ' + (p.activities || []).join(' ')
        )
          .toLocaleLowerCase('vi')
          .includes(q)) &&
      (!params.category || params.category === 'all' || p.category === params.category)
    );
  },

  /* ---------------- Chi tiet 1 dia diem ---------------- */
  async place(id) {
    if (!CFG.USE_MOCK) {
      return mapPlace(await this.request('/places/' + encodeURIComponent(id)));
    }

    await delay();
    return window.DEMO_PLACES.find(p => String(p.id) === String(id)) || null;
  },

  /* ---------------- Dia diem gan toi ---------------- */
  async nearby(radiusKm = 5, category = '') {
    if (userPos.latitude === undefined) {
      throw new Error('Chưa lấy được vị trí của bạn. Hãy cho phép truy cập vị trí.');
    }

    const query = {
      latitude: userPos.latitude,
      longitude: userPos.longitude,
      radius_km: radiusKm
    };

    if (category) query.category = CATEGORY_TO_DB[category] || category;

    const data = await this.request('/places/nearby?' + new URLSearchParams(query));
    return normalizePlaces(data).map(mapPlace);
  },

  /* ---------------- Goi y ca nhan hoa ---------------- */
  async recommend(category = 'all') {
    if (!CFG.USE_MOCK) {
      // Co dang nhap thi dung goi y theo so thich, neu loi thi lay danh sach thuong
      try {
        const data = await this.request('/recommendations/for-me', { auth: true });
        return normalizePlaces(data).map(mapPlace);
      } catch {
        const data = await this.request('/recommendations/trending');
        return normalizePlaces(data).map(mapPlace);
      }
    }

    const arr = await this.places({ category });

    return category === 'all'
      ? [...arr.filter(p => p.id >= 9).slice(0, 2), ...arr.filter(p => p.id < 9).slice(0, 2)]
      : arr.slice(0, 4);
  },

  /* ---------------- CHAT AI (luon goi backend that) ---------------- */
  async chat(message) {
    const headers = { 'Content-Type': 'application/json' };

    // Gui token neu co (khong bat buoc voi /agent/chat)
    const token = localStorage.getItem(CFG.TOKEN_KEY);
    if (token && token !== 'demo-token') {
      headers.Authorization = `Bearer ${token}`;
    }

    let response;
    try {
      response = await fetch(`${CFG.API_BASE}/agent/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message, ...userPos })
      });
    } catch {
      throw new Error('Không kết nối được Chat AI. Hãy kiểm tra FastAPI ở cổng 8000.');
    }

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(extractError(result, response.status));
    }

    return result.reply || result.answer || result.response || 'AI chưa trả về nội dung.';
  },

  /* ---------------- Yeu thich (luu localStorage theo user) ---------------- */
  async favorites() {
    const ids = store.get('lg_favorites_' + this.user()?.email, []);

    if (!CFG.USE_MOCK && ids.length) {
      // Lay thong tin day du tung dia diem tu backend
      const results = await Promise.all(
        ids.map(id => this.place(id).catch(() => null))
      );
      return results.filter(Boolean);
    }

    if (CFG.USE_MOCK) {
      return window.DEMO_PLACES.filter(p => ids.includes(p.id));
    }

    return [];
  },

  async toggleFavorite(id) {
    const key = 'lg_favorites_' + this.user()?.email;
    let ids = store.get(key, []);

    ids = ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id];

    store.set(key, ids);
    return ids;
  },

  /* ---------------- Lich trinh nhap (danh sach dia diem da chon) ---------------- */
  async saveItinerary(ids) {
    store.set('lg_itinerary_' + this.user()?.email, ids);

    // Dong thoi luu len backend (neu dang o che do API va co token that)
    if (!CFG.USE_MOCK && ids.length) {
      try {
        const existingId = store.get('lg_itinerary_server_id_' + this.user()?.email);
        const items = ids.map((placeId, index) => ({
          place_id: placeId,
          day_number: 1,
          order_index: index + 1
        }));

        if (existingId) {
          await this.request('/itineraries/' + existingId, { method: 'DELETE', auth: true })
            .catch(() => {});
        }

        const created = await this.request('/itineraries/', {
          method: 'POST',
          auth: true,
          body: {
            title: 'Lịch trình Đà Nẵng',
            total_days: 1,
            items
          }
        });

        store.set('lg_itinerary_server_id_' + this.user()?.email, created.id);
      } catch (error) {
        console.warn('Không đồng bộ được lịch trình lên server:', error.message);
      }
    }

    return { ids };
  },

  async itinerary() {
    return store.get('lg_itinerary_' + this.user()?.email, []);
  }
};

window.API = API;