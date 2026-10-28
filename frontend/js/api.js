
/*
  DaNang Guide - frontend/js/api.js

  USE_MOCK = true  : Chạy dữ liệu demo
  USE_MOCK = false : Kết nối Backend của Phương
*/

const CFG = window.LOCAL_GUIDE_CONFIG || {
  USE_MOCK: false,
  API_BASE: 'http://127.0.0.1:8000',
  TOKEN_KEY: 'localguide_token'
};

// ================================
// LOCAL STORAGE
// ================================

const store = {
  get(key, fallback = null) {
    try {
      const value = localStorage.getItem(key);

      return value === null
        ? fallback
        : JSON.parse(value);
    } catch {
      return fallback;
    }
  },

  set(key, value) {
    localStorage.setItem(
      key,
      JSON.stringify(value)
    );
  }
};

const delay = () =>
  new Promise(resolve => setTimeout(resolve, 220));

const normalizePlaces = data =>
  Array.isArray(data)
    ? data
    : (data?.places || data?.items || data?.results || []);

// ================================
// DANH MỤC ĐỊA ĐIỂM
// ================================

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

const TOPIC_WORDS = {
  'Biển': ['biển', 'bãi'],

  'Thiên nhiên': [
    'rừng',
    'núi',
    'đèo',
    'bán đảo',
    'suối',
    'thác',
    'hồ',
    'ghềnh'
  ],

  'Văn hóa': [
    'chùa',
    'bảo tàng',
    'nhà thờ',
    'thánh địa',
    'phố cổ',
    'làng'
  ]
};

// ================================
// CHUẨN HÓA ĐỊA ĐIỂM
// ================================

function mapPlace(place) {
  const rawCategory =
    place.rawCategory || place.category || '';

  const address = place.address || '';

  const parts = address
    .split(',')
    .map(x => x.trim())
    .filter(Boolean);

  const district =
    place.district ||
    (parts.length >= 2
      ? parts[parts.length - 2]
      : 'Đà Nẵng');

  return {
    ...place,

    category:
      CATEGORY_LABEL[rawCategory] ||
      place.category ||
      'Tham quan',

    rawCategory,

    district,

    area: place.area || district,

    emoji:
      place.emoji ||
      CATEGORY_EMOJI[rawCategory] ||
      '📍',

    description: place.description || '',

    activities: Array.isArray(place.activities)
      ? place.activities
      : [],

    latitude:
      place.latitude ?? place.lat ?? null,

    longitude:
      place.longitude ?? place.lng ?? null
  };
}

// ================================
// XỬ LÝ THÔNG BÁO LỖI
// ================================

function errorMessage(data, status) {
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map(item =>
        item.msg ||
        item.message ||
        JSON.stringify(item)
      )
      .join('; ');
  }

  if (typeof data?.detail === 'string') {
    return data.detail;
  }

  if (Array.isArray(data?.details)) {
    return data.details
      .map(item =>
        item.message ||
        item.msg ||
        JSON.stringify(item)
      )
      .join('; ');
  }

  return (
    data?.error ||
    data?.message ||
    `HTTP ${status}`
  );
}

// ================================
// KIỂM TRA JWT TOKEN
// ================================

function validLocalToken(token) {
  if (!token || token === 'demo-token') {
    return false;
  }

  try {
    const parts = token.split('.');

    if (parts.length !== 3) {
      return false;
    }

    const payload = JSON.parse(
      atob(
        parts[1]
          .replace(/-/g, '+')
          .replace(/_/g, '/')
      )
    );

    return (
      !payload.exp ||
      payload.exp * 1000 > Date.now()
    );

  } catch {
    return false;
  }
}

// Kiểm tra ở đây chỉ để cập nhật giao diện.
// Backend vẫn phải xác thực chữ ký và quyền của JWT.

function itineraryIdKey() {
  return (
    'lg_itinerary_server_id_' +
    (API.user()?.email || 'guest')
  );
}

// ================================
// API CHÍNH
// ================================

const API = {

  // ==============================
  // GỬI REQUEST ĐẾN BACKEND
  // ==============================

  async request(
    path,
    {
      method = 'GET',
      body,
      auth = false
    } = {}
  ) {
    const token = localStorage.getItem(
      CFG.TOKEN_KEY
    );

    const headers = {
      Accept: 'application/json'
    };

    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    if (auth && validLocalToken(token)) {
      headers.Authorization = `Bearer ${token}`;
    }

    let response;

    try {

    response = await fetch(
  (CFG.API_BASE || '').replace(/\/$/, '') + path,
  {
    method,
    headers,
    credentials: "include",

    body: body === undefined
      ? undefined
      : JSON.stringify(body)
  }
);


    } catch {
      throw new Error(
        'Không kết nối được Backend. ' +
        'Kiểm tra FastAPI, CORS và API_BASE.'
      );
    }

    const data = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {

      if (response.status === 401 && auth) {
        localStorage.removeItem(CFG.TOKEN_KEY);
        localStorage.removeItem('lg_current_user');
      }

      throw new Error(
        errorMessage(data, response.status)
      );
    }

    return data;
  },

  // ==============================
  // ĐĂNG KÝ TÀI KHOẢN
  // ==============================

  async register(name, email, password) {

    if (!CFG.USE_MOCK) {
      return this.request('/auth/register', {
        method: 'POST',

        body: {
          username: name.trim(),
          email: email.trim(),
          password
        }
      });
    }

    await delay();

    const users = store.get('lg_users', []);

    const normalizedEmail =
      email.trim().toLowerCase();

    if (
      users.some(user =>
        user.email === normalizedEmail
      )
    ) {
      throw new Error(
        'Email đã tồn tại trong dữ liệu demo.'
      );
    }

    users.push({
      id: Date.now(),
      name,
      email: normalizedEmail,
      password
    });

    store.set('lg_users', users);

    return {
      message: 'Đăng ký thành công'
    };
  },

  // ==============================
  // ĐĂNG NHẬP EMAIL
  // ==============================

  async login(email, password) {

    if (!CFG.USE_MOCK) {

      const result = await this.request(
        '/auth/login',
        {
          method: 'POST',

          body: {
            email: email.trim(),
            password
          }
        }
      );

      if (!result.access_token) {
        throw new Error(
          'Backend không trả về JWT token.'
        );
      }

      const user = {
        id: result.user_id,

        name:
          result.username ||
          email.split('@')[0],

        email: result.email || email,

        role: result.role
      };

      localStorage.setItem(
        CFG.TOKEN_KEY,
        result.access_token
      );

      store.set('lg_current_user', user);

      return user;
    }

    // Đăng nhập demo
    await delay();

    const user = store.get(
      'lg_users',
      []
    ).find(item =>
      item.email === email.trim().toLowerCase() &&
      item.password === password
    );

    if (!user) {
      throw new Error(
        'Email hoặc mật khẩu không đúng.'
      );
    }

    const safe = {
      id: user.id,
      name: user.name,
      email: user.email
    };

    store.set('lg_current_user', safe);

    localStorage.setItem(
      CFG.TOKEN_KEY,
      'demo-token'
    );

    return safe;
  },

  // ==============================
  // ĐĂNG XUẤT
  // ==============================

  logout() {
    localStorage.removeItem(
      CFG.TOKEN_KEY
    );

    localStorage.removeItem(
      'lg_current_user'
    );

    sessionStorage.removeItem(
      'danang_oauth_user'
    );

    location.href = 'login.html';
  },

  // ==============================
  // LẤY USER ĐANG ĐĂNG NHẬP
  // ==============================

  user() {
    return store.get(
      'lg_current_user'
    );
  },

  // ==============================
  // KIỂM TRA ĐĂNG NHẬP
  // ==============================


isLogged() {
  const token = localStorage.getItem(CFG.TOKEN_KEY);

  return CFG.USE_MOCK
    ? !!token
    : validLocalToken(token) ||
      this._cookieAuthenticated === true;
},

  // ==============================
  // LẤY THÔNG TIN TÀI KHOẢN
  // ==============================


async getProfile() {

  if (CFG.USE_MOCK) {
    return this.user();
  }

  try {
    const result = await this.request(
      '/auth/me',
      {
        auth: true
      }
    );

    // Backend da xac thuc phien dang nhap
    this._cookieAuthenticated = true;

    const user = {
      id: result.id,

      name:
        result.username ||
        result.name ||
        result.email,

      email: result.email,

      role: result.role
    };

    store.set('lg_current_user', user);

    return user;

  } catch (error) {

    // Khong xac thuc duoc phien
    this._cookieAuthenticated = false;

    if (!this.isLogged()) {
      return null;
    }

    throw error;
  }
},

  // ==============================
  // LẤY DANH SÁCH ĐỊA ĐIỂM
  // ==============================

  async places(params = {}) {

    if (!CFG.USE_MOCK) {

      const category = params.category;

      const query = new URLSearchParams();

      const keyword =
        params.q || params.keyword;

      if (keyword) {
        query.set('keyword', keyword);
      }

      if (
        category &&
        category !== 'all'
      ) {
        query.set(
          'category',
          CATEGORY_TO_DB[category] || category
        );
      }

      query.set('limit', '100');

      const data = await this.request(
        '/places/?' + query.toString()
      );

      let places = normalizePlaces(data)
        .map(mapPlace);

      if (TOPIC_WORDS[category]) {

        const words = TOPIC_WORDS[category];

        places = places.filter(place => {
          const text = (
            `${place.name} ${place.description}`
          ).toLocaleLowerCase('vi');

          return words.some(word =>
            text.includes(word)
          );

        }).map(place => ({
          ...place,
          category
        }));
      }

      return places;
    }

    // Dữ liệu demo
    await delay();

    const q = (
      params.q ||
      params.keyword ||
      ''
    ).toLocaleLowerCase('vi');

    return (
      window.DEMO_PLACES || []
    ).filter(place => {

      const searchable = [
        place.name,
        place.description,
        place.district,
        place.area,
        ...(place.activities || [])
      ]
        .join(' ')
        .toLocaleLowerCase('vi');

      return (
        (!q || searchable.includes(q)) &&
        (
          !params.category ||
          params.category === 'all' ||
          place.category === params.category
        )
      );
    });
  },

  // ==============================
  // LẤY CHI TIẾT MỘT ĐỊA ĐIỂM
  // ==============================

  async place(id) {

    if (!CFG.USE_MOCK) {

      const data = await this.request(
        '/places/' + encodeURIComponent(id)
      );

      return mapPlace(data);
    }

    await delay();

    return (
      window.DEMO_PLACES || []
    ).find(place =>
      String(place.id) === String(id)
    ) || null;
  },

  // ==============================
  // GỢI Ý ĐỊA ĐIỂM
  // ==============================

  async recommend(category = 'all') {

    if (!CFG.USE_MOCK) {

      const query = new URLSearchParams({
        limit: '20'
      });

      if (
        category &&
        category !== 'all'
      ) {
        query.set('category', category);
      }

      const data = await this.request(
        '/recommendations?' +
        query.toString()
      );

      return normalizePlaces(data)
        .map(mapPlace)
        .map(place =>
          TOPIC_WORDS[category]
            ? { ...place, category }
            : place
        );
    }

    const places = await this.places({
      category
    });

    return places.slice(0, 4);
  },

  // ==============================
  // CHAT AI
  // ==============================

  async chat(message) {

    if (!CFG.USE_MOCK) {

      const result = await this.request(
        '/agent/chat',
        {
          method: 'POST',

          body: {
            message: String(message).trim()
          }
        }
      );

      return (
        result.reply ||
        result.answer ||
        result.response ||
        'AI chưa trả về nội dung.'
      );
    }

    await delay();

    const places = (
      window.DEMO_PLACES || []
    ).slice(0, 3);

    return (
      '🤖 Chế độ demo — chưa gọi AI thật.\n\n' +
      'Gợi ý: ' +
      places.map(p => p.name).join(', ') +
      '.'
    );
  },

  // ==============================
  // DANH SÁCH YÊU THÍCH
  // ==============================

  async favorites() {

    if (!CFG.USE_MOCK) {

      const ids = await this.request(
        '/favorites',
        {
          auth: true
        }
      );

      return Array.isArray(ids)
        ? ids
        : [];
    }

    return store.get(
      'lg_favorites_' +
      (this.user()?.email || 'guest'),
      []
    );
  },

  // ==============================
  // THÊM / XÓA YÊU THÍCH
  // ==============================

  async toggleFavorite(id) {

    if (!CFG.USE_MOCK) {

      const result = await this.request(
        '/favorites/' +
        encodeURIComponent(id),
        {
          method: 'POST',
          auth: true
        }
      );

      return Array.isArray(
        result.place_ids
      )
        ? result.place_ids
        : [];
    }

    const key =
      'lg_favorites_' +
      (this.user()?.email || 'guest');

    let ids = store.get(key, []);

    const numericId = Number(id);

    ids = ids.includes(numericId)
      ? ids.filter(x => x !== numericId)
      : [...ids, numericId];

    store.set(key, ids);

    return ids;
  },

  // ==============================
  // LẤY LỊCH TRÌNH
  // ==============================

  async itinerary() {

    if (CFG.USE_MOCK) {
      return store.get(
        'lg_itinerary_' +
        (this.user()?.email || 'guest'),
        []
      );
    }

    const list = await this.request(
      '/itineraries/?limit=50',
      {
        auth: true
      }
    );

    const savedId = store.get(
      itineraryIdKey()
    );

    const records = list.itineraries || [];

    const selected =
      records.find(x => x.id === savedId) ||
      records.find(x =>
        x.title === 'Lịch trình Đà Nẵng'
      );

    if (!selected) {
      return [];
    }

    store.set(
      itineraryIdKey(),
      selected.id
    );

    const detail = await this.request(
      '/itineraries/' + selected.id,
      {
        auth: true
      }
    );

    return (
      detail.items || []
    )
      .filter(item =>
        item.place_id != null
      )
      .sort((a, b) =>
        (a.day_number - b.day_number) ||
        (a.order_index - b.order_index)
      )
      .map(item => item.place_id);
  },

  // ==============================
  // LƯU LỊCH TRÌNH
  // ==============================

  async saveItinerary(ids) {

    const uniqueIds = [
      ...new Set(ids.map(Number))
    ].filter(Number.isInteger);

    if (CFG.USE_MOCK) {

      store.set(
        'lg_itinerary_' +
        (this.user()?.email || 'guest'),
        uniqueIds
      );

      return {
        ids: uniqueIds
      };
    }

    // Tìm lịch trình cũ
    const records = await this.request(
      '/itineraries/?limit=50',
      {
        auth: true
      }
    );

    const savedId = store.get(
      itineraryIdKey()
    );

    const current =
      (
        records.itineraries || []
      ).find(x => x.id === savedId) ||

      (
        records.itineraries || []
      ).find(x =>
        x.title === 'Lịch trình Đà Nẵng'
      );

    // Nếu đã có lịch trình, kiểm tra ID
    if (current) {

      const detail = await this.request(
        '/itineraries/' + current.id,
        {
          auth: true
        }
      );

      const oldIds = (
        detail.items || []
      )
        .filter(item =>
          item.place_id != null
        )
        .sort((a, b) =>
          (a.day_number - b.day_number) ||
          (a.order_index - b.order_index)
        )
        .map(item => item.place_id);

      // Không lưu lại nếu không thay đổi
      if (
        JSON.stringify(oldIds) ===
        JSON.stringify(uniqueIds)
      ) {
        return {
          ids: uniqueIds
        };
      }
    }

    // Xóa lịch trình nếu không còn địa điểm
    if (uniqueIds.length === 0) {

      if (current) {
        await this.request(
          '/itineraries/' + current.id,
          {
            method: 'DELETE',
            auth: true
          }
        );
      }

      localStorage.removeItem(
        itineraryIdKey()
      );

      return {
        ids: []
      };
    }

    // Tạo lịch trình mới
    const created = await this.request(
      '/itineraries/',
      {
        method: 'POST',
        auth: true,

        body: {
          title: 'Lịch trình Đà Nẵng',

          total_days: 1,

          items: uniqueIds.map(
            (placeId, index) => ({
              place_id: placeId,
              day_number: 1,
              order_index: index + 1
            })
          )
        }
      }
    );

    store.set(
      itineraryIdKey(),
      created.id
    );

    // Chỉ xóa lịch trình cũ sau khi
    // tạo lịch trình mới thành công
    if (
      current &&
      current.id !== created.id
    ) {
      try {

        await this.request(
          '/itineraries/' + current.id,
          {
            method: 'DELETE',
            auth: true
          }
        );

      } catch (error) {
        console.warn(
          'Đã lưu lịch trình mới nhưng ' +
          'chưa xóa được bản cũ:',
          error
        );
      }
    }

    return {
      ids: uniqueIds,
      id: created.id
    };
  }

};

// ================================
// CHO CÁC FILE JS KHÁC SỬ DỤNG
// ================================

window.API = API;
