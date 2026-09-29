import streamlit as st
import time
import requests
import urllib.parse
from google import genai
_k1 = "AQ.Ab8RN6LjVcS6RlOqq"
_k2 = "yIajcocXt7xL0pVm-"
_k3 = "gJIIIsTzkXbYlsdg"
client = genai.Client(api_key=_k1 + _k2 + _k3)
import io
import re
import pandas as pd
import os
import json
from bs4 import BeautifulSoup
from PIL import Image

FIREBASE_URL = "https://khobds-2026-default-rtdb.firebaseio.com"

st.set_page_config(page_title="Hệ Thống BĐS - Anh Em Cùng Tiến", layout="wide", page_icon="🏘️")

# Cấu hình API Key thật của sếp (Đã chuyển lên trên)

def analyze_images(uploaded_files):
    prompt_text = """Đóng vai một Chuyên gia Thẩm định giá Bất Động Sản thực chiến kiêm Siêu Cò lão luyện.
Hãy soi thật kỹ các bức ảnh này (đặc biệt chú ý nếu có ảnh Sổ Hồng/Sơ đồ thửa đất) và đưa ra 1 Bản Phân Tích Thật Sâu Sắc:
1. 🏠 KIẾN TRÚC & HIỆN TRẠNG: Đánh giá kết cấu, mức độ xuống cấp. Nếu có Sổ Hồng, hãy đọc chính xác Diện tích công nhận, Bề ngang, Diện tích sàn, Cấp nhà.
2. 💎 ĐIỂM ĂN TIỀN: Ưu điểm vượt trội (Vị trí, mặt tiền, hẻm, hình dáng đất vuông vức, lợi thế thương mại/dòng tiền nếu đang cho thuê kinh doanh).
3. 🚨 TỬ HUYỆT (ĐIỂM TRỪ): Bới lông tìm vết! Đọc Sơ đồ Sổ Hồng xem có bị Tóp hậu không? Có bị cắt Ranh Lộ Giới nặng không? Nhìn ảnh thực tế xem có dính cột điện, hố ga, đường đâm, dây điện chằng chịt không?
4. 💡 CHIẾN LƯỢC BÁN: Đưa ra lời khuyên thực chiến cho Môi giới tư vấn chủ nhà nhận ký gửi.

QUAN TRỌNG NHẤT: Bắt buộc ở cuối cùng bài phân tích, bạn phải xuất ra một khối dữ liệu JSON y hệt định dạng sau để phần mềm tự động lấy số liệu tính toán (chỉ xuất JSON, đặt trong ```json ... ```):
```json
{
  "dien_tich_dat_m2": [Nhập diện tích đất nếu thấy trong Sổ Hồng hoặc ảnh, nếu không thấy để 0],
  "be_ngang_m": [Bề ngang mặt tiền đất theo sổ nếu có, nếu không rõ để 4.0],
  "dien_tich_san_m2": [Diện tích sàn xây dựng nếu thấy trên sổ hoặc ước tính, nếu không để 0],
  "xac_nha_trieu_vnd": [Ước tính giá trị xác nhà hiện tại bằng Triệu VNĐ. VD: nhà cấp 4 cũ thì 150-250, 1 trệt 1 lầu thì 400-600, nhà 3-4 tấm thì 800-1500],
  "he_so_hinh_dang_lo_gioi": [0.85 nếu tóp hậu nặng/lộ giới sâu; 0.95 nếu dính ranh lộ giới hoặc tóp hậu nhẹ; 1.0 nếu đẹp vuông vức],
  "he_so_phong_thuy": [0.88 nếu đường đâm/ngã ba; 0.92-0.95 nếu dính cột điện/trạm điện/hố ga trước nhà/hẻm 2 xẹt; 1.0 nếu hoàn hảo],
  "he_so_thuong_mai": [1.05 nếu có mặt bằng kinh doanh hoặc có hợp đồng thuê sẵn thương hiệu/dòng tiền; 1.0 nếu thuần để ở]
}
```
Tuyệt đối tuân thủ định dạng JSON này ở cuối câu trả lời!"""
    
    contents = [prompt_text]
    for f in uploaded_files:
        try:
            img = Image.open(f)
            img.thumbnail((800, 800))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            contents.append(img)
        except Exception:
            pass
            
    try:
        models_to_try = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
        
        last_error = ""
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(model=model_name, contents=contents)
                return f"*(Phân tích bằng lõi: {model_name})*\n" + response.text
            except Exception as e:
                last_error = str(e)
                # Bất kể lỗi 503 (nghẽn mạng) hay 404 (chip bị khai tử), bỏ qua và thử con chip tiếp theo
                continue
                
        return f"Lỗi toàn tập hệ thống Google: {last_error}"
    except Exception as e:
        return f"Lỗi phân tích ảnh: {e}"

def fetch_chotot(keyword, loai_vi_tri):
    try:
        encoded_kw = urllib.parse.quote(keyword)
        # cg=1020 chuyên trang Nhà Ở (Nhà Phố)
        url = f"https://gateway.chotot.com/v1/public/ad-listing?cg=1020&q={encoded_kw}&limit=5"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        
        results = []
        if res.status_code == 200:
            ads = res.json().get('ads', [])
            for ad in ads:
                title = ad.get('subject', '')
                body = ad.get('body', '').lower()
                price = ad.get('price', 0) / 1_000_000_000 
                area = ad.get('size', 0)
                
                # BỘ LỌC THÉP: Loại bỏ Chung cư / Căn hộ và Giá thuê rẻ
                title_lower = title.lower()
                if price < 0.5 or "chung cư" in title_lower or "căn hộ" in title_lower or "apartment" in title_lower:
                    continue
                    
                link = f"https://nha.chotot.com/mua-ban-nha-dat/{ad.get('list_id', '')}.htm"
                
                phap_ly = "Sổ hồng"
                is_vi_bang = False
                title_lower = title.lower()
                
                if "vi bằng" in body or "vi bằng" in title_lower or "giấy tay" in body:
                    phap_ly = "Vi bằng (Giấy tay)"
                    is_vi_bang = True
                elif "sổ chung" in body or "sổ chung" in title_lower or "đồng sở hữu" in body or "đsh" in title_lower:
                    phap_ly = "Sổ chung / ĐSH"
                    is_vi_bang = True
                
                if price > 0 and area > 0:
                    results.append({
                        "title": title, "price": price, "area": area, 
                        "link": link, "phap_ly": phap_ly, "is_vi_bang": is_vi_bang, "source": "Chợ Tốt"
                    })
        return results
    except Exception:
        return []

def fetch_mogi(keyword, loai_vi_tri):
    try:
        url = f"https://mogi.vn/mua-nha-dat?q={urllib.parse.quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        results = []
        for li in soup.find_all('li'):
            prop_info = li.find('div', class_='prop-info')
            if not prop_info: continue
            
            title_el = prop_info.find('h2', class_='prop-title')
            price_el = prop_info.find('div', class_='price')
            link_el = prop_info.find('a', class_='link-overlay')
            attr_ul = prop_info.find('ul', class_='prop-attr')
            
            if not (title_el and price_el and link_el and attr_ul): continue
            
            title = title_el.text.strip()
            
            # BỘ LỌC THÉP: Loại bỏ Chung cư / Căn hộ
            title_lower = title.lower()
            if "chung cư" in title_lower or "căn hộ" in title_lower or "apartment" in title_lower:
                continue
                
            link = link_el['href']
            
            price_str = price_el.text.strip().lower()
            price = 0.0
            match = re.search(r'([0-9.,]+)\s*tỷ', price_str)
            if match:
                price = float(match.group(1).replace(',', '.'))
            else:
                match2 = re.search(r'([0-9.,]+)\s*triệu', price_str)
                if match2:
                    price = float(match2.group(1).replace(',', '.')) / 1000
                    
            area = 0.0
            area_li = attr_ul.find('li')
            if area_li:
                a_match = re.search(r'([0-9.,]+)', area_li.text)
                if a_match:
                    area = float(a_match.group(1).replace(',', '.'))
                    
            if price > 0 and area > 0:
                body = title.lower() 
                phap_ly = "Sổ hồng"
                is_vi_bang = False
                if "vi bằng" in body or "giấy tay" in body:
                    phap_ly = "Vi bằng (Giấy tay)"
                    is_vi_bang = True
                elif "sổ chung" in body or "đồng sở hữu" in body or "đsh" in body:
                    phap_ly = "Sổ chung / ĐSH"
                    is_vi_bang = True
                    
                results.append({
                    "title": title, "price": price, "area": area, 
                    "link": link, "phap_ly": phap_ly, "is_vi_bang": is_vi_bang, "source": "Mogi"
                })
        return results[:5]
    except Exception:
        return []

# --- CSS TÙY CHỈNH CHO GIAO DIỆN DASHBOARD CHUYÊN NGHIỆP ---
st.markdown("""
<style>
    /* 1. DOi FONT CHU SANG MONTSERRAT */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Montserrat', sans-serif !important;
        color: #111111 !important;
    }

    /* 2. HINH NEN BAT DONG SAN TONE MATCHA */
    .stApp { 
        background: linear-gradient(rgba(238, 247, 238, 0.93), rgba(238, 247, 238, 0.97)), 
                    url("https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=2070&auto=format&fit=crop") 
                    center/cover no-repeat fixed !important;
    }
    
    /* 3. SIDEBAR TONE MATCHA DEEP */
    [data-testid="stSidebar"] { background-color: #2e4431 !important; }
    [data-testid="stSidebar"] h1 { color: #a5d6a7 !important; font-size: 1.6rem; text-align: center; border-bottom: 2px solid #4a684e; padding-bottom: 15px; margin-bottom: 20px;}
    [data-testid="stSidebar"] .stRadio label { font-size: 1.1rem; font-weight: 600; padding: 12px 10px; cursor: pointer; border-radius: 8px; margin-bottom: 5px; color: #f1f8f1 !important;}
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover { background-color: #436347 !important; color: #c8e6c9 !important; }
    [data-testid="stSidebar"] p { color: #c8e6c9 !important; }
    
    /* 4. TIEU DE CHINH */
    h1 { color: #1a3615 !important; font-weight: 800; font-size: 2.5rem; text-transform: uppercase; border-bottom: 4px solid #558b2f; padding-bottom: 10px; margin-bottom: 10px; text-align: center; }
    .subtitle { text-align: center; color: #2e4431; font-size: 1.2rem; font-weight: 600; font-style: italic; margin-bottom: 40px; }
    
    /* 5. INPUTS */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] > div[data-baseweb="select"] {
        border-radius: 8px !important;
        border: 2px solid #a5d6a7 !important;
        padding: 10px 15px !important;
        background-color: #ffffff !important;
        color: #111111 !important;
        font-weight: 600 !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stSelectbox"] > div[data-baseweb="select"]:focus-within {
        border-color: #558b2f !important;
        box-shadow: 0 0 0 3px rgba(85, 139, 47, 0.2) !important;
        background-color: #f1f8f1 !important;
    }
    
    .stTextInput label p, .stSelectbox label p, .stNumberInput label p {
        color: #1a3615 !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        margin-bottom: 5px !important;
    }
    
    /* 6. H2 */
    h2 {
        background: linear-gradient(135deg, #2e4431 0%, #558b2f 100%);
        color: white !important;
        padding: 15px 20px !important;
        border-radius: 10px !important;
        font-size: 1.4rem !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2) !important;
        margin-top: 10px !important;
        margin-bottom: 20px !important;
        text-transform: uppercase;
    }
    
    /* 7. METRICS */
    div[data-testid="stMetric"] { 
        background: linear-gradient(to bottom right, #ffffff, #f1f8f1) !important;
        padding: 20px !important; 
        border-radius: 12px !important; 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important; 
        border-top: 5px solid #558b2f !important; 
    }
    div[data-testid="stMetric"] label p { color: #2e4431 !important; font-weight: 700 !important; font-size: 1.1rem !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #1a3615 !important; font-weight: 900 !important; font-size: 2.2rem !important; }
    
    /* 8. EXPANDERS */
    .streamlit-expanderHeader { 
        background-color: #e8f5e9 !important; 
        color: #1a3615 !important; 
        border-radius: 8px !important; 
        font-weight: 800 !important; 
        font-size: 1.2rem !important; 
        border-left: 5px solid #558b2f !important;
    }
    
    /* 9. BUTTONS */
    .stButton > button {
        background: linear-gradient(90deg, #558b2f 0%, #33691e 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 800 !important;
        padding: 12px 24px !important;
        border: none !important;
        box-shadow: 0 4px 6px -1px rgba(85, 139, 47, 0.4) !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 15px -3px rgba(85, 139, 47, 0.5) !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏢 HỆ THỐNG CRM & QUẢN LÝ BĐS TẬP TRUNG")
st.markdown("<div class='subtitle'>Bản quyền Hệ thống thuộc về Hội <b>Anh Em Cùng Tiến</b> (Tâm - Dinh - Việt - Phát)</div>", unsafe_allow_html=True)

st.sidebar.markdown("<h1>⚙️ BẢNG ĐIỀU KHIỂN</h1>", unsafe_allow_html=True)
menu = st.sidebar.radio(
    "CHỌN TÍNH NĂNG:",
    ["📊 1. AI ĐỊNH GIÁ & RÚT TRÍCH", "🗺️ 2. KIỂM TRA QUY HOẠCH", "🤝 3. CRM & QUẢN LÝ RỔ HÀNG", "⚖️ 4. TỪ ĐIỂN PHÁP LÝ", "🎓 5. HỌC VIỆN MÔI GIỚI", "🏢 6. TÌNH BÁO DỰ ÁN"]
)
st.sidebar.markdown("---")
st.sidebar.info("Hệ thống độc quyền tích hợp AI phân tích Sổ Hồng và dữ liệu thị trường theo thời gian thực.")

if menu == "📊 1. AI ĐỊNH GIÁ & RÚT TRÍCH":
    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.header("📥 Nhập Dữ Liệu Căn Nhà")
        dia_chi = st.text_input("📍 Từ khóa khu vực (Quan trọng)", placeholder="VD: Quốc Lộ 13 Thủ Đức")
        st.caption("Hãy nhập từ khóa ngắn gọn (Ví dụ: tên đường + quận) để Bot cào được nhiều nhà nhất.")
        
        nguon_du_lieu = st.selectbox("🌐 Nguồn cào dữ liệu", ["Chợ Tốt (Khuyên dùng)", "Mogi.vn", "Cào Tất Cả (Chợ Tốt + Mogi)"])
        loai_vi_tri = st.selectbox("📍 Vị trí nhà (Quyết định 30% giá)", ["Hẻm Xe Hơi", "Mặt Tiền", "Hẻm Ba Gác / Xe Máy"])
        
        c1, c2 = st.columns(2)
        with c1:
            dien_tich = st.number_input("📐 Diện tích đất (m2)", min_value=10.0, value=50.0, step=1.0)
        with c2:
            ket_cau = st.text_input("🏠 Kết cấu", placeholder="VD: Trệt 1 Lầu")
            
        gia_chu_keu = st.number_input("💰 Giá chủ rao (Tỷ VNĐ)", value=0.0, step=0.1)
        
        st.markdown("---")
        st.subheader("📸 Tải ảnh để MẮT THẦN AI soi lỗi")
        uploaded_files = st.file_uploader("Kéo thả tối đa 7 ảnh vào đây (Bao gồm Sổ Hồng + Ảnh thực tế)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        
        # Chỉ lấy tối đa 7 ảnh đầu tiên để tránh bị Google chặn do dung lượng quá lớn
        if uploaded_files and len(uploaded_files) > 7:
            uploaded_files = uploaded_files[:7]
            st.warning("⚠️ Sếp tải lên quá nhiều ảnh. Hệ thống chỉ lấy 7 ảnh đầu tiên để phân tích cho nhanh nhé!")
            
        luu_bao_cao = st.checkbox("💾 Lưu bài phân tích này vào Lịch sử (Kho mây)", value=False)
        btn = st.button("🚀 KÍCH HOẠT ĐỊNH GIÁ TOÀN DIỆN", type="primary", use_container_width=True)

    with col2:
        st.header("📤 Báo Cáo Chiến Lược")
        if btn:
            if not dia_chi:
                st.error("⚠️ Phải nhập từ khóa địa chỉ thì Bot mới biết đường lên mạng cào dữ liệu!")
            else:
                with st.spinner("🤖 Đang kết nối Mắt thần AI và bung Bot cào thị trường..."):
                    
                    st.subheader("👁️ 1. Phân tích Hiện trạng (Vision AI Thật)")
                    ai_params = {
                        "dien_tich_dat_m2": 0,
                        "be_ngang_m": 4.0,
                        "dien_tich_san_m2": 0,
                        "xac_nha_trieu_vnd": 0,
                        "he_so_hinh_dang_lo_gioi": 1.0,
                        "he_so_phong_thuy": 1.0,
                        "he_so_thuong_mai": 1.0
                    }
                    if uploaded_files:
                        with st.spinner("🧠 AI đang quét từng chi tiết trong ảnh và Sổ Hồng..."):
                            ai_analysis = analyze_images(uploaded_files)
                            
                            import re, json
                            
                            # Tìm block JSON bằng cách linh hoạt hơn
                            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', ai_analysis, re.DOTALL | re.IGNORECASE)
                            if not json_match:
                                # Nếu model trả về JSON mà không có thẻ markdown
                                json_match_raw = re.search(r'(\{.*?\})', ai_analysis, re.DOTALL)
                                if json_match_raw:
                                    try:
                                        # Kiểm tra xem đoạn chứa ngoặc nhọn có thực sự là JSON hợp lệ hay không
                                        json.loads(json_match_raw.group(1)) 
                                        json_str = json_match_raw.group(1)
                                    except:
                                        json_str = None
                                else:
                                    json_str = None
                            else:
                                json_str = json_match.group(1)

                            if json_str:
                                try:
                                    parsed = json.loads(json_str)
                                    ai_params.update(parsed)
                                    # Xóa json khỏi text
                                    if json_match:
                                        ai_analysis = ai_analysis.replace(json_match.group(0), "")
                                    else:
                                        ai_analysis = ai_analysis.replace(json_str, "")
                                except Exception as e:
                                    pass
                                    
                            st.info(ai_analysis)
                            
                            # Logic lưu đã được chuyển xuống phần Chốt Giá để lưu được cả Giá Tiền
                    else:
                        st.warning("⚠️ Không có ảnh. Hệ thống bỏ qua bước soi lỗi nhà.")
                        
                    st.subheader(f"🌐 2. Dữ liệu ĐANG BÁN THỰC TẾ trên mạng")
                    
                    real_listings = []
                    if nguon_du_lieu in ["Chợ Tốt (Khuyên dùng)", "Cào Tất Cả (Chợ Tốt + Mogi)"]:
                        real_listings.extend(fetch_chotot(dia_chi, loai_vi_tri))
                    if nguon_du_lieu in ["Mogi.vn", "Cào Tất Cả (Chợ Tốt + Mogi)"]:
                        real_listings.extend(fetch_mogi(dia_chi, loai_vi_tri))
                        
                    don_gia_dat = 100.0 
                    
                    if real_listings:
                        st.success(f"Phát hiện {len(real_listings)} căn nhà đang rao bán công khai:")
                        sum_don_gia_sach = 0
                        count_sach = 0
                        
                        for item in real_listings:
                            don_gia_1_can = (item['price'] / item['area']) * 1000 
                            
                            st.markdown(f"🏠 **[{item['source']}] {item['title']}**")
                            if item['is_vi_bang']:
                                st.error(f"👉 Diện tích: **{item['area']} m2** | Giá rao: **{item['price']:.2f} Tỷ** *(~ {don_gia_1_can:.1f} tr/m2)*\n\n⚠️ **Pháp lý: {item['phap_ly']}** -> (Hệ thống tự động loại bỏ, không tính trung bình vì làm nhiễu giá)")
                            else:
                                st.info(f"👉 Diện tích: **{item['area']} m2** | Giá rao: **{item['price']:.2f} Tỷ** *(~ {don_gia_1_can:.1f} tr/m2)*\n\n✅ **Pháp lý: 100% Sổ Hồng**")
                                sum_don_gia_sach += don_gia_1_can
                                count_sach += 1
                                
                            st.markdown(f"[🔗 Xem tin gốc]({item['link']})")
                            st.markdown("---")
                            
                        if count_sach > 0:
                            don_gia_dat = sum_don_gia_sach / count_sach
                            st.success(f"**=> Đơn giá nền khu vực (CHỈ TÍNH NHÀ SỔ HỒNG SẠCH): {don_gia_dat:.1f} Triệu/m2**")
                            p_base = don_gia_dat
                        else:
                            st.warning("⚠️ Toàn bộ nhà tìm thấy đều là Vi Bằng/Sổ chung. Đang dùng đơn giá dự phòng 80tr/m2 để tính toán.")
                            don_gia_dat = 80.0
                            p_base = 80.0
                    else:
                        st.warning("⚠️ Bot không tìm thấy tin rao bán nào khớp với từ khóa này. Đang dùng giá dự phòng.")
                        p_base = 80.0
                        
                    st.subheader("💰 3. BỘ TIÊU CHUẨN ĐỊNH GIÁ & CHIẾN LƯỢC MÔI GIỚI")
                    
                    # 1. Diện tích áp dụng (Ưu tiên Sổ Hồng AI bóc được)
                    dt_thuc_te = ai_params["dien_tich_dat_m2"] if ai_params.get("dien_tich_dat_m2", 0) > 0 else dien_tich
                    
                    # 2. Đơn giá đất cơ sở thuần (Bóc tách tiền xác nhà cũ trung bình 5tr/m2 khỏi tin rao)
                    p_base_thuan = max(p_base - 5.0, 30.0) if p_base > 30 else p_base
                    
                    # 3. TÍNH TOÁN BỘ 6 HỆ SỐ ĐIỀU CHỈNH ĐẤT (K1 -> K6)
                    # K1: Vị trí hẻm / mặt tiền
                    if loai_vi_tri == "Mặt Tiền":
                        k1_vitri = 1.35
                        k1_desc = "Mặt tiền kinh doanh (+35%)"
                    elif loai_vi_tri == "Hẻm Ba Gác / Xe Máy":
                        k1_vitri = 0.85
                        k1_desc = "Hẻm nhỏ / Ba gác (-15%)"
                    else:
                        k1_vitri = 1.00
                        k1_desc = "Hẻm xe hơi chuẩn (1.0)"
                        
                    # K2: Quy mô diện tích
                    if dt_thuc_te < 40:
                        k2_dientich = 1.05
                        k2_desc = "Diện tích nhỏ <40m2 (+5%)"
                    elif dt_thuc_te <= 70:
                        k2_dientich = 1.00
                        k2_desc = "Diện tích chuẩn 40-70m2 (1.0)"
                    elif dt_thuc_te <= 100:
                        k2_dientich = 0.98
                        k2_desc = "Diện tích vừa 70-100m2 (-2%)"
                    else:
                        k2_dientich = 0.95
                        k2_desc = "Diện tích lớn >100m2 (-5% do kén khách)"
                        
                    # K3: Bề ngang mặt tiền đất
                    be_ngang = ai_params.get("be_ngang_m", 4.0)
                    if be_ngang >= 5.0:
                        k3_ngang = 1.05
                        k3_desc = f"Bề ngang rộng {be_ngang}m (+5%)"
                    elif be_ngang >= 4.0:
                        k3_ngang = 1.00
                        k3_desc = f"Bề ngang chuẩn {be_ngang}m (1.0)"
                    elif be_ngang >= 3.3:
                        k3_ngang = 0.95
                        k3_desc = f"Bề ngang hẹp vừa {be_ngang}m (-2%)"
                    else:
                        k3_ngang = 0.88
                        k3_desc = f"Bề ngang hẹp <3.3m ({be_ngang}m, -12%)"
                        
                    # K4: Hình thể thửa đất & Ranh Lộ giới
                    k4_logioi = ai_params.get("he_so_hinh_dang_lo_gioi", 1.0)
                    k4_desc = "Vuông vức (1.0)" if k4_logioi >= 1.0 else f"Tóp hậu / Dính ranh lộ giới ({k4_logioi:.2f})"
                    
                    # K5: Phong thủy & Hạ tầng trước nhà
                    k5_phongthuy = ai_params.get("he_so_phong_thuy", 1.0)
                    k5_desc = "Sạch sẽ, không lỗi (1.0)" if k5_phongthuy >= 1.0 else f"Cột điện / Hố ga / Đường đâm ({k5_phongthuy:.2f})"
                    
                    # K6: Lợi thế thương mại & Dòng tiền cho thuê
                    k6_thuongmai = ai_params.get("he_so_thuong_mai", 1.0)
                    k6_desc = "Có hợp đồng thuê / Dòng tiền (+5%)" if k6_thuongmai > 1.0 else "Nhà ở thuần túy (1.0)"
                    
                    # TỔNG HỢP HỆ SỐ ĐẤT & GIÁ TRỊ ĐẤT
                    k_tong_dat = k1_vitri * k2_dientich * k3_ngang * k4_logioi * k6_thuongmai
                    don_gia_dat_thuc_te = p_base_thuan * k_tong_dat
                    gia_tri_dat_thuc_te = (dt_thuc_te * don_gia_dat_thuc_te) / 1000.0 # Tỷ đồng
                    
                    # 4. GIÁ TRỊ XÁC NHÀ (AI bóc từ sổ hoặc tính theo kết cấu nhập)
                    gia_tri_xac_nha = ai_params.get("xac_nha_trieu_vnd", 0) / 1000.0 # Tỷ đồng
                    if gia_tri_xac_nha == 0 and ket_cau:
                        kc_lower = ket_cau.lower()
                        if "cấp 4" in kc_lower or "cap 4" in kc_lower:
                            gia_tri_xac_nha = 0.20
                        elif "1 lầu" in kc_lower or "2 tầng" in kc_lower or "trệt lầu" in kc_lower:
                            gia_tri_xac_nha = 0.50
                        elif "2 lầu" in kc_lower or "3 tầng" in kc_lower or "3 lầu" in kc_lower:
                            gia_tri_xac_nha = 0.80
                            
                    # 5. TỔNG GIÁ TRỊ THỊ TRƯỜNG CHUẨN (FAIR VALUE)
                    gia_tri_chuan = gia_tri_dat_thuc_te + gia_tri_xac_nha
                    
                    # 6. BỘ 3 MỨC GIÁ CHIẾN LƯỢC CHO MÔI GIỚI
                    gia_chot = round(gia_tri_chuan, 2)
                    gia_rao = round(gia_chot * 1.08, 2)  # Tạo khoảng bớt lộc 5%
                    gia_gap = round(gia_chot * 0.94, 2)  # Bán gấp cho chủ kẹt tiền
                    
                    # 7. BẢNG TÍNH THỰC THU CHO CHỦ NHÀ (NET CASH)
                    thue_tncn = gia_chot * 0.02
                    phi_moi_gioi = gia_chot * 0.02 # Hoa hồng 2% cho team
                    phi_giay_to = 0.02 # Dự phòng 20tr công chứng & bớt lộc
                    tien_thuc_thu = gia_chot - thue_tncn - phi_moi_gioi - phi_giay_to
                    
                    # HIỂN THỊ 3 METRIC CHIẾN LƯỢC MÔI GIỚI
                    m_col1, m_col2, m_col3 = st.columns(3)
                    with m_col1:
                        st.metric("📢 Giá Rao Bán (Đăng tin)", f"{gia_rao:.2f} Tỷ", help="Giá chào thị trường, có sẵn 5% biên độ bớt lộc đàm phán.")
                    with m_col2:
                        st.metric("🤝 Giá Chốt Hợp Lý", f"{gia_chot:.2f} Tỷ", help="Giá trị thị trường chuẩn, khách thiện chí đàm phán về mốc này là chốt.")
                    with m_col3:
                        st.metric("💰 Chủ Thực Thu (Net)", f"{tien_thuc_thu:.2f} Tỷ", help="Số tiền mặt cầm về sau khi trừ Thuế TNCN 2%, Hoa hồng 2% và giấy tờ.")
                        
                    # BẢNG BÓC TÁCH CÔNG THỨC 5 BƯỚC CHI TIẾT
                    
                    full_breakdown_md = f"""### 📍 BƯỚC 1 & 2: Định giá Đất ({dt_thuc_te} m2)
- **Đơn giá cơ sở khu vực (P_base thuần):** `{p_base_thuan:.1f} tr/m2` *(sau khi bóc tách xác nhà khỏi tin cào)*
  > 💡 *Giải thích: Đơn giá cào trên mạng là giá GỘP (nhà+đất). Phải trừ bớt ~5tr/m2 tiền xác nhà cũ để lòi ra giá Đất Nền thuần túy.*
- **1. Vị trí ({k1_desc}):** `x {k1_vitri:.2f}`
  > 💡 *Giải thích: Mặt tiền kinh doanh sầm uất thì cộng thêm 35% giá trị so với hẻm. Còn hẻm ba gác/xe máy lụp xụp thì phải trừ đi 15% vì thanh khoản kém.*
- **2. Quy mô diện tích ({k2_desc}):** `x {k2_dientich:.2f}`
  > 💡 *Giải thích: Nhà càng to, tổng tiền càng lớn, càng ít người đủ tiền mua (kén khách). Theo luật giang hồ, diện tích >100m2 thì đơn giá/m2 phải rẻ hơn nhà 50m2 khoảng 5-10%.*
- **3. Bề ngang mặt tiền ({k3_desc}):** `x {k3_ngang:.2f}`
  > 💡 *Giải thích: Nhà bề ngang rộng (>5m) làm form nhà cực đẹp, dễ kinh doanh, dễ bố trí phòng nên được cộng 5% giá trị. Ngược lại bề ngang hẹp (<3.3m) nhìn như cái ống, bí bách, ép giá ngay 5-12%.*
- **4. Hình thể & Lộ giới ({k4_desc}):** `x {k4_logioi:.2f}`
  > 💡 *Giải thích: Dính quy hoạch lộ giới bị cắt sâu, hoặc nhà tóp hậu (nở tiền tóp hậu) là lỗi cực nặng trong phong thủy và xây dựng. AI soi Sổ Hồng thấy lỗi này sẽ tự động trừ 5-15% tùy mức độ.*
- **5. Phong thủy & Hạ tầng ({k5_desc}):** `x {k5_phongthuy:.2f}`
  > 💡 *Giải thích: Khách đi mua ở cực kỵ cột điện to, trạm biến áp, hố ga nằm chình ình trước cửa, hoặc đường đâm thẳng vào nhà. Thấy lỗi này, môi giới vịn vào chém ngay 5-12% giá.*
- **6. Thương mại / Dòng tiền ({k6_desc}):** `x {k6_thuongmai:.2f}`
  > 💡 *Giải thích: Nếu nhà đang có sẵn Hợp đồng thuê dài hạn, thương hiệu xịn thuê, sinh ra dòng tiền hàng tháng ổn định thì đây là Con Gà Đẻ Trứng Vàng, được cộng thêm 5% giá trị.*

**=> Hệ số tổng hợp đất:** `{k_tong_dat:.3f}` | **Đơn giá đất thực tế:** `{don_gia_dat_thuc_te:.1f} tr/m2`
💵 **Tiền Đất:** `{gia_tri_dat_thuc_te:.2f} Tỷ đồng`

---
### 🏠 BƯỚC 3: Định giá Xác Nhà
- **Tiền xác nhà hoàn công:** `{gia_tri_xac_nha:.2f} Tỷ đồng` *(tính theo cấp nhà và khấu hao)*
  > 💡 *Giải thích: Nếu AI đọc Sổ Hồng thấy ghi Cấp 4 (nhưng thực tế nhà 1 lầu), tức là nhà xây chui chưa hoàn công, định giá xác nhà chỉ được tính như nhà Cấp 4 (rất rẻ).*

---
### 🎯 BƯỚC 4 & 5: Tổng Hợp & Bảng Tính Thực Thu (Net Cash)
- **Tổng giá trị tài sản chuẩn:** `{gia_tri_chuan:.2f} Tỷ đồng`
- **Giá bán gấp (Thanh khoản nhanh):** `{gia_gap:.2f} Tỷ đồng`

| Khoản mục | Tỷ lệ / Cách tính | Số tiền (Tính trên giá chốt {gia_chot:.2f} Tỷ) |
| :--- | :--- | :--- |
| **Giá chốt hợp đồng** | Giá thị trường chuẩn | **{gia_chot:.2f} Tỷ** |
| **Thuế Thu nhập cá nhân (TNCN)** | 2% trên giá bán | Trừ **{thue_tncn*1000:.0f} Triệu** |
| **Phí môi giới cho team** | 2% hoa hồng | Trừ **{phi_moi_gioi*1000:.0f} Triệu** |
| **Phí công chứng & bớt lộc** | Dự phòng hồ sơ | Trừ **{phi_giay_to*1000:.0f} Triệu** |
| **👉 TIỀN THỰC THU CỦA CHỦ NHÀ** | **= Giá bán - Các chi phí trên** | **{tien_thuc_thu:.2f} Tỷ đồng (Net)** |

> 💡 *Giải thích cho Lính mới (Dùng để chốt chủ nhà): Chủ nhà hay bị ảo tưởng con số Tỷ đồng đăng bán mà quên mất chi phí chìm. Môi giới phải lấy bảng này đập vào mắt chủ: 'Anh chị kêu {gia_chot} Tỷ, nhưng nhà nước thu Thuế 2%, đóng Phí môi giới 2%, rồi tiền làm giấy tờ công chứng, phí trước bạ... Thực tế anh chị đút túi chỉ có {tien_thuc_thu:.2f} Tỷ thôi. Bán nhanh đi anh chị ơi!'*
"""
                    with st.expander("🧮 BẢNG BÓC TÁCH ĐỊNH GIÁ ĐA TIÊU CHÍ 5 BƯỚC (ĐÀO TẠO & TƯ VẤN CHỦ NHÀ)", expanded=True):
                        st.markdown(full_breakdown_md)
                        
                    # SO SÁNH VỚI GIÁ CHỦ KÊU NẾU CÓ
                    if gia_chu_keu > 0:
                        lech = gia_chu_keu - gia_chot
                        if lech > 0.4:
                            st.error(f"❌ **Phân tích:** Chủ đang rao cao hơn thị trường **{lech:.2f} Tỷ**. Dùng bảng bóc tách 6 hệ số trên để phân tích cho chủ hiểu, khuyên chủ hạ giá rao về **{gia_rao:.2f} Tỷ** để thu hút khách.")
                        elif lech < -0.3:
                            st.warning(f"🔥 **Phân tích:** Chủ đang rao giá ngộp (Rẻ hơn thị trường {abs(lech):.2f} Tỷ). Căn này tiềm năng thanh khoản siêu tốc, chốt cọc ngay kẻo lỡ!")
                        else:
                            st.success(f"✅ **Phân tích:** Chủ rao rất sát giá thị trường ({gia_chu_keu:.2f} Tỷ vs {gia_chot:.2f} Tỷ chuẩn). Đàm phán bớt nhẹ lộc là chốt cọc được ngay.")
                    else:
                        st.info(f"💡 Tư vấn chủ nhà nhận ký gửi: Đề xuất chủ chào bán ở mức **{gia_rao:.2f} Tỷ**, thương lượng chốt về mốc **{gia_chot:.2f} Tỷ**, chủ thực thu về tay trọn vẹn **{tien_thuc_thu:.2f} Tỷ**.")
                        
                    # LƯU THEO TÙY CHỌN CỦA USER (ĐÃ BAO GỒM GIÁ)
                    if luu_bao_cao:
                        try:
                            if 'ai_analysis' not in locals():
                                ai_analysis = "*Không tải ảnh lên để phân tích.*"
                                
                            if "Lỗi toàn tập" not in ai_analysis:
                                gia_tien_str = f"### 💰 ĐỊNH GIÁ: Rao {gia_rao:.2f} Tỷ | Chốt {gia_chot:.2f} Tỷ | Chủ Thực Thu {tien_thuc_thu:.2f} Tỷ\n\n"
                                bang_tinh_str = f"**Bảng bóc tách chi tiết:**\n\n{full_breakdown_md}\n\n"
                                full_report = gia_tien_str + bang_tinh_str + "---\n\n" + ai_analysis
                                
                                ts = int(time.time())
                                req_data = {"time": ts, "address": dia_chi, "analysis": full_report}
                                requests.put(f"{FIREBASE_URL}/ai_reports/{ts}.json", json=req_data)
                                st.toast("✅ Đã lưu toàn bộ Báo cáo (Bao gồm Giá tiền) vào Lịch sử!")
                            else:
                                st.warning("⚠️ Báo cáo AI bị lỗi mạng nên hệ thống từ chối lưu.")
                        except Exception as e:
                            st.warning(f"⚠️ Không thể lưu Lịch sử: {e}")
    st.markdown("---")
    with st.expander("📚 LỊCH SỬ PHÂN TÍCH HÌNH ẢNH (AUTO-SAVED)", expanded=False):
        try:
            res_rep = requests.get(f"{FIREBASE_URL}/ai_reports.json").json()
            if res_rep:
                for k, v in res_rep.items():
                    col_rp1, col_rp2 = st.columns([4, 1])
                    with col_rp1:
                        st.markdown(f"**🏠 Địa chỉ: {v.get('address', 'Không tên')}**")
                    with col_rp2:
                        if st.button("🗑️ Xóa", key=f"del_rep_{k}"):
                            requests.delete(f"{FIREBASE_URL}/ai_reports/{k}.json")
                            try:
                                st.rerun()
                            except:
                                st.experimental_rerun()
                    st.write(v.get('analysis', ''))
                    st.markdown("---")
            else:
                st.write("Chưa có báo cáo nào được lưu.")
        except:
            st.write("Chưa có báo cáo nào được lưu.")

elif menu == "🗺️ 2. KIỂM TRA QUY HOẠCH":
    st.header("🗺️ CỔNG TRA CỨU QUY HOẠCH CHÍNH THỨC (TP.HCM)")
    st.markdown("---")
    
    colA, colB = st.columns([1, 1])
    with colA:
        st.subheader("Kết nối đến Sở Xây Dựng")
        st.link_button("👉 BẤM VÀO ĐÂY ĐỂ MỞ BẢN ĐỒ GIS TP.HCM", "https://gisxaydung.tphcm.gov.vn/tracuuttqh", type="primary")

    with colB:
        st.info("📌 **Quy trình soi quy hoạch cho Thành viên 4 (Pháp lý):**")
        st.write("1. Nhập Số tờ/Số thửa vào ô tìm kiếm trên bản đồ.")
        st.write("2. **Kiểm tra màu đất:** Đất ở (Màu vàng/cam) là an toàn. Dính màu xanh lá (Cây xanh) hoặc đường gạch sọc chéo (Lộ giới/Dự phóng) -> Trừ diện tích đó ra khỏi giá mua!")


# --- TAB 3: CRM HỆ THỐNG QUẢN LÝ ---
elif menu == "🤝 3. CRM & QUẢN LÝ RỔ HÀNG":
    st.header("🤝 HỆ THỐNG QUẢN LÝ TỪNG SẢN PHẨM (MINI CRM)")
    st.markdown("---")
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.info("📸 **(1) Dinh (Thực địa)**\n\nĐi công trình, chụp ảnh và up video lên chung.")
    with col_kpi2:
        st.success("📢 **(2) Việt (Content & Sale)**\n\nViết bài, đi đăng tin & báo cáo kênh.")
    with col_kpi3:
        st.warning("⚖️ **(3) Phát (Chốt sale)**\n\nTiếp khách, đàm phán, cập nhật trạng thái Cọc.")
    with col_kpi4:
        st.error("🤝 **(4) Tâm (Hỗ trợ)**\n\nBao quát toàn bộ tiến độ, ghi chú, hỗ trợ anh em.")
        
    st.markdown("---")
    
    # KHỞI TẠO CẤU HÌNH FIREBASE CLOUD VÀ CATBOX
    # Removed redundant FIREBASE_URL definition
    
    def upload_to_catbox(file_bytes, filename):
        try:
            files = {'reqtype': (None, 'fileupload'), 'fileToUpload': (filename, file_bytes)}
            res = requests.post('https://catbox.moe/user/api.php', files=files, timeout=60)
            if res.status_code == 200 and "catbox.moe" in res.text:
                return res.text.strip()
        except Exception:
            pass
        return None

    # Lấy dữ liệu từ Mây
    try:
        r = requests.get(f"{FIREBASE_URL}/properties.json", timeout=5)
        cloud_db = r.json() or {}
    except:
        cloud_db = {}
        
    # FORM TẠO SẢN PHẨM MỚI
    with st.form("tao_san_pham_moi"):
        st.subheader("➕ TẠO KHÔNG GIAN LÀM VIỆC CHO CĂN NHÀ MỚI (TRÊN CLOUD)")
        ten_nha_moi = st.text_input("Nhập tên Căn nhà/Dự án mới (VD: Mặt tiền QL13, Hẻm 740 QL13...):")
        submit_tao = st.form_submit_button("Tạo Không Gian Căn Mới", type="primary")
        
        if submit_tao and ten_nha_moi:
            folder_name = ten_nha_moi.replace("/", "_").replace("\\", "_")
            if folder_name not in cloud_db:
                default_data = {
                    "kenh_dang": "",
                    "trang_thai_phat": "⏳ Chưa có khách",
                    "ghi_chu": "",
                    "media_urls": []
                }
                requests.put(f"{FIREBASE_URL}/properties/{folder_name}.json", json=default_data)
                st.success(f"Đã tạo không gian làm việc cho: {ten_nha_moi} trên Đám Mây!")
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()
            else:
                st.error("Căn nhà này đã tồn tại trong hệ thống!")

    st.markdown("---")
    st.subheader("📂 DANH SÁCH CÁC CĂN NHÀ ĐANG XỬ LÝ (CLOUD)")
    
    folders = list(cloud_db.keys())
    if not folders:
        st.info("Chưa có căn nhà nào trên Cloud. Sếp hãy tạo Căn Mới ở trên.")
        
    def get_safe_index(lst, val, default=0):
        try: return lst.index(val)
        except: return default

    if folders:
        loc_trang_thai = st.selectbox("🔍 Lọc danh sách nhà theo trạng thái:", ["Tất cả (Hiển thị hết)"] + ["⏳ Chưa có khách", "👀 Khách đang xem", "🗣️ Đang đàm phán", "💰 ĐÃ NHẬN CỌC", "❌ Khách chê/Hủy", "🤝 ĐÃ GIAO DỊCH XONG"])

    for p_name in folders:
        p_data = cloud_db[p_name]
        trang_thai_hien_tai = p_data.get('trang_thai_phat', '⏳ Chưa có khách')
        
        if loc_trang_thai != "Tất cả (Hiển thị hết)" and trang_thai_hien_tai != loc_trang_thai:
            continue
            
        with st.expander(f"🏠 SẢN PHẨM: {p_name} | Trạng thái: {trang_thai_hien_tai}", expanded=False):
            
            st.markdown("### 🪄 Nhờ AI Điền Form (Tùy chọn cho Việt)")
            st.caption("Khỏi cần gõ tay! Quăng nguyên đoạn tin nhắn Zalo vào đây, AI sẽ tự động đọc hiểu và điền vào form bên dưới cho Việt.")
            col_zalo, col_btn_zalo = st.columns([4, 1])
            with col_zalo:
                tin_nhan_zalo = st.text_area("Paste tin nhắn Zalo vào đây:", key=f"zalo_{p_name}", label_visibility="collapsed", placeholder="Paste nội dung tin nhắn Zalo vào đây...")
            with col_btn_zalo:
                boc_tach_btn = st.button("🪄 Bốc Tách Tự Động", key=f"btn_zalo_{p_name}", use_container_width=True)
                
            if boc_tach_btn and tin_nhan_zalo:
                with st.spinner("🤖 AI đang đọc tin nhắn và điền form..."):
                    prompt_parse = f"""Bạn là một trợ lý ảo. Hãy đọc tin nhắn Zalo về 1 căn nhà và trích xuất thông tin ra định dạng JSON. Chỉ trả về chuỗi JSON hợp lệ, không thêm bất kỳ văn bản nào khác.
Tin nhắn:
{tin_nhan_zalo}

Định dạng JSON bắt buộc:
{{
  "loai_nha": "Mặt Tiền" (nếu có chữ MT, Mặt tiền) hoặc "Trong Hẻm" (nếu có chữ hẻm, ngõ),
  "diachi_tho": "Địa chỉ đầy đủ",
  "dac_diem": "Đặc điểm ngõ hẻm, lô góc...",
  "ket_cau": "Kết cấu nhà (trệt, lầu, wc...)",
  "dientich": "Diện tích đất (kèm chiều ngang/dài nếu có)",
  "dtsan": "Diện tích sàn / xây dựng",
  "phaply_gia": "Pháp lý (sổ hồng...) và Giá bán"
}}"""
                    try:
                        res = client.models.generate_content(model="gemini-3.5-flash", contents=prompt_parse)
                        import re
                        json_str = res.text
                        json_str = re.sub(r'```json\n?', '', json_str)
                        json_str = re.sub(r'```\n?', '', json_str).strip()
                        import json
                        parsed = json.loads(json_str)
                        
                        p_data["loai_nha_idx"] = 1 if parsed.get("loai_nha") == "Mặt Tiền" else 0
                        p_data["diachi_tho"] = parsed.get("diachi_tho", "")
                        p_data["dac_diem"] = parsed.get("dac_diem", "")
                        p_data["ket_cau"] = parsed.get("ket_cau", "")
                        p_data["dientich"] = parsed.get("dientich", "")
                        p_data["dtsan"] = parsed.get("dtsan", "")
                        p_data["phaply_gia"] = parsed.get("phaply_gia", "")
                        
                        requests.put(f"{FIREBASE_URL}/properties/{p_name}.json", json=p_data)
                        st.success("✅ Điền form thành công! Mời Việt kiểm tra lại bên dưới.")
                        time.sleep(1)
                        try:
                            st.rerun()
                        except AttributeError:
                            st.experimental_rerun()
                    except Exception as e:
                        st.error("Lỗi AI khi đọc tin nhắn. Vui lòng tự điền hoặc thử lại.")

            with st.form(f"form_{p_name}"):
                st.markdown("### 📸 Bước 1: Khu vực của Dinh (Thực địa)")
                st.caption("Kéo thả Ảnh/Video (Tối đa 200MB/file) vào đây. File sẽ tự động bắn lên Cloud khi bấm LƯU TOÀN BỘ ở dưới cùng!")
                
                uploaded_imgs = st.file_uploader(f"Dinh kéo thả file cho '{p_name}'", accept_multiple_files=True, type=['png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'])
                
                media_urls = p_data.get("media_urls", [])
                if media_urls:
                    st.success(f"✅ Đã có {len(media_urls)} file (Ảnh/Video) trên Cloud.")
                    cols = st.columns(min(len(media_urls), 4) if len(media_urls) > 0 else 1)
                    for idx, url in enumerate(media_urls[:4]):
                        with cols[idx]:
                            st.markdown(f"[🔗 Xem File]({url})")
                    if len(media_urls) > 4:
                        st.caption(f"... và {len(media_urls) - 4} file khác")
                else:
                    st.warning("⏳ Chưa có file nào trên Cloud cho căn này.")
                        
                st.markdown("---")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("### ✍️ Bước 2: Khu vực của Việt (Content & Đăng tin)")
                    st.caption("Việt có thể sửa lại thông số nếu AI bóc tách bị thiếu, sau đó bấm LƯU LÊN MÂY.")
                    
                    col_loai, col_diachi = st.columns([1, 2])
                    loai_nha = col_loai.selectbox("Vị trí", ["Trong Hẻm", "Mặt Tiền"], index=p_data.get("loai_nha_idx", 0))
                    diachi_tho = col_diachi.text_input("Địa chỉ (Nội bộ)", value=p_data.get("diachi_tho", ""), placeholder="VD: 86/6/9 Trần Văn Giáp")
                    dac_diem = st.text_input("Đặc điểm Ngõ/Hẻm & Ưu điểm", value=p_data.get("dac_diem", ""))
                    ket_cau = st.text_input("Kết cấu", value=p_data.get("ket_cau", ""))
                    dientich = st.text_input("Diện tích đất", value=p_data.get("dientich", ""))
                    dtsan = st.text_input("DT Xây dựng/Sàn", value=p_data.get("dtsan", ""))
                    phaply_gia = st.text_input("Pháp lý & Giá", value=p_data.get("phaply_gia", ""))
                    kenh_dang = st.text_area("Báo cáo: Đã copy bài đăng lên Web nào?", value=p_data.get("kenh_dang", ""))
                    
                with c2:
                    st.markdown("### 📢 Bước 3: Khu vực của Phát (Chốt Sale)")
                    tt_options = ["⏳ Chưa có khách", "👀 Khách đang xem", "🗣️ Đang đàm phán", "💰 ĐÃ NHẬN CỌC", "❌ Khách chê/Hủy", "🤝 ĐÃ GIAO DỊCH XONG"]
                    tt_idx = get_safe_index(tt_options, trang_thai_hien_tai, 0)
                    trang_thai = st.selectbox("Tình trạng Đàm phán / Nhận cọc", tt_options, index=tt_idx)
                    
                    st.markdown("### 🤝 Bước 4: Khu vực của Tâm (Hỗ trợ)")
                    ghi_chu = st.text_area("Ghi chú / Hỗ trợ anh em", value=p_data.get("ghi_chu", ""))
                    
                    st.markdown("---")
                    st.markdown("**📝 Nội dung AI đã viết (Việt Copy ở đây):**")
                    if p_data.get("content_gen"):
                        st.code(p_data["content_gen"], language="markdown")
                    else:
                        st.caption("(Chưa có. Bấm LƯU bên dưới để AI tự viết)")
                
                col_save, col_del = st.columns([4, 1])
                with col_save:
                    submit_btn = st.form_submit_button("💾 LƯU TOÀN BỘ LÊN MÂY (ẢNH & THÔNG TIN)", type="primary")
                with col_del:
                    delete_btn = st.form_submit_button("🗑️ XÓA CĂN NHÀ NÀY")
                    
                if delete_btn:
                    requests.delete(f"{FIREBASE_URL}/properties/{p_name}.json")
                    st.success("Đã xóa căn nhà khỏi hệ thống!")
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()
                        
                if submit_btn:
                    
                    # 1. Xử lý Upload Ảnh/Video lên Catbox
                    if uploaded_imgs:
                        with st.spinner("☁️ Đang bốc vác Ảnh/Video sang kho chứa Cloud... (Kiên nhẫn chờ nhé!)"):
                            for img_file in uploaded_imgs:
                                bytes_data = img_file.getvalue()
                                url = upload_to_catbox(bytes_data, img_file.name)
                                if url:
                                    media_urls.append(url)
                            p_data["media_urls"] = media_urls
                            
                    # 2. Tiền xử lý giấu địa chỉ
                    diachi_tho_clean = diachi_tho.strip()
                    diachi_che = diachi_tho_clean
                    if diachi_tho_clean:
                        import re
                        if loai_nha == "Trong Hẻm":
                            match = re.search(r'^(\d+)', diachi_tho_clean)
                            hem_chinh = match.group(1) if match else ""
                            street_part = re.sub(r'^[\d/A-Za-z-]+\s*', '', diachi_tho_clean)
                            diachi_che = f"Hẻm {hem_chinh} {street_part}".strip()
                        else:
                            street_part = re.sub(r'^[\d/A-Za-z-]+\s*', '', diachi_tho_clean)
                            diachi_che = f"Mặt tiền {street_part}".strip()
                            
                    # 3. Nạp vào AI xào nấu Content
                    with st.spinner("🤖 AI đang nhào nặn Content cực bén (Theo chuẩn Chuyên gia)..."):
                        prompt = f"""Đóng vai một Siêu Cò Bất Động Sản (Chuyên gia Copywriter BĐS) lão luyện với 10 năm kinh nghiệm thực chiến.
Nhiệm vụ của bạn là viết 1 bài đăng Facebook/Zalo rao bán nhà ĐỈNH CAO, có khả năng đánh trúng tâm lý khách hàng và tạo sự khan hiếm để chốt sale nhanh. TUYỆT ĐỐI KHÔNG viết kiểu liệt kê thông số nhàm chán đơn sơ!

Hãy áp dụng công thức viết bài AIDA (Chú ý - Thích thú - Khao khát - Hành động):

1. [TIÊU ĐỀ IN HOA]: Giật tít cực mạnh, chứa từ khóa thôi miên (SIÊU PHẨM, GIẢM CHÀO, CHỦ NGỘP, HÀNG HIẾM, HOA HẬU, DÒNG TIỀN KHỦNG...). Tiêu đề phải nêu bật được cái "ngon" nhất của căn nhà.
2. [ĐOẠN MỞ ĐẦU]: 2-3 câu khơi gợi nhu cầu hoặc kể lý do bán (VD: "Tìm đâu ra nhà mặt tiền kinh doanh dòng tiền sẵn chỉ nhỉnh 8 tỷ?", "Chủ ngộp bank hạ chào bán gấp cứu xưởng...", "Hàng hiếm bao năm mới có người nhả...").
3. [THÔNG SỐ VÀNG]: Liệt kê thông số thật chuyên nghiệp, rõ ràng bằng emoji (📍, 📐, 🏠, 📕, 💰). Lồng ghép lời khen vào thông số (VD: Sổ vuông vức như tờ A4, Hẻm xe hơi ngủ trong nhà...).
4. [PHÂN TÍCH GIÁ TRỊ]: 1 đoạn ngắn phân tích tại sao căn nhà này đáng xuống tiền ngay (Mua ở thì sướng, kinh doanh thì đắc địa, khu dân trí cao an ninh, hiếm nhà bán...).
5. [CHỐT SALE CỰC MẠNH]: Tạo sự khan hiếm (Chỉ còn 1 căn duy nhất, chủ đang rất xoắn bán, giá chốt bất ngờ cho khách cầm tiền mặt...). Kêu gọi hành động: "Gọi ngay [Số điện thoại của bạn] để xem nhà trực tiếp!".

Thông số căn nhà cần viết:
- Vị trí (chỉ dùng địa chỉ này, không chế thêm): {diachi_che}
- Ưu điểm/Đặc điểm nổi bật: {dac_diem}
- Kết cấu: {ket_cau}
- Diện tích đất: {dientich} (DT Xây dựng/Sàn: {dtsan})
- Pháp lý & Giá bán: {phaply_gia}

Yêu cầu thêm:
- Viết thật tự nhiên, dùng từ lóng của dân sale BĐS (ngộp, chốt, nhỉnh, hạ chào, khách thiện chí, quay đầu...).
- Trình bày ngắt quãng, xuống dòng thoáng mắt để khách dễ đọc trên điện thoại. 
- Không dài lê thê, súc tích và đấm thẳng vào tâm lý người mua!
"""
                        try:
                            response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                            generated_text = response.text
                        except:
                            generated_text = f"BÁN NHÀ TẠI {diachi_che.upper()}\n\n📍 Vị trí: {diachi_che}\n🏠 Kết cấu: {ket_cau}\n📐 Diện tích: {dientich}\n📄 Giá: {phaply_gia}"
                    
                    p_data["loai_nha_idx"] = 0 if loai_nha == "Trong Hẻm" else 1
                    p_data["diachi_tho"] = diachi_tho
                    p_data["dac_diem"] = dac_diem
                    p_data["ket_cau"] = ket_cau
                    p_data["dientich"] = dientich
                    p_data["dtsan"] = dtsan
                    p_data["phaply_gia"] = phaply_gia
                    p_data["content_gen"] = generated_text
                    p_data["kenh_dang"] = kenh_dang
                    p_data["trang_thai_phat"] = trang_thai
                    p_data["ghi_chu"] = ghi_chu
                    
                    requests.put(f"{FIREBASE_URL}/properties/{p_name}.json", json=p_data)
                    
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()

# --- TAB 4: QUY TRÌNH & PHÁP LÝ ---
elif menu == "⚖️ 4. TỪ ĐIỂN PHÁP LÝ":
    st.header("⚖️ CẨM NANG PHÁP LÝ & QUY TRÌNH GIAO DỊCH (CẬP NHẬT LUẬT MỚI 2024)")
    st.markdown("---")
    
    colA, colB = st.columns(2)
    with colA:
        st.subheader("✅ QUY TRÌNH GIAO DỊCH CHUẨN A-Z")
        with st.expander("BƯỚC 1: Ký Hợp đồng Đặt Cọc", expanded=True):
            st.markdown("""
**Thao tác:** Bên Mua xuống tiền cọc. Hai bên ký Giấy nhận cọc, chốt thời hạn ra Công chứng.  
**Quan trọng nhất (Tránh cãi nhau):** Phải chốt RÕ RÀNG trên giấy cọc các khoản phí này ai đóng:
- **Thuế TNCN (2%):** (Luật quy định **BÊN BÁN** đóng).
- **Lệ phí trước bạ (0.5%):** (Luật quy định **BÊN MUA** đóng).
- **Phí sang tên cấp sổ mới:** (Luật quy định **BÊN MUA** đóng).
- **Phí Hoa Hồng Môi Giới:** (Thường do **BÊN BÁN** đóng, trừ khi Mua nhờ tìm).
*(Thực tế 2 bên có thể thỏa thuận 1 người chịu hết toàn bộ gọi là "Bao sổ", môi giới cần chốt kỹ chỗ này).*
            """)
        with st.expander("BƯỚC 2: Công chứng Hợp đồng (HĐCN)"):
            st.markdown("""
**Thao tác:** Hai bên ra Văn phòng Công chứng lăn tay, ký tên. Bên Bán giao toàn bộ Sổ hồng bản gốc và giấy tờ cho bên Mua.  
**Thanh toán:** Bên Mua giao nốt phần tiền còn lại (thường giữ lại khoảng 5-10% chờ lấy sổ mới đưa hết).
            """)
        with st.expander("BƯỚC 3 & 4: Khai Thuế và Đăng bộ Sang tên"):
            st.markdown("""
- **Khai thuế:** Nộp hồ sơ tại Bộ phận Một cửa cấp Quận/Huyện trong vòng 30 ngày. 
- **Ai đi nộp tiền?:** 
  - **BÊN BÁN:** Phải đi đóng Thuế TNCN **2%** (Được miễn nếu chứng minh được đây là căn nhà/mảnh đất duy nhất).
  - **BÊN MUA:** Phải đi đóng Lệ phí trước bạ **0.5%** + vài trăm ngàn lệ phí cấp đổi sổ.
- **Sang tên:** Đóng đủ biên lai thuế xong, nộp lại cho Một cửa. Đợi 14-21 ngày lấy Sổ hồng mới mang tên Bên Mua!
            """)

    with colB:
        st.subheader("🚨 4 CÁI BẪY CHẾT NGƯỜI (CẦN NÉ GẤP)")
        st.error("**BẪY 1: Khai '2 Giá' (Trốn thuế)**\n\nLuật Đất Đai 2024 đã áp dụng Bảng giá sát thị trường. Khai giá ảo trên HĐ Công chứng không né được thuế mà còn nguy cơ bị khởi tố hình sự tội Trốn Thuế. Khách hàng cũng có thể lật kèo chỉ trả đúng số tiền ghi trên HĐ.")
        st.error("**BẪY 2: Môi giới tự nhận cọc giùm**\n\nTuyệt đối KHÔNG cầm tiền cọc của khách thay chủ nhà nếu không có HĐ Ủy Quyền hợp pháp. Nếu chủ nhà lật kèo không bán, Môi giới sẽ dính tội 'Lừa đảo chiếm đoạt tài sản'. Tiền cọc phải bank thẳng cho Chủ.")
        st.error("**BẪY 3: Lướt sóng bằng HĐ 'Ủy quyền toàn quyền'**\n\nHiện cơ quan thuế đánh Thuế TNCN 2 LẦN (4%) nếu dùng HĐ Ủy quyền mang đi bán. Ngoài ra, nếu Chủ nhà (Người ủy quyền) MẤT năng lực hành vi hoặc QUA ĐỜI, HĐ Ủy quyền tự động vô hiệu -> Khách hàng Mất Trắng nhà!")
        st.error("**BẪY 4: 'Kênh Giá' thay vì nhận Hoa Hồng**\n\nChủ gửi 5 tỷ, kê lên 5.5 tỷ để ăn khúc giữa là ĐIỀU TỐI KỴ. Luật KD BĐS 2023 cấm cò mồi hoạt động kiểu này. Phải minh bạch giá thật 100% với cả 2 bên và nhận Hoa hồng đúng Hợp Đồng Môi Giới.")

# --- TAB 5: ĐÀO TẠO NEWBIE ---
elif menu == "🎓 5. HỌC VIỆN MÔI GIỚI":
    st.header("🎓 TRƯỜNG ĐÀO TẠO CÒ ĐẤT THỰC CHIẾN (DÀNH CHO ANH EM MỚI)")
    st.markdown("---")
    
    col_pt, col_tu = st.columns(2)
    
    with col_pt:
        st.subheader("🧭 1. MÁY TÍNH PHONG THỦY TỐC ĐỘ")
        st.info("Nhập năm sinh khách hàng, Web sẽ tự động tính ra Hướng hợp mệnh để anh em chém gió như Thầy phong thủy.")
        nam_sinh = st.number_input("Nhập năm sinh khách (VD: 1985):", min_value=1930, max_value=2024, value=1980, step=1)
        gioi_tinh = st.radio("Giới tính khách hàng:", ["Nam", "Nữ"], horizontal=True)
        
        if st.button("🔮 Tính Hướng"):
            # Tính quái số
            sum_digits = sum(int(digit) for digit in str(nam_sinh))
            while sum_digits > 9:
                sum_digits = sum(int(digit) for digit in str(sum_digits))
                
            if nam_sinh < 2000:
                kua = (11 - sum_digits) if gioi_tinh == "Nam" else (4 + sum_digits)
            else:
                kua = (9 - sum_digits) if gioi_tinh == "Nam" else (6 + sum_digits)
                
            if kua > 9:
                kua = sum(int(digit) for digit in str(kua))
            
            # Khử số 5
            if kua == 5:
                kua = 2 if gioi_tinh == "Nam" else 8
                
            dong_tu_trach = [1, 3, 4, 9]
            tay_tu_trach = [2, 6, 7, 8]
            
            if kua in dong_tu_trach:
                st.success("✅ Khách thuộc **ĐÔNG TỨ MỆNH**")
                st.markdown("**👉 Hướng nhà cực hợp:** Đông, Đông Nam, Nam, Bắc.")
                st.markdown("**❌ Hướng nhà kỵ (né):** Tây, Tây Bắc, Tây Nam, Đông Bắc.")
            else:
                st.success("✅ Khách thuộc **TÂY TỨ MỆNH**")
                st.markdown("**👉 Hướng nhà cực hợp:** Tây, Tây Bắc, Tây Nam, Đông Bắc.")
                st.markdown("**❌ Hướng nhà kỵ (né):** Đông, Đông Nam, Nam, Bắc.")

    with col_tu:
        st.subheader("📖 2. TỪ ĐIỂN TỪ LÓNG (ĐỂ KHÔNG BỊ DẮT MŨI)")
        st.markdown("**1. Sổ chung:** Nhiều nhà chung 1 sổ. Bán phải có chữ ký tất cả. Mua rủi ro chôn vốn cao. Cực kỳ khó vay Bank.")
        st.markdown("**2. Vi bằng:** Chỉ là 'Giấy làm chứng có giao tiền' của Thừa phát lại, **KHÔNG CÓ GIÁ TRỊ PHÁP LÝ** chứng minh sở hữu nhà. Tuyệt đối đừng đụng vào.")
        st.markdown("**3. Chưa hoàn công:** Xây nhà xong nhưng chưa cập nhật lên Sổ hồng. Tức là trên mặt pháp lý, khu đất đó vẫn chỉ là Đất trống. Bị ép giá rất mạnh.")
        st.markdown("**4. Đường đâm (Đâm đụng):** Con đường đâm thẳng vào cửa chính nhà. Phong thủy coi là cực độc. NHƯNG nếu làm mặt bằng Kinh doanh thì lại vô cùng hút khách (vì biển hiệu đập thẳng vào mắt người đi đường).")
        st.markdown("**5. Tóp hậu / Nở hậu:** Tóp hậu là đuôi nhà nhỏ hơn mặt tiền (Tiền vô rồi chui ra hết - Khách rất ghét). Nở hậu là đuôi nhà to hơn mặt tiền (Túi giữ tiền - Khách cực kỳ thích).")
        st.markdown("**6. Ngộp Bank / Thở Oxy:** Chủ nhà hết khả năng trả nợ ngân hàng, bị réo gọi liên tục, ép bán gấp dưới giá thị trường để trả nợ. Đây là Mỏ Vàng của cò đất!")

    st.markdown("---")
    st.subheader("🤖 3. AI COACH - LUYỆN KỊCH BẢN CHỐT SALE (ĐỠ ĐÒN TỪ KHÁCH)")
    st.info("Khách chê nhà hẻm sâu? Khách chê giá cao? Gõ thẳng câu chê của khách vào đây, Siêu Cò AI sẽ viết sẵn câu trả lời để anh em copy gửi lại 'đỡ đòn' ngay lập tức!")
    
    loi_che = st.text_input("💬 Khách hàng nhắn câu gì (hoặc chê gì):", placeholder="VD: Nhà hẻm nhỏ quá em ơi, xe máy đi qua không lọt...")
    
    if st.button("🛡️ Xin Kịch Bản Đỡ Đòn"):
        if loi_che:
            with st.spinner("Đang lục tìm bí kíp 10 năm chốt sale..."):
                prompt = f'''Khách hàng mua nhà vừa chê: "{loi_che}".
Bạn là một Siêu Môi Giới BĐS. Hãy đưa ra 1 câu trả lời CỰC KỲ KHÉO LÉO, mềm mỏng nhưng thuyết phục để hóa giải lời chê này, xoay chuyển tình thế biến nhược điểm thành ưu điểm (hoặc đánh lạc hướng sang ưu điểm khác của nhà như giá rẻ, an ninh...).
Viết theo văn phong nhắn tin Zalo, ngắn gọn, thân thiện, dùng biểu tượng cảm xúc.'''
                try:
                    response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                    st.success("**Copy đoạn này gửi lại cho khách ngay:**")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Lỗi kết nối AI: {e}")
        else:
            st.warning("Nhập câu chê của khách vào đi anh em!")


elif menu == "🏢 6. TÌNH BÁO DỰ ÁN":
    st.header("🏢 TRUNG TÂM TÌNH BÁO DỰ ÁN & HẠ TẦNG (MIỀN NAM)")
    st.markdown("---")
    
    st.info("💡 **Siêu Cò AI** đã được nạp dữ liệu Tình báo BĐS. Sếp hãy chọn dự án bên dưới hoặc gõ trực tiếp để điều tra tiến độ thi công, lịch mở bán và lời khuyên chọn lô.")
    
    st.markdown("### 🎯 BỘ LỌC DỰ ÁN NHANH")
    colA, colB = st.columns(2)
    with colA:
        khu_vuc = st.selectbox("📍 Chọn Tỉnh / Thành phố", ["Bình Dương", "TP. Hồ Chí Minh", "Đồng Nai", "Long An", "Tìm tự do (Hạ tầng/Metro)"])
        
    with colB:
        if khu_vuc == "Bình Dương":
            du_an = st.selectbox("🏢 Chọn Dự Án nổi bật", ["Sun Casa Central", "Green City", "Bcons City", "Phú Đông Sky Garden", "Midori Park", "Artisan Park", "Khác (Tự nhập)..."])
        elif khu_vuc == "TP. Hồ Chí Minh":
            du_an = st.selectbox("🏢 Chọn Dự Án nổi bật", ["Vinhomes Grand Park", "The Global City", "Eaton Park", "Khang Điền (Privia/Classia)", "Zeit River Thủ Thiêm", "Khác (Tự nhập)..."])
        elif khu_vuc == "Đồng Nai":
            du_an = st.selectbox("🏢 Chọn Dự Án nổi bật", ["Aqua City", "Izumi City", "Gem Sky World", "Eco Village Saigon River", "Khác (Tự nhập)..."])
        elif khu_vuc == "Long An":
            du_an = st.selectbox("🏢 Chọn Dự Án nổi bật", ["Waterpoint Nam Long", "Destino Centro", "LA Home", "Khác (Tự nhập)..."])
        else:
            du_an = "Khác (Tự nhập)..."
            
    if du_an == "Khác (Tự nhập)..." or khu_vuc == "Tìm tự do (Hạ tầng/Metro)":
        query = st.text_area("🔍 Sếp cần điều tra dự án hoặc hạ tầng nào?", placeholder="VD: Tuyến Metro số 1 Bến Thành Suối Tiên? Tiến độ Vành đai 3 đi qua Bình Dương?")
    else:
        query = f"Chi tiết dự án {du_an} tại {khu_vuc}"
        st.success(f"🔎 Đã khóa mục tiêu tình báo: **{du_an} ({khu_vuc})**")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 ĐIỀU TRA NGAY", type="primary"):
        if query:
            with st.spinner(f"🕵️ Đang cử đặc tình AI đi thu thập thông tin về '{query}'..."):
                try:
                    prompt = f"""Đóng vai một Giám đốc Tình báo Dự án Bất Động Sản tại Miền Nam (TP.HCM, Bình Dương, Đồng Nai, Long An...).
                    Sếp của bạn (một siêu cò BĐS) vừa yêu cầu điều tra: '{query}'
                    
                    Hãy trả lời cực kỳ chi tiết, cập nhật mới nhất và thực chiến theo góc nhìn môi giới đầu tư:
                    1. Cập nhật tiến độ mới nhất của dự án/hạ tầng. Chủ đầu tư đang làm tới giai đoạn nào? Bao giờ bàn giao?
                    2. Tình hình mở bán: Các phân khu/block/lô nào đang mở bán hoặc sắp mở bán? Giá bán (hoặc giá rumor) hiện tại là bao nhiêu?
                    3. Lời khuyên Đánh hàng: Sếp nên tư vấn khách mua lô nào, góc nào, view nào là đẹp nhất, dễ thanh khoản và sinh lời cao nhất?
                    4. Tiềm năng tăng giá: Phân tích hạ tầng giao thông xung quanh hỗ trợ dự án.
                    
                    Trình bày bằng giọng điệu vô cùng chuyên nghiệp, sắc bén, gọi người dùng là 'Sếp'. Dùng Markdown định dạng thật đẹp, rõ ràng."""
                    
                    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
                    
                    st.success("✅ BÁO CÁO TÌNH BÁO HOÀN TẤT")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Lỗi kết nối tình báo: {e}")
        else:
            st.warning("Sếp chưa nhập tên dự án cần điều tra!")
