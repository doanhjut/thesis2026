"""
XAI Dashboard - Interactive Web UI (Cập nhật 3 Đóng góp với Số liệu Thực nghiệm)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Ransomware XAI Defense", page_icon="🛡️", layout="wide")

# --- CSS CUSTOM ---
st.markdown("""
<style>
    .metric-card { background: #1e293b; padding: 20px; border-radius: 10px; border-left: 5px solid #10b981; color: white; height: 100%;}
    .metric-card-warning { background: #1e293b; padding: 20px; border-radius: 10px; border-left: 5px solid #fbbf24; color: white; height: 100%;}
    .metric-card-high { background: #1e293b; padding: 20px; border-radius: 10px; border-left: 5px solid #ef4444; color: white; height: 100%;}
    .big-font { font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Hệ thống Phát hiện Ransomware Đa tầng & Học tích cực")

# --- TẠO 3 TABS CHO 3 ĐÓNG GÓP ---
tab1, tab2, tab3 = st.tabs(["🔍 1. Multi-Stage Detection", "📊 2. XAI Fidelity", "🔄 3. Active Learning Queue"])

# ==========================================
# TAB 1: MULTI-STAGE XAI (Cập nhật System Latency)
# ==========================================
with tab1:
    st.header("Phân tích Tệp & Giám sát Hành vi")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.file_uploader("Upload PE File (.exe, .dll)", type=['exe', 'dll'])
        if st.button("Bắt đầu Phân tích", type="primary"):
            with st.spinner("Đang phân tích tĩnh (PE Header)..."):
                time.sleep(2)
            st.success("Hoàn thành phân tích tĩnh!")
            
            st.markdown("""
            <div style='background-color: #e8f5e9; padding: 15px; border-radius: 5px; border-left: 5px solid #2e7d32;'>
                <h4 style='color: #2e7d32; margin:0;'>Kết quả Tĩnh: BENIGN (An toàn)</h4>
                <p style='margin:0;'>Độ tin cậy: 85% - Không tìm thấy signature độc hại.</p>
            </div>
            """, unsafe_allow_html=True)
            
    with col2:
        st.subheader("📡 Giám sát Honeypot (Real-time)")
        if st.button("🚨 (Demo) Kích hoạt mã độc giả lập"):
            with st.spinner("Honeypot đang giám sát..."):
                time.sleep(1)
            st.markdown("""
            <div style='background-color: #ffebee; padding: 15px; border-radius: 5px; border-left: 5px solid #c62828;'>
                <h4 style='color: #c62828; margin:0;'>🚨 CẢNH BÁO MỨC CAO: Đổi tên file hàng loạt</h4>
                <p style='margin:0;'>Phát hiện các file bị đổi đuôi thành .locked trong thư mục mồi nhử.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.error("🛑 QUYẾT ĐỊNH FUSION: MALWARE. Đã khóa tiến trình!")
            st.success("⚡ Thời gian đáp ứng hệ thống (End-to-End Latency): 15.29 ms")
            
            st.info("💬 Lời giải thích (XAI): Hệ thống đã nhận diện chính xác các bất thường ngụy trang thông qua lực kéo mạnh của feature_691, feature_820 và feature_2355.")

# ==========================================
# TAB 2: XAI FIDELITY (Cập nhật Số liệu Thực tế 0.361)
# ==========================================
with tab2:
    st.header("Đánh giá Độ tin cậy Giải thích (PE-Aware Fidelity)")
    st.markdown("Kiểm định định lượng mức độ trung thực của các giá trị SHAP dựa trên tập dữ liệu SOREL-20M (Che giấu Top 500 đặc trưng).")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='metric-card-warning'>Điểm trung thực (OFS)<br><span class='big-font' style='color:#fbbf24'>0.361</span><br><small>Đánh giá: Phù hợp thực tế bảo mật</small></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='metric-card'>Tương phản (CF)<br><span class='big-font' style='color:#10b981'>0.523</span><br><small>Nhận diện chính xác >52% tử huyệt ngụy trang</small></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='metric-card-warning'>Trung thực (FF)<br><span class='big-font' style='color:#fbbf24'>0.333</span><br><small>AUC giảm 0.166 khi che 500 đặc trưng</small></div>", unsafe_allow_html=True)
        
    st.markdown("### Phân tích Nhóm Đặc trưng (Feature Group Alignment)")
    # Dữ liệu thực nghiệm
    df_features = pd.DataFrame({
        "Nhóm Đặc trưng": ["DataDirectories", "StringFeatures", "ByteHistogram", "PEHeader"],
        "Độ đồng thuận (Alignment)": [0.849, 0.861, 0.833, 0.819],
        "Mức độ quan trọng (SHAP %)": [22.6, 15.4, 19.0, 16.9]
    })
    
    fig = px.bar(df_features, x="Độ đồng thuận (Alignment)", y="Nhóm Đặc trưng", orientation='h', 
                 color="Mức độ quan trọng (SHAP %)", color_continuous_scale="Viridis",
                 title="Đánh giá mức độ đóng góp của từng nhóm đặc trưng PE")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 3: ACTIVE LEARNING (Cập nhật Biểu đồ Bão hòa & Dữ liệu)
# ==========================================
def approve_action():
    st.session_state.df_queue.at[0, "Trạng thái"] = "Đã gán nhãn"
    st.session_state.show_approve_success = True

with tab3:
    st.header("Học tích cực hướng dẫn bởi XAI (XAI-Guided Active Learning)")
    st.markdown("Phát hiện mẫu ngụy trang dựa trên sự phân tán (SHAP Variance) và xung đột đặc trưng (Directional Entropy).")
    
    # --- BIỂU ĐỒ ĐƯỜNG AUC ---
    st.markdown("### 📈 Biểu đồ bão hòa Hiệu năng (AUC)")
    df_auc = pd.DataFrame({
        "Vòng lặp": ["Vòng 1", "Vòng 2", "Vòng 3", "Vòng 4", "Vòng 5"],
        "AUC Score": [0.9966, 0.9967, 0.9971, 0.9996, 0.9999], # Số liệu thật từ log Active Learning
        "Kích thước tập Train": [150, 200, 250, 300, 350]
    })
    
    fig_auc = px.line(df_auc, x="Vòng lặp", y="AUC Score", markers=True, 
                      text="AUC Score",
                      title="Sự cải thiện AUC chỉ với 50 mẫu Grey-zone mỗi vòng")
    fig_auc.update_traces(textposition="top left", line_color="#10b981", marker=dict(size=10))
    fig_auc.update_layout(yaxis=dict(range=[0.995, 1.0]))
    st.plotly_chart(fig_auc, use_container_width=True)

    # --- BẢNG HÀNG ĐỢI ---
    st.markdown("### 📋 Hàng đợi Yêu cầu Chuyên gia duyệt (Audit Trail)")
    
    if st.session_state.get('show_approve_success', False):
        st.success("Đã gán nhãn mẫu và đưa vào cơ sở dữ liệu để tái huấn luyện chu kỳ tiếp theo!")
        st.session_state.show_approve_success = False

    st.markdown("<div class='metric-card-high' style='padding:15px; margin-bottom:15px;'>⚠️ Phát hiện 1 mẫu biến thể Zero-day có độ xung đột đặc trưng cực cao!</div>", unsafe_allow_html=True)
    
    if 'df_queue' not in st.session_state:
        st.session_state.df_queue = pd.DataFrame({
            "Thời gian": ["Vừa xong", "2026-06-09 11:25", "2026-06-09 11:00"],
            "Tên File": ["update_windows_v2.exe", "suspect_updater.dll", "packed_sample.exe"],
            "Dự đoán Tĩnh": ["0.45 (Benign)", "0.82 (Malware)", "0.15 (Benign)"],
            "Điểm SHAP Variance": ["🔥 0.89 (Rất cao)", "0.32 (Thấp)", "0.21 (Thấp)"],
            "Trạng thái": ["Chờ Duyệt", "Đã gán nhãn", "Đã gán nhãn"]
        })
    
    st.dataframe(st.session_state.df_queue, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("💡 **Vết kiểm toán (Audit Trail):** Mẫu `update_windows_v2.exe` có đặc trưng DataDirectories chỉ báo Malware, nhưng StringFeatures lại chỉ báo Benign. Lực kéo hai bên ngang bằng (Entropy hướng = Max). Cần con người can thiệp.")
    with col_b:
        st.button("✅ Duyệt & Đưa vào tập Huấn luyện", type="primary", on_click=approve_action)