/* =========================================================
   DA NANG GUIDE - API CLIENT
   - USE_MOCK:true  -> dung data.js + localStorage (demo)
   - USE_MOCK:false -> goi FastAPI that
   - Chat AI luon goi backend /agent/chat (ke ca khi USE_MOCK:true)
   - Yeu thich / lich trinh: dong bo FastAPI backend /favorites va /itineraries
     (kem fallback localStorage khi chua dang nhap)
   ========================================================= */

const CFG = window.LOCAL_GUIDE_CONFIG || {
  USE_MOCK: false,
  API_BASE: '',
  TOKEN_KEY: 'localguide_token',
  GOOGLE_CLIENT_ID: '853984856354-131ekmamkn9sqn75mbckbbm0805ab21m.apps.googleusercontent.com'
};

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

/* Chuyen 1 ban ghi tu backend sang dang giao dien dang dung va lam giau du lieu */
function mapPlace(p) {
  if (!p) return p;

  const addr = p.address || '';
  const parts = addr.split(',').map(s => s.trim()).filter(Boolean);

  // Tim trong DEMO_PLACES de lam giau thong tin chi tiet (activities, highlights, best_time, tips, ticket_price, sourceUrl)
  const demo = (window.DEMO_PLACES || []).find(d =>
    String(d.id) === String(p.id) ||
    (d.name && p.name && (
      d.name.trim().toLowerCase() === p.name.trim().toLowerCase() ||
      p.name.trim().toLowerCase().includes(d.name.trim().toLowerCase()) ||
      d.name.trim().toLowerCase().includes(p.name.trim().toLowerCase())
    ))
  );

  const rawCat = p.rawCategory || p.category || (demo ? (demo.rawCategory || demo.category) : '');
  const catLabel = CATEGORY_LABEL[rawCat] || p.category || (demo ? demo.category : 'Tham quan');

  return {
    ...(demo || {}),
    ...p,
    id: p.id !== undefined ? p.id : (demo ? demo.id : p.id),
    name: p.name || (demo ? demo.name : ''),
    category: catLabel,
    rawCategory: rawCat,
    district: parts.length >= 2 ? parts[parts.length - 2] : ((demo && demo.district) || 'Đà Nẵng'),
    area: (demo && demo.area) || (parts.length >= 2 ? parts[parts.length - 2] : 'Đà Nẵng'),
    address: p.address || (demo && demo.address) || '',
    emoji: (demo && demo.emoji) || CATEGORY_EMOJI[rawCat] || '📍',
    rating: p.rating ?? (demo ? demo.rating : null),
    latitude: p.latitude ?? (demo ? demo.latitude : null),
    longitude: p.longitude ?? (demo ? demo.longitude : null),
    opening_hours: p.opening_hours || (demo ? demo.opening_hours : ''),
    price_level: p.price_level ?? (demo ? demo.price_level : 1),
    ticket_price: (demo && demo.ticket_price) || (p.price_level ? (p.price_level === 1 ? 'Miễn phí / Tiết kiệm' : p.price_level === 2 ? 'Bình dân (~50.000 – 150.000 VNĐ)' : p.price_level === 3 ? 'Trung cấp (~200.000 – 600.000 VNĐ)' : 'Cao cấp (~700.000 – 1.500.000 VNĐ)') : 'Vui lòng xác nhận trước khi đi'),
    activities: (demo && Array.isArray(demo.activities) && demo.activities.length) ? demo.activities : (p.activities || []),
    highlights: (demo && demo.highlights) || p.highlights || '',
    best_time: (demo && demo.best_time) || p.best_time || '',
    tips: (demo && demo.tips) || p.tips || '',
    distanceNote: (demo && demo.distanceNote) || p.distanceNote || '',
    sourceUrl: p.sourceUrl || (demo && demo.sourceUrl) || null
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

    // Tu dong dinh tuyen sang FastAPI cong 8000 neu FE dang mo bang Live Server cong 5500/3000
    let apiBase = CFG.API_BASE || '';
    if (!apiBase && typeof location !== 'undefined' && (location.port === '5500' || location.port === '3000' || location.port === '5173')) {
      apiBase = 'http://127.0.0.1:8000';
    }

    let response;
    try {
      response = await fetch(apiBase + path, {
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

  /* ---------------- Dang nhap bang Google ---------------- */
  async googleLogin({ credential, access_token, email, name, picture, google_id } = {}) {
    if (!CFG.USE_MOCK) {
      const res = await this.request('/auth/google', {
        method: 'POST',
        body: { credential, access_token, email, name, picture, google_id }
      });

      localStorage.setItem(CFG.TOKEN_KEY, res.access_token);

      const user = {
        id: res.user_id,
        name: res.username || (email ? email.split('@')[0] : 'Google User'),
        email: res.email || email,
        role: res.role,
        picture: picture || ''
      };

      store.set('lg_current_user', user);
      return user;
    }

    await delay();
    const gEmail = (email || 'google.user@gmail.com').toLowerCase();
    const gName = name || gEmail.split('@')[0];

    let users = store.get('lg_users', []);
    let user = users.find(x => x.email === gEmail);

    if (!user) {
      user = { id: Date.now(), name: gName, email: gEmail, role: 'user', picture };
      users.push(user);
      store.set('lg_users', users);
    }

    const safe = cleanUser(user);
    store.set('lg_current_user', safe);
    localStorage.setItem(CFG.TOKEN_KEY, 'demo-google-token');
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

  async getProfile() {
    if (!CFG.USE_MOCK) {
      try {
        const u = await this.request('/auth/me', { auth: true });
        const user = {
          id: u.id,
          name: u.username,
          email: u.email,
          role: u.role
        };
        store.set('lg_current_user', user);
        return user;
      } catch {
        return this.user();
      }
    }
    return this.user();
  },

  isLogged() {
    return !!localStorage.getItem(CFG.TOKEN_KEY);
  },

  /* ---------------- Danh sach dia diem ---------------- */
  async places(params = {}) {
    if (!CFG.USE_MOCK) {
      try {
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
      } catch (err) {
        console.warn('Backend /places fetch failed, falling back to DEMO_PLACES:', err);
      }
    }

    await delay();
    const q = (params.q || '').toLocaleLowerCase('vi');

    return (window.DEMO_PLACES || []).map(mapPlace).filter(p =>
      (!q ||
        (
          p.name + ' ' + (p.description || '') + ' ' + (p.district || '') + ' ' +
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
      try {
        const data = await this.request('/places/' + encodeURIComponent(id));
        return mapPlace(data);
      } catch (err) {
        // Fallback sang DEMO_PLACES neu backend khong tim thay ID hoac backend offline
        const demo = (window.DEMO_PLACES || []).find(p => String(p.id) === String(id));
        if (demo) return mapPlace(demo);
        throw err;
      }
    }

    await delay();
    const demo = (window.DEMO_PLACES || []).find(p => String(p.id) === String(id)) || null;
    return demo ? mapPlace(demo) : null;
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
      const query = category && category !== 'all'
        ? `?category=${encodeURIComponent(category)}`
        : '';

      // Co dang nhap thi dung goi y theo so thich, neu loi thi lay danh sach thuong
      try {
        const data = await this.request('/recommendations/for-me', { auth: true });
        let list = normalizePlaces(data).map(mapPlace);
        if (category && category !== 'all') {
          const catLower = category.toLowerCase();
          const filtered = list.filter(p =>
            (p.category && p.category.toLowerCase() === catLower) ||
            (p.rawCategory && p.rawCategory.toLowerCase() === (CATEGORY_TO_DB[category] || category).toLowerCase())
          );
          if (filtered.length) return filtered;
        }
        return list;
      } catch {
        const data = await this.request('/recommendations' + query);
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

  /* ---------------- Yeu thich (Dong bo Backend /favorites + Cache Local) ---------------- */
  async favorites() {
    if (!CFG.USE_MOCK && this.isLogged()) {
      try {
        const ids = await this.request('/favorites', { auth: true });
        if (Array.isArray(ids)) {
          store.set('lg_favorites_' + this.user()?.email, ids);
          return ids;
        }
      } catch (err) {
        console.warn('Khong lay duoc yeu thich tu backend, dung cache:', err.message);
      }
    }

    // Tra ve mang ID de places.js va recommendations.js dung saved.includes(p.id)
    return store.get('lg_favorites_' + this.user()?.email, []);
  },

  async favoritePlaces() {
    if (!CFG.USE_MOCK && this.isLogged()) {
      try {
        const data = await this.request('/favorites/details', { auth: true });
        return normalizePlaces(data).map(mapPlace);
      } catch {}
    }
    const ids = await this.favorites();
    if (!ids.length) return [];
    if (!CFG.USE_MOCK) {
      const results = await Promise.all(
        ids.map(id => this.place(id).catch(() => null))
      );
      return results.filter(Boolean);
    }
    return window.DEMO_PLACES.filter(p => ids.includes(p.id));
  },

  async toggleFavorite(id) {
    const key = 'lg_favorites_' + this.user()?.email;
    let ids = store.get(key, []);

    if (!CFG.USE_MOCK && this.isLogged()) {
      try {
        const res = await this.request('/favorites/' + encodeURIComponent(id), {
          method: 'POST',
          auth: true
        });
        if (res && Array.isArray(res.place_ids)) {
          store.set(key, res.place_ids);
          return res.place_ids;
        }
      } catch (err) {
        console.warn('Khong dong bo duoc yeu thich len server:', err.message);
      }
    }

    ids = ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id];
    store.set(key, ids);
    return ids;
  },

  /* ---------------- Lich trinh (danh sach dia diem da chon) ---------------- */
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
    const local = store.get('lg_itinerary_' + this.user()?.email, []);

    // Neu local chua co nhung da dang nhap API that, thu lay tu server
    if (!CFG.USE_MOCK && this.isLogged() && !local.length) {
      try {
        const data = await this.request('/itineraries/?limit=1', { auth: true });
        const list = data.itineraries || [];
        if (list.length && list[0].id) {
          const detail = await this.request('/itineraries/' + list[0].id, { auth: true });
          const ids = (detail.items || []).map(item => item.place_id).filter(Boolean);
          if (ids.length) {
            store.set('lg_itinerary_' + this.user()?.email, ids);
            store.set('lg_itinerary_server_id_' + this.user()?.email, detail.id);
            return ids;
          }
        }
      } catch (err) {
        console.warn('Khong lay duoc lich trinh tu backend:', err.message);
      }
    }

    return local;
  }
};

window.API = API;