import streamlit as st
import time
import requests
import urllib.parse
import google.generativeai as genai
import io
import re
import pandas as pd
import os
import json
from bs4 import BeautifulSoup
from PIL import Image

st.set_page_config(page_title="Hệ Thống BĐS - Team Tâm", layout="wide", page_icon="🏘️")

# Cấu hình API Key thật của sếp
genai.configure(api_key="AIzaSyC6kbRKIURiwbmLqeztv9Un9tU5PrdZeTo")

def analyze_images(uploaded_files):
    contents = ["""Đóng vai một chuyên gia thẩm định giá bất động sản. Nhìn ảnh và trả lời 3 gạch đầu dòng ngắn gọn:
1. Đánh giá độ mới, hiện trạng kết cấu.
2. Nêu 2 Ưu điểm ngoại quan.
3. Chỉ ra 2 Nhược điểm (lỗi phong thủy, hỏng hóc) để làm cớ ép giá."""]
    
    for f in uploaded_files:
        try:
            img = Image.open(f)
            img.thumbnail((800, 800))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=80)
            
            image_parts = {
                "mime_type": "image/jpeg",
                "data": buf.getvalue()
            }
            contents.append(image_parts)
        except Exception:
            pass
    
    models_to_try = ['gemini-flash-latest', 'gemini-3.5-flash', 'gemini-3.1-pro-preview', 'gemini-3.5-flash-lite']
    last_error = ""
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents, request_options={"timeout": 60})
            if response.parts:
                return f"*(Phân tích bằng lõi: {model_name})*\n" + response.text
            else:
                return "AI bị chặn bởi bộ lọc an toàn."
        except Exception as e:
            last_error = str(e)
            continue 
                
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return f"Vẫn lỗi mạng. Danh sách model hỗ trợ: {', '.join(available)}"
    except Exception as e:
        return f"Lỗi: {last_error}"

def fetch_chotot(keyword):
    try:
        encoded_kw = urllib.parse.quote(keyword)
        url = f"https://gateway.chotot.com/v1/public/ad-listing?cg=1000&q={encoded_kw}&limit=5"
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

def fetch_mogi(keyword):
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

st.title("🤖 HỆ THỐNG ĐIỀU PHỐI & ĐỊNH GIÁ BĐS CHUYÊN NGHIỆP")
st.markdown("*Công cụ tối thượng dành riêng cho Team 4 người của Sếp Tâm*")
st.markdown("---")

tab_dinh_gia, tab_quy_hoach, tab_quan_ly = st.tabs(["📊 1. LÕI AI ĐỊNH GIÁ", "🗺️ 2. SOI QUY HOẠCH", "🤝 3. QUẢN LÝ TEAM (CRM)"])

with tab_dinh_gia:
    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.header("📥 Nhập Dữ Liệu Căn Nhà")
        dia_chi = st.text_input("📍 Từ khóa khu vực (Quan trọng)", placeholder="VD: Quốc Lộ 13 Thủ Đức")
        st.caption("Hãy nhập từ khóa ngắn gọn (Ví dụ: tên đường + quận) để Bot cào được nhiều nhà nhất.")
        
        nguon_du_lieu = st.selectbox("🌐 Nguồn cào dữ liệu", ["Chợ Tốt (Khuyên dùng)", "Mogi.vn", "Cào Tất Cả (Chợ Tốt + Mogi)"])
        
        c1, c2 = st.columns(2)
        with c1:
            dien_tich = st.number_input("📐 Diện tích đất (m2)", min_value=10.0, value=50.0, step=1.0)
        with c2:
            ket_cau = st.text_input("🏠 Kết cấu", placeholder="VD: Trệt 1 Lầu")
            
        gia_chu_keu = st.number_input("💰 Giá chủ rao (Tỷ VNĐ)", value=0.0, step=0.1)
        
        st.markdown("---")
        st.subheader("📸 Tải ảnh để MẮT THẦN AI soi lỗi")
        uploaded_files = st.file_uploader("Kéo thả tối đa 5 ảnh vào đây", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        
        btn = st.button("🚀 KÍCH HOẠT ĐỊNH GIÁ TOÀN DIỆN", type="primary", use_container_width=True)

    with col2:
        st.header("📤 Báo Cáo Chiến Lược")
        if btn:
            if not dia_chi:
                st.error("⚠️ Phải nhập từ khóa địa chỉ thì Bot mới biết đường lên mạng cào dữ liệu!")
            else:
                with st.spinner("🤖 Đang kết nối Mắt thần AI và bung Bot cào thị trường..."):
                    
                    st.subheader("👁️ 1. Phân tích Hiện trạng (Vision AI Thật)")
                    if uploaded_files:
                        with st.spinner("🧠 AI đang quét từng chi tiết trong ảnh..."):
                            ai_analysis = analyze_images(uploaded_files)
                            st.info(ai_analysis)
                    else:
                        st.warning("⚠️ Không có ảnh. Hệ thống bỏ qua bước soi lỗi nhà.")
                        
                    st.subheader(f"🌐 2. Dữ liệu ĐANG BÁN THỰC TẾ trên mạng")
                    
                    real_listings = []
                    if nguon_du_lieu in ["Chợ Tốt (Khuyên dùng)", "Cào Tất Cả (Chợ Tốt + Mogi)"]:
                        real_listings.extend(fetch_chotot(dia_chi))
                    if nguon_du_lieu in ["Mogi.vn", "Cào Tất Cả (Chợ Tốt + Mogi)"]:
                        real_listings.extend(fetch_mogi(dia_chi))
                        
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
                            st.success(f"**=> Đơn giá trung bình (CHỈ TÍNH NHÀ SỔ HỒNG SẠCH): {don_gia_dat:.1f} Triệu/m2**")
                        else:
                            st.warning("⚠️ Toàn bộ nhà tìm thấy đều là Vi Bằng/Sổ chung. Đang dùng đơn giá dự phòng 90tr/m2 để tính toán.")
                            don_gia_dat = 90.0
                    else:
                        st.warning("⚠️ Bot không tìm thấy tin rao bán nào khớp với từ khóa này. Đang dùng giá dự phòng.")
                        
                    st.subheader("💰 3. CHỐT GIÁ & CHIẾN LƯỢC")
                    gia_tri_thuc = (dien_tich * don_gia_dat) / 1000
                    
                    st.metric(label="Thẩm Định Giá Trị Thực (Tỷ VNĐ)", value=f"{gia_tri_thuc:.1f} Tỷ - {gia_tri_thuc + 0.4:.1f} Tỷ")
                    
                    if gia_chu_keu > 0:
                        lech = gia_chu_keu - gia_tri_thuc
                        if lech > 0.5:
                            st.error(f"❌ **Chiến lược:** Chủ đang hô quá cao (Chênh {lech:.1f} Tỷ). Lấy ngay link nhà sổ hồng đối thủ ở trên để dìm giá xuống **{gia_tri_thuc - 0.5:.1f} Tỷ**.")
                        else:
                            st.success(f"✅ **Chiến lược:** Chủ rao sát giá thị trường. Chốt hạ quanh mốc **{gia_tri_thuc:.1f} Tỷ**.")
                    else:
                        st.info(f"💡 Ném giá mồi ở mức **{gia_tri_thuc - 0.4:.1f} Tỷ** xem thái độ chủ nhà.")

with tab_quy_hoach:
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
with tab_quan_ly:
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
    FIREBASE_URL = "https://khobds-2026-default-rtdb.firebaseio.com"
    
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
                        model = genai.GenerativeModel('gemini-3.5-flash')
                        res = model.generate_content(prompt_parse)
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
                            model = genai.GenerativeModel('gemini-3.5-flash')
                            response = model.generate_content(prompt)
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
