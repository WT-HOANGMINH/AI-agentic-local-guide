
/* =========================================
   DA NANG GUIDE - COMMON JAVASCRIPT
========================================= */

// ===== HAM TIEN ICH =====

const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];

const esc = s => String(s ?? '').replace(
  /[&<>"']/g,
  c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c])
);


// ===== HIEN THI THONG BAO =====

function flash(message, type = 'danger', target = '#message') {
  const box = $(target);

  if (box) {
    box.innerHTML = `
      <div class="alert alert-${type}" role="alert">
        ${esc(message)}
      </div>
    `;

    box.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest'
    });
  }
}


// ===== KIEM TRA DANG NHAP =====

function protect() {
  if (!API.isLogged()) {
    location.replace('login.html');
    return false;
  }
  return true;
}


// =========================================
// ANH DIA DIEM
// =========================================

const placeImages = {
  "Cầu Rồng": "images/caurong.jpg",
  "Bãi biển Mỹ Khê": "images/bien-my-khe-da-nang.jpg",
  "Ngũ Hành Sơn": "images/nguhanhson.jpg",
  "Bán đảo Sơn Trà": "images/Ban-dao-son-tra.jpg",
  "Bảo tàng Điêu khắc Chăm": "images/bao-tang-dieu-khac-cham.jpg",
  "Chợ Hàn": "images/chohan.jpg",
  "Cầu Tình Yêu": "images/cautinhyeu.webp",
  "Đỉnh Bàn Cờ": "images/dinhbanco.jpg",
  "Ghềnh Bàng": "images/ghenhbang.jpg",
  "Bãi Bụt": "images/baibut.png",
  "Mũi Nghê": "images/Muinghe.webp",
  "Hải đăng Tiên Sa": "images/haidangtiensa.jpg",
  "Nhất Lâm Thủy Trang Trà": "images/nhatlamthuytrangtra.jpg",
  "Cầu vòm Đồn Cả": "images/cauvomdonca.jpg",
  "Thác Ba Đờ Phọt": "images/thacbadophot.jpg",
  "Hồ Hòa Trung": "images/hohoatrung.jpg",
  "Giếng Trời": "images/giengtroi.webp",
  "Bãi Rạn Nam Ô": "images/rannamo.webp",
  "Rừng thông Bồ Bồ": "images/rungthongbobo.jpg",
  "Thánh địa Mỹ Sơn": "images/thanhdiamyson.jpg",
  "Công viên Văn hóa Ấn Tượng Hội An": "images/congvienantuonghoian.jpg",
  "Mì Quảng Bà Mua": "images/miquangbamua.png",
  "Trình Cà Phê": "images/trinhcaphe.jpg",
  "Wonderlust Danang": "images/wonderlustdanang.png",
  "Sun World Bà Nà Hills và Cầu Vàng": "images/banahills.jpg",
  "Chùa Linh Ứng Sơn Trà": "images/chualinhung.jpg",
  "Bãi biển Non Nước": "images/biennonnuoc.jpg",
  "Nhà thờ Chính tòa Đà Nẵng": "images/nhathochinhtoa.png",
  "Làng đá mỹ nghệ Non Nước": "images/langdamynghenonnuoc.png",
  "Đèo Hải Vân": "images/deohaivan.jpg",
  "Biển An Bàng": "images/bienanbang.png",
  "Làng gốm Thanh Hà": "images/langgomthanhha.jpg",
  "Công viên Đất nung Thanh Hà": "images/congviendatnungthanhha.png",
  "Làng rau Trà Quế": "images/langrautraque.jpg",
  "Bánh xèo Bà Dưỡng": "images/banhxeobaduong.jpg",
  "Bánh tráng cuốn thịt heo Trần": "images/banhtrangcuonthitheotran.jpg",
  "Bún chả cá Nguyễn Chí Thanh": "images/bunchacanguyenchithanh.png",
  "Bánh mì Phượng": "images/banhmiphuong.jpg",
  "Cao lầu Thanh": "images/caolauthanh.jpg",
  "Cơm gà Bà Buội": "images/comgababuoi.png",
  "Cộng Cà Phê Bạch Đằng": "images/congcaphebachdang.jpg",
  "Hội An Roastery": "images/hoianroastery.png",
  "Faifo Coffee": "images/faifocoffee.png",
  "Chợ Cồn": "images/chocon.png",
  "Chợ đêm Sơn Trà": "images/chodemsontra.jpg",
  "Chợ Hội An": "images/chohoian.png",
  "Chợ đêm Hội An": "images/chodemhoian.png",
  "Phố cổ Hội An": "images/phocohoian.jpg",
  "Phố cổ Hộ An": "images/phocohoian.jpg",
  "Chùa Cầu Hội An": "images/chuacauhoian.jpg",
  "Rừng dừa Bảy Mẫu": "images/rungduabaymau.jpg",
  "Bãi Bắc": "images/vinhbaibac.jpg",
  "Cộng Cà Phê": "images/congcaphebachdang.jpg",
  "Bánh cuốn thịt heo Trần": "images/banhtrangcuonthitheotran.jpg",
  "Faifo coffe": "images/faifocoffee.png",
  "faifo coffe": "images/faifocoffee.png"
};


const placeImageAliases = {
  'Phố cổ Hộ An': 'Phố cổ Hội An',
  'phố cổ hộ an': 'Phố cổ Hội An',
  'faifo coffe': 'Faifo Coffee',
  'Faifo coffe': 'Faifo Coffee',
  'Bánh cuốn thịt heo Trần': 'Bánh tráng cuốn thịt heo Trần',
  'bánh cuốn thịt heo trần': 'Bánh tráng cuốn thịt heo Trần',
  'Bãi Biển Nam Ô': 'Bãi Rạn Nam Ô',
  'Bãi Biển Mỹ Khê': 'Bãi biển Mỹ Khê',
  'Bãi biển Nam Ô': 'Bãi Rạn Nam Ô',
  'Bãi Bụt Sơn Trà': 'Bãi Bụt',
  'Bảo tàng Điêu khắc Chăm': 'Bảo tàng Điêu khắc Chăm',
  'Cầu Rồng Đà Nẵng': 'Cầu Rồng',
  'Cầu Tình Yêu Đà Nẵng': 'Cầu Tình Yêu',
  'Cầu vòm Đồn Cả': 'Cầu vòm Đồn Cả',
  'Chợ Hàn': 'Chợ Hàn',
  'Đỉnh Bàn Cờ': 'Đỉnh Bàn Cờ',
  'Ghềnh Bàng': 'Ghềnh Bàng',
  'Hồ Hòa Trung': 'Hồ Hòa Trung',
  'Mũi Nghê': 'Mũi Nghê',
  'Ngọn Thủy Sơn (Ngũ Hành Sơn)': 'Ngũ Hành Sơn',
  'Thánh địa Mỹ Sơn': 'Thánh địa Mỹ Sơn',
  'Bán đảo Sơn Trà': 'Bán đảo Sơn Trà',
  'Mỳ Quảng Bà Mua': 'Mì Quảng Bà Mua',
  'Mỳ quảng bà mua': 'Mì Quảng Bà Mua',
  'Mì Quảng': 'Mì Quảng Bà Mua',
  'Mỳ Quảng': 'Mì Quảng Bà Mua',
  'Mì Quảng Bà Mua - Trần Bình Trọng': 'Mì Quảng Bà Mua',
  'Trình Cà Phê - Không Gian Xanh & Vintage': 'Trình Cà Phê',
  'Trình Cafe': 'Trình Cà Phê',
  'Trình cafe': 'Trình Cà Phê',
  'Trinh Ca Phe': 'Trình Cà Phê',
  'Wonderlust': 'Wonderlust Danang',
  'Wonderlust Danang - Cà phê Concept': 'Wonderlust Danang',
  'Wonderlust Danang - Concept Cafe': 'Wonderlust Danang',
  'Wonderlust Cafe': 'Wonderlust Danang',
  'Wonderlust cafe': 'Wonderlust Danang',
  'Wonderlust Đà Nẵng': 'Wonderlust Danang',
  'Sun World Bà Nà Hills & Cầu Vàng': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Sun World Bà Nà Hills': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Bà Nà Hills và Cầu Vàng': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Bà Nà Hills': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Ba Na Hills': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Bà Nà': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Cầu Vàng': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Cầu Vàng Bà Nà Hills': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Cầu Vàng - Bà Nà Hills': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Golden Bridge': 'Sun World Bà Nà Hills và Cầu Vàng',
  'Chùa Linh Ứng - Bán Đảo Sơn Trà': 'Chùa Linh Ứng Sơn Trà',
  'Chùa Linh Ứng': 'Chùa Linh Ứng Sơn Trà',
  'Chùa Linh Ứng Bãi Bụt': 'Chùa Linh Ứng Sơn Trà',
  'Chùa Linh Ứng (Bãi Bụt)': 'Chùa Linh Ứng Sơn Trà',
  'Chùa Linh Ứng - Bãi Bụt': 'Chùa Linh Ứng Sơn Trà',
  'Chua Linh Ung': 'Chùa Linh Ứng Sơn Trà',
  'Linh Ứng Tự': 'Chùa Linh Ứng Sơn Trà',
  'Tượng Phật Bà Quan Âm': 'Chùa Linh Ứng Sơn Trà',
  'Bãi Biển Non Nước': 'Bãi biển Non Nước',
  'Biển Non Nước': 'Bãi biển Non Nước',
  'Bãi tắm Non Nước': 'Bãi biển Non Nước',
  'Non Nuoc Beach': 'Bãi biển Non Nước',
  'Nhà thờ Chính Tòa Đà Nẵng': 'Nhà thờ Chính tòa Đà Nẵng',
  'Nhà thờ Con Gà': 'Nhà thờ Chính tòa Đà Nẵng',
  'Nhà thờ Con Gà Đà Nẵng': 'Nhà thờ Chính tòa Đà Nẵng',
  'Nhà thờ Chính tòa': 'Nhà thờ Chính tòa Đà Nẵng',
  'Nhà thờ Chính Tòa': 'Nhà thờ Chính tòa Đà Nẵng',
  'Da Nang Cathedral': 'Nhà thờ Chính tòa Đà Nẵng',
  'Làng Đá Mỹ Nghệ Non Nước': 'Làng đá mỹ nghệ Non Nước',
  'Làng đá Non Nước': 'Làng đá mỹ nghệ Non Nước',
  'Làng Đá Non Nước': 'Làng đá mỹ nghệ Non Nước',
  'Làng nghề đá Non Nước': 'Làng đá mỹ nghệ Non Nước',
  'Làng điêu khắc đá Non Nước': 'Làng đá mỹ nghệ Non Nước',
  'Non Nuoc Stone Carving Village': 'Làng đá mỹ nghệ Non Nước',
  'Deo Hai Van': 'Đèo Hải Vân',
  'Đèo Hải Vân Đà Nẵng': 'Đèo Hải Vân',
  'Hai Van Pass': 'Đèo Hải Vân',
  'Bãi biển An Bàng': 'Biển An Bàng',
  'Bãi Biển An Bàng': 'Biển An Bàng',
  'An Bang Beach': 'Biển An Bàng',
  'Làng Gốm Thanh Hà': 'Làng gốm Thanh Hà',
  'Làng gốm Thanh Hà Hội An': 'Làng gốm Thanh Hà',
  'Thanh Ha Pottery Village': 'Làng gốm Thanh Hà',
  'Làng Rau Trà Quế': 'Làng rau Trà Quế',
  'Làng rau Trà Quế Hội An': 'Làng rau Trà Quế',
  'Tra Que Vegetable Village': 'Làng rau Trà Quế',
  'Bánh Xèo Bà Dưỡng': 'Bánh xèo Bà Dưỡng',
  'Bánh Xèo Tôm Nhảy Bà Dưỡng': 'Bánh xèo Bà Dưỡng',
  'Bánh xèo tôm nhảy Bà Dưỡng': 'Bánh xèo Bà Dưỡng',
  'Bánh xèo Bà Dưỡng - Hoàng Diệu': 'Bánh xèo Bà Dưỡng',
  'Banh xeo Ba Duong': 'Bánh xèo Bà Dưỡng',
  'Ba Duong Sizzling Pancake': 'Bánh xèo Bà Dưỡng',
  'Bánh Tráng Cuốn Thịt Heo Trần': 'Bánh tráng cuốn thịt heo Trần',
  'Bánh tráng thịt heo Trần': 'Bánh tráng cuốn thịt heo Trần',
  'Bánh Tráng Thịt Heo Trần': 'Bánh tráng cuốn thịt heo Trần',
  'Thịt heo Trần': 'Bánh tráng cuốn thịt heo Trần',
  'Ẩm thực Trần': 'Bánh tráng cuốn thịt heo Trần',
  'Banh trang cuon thit heo Tran': 'Bánh tráng cuốn thịt heo Trần',
  'Bún Chả Cá Nguyễn Chí Thanh': 'Bún chả cá Nguyễn Chí Thanh',
  'Bún chả cá 109 Nguyễn Chí Thanh': 'Bún chả cá Nguyễn Chí Thanh',
  'Bún chả cá Nguyễn Chí Thanh Đà Nẵng': 'Bún chả cá Nguyễn Chí Thanh',
  'Bun cha ca Nguyen Chi Thanh': 'Bún chả cá Nguyễn Chí Thanh',
  'Bánh Mì Phượng': 'Bánh mì Phượng',
  'bánh mì Phượng': 'Bánh mì Phượng',
  'Bánh mì Phượng Hội An': 'Bánh mì Phượng',
  'Banh mi Phuong': 'Bánh mì Phượng',
  'Banh Mi Phuong Hoi An': 'Bánh mì Phượng',
  'Cao Lầu Thanh': 'Cao lầu Thanh',
  'cao lầu thanh': 'Cao lầu Thanh',
  'Cao lầu Thanh Hội An': 'Cao lầu Thanh',
  'Cao Lầu Thanh Hội An': 'Cao lầu Thanh',
  'Thanh Cao Lầu': 'Cao lầu Thanh',
  'Cao lau Thanh': 'Cao lầu Thanh',
  'Cơm Gà Bà Buội': 'Cơm gà Bà Buội',
  'Cơm gà Bà Buội Hội An': 'Cơm gà Bà Buội',
  'Com ga Ba Buoi': 'Cơm gà Bà Buội',
  'Cộng Cà Phê': 'Cộng Cà Phê Bạch Đằng',
  'Cộng Cafe': 'Cộng Cà Phê Bạch Đằng',
  'Cộng cafe': 'Cộng Cà Phê Bạch Đằng',
  'Cong Ca Phe': 'Cộng Cà Phê Bạch Đằng',
  'Cong Cafe': 'Cộng Cà Phê Bạch Đằng',
  'Cộng Cà Phê - Bạch Đằng': 'Cộng Cà Phê Bạch Đằng',
  'Cộng Cà Phê 96 Bạch Đằng': 'Cộng Cà Phê Bạch Đằng',
  'Hoi An Roastery': 'Hội An Roastery',
  'Hội An Roastery - Espresso & Coffee House': 'Hội An Roastery',
  'Hoi An Roastery Espresso & Coffee House': 'Hội An Roastery',
  'Xưởng cà phê rang xay Hội An': 'Hội An Roastery',
  'Faifo Cafe': 'Faifo Coffee',
  'Faifo coffee': 'Faifo Coffee',
  'Cà phê Faifo': 'Faifo Coffee',
  'Faifo Coffee Hội An': 'Faifo Coffee',
  'Faifo Coffee 130 Trần Phú': 'Faifo Coffee',
  'Chợ Cồn Đà Nẵng': 'Chợ Cồn',
  'chợ cồn': 'Chợ Cồn',
  'Cho Con': 'Chợ Cồn',
  'Cho Con Da Nang': 'Chợ Cồn',
  'Con Market': 'Chợ Cồn',
  'Chợ Đêm Sơn Trà': 'Chợ đêm Sơn Trà',
  'chợ đên sơn trà': 'Chợ đêm Sơn Trà',
  'chợ đêm sơn trà': 'Chợ đêm Sơn Trà',
  'Cho Dem Son Tra': 'Chợ đêm Sơn Trà',
  'Son Tra Night Market': 'Chợ đêm Sơn Trà',
  'Cho Hoi An': 'Chợ Hội An',
  'chợ hội an': 'Chợ Hội An',
  'Hoi An Market': 'Chợ Hội An',
  'Hoi An Central Market': 'Chợ Hội An',
  'Chợ Đêm Hội An': 'Chợ đêm Hội An',
  'chợ đêm hội an': 'Chợ đêm Hội An',
  'Cho Dem Hoi An': 'Chợ đêm Hội An',
  'Hoi An Night Market': 'Chợ đêm Hội An',
  'Chợ đêm Nguyễn Hoàng': 'Chợ đêm Hội An',
  'Pho Co Hoi An': 'Phố cổ Hội An',
  'pho co hoi an': 'Phố cổ Hội An',
  'Hoi An Ancient Town': 'Phố cổ Hội An',
  'Phố Cổ Hội An': 'Phố cổ Hội An',
  'Rung Dua Bay Mau': 'Rừng dừa Bảy Mẫu',
  'rung dua bay mau': 'Rừng dừa Bảy Mẫu',
  'Rừng Dừa Bảy Mẫu': 'Rừng dừa Bảy Mẫu',
  'Rừng dừa Cẩm Thanh': 'Rừng dừa Bảy Mẫu',
  'Rừng Dừa Cẩm Thanh': 'Rừng dừa Bảy Mẫu',
  'Bay Mau Coconut Forest': 'Rừng dừa Bảy Mẫu',
  'Ấn Tượng Hội An': 'Công viên Văn hóa Ấn Tượng Hội An',
  'Công viên Ấn Tượng Hội An': 'Công viên Văn hóa Ấn Tượng Hội An',
  'Ký Ức Hội An': 'Công viên Văn hóa Ấn Tượng Hội An',
  'Hoi An Memories Land': 'Công viên Văn hóa Ấn Tượng Hội An',
  'Bãi biển An Bàng': 'Biển An Bàng',
  'An Bang Beach': 'Biển An Bàng',
  'Thanh Ha Pottery Village': 'Làng gốm Thanh Hà',
  'Làng Gốm Thanh Hà': 'Làng gốm Thanh Hà',
  'Công viên đất nung Thanh Hà': 'Công viên Đất nung Thanh Hà',
  'Công viên Đất nung Thanh Hà': 'Công viên Đất nung Thanh Hà',
  'Công viên Đất Nung Thanh Hà': 'Công viên Đất nung Thanh Hà',
  'Thanh Ha Terracotta Park': 'Công viên Đất nung Thanh Hà',
  'Chùa Cầu': 'Chùa Cầu Hội An',
  'Chùa Cầu Hội An': 'Chùa Cầu Hội An',
  'Chùa cầu Hội An': 'Chùa Cầu Hội An',
  'chùa cầu hội an': 'Chùa Cầu Hội An',
  'chùa cầu': 'Chùa Cầu Hội An',
  'Chua Cau': 'Chùa Cầu Hội An',
  'Chua Cau Hoi An': 'Chùa Cầu Hội An',
  'Japanese Covered Bridge': 'Chùa Cầu Hội An',
  'Japanese Bridge': 'Chùa Cầu Hội An',
  'Bãi Bụt Sơn Trà': 'Bãi Bụt',
  'Bai But': 'Bãi Bụt',
  'Bai But Bay': 'Bãi Bụt',
  'Bai But Son Tra': 'Bãi Bụt',
  'Vịnh Bãi Bắc': 'Bán đảo Sơn Trà',
  'Bãi Bắc': 'Bán đảo Sơn Trà'
};




// Lay anh dua theo ten dia diem
function getPlaceImage(p) {
  if (!p) return "";

  const rawName = String(p.name || '').trim();
  if (rawName) {
    const aliasName = placeImageAliases[rawName] || rawName;
    if (placeImages[aliasName]) return placeImages[aliasName];
    if (placeImages[rawName]) return placeImages[rawName];

    // Khớp thông minh theo chữ thường / tên phụ
    const nameLower = rawName.toLowerCase();
    for (const [key, imgPath] of Object.entries(placeImages)) {
      const keyLower = key.toLowerCase();
      if (nameLower === keyLower || nameLower.includes(keyLower) || keyLower.includes(nameLower)) {
        return imgPath;
      }
    }

    for (const [alias, target] of Object.entries(placeImageAliases)) {
      const aLower = alias.toLowerCase();
      if (nameLower === aLower || nameLower.includes(aLower) || aLower.includes(nameLower)) {
        if (placeImages[target]) return placeImages[target];
      }
    }
  }

  // Fallback: nếu không có trong placeImages nhưng đối tượng có ảnh riêng
  if (p.image) return p.image;

  return "";
}



// =========================================
// BỘ CHUYỂN ĐỔI NGÔN NGỮ (VI / EN)
// =========================================

const LANG_STORAGE_KEY = 'localguide_lang';

function getLang() {
  try {
    return localStorage.getItem(LANG_STORAGE_KEY) === 'en' ? 'en' : 'vi';
  } catch {
    return 'vi';
  }
}

function setLang(lang) {
  const target = lang === 'en' ? 'en' : 'vi';
  try {
    localStorage.setItem(LANG_STORAGE_KEY, target);
  } catch {}

  document.documentElement.lang = target;

  // Cập nhật lại thanh điều hướng và footer
  renderNav();
  renderFooter();

  // Dịch các thành phần trên trang
  applyPageTranslations(target);

  // Gọi dịch i18n nếu có
  if (window.i18n && typeof window.i18n.setLang === 'function') {
    window.i18n.setLang(target);
  }

  // Bắn sự kiện tùy chỉnh cho các trang (places, place-detail, map, chat, v.v.)
  window.dispatchEvent(
    new CustomEvent('languageChanged', { detail: { lang: target } })
  );
}

// Bảng dịch địa danh sang tiếng Anh cho 21 địa điểm chuẩn
const PLACE_NAME_MAP_EN = {
  'Cầu Rồng': {
    name: 'Dragon Bridge',
    description: 'Iconic bridge arching over the Han River, famous for breathing fire and water on weekend nights.',
    district: 'Hai Chau'
  },
  'Bãi biển Mỹ Khê': {
    name: 'My Khe Beach',
    description: "Voted by Forbes as one of the most attractive beaches on the planet with soft white sand and gentle blue waves.",
    district: 'Son Tra'
  },
  'Ngũ Hành Sơn': {
    name: 'Marble Mountains',
    description: 'Cluster of five limestone and marble hills featuring sacred Buddhist shrines, natural grottos, and panoramic peaks.',
    district: 'Ngu Hanh Son'
  },
  'Bán đảo Sơn Trà': {
    name: 'Son Tra Peninsula',
    description: 'Lush natural reserve dubbed the Green Lung of Da Nang, home to endangered red-shanked douc langurs.',
    district: 'Son Tra'
  },
  'Bảo tàng Điêu khắc Chăm': {
    name: 'Cham Sculpture Museum',
    description: "The world's largest collection of Cham sandstone and terracotta sculptures and religious relics.",
    district: 'Hai Chau'
  },
  'Chợ Hàn': {
    name: 'Han Market',
    description: 'Historic vibrant central market offering famous Da Nang specialty foods, dried seafood, and souvenirs.',
    district: 'Hai Chau'
  },
  'Cầu Tình Yêu': {
    name: 'Love Bridge Pier',
    description: 'Romantic riverside boardwalk adorned with red heart lanterns and padlocks overlooking Da Nang skyline.',
    district: 'Son Tra'
  },
  'Đỉnh Bàn Cờ': {
    name: 'Ban Co Peak',
    description: 'The highest summit on Son Tra Peninsula with a legendary fairy chessboard overlooking the entire city.',
    district: 'Son Tra'
  },
  'Ghềnh Bàng': {
    name: 'Ghenh Bang Coastal Reef',
    description: 'Pristine coastal reef with crystal clear turquoise water, ideal for snorkeling and wild camping.',
    district: 'Son Tra'
  },
  'Bãi Bụt': {
    name: 'Bai But Bay',
    description: 'Serene sea-facing cove nestled at the foot of Linh Ung Pagoda and the giant Lady Buddha statue.',
    district: 'Son Tra'
  },
  'Mũi Nghê': {
    name: 'Mui Nghe Cape',
    description: 'The easternmost point of Da Nang Peninsula, renowned for sunrise views and natural ocean whirlpools.',
    district: 'Son Tra'
  },
  'Hải đăng Tiên Sa': {
    name: 'Tien Sa Lighthouse',
    description: 'Classic French colonial lighthouse standing atop dramatic cliffs with an infinite horizon view.',
    district: 'Son Tra'
  },
  'Nhất Lâm Thủy Trang Trà': {
    name: 'Nhat Lam Thuy Trang Tra',
    description: 'Peaceful ecological forest valley nestled inside the jungle of Son Tra Peninsula.',
    district: 'Son Tra'
  },
  'Cầu vòm Đồn Cả': {
    name: 'Don Ca Arch Bridge',
    description: 'Picturesque historic railway arch bridge tucked beneath the Hai Van Pass amidst cascading streams.',
    district: 'Hai Van Pass'
  },
  'Thác Ba Đờ Phọt': {
    name: 'Ba Do Phot Waterfall',
    description: 'Untouched multi-tiered jungle waterfall offering refreshing rock pools for adventure trekking.',
    district: 'Hoa Vang'
  },
  'Hồ Hòa Trung': {
    name: 'Hoa Trung Lake',
    description: 'Tranquil freshwater reservoir with scenic grasslands, popular for canoeing and camping escapes.',
    district: 'Hoa Vang'
  },
  'Giếng Trời': {
    name: 'Gieng Troi (Sky Well)',
    description: 'Enchanting natural mountain spring pool with a 25-meter waterfall hidden in primeval forest.',
    district: 'Hoa Vang'
  },
  'Bãi Rạn Nam Ô': {
    name: 'Nam O Mossy Reef',
    description: 'Ancient coastal rock reef blanketed in green velvet moss, famous for traditional raw fish salad (Goi ca).',
    district: 'Lien Chieu'
  },
  'Rừng thông Bồ Bồ': {
    name: 'Bo Bo Pine Hill',
    description: 'Cool pine-covered hilltop reminiscent of Da Lat, perfect for picnics and sunset photography.',
    district: 'Dien Ban'
  },
  'Thánh địa Mỹ Sơn': {
    name: 'My Son Sanctuary',
    description: 'UNESCO World Heritage site featuring monumental ancient Hindu temple ruins of the Champa Kingdom.',
    district: 'Duy Xuyen'
  },
  'Công viên Văn hóa Ấn Tượng Hội An': {
    name: 'Hoi An Memories Land',
    description: 'World-renowned cultural theme park featuring the largest outdoor performance show in Vietnam.',
    district: 'Hoi An'
  },
  'Mì Quảng Bà Mua': {
    name: 'Ba Mua Quang Noodles',
    description: 'Traditional Quang-style noodles with savory shrimp, pork, quail eggs, native chicken, fresh herbs, and toasted sesame rice crackers.',
    district: 'Hai Chau'
  },
  'Trình Cà Phê': {
    name: 'Trinh Coffee - Greenery & Vintage Vibe',
    description: 'Rustic cafe with vintage decor serving signature rich avocado coffee, featuring a tranquil garden to work and relax.',
    district: 'Hai Chau'
  },
  'Wonderlust Danang': {
    name: 'Wonderlust Danang - Concept Cafe',
    description: 'Modern open-concept cafe bathed in natural sunlight through a soaring glass ceiling, serving refreshing craft drinks and pastries.',
    district: 'Hai Chau'
  },
  'Sun World Bà Nà Hills và Cầu Vàng': {
    name: 'Sun World Ba Na Hills & Golden Bridge',
    description: 'World-famous mountaintop resort featuring the iconic Golden Bridge held by giant stone hands, French Village, and Guinness-record cable cars.',
    district: 'Hoa Vang'
  },
  'Chùa Linh Ứng Sơn Trà': {
    name: 'Linh Ung Pagoda Son Tra',
    description: 'Serene Buddhist sanctuary overlooking the ocean with a towering 67-meter Lady Buddha statue gazing upon Da Nang Bay.',
    district: 'Son Tra'
  },
  'Bãi biển Non Nước': {
    name: 'Non Nuoc Beach',
    description: 'Pristine beach with silky white sand and calm azure waters nestled at the foot of the Marble Mountains.',
    district: 'Ngu Hanh Son'
  },
  'Nhà thờ Chính tòa Đà Nẵng': {
    name: 'Da Nang Cathedral (Pink Church)',
    description: 'Historic French Gothic cathedral with distinctive pastel pink facade and a rooster weathercock atop its steeple.',
    district: 'Hai Chau'
  },
  'Làng đá mỹ nghệ Non Nước': {
    name: 'Non Nuoc Stone Carving Village',
    description: 'Centuries-old artisanal craft village renowned for intricate marble sculptures, Buddha statues, and fine stone jewelry.',
    district: 'Ngu Hanh Son'
  },
  'Đèo Hải Vân': {
    name: 'Hai Van Pass',
    description: 'Breathtaking coastal mountain pass with winding cliffside roads offering panoramic vistas of Da Nang Bay and Lang Co Lagoon.',
    district: 'Lien Chieu'
  },
  'Biển An Bàng': {
    name: 'An Bang Beach',
    description: 'Serene beach famous for fine sand, gentle turquoise surf, rustic seaside cafes, and relaxed bohemian atmosphere near Hoi An.',
    district: 'Hoi An'
  },
  'Làng gốm Thanh Hà': {
    name: 'Thanh Ha Pottery Village',
    description: 'Over 500-year-old terracotta craft village along the Thu Bon River where visitors can shape their own clay pottery.',
    district: 'Hoi An'
  },
  'Làng rau Trà Quế': {
    name: 'Tra Que Herb & Vegetable Village',
    description: 'Charming organic farming village celebrated for cultivating fragrant culinary herbs using traditional algae fertilizers.',
    district: 'Hoi An'
  },
  'Bánh xèo Bà Dưỡng': {
    name: 'Ba Duong Sizzling Pancake',
    description: 'Legendary eatery hidden in an alleyway, famous for crispy stuffed rice crepes, grilled pork skewers, and signature rich peanut liver dipping sauce.',
    district: 'Hai Chau'
  },
  'Bánh tráng cuốn thịt heo Trần': {
    name: 'Tran Special Pork Rolled in Rice Paper',
    description: 'Renowned Da Nang specialty featuring signature two-edged pork belly wrapped in fresh rice paper with a bouquet of wild herbs and savory fermented anchovy dip (mam nem).',
    district: 'Hai Chau'
  },
  'Bún chả cá Nguyễn Chí Thanh': {
    name: 'Nguyen Chi Thanh Fish Cake Noodle Soup',
    description: 'Legendary family-recipe fish cake noodles operating for over 50 years, featuring fragrant broth simmered with pumpkin, cabbage, and homemade steamed and fried mackerel cakes.',
    district: 'Hai Chau'
  },
  'Bánh mì Phượng': {
    name: 'Banh Mi Phuong Hoi An',
    description: 'Internationally acclaimed Vietnamese baguette made famous by Anthony Bourdain, loaded with rich pate, tender roasted pork, fresh herbs, and secret savory sauce.',
    district: 'Hoi An'
  },
  'Cao lầu Thanh': {
    name: 'Thanh Cao Lau Hoi An',
    description: 'Authentic local eatery serving traditional Hoi An Cao Lau noodles with chewy lye-soaked noodles, tender char siu pork, crispy croutons, and aromatic garden herbs.',
    district: 'Hoi An'
  },
  'Cơm gà Bà Buội': {
    name: 'Ba Buoi Chicken Rice',
    description: 'Historic Hoi An culinary landmark since the 1950s, famous for golden turmeric-infused rice cooked in rich chicken broth topped with tender free-range shredded chicken.',
    district: 'Hoi An'
  },
  'Cộng Cà Phê Bạch Đằng': {
    name: 'Cong Caphe - Bach Dang',
    description: 'Iconic retro military-chic Vietnamese coffee house perched right along the Han River waterfront, famous for its signature frozen coconut coffee.',
    district: 'Hai Chau'
  },
  'Hội An Roastery': {
    name: 'Hoi An Roastery - Espresso & Coffee House',
    description: 'Rustic wooden coffee house and artisanal roastery nestled in Hoi An Ancient Town, renowned for premium slow-dripped Vietnamese coffee, espresso, and cozy vintage atmosphere.',
    district: 'Hoi An'
  },
  'Faifo Coffee': {
    name: 'Faifo Coffee',
    description: 'Famous cafe in Hoi An Ancient Town featuring a charming rooftop terrace with sweeping panoramic views over historic yellow walls and tiled rooftops.',
    district: 'Hoi An'
  },
  'Chợ Cồn': {
    name: 'Con Market (Cho Con)',
    description: "Da Nang's most vibrant food paradise and wholesale market, packed with stalls serving tantalizing local street food delicacies at affordable prices.",
    district: 'Hai Chau'
  },
  'Chợ đêm Sơn Trà': {
    name: 'Son Tra Night Market',
    description: 'Bustling night market located right by the Dragon Bridge and Love Pier, brimming with sizzling fresh seafood stalls, street snacks, and lively souvenir shopping.',
    district: 'Son Tra'
  },
  'Chợ Hội An': {
    name: 'Hoi An Market',
    description: 'Historic central market nestled by the Thu Bon River, brimming with colorful fresh produce, traditional spices, and authentic Hoi An street delicacies.',
    district: 'Hoi An'
  },
  'Chợ đêm Hội An': {
    name: 'Hoi An Night Market',
    description: 'Lively pedestrian night market on Nguyen Hoang street, illuminated by hundreds of glowing silk lanterns, vibrant souvenir stalls, and tasty street snacks.',
    district: 'Hoi An'
  },
  'Phố cổ Hội An': {
    name: 'Hoi An Ancient Town',
    description: 'UNESCO World Heritage site celebrated for its exceptionally well-preserved traditional Asian trading port, yellow shophouses, and romantic lantern-lit canals.',
    district: 'Hoi An'
  },
  'Rừng dừa Bảy Mẫu': {
    name: 'Bay Mau Coconut Forest',
    description: 'Lush eco-tourism haven in Cam Thanh featuring thrilling spinning basket boat rides through winding waterways shaded by water coconut palms.',
    district: 'Hoi An'
  },
  'Chùa Cầu Hội An': {
    name: 'Japanese Covered Bridge (Chua Cau)',
    description: 'Iconic 400-year-old wooden covered bridge and temple spanning a tranquil canal, a cherished symbol of Hoi An heritage.',
    district: 'Hoi An'
  },
  'Chùa Cầu': {
    name: 'Japanese Covered Bridge (Chua Cau)',
    description: 'Iconic 400-year-old wooden covered bridge and temple spanning a tranquil canal, a cherished symbol of Hoi An heritage.',
    district: 'Hoi An'
  },
  'Công viên Đất nung Thanh Hà': {
    name: 'Thanh Ha Terracotta Park',
    description: 'Vietnam\'s largest ceramic museum and art park featuring unique red terracotta architectural pavilions, pottery models of world wonders, and clay crafting workshops.',
    district: 'Hoi An'
  }
};


// Hàm lấy dữ liệu bản dịch cho địa điểm
function getLocalizedPlace(originalPlace) {
  if (!originalPlace) return originalPlace;
  if (getLang() !== 'en') return originalPlace;

  const rawName = String(originalPlace.name || '').trim();
  const enData =
    PLACE_NAME_MAP_EN[rawName] ||
    (window.PLACE_TRANSLATIONS_EN && window.PLACE_TRANSLATIONS_EN[originalPlace.id]);

  if (enData) {
    return {
      ...originalPlace,
      name: enData.name || originalPlace.name,
      description: enData.description || originalPlace.description,
      district: enData.district || originalPlace.district
    };
  }
  return originalPlace;
}

// =========================================
// THANH DIEU HUONG - NAVBAR (TASK BAR)
// =========================================

function renderNav() {
  const currentPage = location.pathname.split('/').pop() || 'index.html';
  const host = $('#site-nav');
  if (!host) return;

  const currentLang = getLang();
  const isEn = currentLang === 'en';

  const links = [
    ['index.html', isEn ? 'Home' : 'Trang chủ'],
    ['places.html', isEn ? 'Places' : 'Địa điểm'],
    ['recommendations.html', isEn ? 'Recommendations' : 'Gợi ý'],
    ['map.html', isEn ? 'Map' : 'Bản đồ'],
    ['chat.html', 'Chat AI']
  ];

  host.innerHTML = `
    <nav class="navbar navbar-expand-lg travel-navbar">
      <div class="container">

        <!-- LOGO -->
        <a class="navbar-brand travel-brand" href="index.html">
          <span class="travel-logo">
            <svg
              width="25"
              height="25"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9"></circle>
              <path d="m15.5 8.5-2 5-5 2 2-5 5-2z"></path>
            </svg>
          </span>

          <span class="travel-brand-text">
            <strong>DaNang<span>Guide</span></strong>
            <small>${isEn ? 'EXPLORE DA NANG' : 'KHÁM PHÁ ĐÀ NẴNG'}</small>
          </span>
        </a>

        <!-- MENU MOBILE -->
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navItems"
          aria-controls="navItems"
          aria-expanded="false"
          aria-label="${isEn ? 'Toggle navigation' : 'Mở menu'}"
        >
          <span class="navbar-toggler-icon"></span>
        </button>

        <!-- MENU CHINH -->
        <div class="collapse navbar-collapse" id="navItems">

          <div class="navbar-nav mx-auto travel-links">
            ${links
              .map(
                ([href, label]) => `
              <a
                class="nav-link ${currentPage === href ? 'active' : ''}"
                href="${href}"
                ${currentPage === href ? 'aria-current="page"' : ''}
              >
                ${label}
              </a>
            `
              )
              .join('')}
          </div>

          <!-- PHẦN TÀI KHOẢN & BỘ ĐỔI NGÔN NGỮ (VI / EN) -->
          <div class="d-flex align-items-center gap-3">
            <div class="travel-account" id="account-actions"></div>

            <!-- NÚT ĐỔI NGÔN NGỮ TIẾNG ANH & TIẾNG VIỆT (CÔNG TẮC NGANG) -->
            <div class="lang-switch-wrap" id="lang-switcher">
              <div
                class="lang-toggle-switch ${isEn ? 'is-en' : 'is-vi'}"
                role="switch"
                aria-checked="${isEn ? 'true' : 'false'}"
                tabindex="0"
                title="${isEn ? 'Switch language (VI / EN)' : 'Đổi ngôn ngữ (VI / EN)'}"
              >
                <!-- Con trượt ngang (Sliding Pill Knob) -->
                <span class="lang-toggle-slider" aria-hidden="true"></span>

                <button
                  type="button"
                  class="lang-btn ${!isEn ? 'active' : ''}"
                  data-lang="vi"
                  title="Tiếng Việt"
                  aria-label="Tiếng Việt"
                >
                  <svg class="flag-icon" width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true">
                    <rect width="16" height="12" rx="2" fill="#DA251D"/>
                    <polygon points="8,2.4 8.94,5.3 12,5.3 9.53,7.1 10.47,10 8,8.2 5.53,10 6.47,7.1 4,5.3 7.06,5.3" fill="#FFFF00"/>
                  </svg>
                  <span class="lang-code">VI</span>
                </button>

                <button
                  type="button"
                  class="lang-btn ${isEn ? 'active' : ''}"
                  data-lang="en"
                  title="English"
                  aria-label="English"
                >
                  <svg class="flag-icon" width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true">
                    <rect width="16" height="12" rx="2" fill="#012169"/>
                    <path d="M0,0 L16,12 M16,0 L0,12" stroke="#FFFFFF" stroke-width="2"/>
                    <path d="M0,0 L16,12 M16,0 L0,12" stroke="#C8102E" stroke-width="1"/>
                    <path d="M8,0 V12 M0,6 H16" stroke="#FFFFFF" stroke-width="3.6"/>
                    <path d="M8,0 V12 M0,6 H16" stroke="#C8102E" stroke-width="2.2"/>
                  </svg>
                  <span class="lang-code">EN</span>
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>
    </nav>
  `;

  // Gắn sự kiện chuyển đổi ngôn ngữ cho công tắc ngang
  const switcher = host.querySelector('#lang-switcher');
  if (switcher) {
    const toggleSwitch = switcher.querySelector('.lang-toggle-switch');

    switcher.querySelectorAll('.lang-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = btn.dataset.lang;
        setLang(target);
      });
    });

    if (toggleSwitch) {
      toggleSwitch.addEventListener('click', (e) => {
        if (e.target.closest('.lang-btn')) return;
        const current = getLang();
        setLang(current === 'vi' ? 'en' : 'vi');
      });

      toggleSwitch.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const current = getLang();
          setLang(current === 'vi' ? 'en' : 'vi');
        }
      });
    }
  }

  // Cập nhật trạng thái đăng nhập
  const actions = $('#account-actions');
  if (actions) {
    if (API.isLogged()) {
      actions.innerHTML = `
        <span class="account-greeting">
          ${isEn ? 'Hello,' : 'Xin chào,'} ${esc(API.user()?.name || (isEn ? 'traveler' : 'bạn'))}
        </span>

        <button
          class="btn btn-outline-primary"
          id="logout"
          type="button"
        >
          ${isEn ? 'Sign out' : 'Đăng xuất'}
        </button>
      `;

      const logoutBtn = $('#logout');
      if (logoutBtn) logoutBtn.onclick = () => API.logout();
    } else {
      actions.innerHTML = `
        <a class="travel-login" href="login.html">
          ${isEn ? 'Sign in' : 'Đăng nhập'}
        </a>

        <a
          class="btn btn-primary travel-register"
          href="register.html"
        >
          ${isEn ? 'Sign up' : 'Đăng ký'}
        </a>
      `;
    }
  }
}

// =========================================
// FOOTER
// =========================================

function renderFooter() {
  const footer = $('#site-footer');
  if (!footer) return;

  const isEn = getLang() === 'en';

  footer.innerHTML = `
    <footer class="footer">
      <div class="container d-flex flex-wrap
                  justify-content-between
                  align-items-center gap-2">

        <span>
          © 2026 DaNang Guide.
          ${isEn ? 'Explore Da Nang your way.' : 'Khám phá Đà Nẵng theo cách của bạn.'}
        </span>

        <span id="mode-label"></span>
      </div>
    </footer>
  `;

  const label = $('#mode-label');
  if (label) {
    label.textContent = CFG.USE_MOCK
      ? isEn
        ? '● DEMO MODE — Mock Data'
        : '● DEMO MODE — dữ liệu minh họa'
      : isEn
      ? '● API MODE — FastAPI'
      : '● API MODE — FastAPI';
  }
}

// =========================================
// HIEN THI THE DIA DIEM CO ANH (LOCALIZED)
// =========================================

function placeCard(rawP, fav = false, eagerImage = false) {
  const isEn = getLang() === 'en';
  const p = getLocalizedPlace(rawP);

  // Lay duong dan anh theo ten goc
  const imageUrl = getPlaceImage(rawP);

  // Kiem tra toa do
  const hasCoordinates =
    p.latitude !== null &&
    p.latitude !== undefined &&
    p.longitude !== null &&
    p.longitude !== undefined &&
    Number.isFinite(Number(p.latitude)) &&
    Number.isFinite(Number(p.longitude));

  const mapUrl = hasCoordinates
    ? `map.html?place=${encodeURIComponent(p.id)}`
    : `https://www.openstreetmap.org/search?query=${encodeURIComponent(
        rawP.name + ', Đà Nẵng, Việt Nam'
      )}`;

  // Dịch danh mục
  let categoryLabel = p.category || 'Địa điểm';
  if (isEn) {
    if (categoryLabel === 'tourist_attraction' || categoryLabel.includes('tham quan')) {
      categoryLabel = 'Attraction';
    } else if (categoryLabel === 'restaurant' || categoryLabel.includes('thực') || categoryLabel.includes('Nhà hàng')) {
      categoryLabel = 'Dining & Cuisine';
    } else if (categoryLabel === 'cafe' || categoryLabel.includes('cà phê')) {
      categoryLabel = 'Cafe & Coffee';
    } else if (categoryLabel === 'shopping' || categoryLabel.includes('sắm')) {
      categoryLabel = 'Shopping & Market';
    } else {
      categoryLabel = 'Destination';
    }
  }

  const ratingLabel =
    p.rating == null
      ? isEn
        ? 'New Place'
        : 'Địa điểm mới'
      : '⭐ ' + esc(p.rating);

  const detailText = isEn ? 'Details' : 'Chi tiết';
  const mapBtnText = hasCoordinates
    ? isEn
      ? 'View map'
      : 'Xem bản đồ'
    : isEn
    ? 'Locate'
    : 'Tra vị trí';
  const favText = fav
    ? isEn
      ? '♥ Saved'
      : '♥ Đã lưu'
    : isEn
    ? '♡ Favorite'
    : '♡ Yêu thích';
  const addText = isEn ? '+ Itinerary' : '+ Lịch trình';

  return `
    <article class="card-soft place-card">

      <!-- HINH ANH DIA DIEM -->
      <div class="place-art">

        ${
          imageUrl
            ? `
              <img
                src="${esc(imageUrl)}"
                alt="${esc(p.name)}"
                class="place-image"
                loading="${eagerImage ? 'eager' : 'lazy'}"
                onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
              >
              <span
                class="place-fallback"
                style="display:none"
                aria-hidden="true"
              >
                ${esc(p.emoji || '📍')}
              </span>
            `
            : `
              <span class="place-fallback" aria-hidden="true">
                ${esc(p.emoji || '📍')}
              </span>
            `
        }

        <!-- DANH GIA -->
        <span class="badge text-bg-light">
          ${ratingLabel}
        </span>

      </div>

      <!-- NOI DUNG -->
      <div class="card-body">

        <span class="tag">
          ${esc(categoryLabel)}
        </span>

        <h5>${esc(p.name)}</h5>

        <p class="small muted mb-2">
          📍 ${esc(p.district || (isEn ? 'Da Nang' : 'Đà Nẵng'))}
        </p>

        <p class="muted small">
          ${esc(p.description || '')}
        </p>

        ${
          p.distanceNote
            ? `<p class="small muted">
                 📏 ${esc(p.distanceNote)}
               </p>`
            : ''
        }

        <!-- CAC NUT CHUC NANG -->
        <div class="d-flex gap-2 flex-wrap">

          <a
            class="btn btn-sm btn-primary"
            href="place.html?id=${encodeURIComponent(p.id)}"
          >
            ${detailText}
          </a>

          <a
            class="btn btn-sm btn-outline-primary"
            href="${mapUrl}"
            ${!hasCoordinates ? 'target="_blank" rel="noopener noreferrer"' : ''}
          >
            ${mapBtnText}
          </a>

          ${
            API.isLogged()
              ? `
                <button
                  type="button"
                  data-favorite="${esc(p.id)}"
                  class="btn btn-sm ${
                    fav ? 'btn-primary' : 'btn-outline-secondary'
                  }"
                >
                  ${favText}
                </button>

                <button
                  type="button"
                  data-add="${esc(p.id)}"
                  class="btn btn-sm btn-outline-secondary"
                >
                  ${addText}
                </button>
              `
              : ''
          }

        </div>
      </div>
    </article>
  `;
}

// =========================================
// DỊCH NỘI DUNG TĨNH TRÊN TOÀN TRANG
// =========================================

function applyPageTranslations(lang) {
  const isEn = lang === 'en';

  // 1. Dịch ô tìm kiếm và placeholder
  const searchInputs = document.querySelectorAll(
    'input[type="search"], input[name="q"], #search, #query, .search-box input'
  );
  searchInputs.forEach(input => {
    if (isEn) {
      input.setAttribute('placeholder', 'What do you want to explore in Da Nang?');
    } else {
      input.setAttribute('placeholder', 'Bạn muốn khám phá gì ở Đà Nẵng?');
    }
  });

  // 1b. Dịch Hero banner trên index.html
  const heroTag = document.querySelector('.hero-tag');
  if (heroTag) {
    heroTag.textContent = isEn ? 'EXPLORE THE LIVEABLE CITY' : 'KHÁM PHÁ THÀNH PHỐ ĐÁNG SỐNG';
  }

  const heroTitle = document.querySelector('.hero-title');
  if (heroTitle) {
    heroTitle.innerHTML = isEn
      ? 'Da Nang in the<br>palm of your hand'
      : 'Đà Nẵng trong<br>tầm tay của bạn';
  }

  const heroDesc = document.querySelector('.hero-description');
  if (heroDesc) {
    heroDesc.textContent = isEn
      ? 'Find exciting destinations, taste authentic local food, and plan your journey with ease.'
      : 'Tìm địa điểm thú vị, thưởng thức ẩm thực địa phương và lên kế hoạch cho chuyến đi thật dễ dàng.';
  }

  const homeKwLabel = document.querySelector('label[for="home-keyword"]');
  if (homeKwLabel) homeKwLabel.textContent = isEn ? 'Where to go?' : 'Bạn muốn đi đâu?';

  const homeKwInput = document.querySelector('#home-keyword');
  if (homeKwInput) homeKwInput.setAttribute('placeholder', isEn ? 'Destinations, sights...' : 'Địa điểm, khu vui chơi...');

  const homeDateLabel = document.querySelector('label[for="home-date"]');
  if (homeDateLabel) homeDateLabel.textContent = isEn ? 'Travel date' : 'Chọn ngày đi';

  const homeGuestsLabel = document.querySelector('label[for="home-guests"]');
  if (homeGuestsLabel) homeGuestsLabel.textContent = isEn ? 'Guests' : 'Số người';

  const searchBtn = document.querySelector('.search-button');
  if (searchBtn) searchBtn.textContent = isEn ? 'Search →' : 'Tìm kiếm →';

  // Dịch các tiện ích travel-features trên index.html
  const features = document.querySelectorAll('.travel-features .feature');
  features.forEach(feat => {
    const strong = feat.querySelector('strong');
    const small = feat.querySelector('small');
    if (strong) {
      const sText = strong.textContent.trim();
      if (sText === 'Địa điểm nổi bật' || sText === 'Top Attractions') {
        strong.textContent = isEn ? 'Top Attractions' : 'Địa điểm nổi bật';
        if (small) small.textContent = isEn ? 'Explore iconic places' : 'Khám phá những điểm đến hấp dẫn';
      } else if (sText === 'Ẩm thực Đà Nẵng' || sText === 'Da Nang Cuisine') {
        strong.textContent = isEn ? 'Da Nang Cuisine' : 'Ẩm thực Đà Nẵng';
        if (small) small.textContent = isEn ? 'Taste famous local dishes' : 'Khám phá món ngon địa phương';
      } else if (sText === 'Gợi ý trải nghiệm' || sText === 'Curated Picks') {
        strong.textContent = isEn ? 'Curated Picks' : 'Gợi ý trải nghiệm';
        if (small) small.textContent = isEn ? 'Tailored to your preferences' : 'Lựa chọn phù hợp với sở thích';
      } else if (sText === 'Bản đồ du lịch' || sText === 'Travel Map') {
        strong.textContent = isEn ? 'Travel Map' : 'Bản đồ du lịch';
        if (small) small.textContent = isEn ? 'View locations & smart routes' : 'Xem vị trí và lộ trình thuận tiện';
      }
    }
  });

  // 2. Dịch các thành phần trang chủ index.html
  const homeEyebrows = document.querySelectorAll('.eyebrow');
  homeEyebrows.forEach(el => {
    const text = el.textContent.trim();
    if (text === 'GỢI Ý HÔM NAY' || text === "TODAY'S PICKS") {
      el.textContent = isEn ? "TODAY'S PICKS" : 'GỢI Ý HÔM NAY';
    } else if (text === 'ĐỒNG HÀNH CÙNG BẠN' || text === 'YOUR LOCAL COMPANION') {
      el.textContent = isEn ? 'YOUR LOCAL COMPANION' : 'ĐỒNG HÀNH CÙNG BẠN';
    }
  });

  const sectionHeadings = document.querySelectorAll('.section-head h2');
  sectionHeadings.forEach(el => {
    const text = el.textContent.trim();
    if (text === 'Địa điểm nổi bật' || text === 'Featured Places') {
      el.textContent = isEn ? 'Featured Places' : 'Địa điểm nổi bật';
    } else if (text === 'Khám phá theo cách của bạn' || text === 'Explore In Your Own Way') {
      el.textContent = isEn ? 'Explore In Your Own Way' : 'Khám phá theo cách của bạn';
    }
  });

  const viewAllLinks = document.querySelectorAll('.view-all');
  viewAllLinks.forEach(el => {
    el.textContent = isEn ? 'View all →' : 'Xem tất cả →';
  });

  // Dịch các explore cards
  const exploreCards = document.querySelectorAll('.explore-card');
  exploreCards.forEach(card => {
    const h5 = card.querySelector('h5');
    const p = card.querySelector('p');
    const link = card.querySelector('.explore-link');

    if (h5) {
      const h5Text = h5.textContent.trim();
      if (h5Text === 'Khám phá địa điểm' || h5Text === 'Explore Places') {
        h5.textContent = isEn ? 'Explore Places' : 'Khám phá địa điểm';
        if (p) p.textContent = isEn
          ? 'Discover attractions, beaches, delicious cuisine, and local entertainment spots.'
          : 'Tìm kiếm các điểm tham quan, bãi biển, địa điểm ăn uống và vui chơi.';
        if (link) link.textContent = isEn ? 'Explore now →' : 'Khám phá ngay →';
      } else if (h5Text === 'Trợ lý du lịch AI' || h5Text === 'AI Travel Assistant') {
        h5.textContent = isEn ? 'AI Travel Assistant' : 'Trợ lý du lịch AI';
        if (p) p.textContent = isEn
          ? 'Ask questions, get local tips, and receive smart recommendations for your journey.'
          : 'Hỏi đáp, tìm hiểu thông tin và nhận hỗ trợ lên kế hoạch cho chuyến đi.';
        if (link) link.textContent = isEn ? 'Start chat →' : 'Bắt đầu trò chuyện →';
      } else if (h5Text === 'Bản đồ & lịch trình' || h5Text === 'Map & Itinerary') {
        h5.textContent = isEn ? 'Map & Itinerary' : 'Bản đồ & lịch trình';
        if (p) p.textContent = isEn
          ? 'View destination coordinates on interactive map and organize convenient routes.'
          : 'Xem vị trí các điểm đến và sắp xếp hành trình thuận tiện hơn.';
        if (link) link.textContent = isEn ? 'View map →' : 'Xem bản đồ →';
      }
    }
  });

  // 3. Dịch form đăng nhập / đăng ký
  const authCardTitle = document.querySelector('.auth-card h2, .auth-card h3');
  if (authCardTitle) {
    const tText = authCardTitle.textContent.trim();
    if (tText.includes('Đăng nhập') || tText.includes('Sign In')) {
      authCardTitle.textContent = isEn ? 'Sign in to your account' : 'Đăng nhập tài khoản';
    } else if (tText.includes('Đăng ký') || tText.includes('Tạo tài khoản') || tText.includes('Create an account')) {
      authCardTitle.textContent = isEn ? 'Create an account' : 'Tạo tài khoản mới';
    }
  }

  const googleTextSpan = document.querySelector('#google-login span, #google-register span');
  if (googleTextSpan) {
    const isLogin = !!document.querySelector('#google-login');
    googleTextSpan.textContent = isEn
      ? isLogin
        ? 'Sign in with Google'
        : 'Sign up with Google'
      : isLogin
      ? 'Đăng nhập bằng Google'
      : 'Đăng ký bằng Google';
  }

  const dividerSpan = document.querySelector('.divider span');
  if (dividerSpan) {
    const isLogin = !!document.querySelector('#google-login');
    dividerSpan.textContent = isEn
      ? isLogin
        ? 'or sign in with email'
        : 'or sign up with email'
      : isLogin
      ? 'hoặc đăng nhập bằng email'
      : 'hoặc tạo tài khoản bằng email';
  }

  const authSubmitBtn = document.querySelector('#auth-form button[type="submit"]');
  if (authSubmitBtn) {
    const isLogin = !document.querySelector('#name');
    authSubmitBtn.textContent = isEn
      ? isLogin
        ? 'Sign In'
        : 'Create Account'
      : isLogin
      ? 'Đăng nhập'
      : 'Tạo tài khoản';
  }

  // Labels form auth
  const emailLabel = document.querySelector('label[for="email"]');
  if (emailLabel) emailLabel.textContent = isEn ? 'Email address' : 'Địa chỉ email';

  const passLabel = document.querySelector('label[for="password"]');
  if (passLabel) passLabel.textContent = isEn ? 'Password' : 'Mật khẩu';

  const nameLabel = document.querySelector('label[for="name"]');
  if (nameLabel) nameLabel.textContent = isEn ? 'Full name' : 'Họ và tên';

  const switchAuthP = document.querySelector('.auth-switch');
  if (switchAuthP) {
    const link = switchAuthP.querySelector('a');
    if (link) {
      if (link.getAttribute('href')?.includes('register')) {
        switchAuthP.childNodes[0].textContent = isEn ? "Don't have an account? " : 'Chưa có tài khoản? ';
        link.textContent = isEn ? 'Sign up now' : 'Đăng ký ngay';
      } else if (link.getAttribute('href')?.includes('login')) {
        switchAuthP.childNodes[0].textContent = isEn ? 'Already have an account? ' : 'Đã có tài khoản? ';
        link.textContent = isEn ? 'Sign in now' : 'Đăng nhập ngay';
      }
    }
  }

  // 4. Nếu có hàm translateDOM trong i18n
  if (window.i18n && typeof window.i18n.translateDOM === 'function') {
    try {
      window.i18n.translateDOM();
    } catch {}
  }
}

// =========================================
// XU LY YEU THICH VA LICH TRINH
// =========================================

async function wirePlaceActions(container) {
  if (!container) return;

  container.addEventListener('click', async event => {
    const favoriteButton = event.target.closest('[data-favorite]');
    const addButton = event.target.closest('[data-add]');
    const isEn = getLang() === 'en';

    try {
      if (favoriteButton) {
        const id = Number(favoriteButton.dataset.favorite);
        await API.toggleFavorite(id);

        const wasSaved =
          favoriteButton.textContent.includes('Đã lưu') ||
          favoriteButton.textContent.includes('Saved');

        favoriteButton.textContent = wasSaved
          ? isEn
            ? '♡ Favorite'
            : '♡ Yêu thích'
          : isEn
          ? '♥ Saved'
          : '♥ Đã lưu';

        favoriteButton.classList.toggle('btn-primary');
        favoriteButton.classList.toggle('btn-outline-secondary');
      }

      if (addButton) {
        const ids = await API.itinerary();
        const id = Number(addButton.dataset.add);

        if (ids.includes(id)) {
          flash(
            isEn
              ? 'Place is already in your itinerary.'
              : 'Địa điểm đã có trong lịch trình.',
            'info'
          );
          return;
        }

        await API.saveItinerary([...ids, id]);
        flash(
          isEn ? 'Added to itinerary!' : 'Đã thêm vào lịch trình.',
          'success'
        );
      }
    } catch (error) {
      flash(error.message);
    }
  });
}

// Gán hàm vào window để các trang khác có thể gọi
window.getLang = getLang;
window.setLang = setLang;
window.getLocalizedPlace = getLocalizedPlace;
window.applyPageTranslations = applyPageTranslations;

// =========================================
// KHOI TAO WEBSITE
// =========================================

document.addEventListener('DOMContentLoaded', () => {
  renderNav();
  renderFooter();
  applyPageTranslations(getLang());
});

