"""Interactive, offline replay of the three measured thesis contributions."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.defense_demo import DEFAULT_BUNDLE, load_demo_bundle


COLORS = {
    "blue": "#114A7E",
    "red": "#BE3737",
    "orange": "#F48024",
    "green": "#23915A",
    "gray": "#55606E",
}

METHOD_LABELS = {
    "Static_only": "Static only",
    "Dynamic_only": "Dynamic only",
    "Average_50_50": "Average 50/50",
    "Max_score": "Max-risk",
    "Fixed_weight": "Fixed weight",
    "Logistic_stack": "Logistic stacking",
    "Reliability_P": "Adaptive P",
    "Reliability_PI": "Adaptive PI",
    "Reliability_full_PID": "Full PID",
}

METHOD_COLORS = {
    "Static_only": COLORS["blue"],
    "Dynamic_only": COLORS["gray"],
    "Average_50_50": "#6D8BA4",
    "Max_score": "#9AA5AE",
    "Fixed_weight": "#6750A4",
    "Logistic_stack": "#222222",
    "Reliability_P": COLORS["red"],
    "Reliability_PI": "#D66A5D",
    "Reliability_full_PID": "#8C1D2C",
    "Random": "#7C8793",
    "Uncertainty": COLORS["blue"],
    "U+H": COLORS["orange"],
    "U+V": COLORS["green"],
    "XAI_full": "#8C4FA3",
}


st.set_page_config(
    page_title="Demo ba đóng góp luận văn",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .block-container {padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1450px;}
  .demo-banner {padding: .8rem 1rem; border-radius: .6rem; background: #E7F2FA;
                border-left: 6px solid #114A7E; margin-bottom: 1rem;}
  .contribution {padding: 1rem; border-radius: .7rem; min-height: 150px;
                 box-shadow: 0 1px 4px rgba(0,0,0,.12);}
  .c1 {background:#FBEBEB; border-top:7px solid #BE3737;}
  .c2 {background:#FFF4E4; border-top:7px solid #F48024;}
  .c3 {background:#E8F7EF; border-top:7px solid #23915A;}
  .talk {padding:.8rem 1rem; border-left:5px solid #114A7E; background:#F6F8FA;
         border-radius:.3rem; margin:.6rem 0;}
  .scope {font-size:.92rem; color:#394653; padding:.65rem .9rem; background:#FFF8E8;
          border:1px solid #F0C36E; border-radius:.5rem;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_bundle() -> dict:
    configured = os.environ.get("THESIS_DEMO_BUNDLE")
    path = Path(configured) if configured else REPO_ROOT / DEFAULT_BUNDLE
    if not path.is_absolute():
        path = REPO_ROOT / path
    return load_demo_bundle(path)


def method_label(value: str) -> str:
    return METHOD_LABELS.get(value, value)


def metric_card(column, label: str, value: str, help_text: str | None = None):
    column.metric(label, value, help=help_text)


def presenter_note(text: str):
    st.markdown(f'<div class="talk"><b>Lời trình bày:</b> {text}</div>', unsafe_allow_html=True)


def scope_note(text: str):
    st.markdown(f'<div class="scope"><b>Phạm vi:</b> {text}</div>', unsafe_allow_html=True)


def overview(bundle: dict):
    st.title("Demo ba đóng góp của luận văn")
    st.markdown(
        '<div class="demo-banner"><b>Chế độ:</b> phát lại artifact thực nghiệm '
        "đã đo. Dashboard không tải, nhận hoặc thực thi PE; không gọi mạng và "
        "không huấn luyện lại mô hình.</div>",
        unsafe_allow_html=True,
    )
    st.subheader("Một luồng: ra quyết định → cập nhật mô hình → kiểm chứng căn cứ")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="contribution c1"><h3>1. Dung hợp thích nghi</h3>'
            "<p>Quan sát điểm tĩnh, điểm động và trọng số thay đổi theo chuỗi; "
            "đối chiếu Fixed, Logistic stacking, Adaptive P và Full PID.</p>"
            "<b>Kết quả trọng tâm:</b> Adaptive P giảm 1,28 pp FPR so với Fixed."
            "</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="contribution c2"><h3>2. XAI-Guided AL</h3>'
            "<p>Theo dõi đường học khi thêm nhãn và so sánh Random, Uncertainty, "
            "U+H, U+V, XAI-full.</p><b>Kết quả trọng tâm:</b> XAI-full giảm 92 "
            "nhãn so với Random.</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="contribution c3"><h3>3. Kiểm chứng Fidelity</h3>'
            "<p>Che top-|SHAP| và đặc trưng ngẫu nhiên cùng số lượng; kiểm tra "
            "ổn định thứ hạng qua seed/fold.</p><b>Kết quả trọng tâm:</b> top-50 "
            "làm AUC giảm 0,3067; random giảm 0,0010.</div>",
            unsafe_allow_html=True,
        )
    st.markdown("### Trình tự đề xuất khi demo")
    st.write(
        "Chọn lần lượt **Đóng góp 1 → Đóng góp 2 → Đóng góp 3** ở thanh bên. "
        "Mỗi phần chỉ cần một biểu đồ, một con số và một câu giới hạn."
    )
    presenter_note(
        "Ba đóng góp xử lý ba thời điểm khác nhau của hệ thống: dung hợp bằng "
        "chứng để ra quyết định, chọn đúng mẫu để cập nhật, và kiểm tra xem lời "
        "giải thích có thật sự bám vào mô hình hay không."
    )


def pid_page(bundle: dict):
    pid = bundle["pid"]
    st.title("Đóng góp 1 — Dung hợp thích nghi theo chuỗi")
    methods = pd.DataFrame(pid["methods"])
    methods["display"] = methods["method"].map(method_label)

    p_row = methods.loc[methods["method"] == "Reliability_P"].iloc[0]
    fixed_row = methods.loc[methods["method"] == "Fixed_weight"].iloc[0]
    pid_row = methods.loc[methods["method"] == "Reliability_full_PID"].iloc[0]
    a, b, c, d = st.columns(4)
    metric_card(a, "Cohort", f"{pid['samples']:,} mẫu".replace(",", "."))
    metric_card(b, "Adaptive P — FPR", f"{100*p_row.fpr:.2f}%".replace(".", ","))
    metric_card(c, "Fixed — FPR", f"{100*fixed_row.fpr:.2f}%".replace(".", ","))
    metric_card(d, "Full PID — AUC", f"{pid_row.auc:.4f}".replace(".", ","))

    chart_methods = [
        "Average_50_50",
        "Max_score",
        "Logistic_stack",
        "Fixed_weight",
        "Reliability_full_PID",
        "Reliability_P",
    ]
    bars = methods[methods["method"].isin(chart_methods)].copy()
    bars["FPR (%)"] = 100 * bars["fpr"]
    bars = bars.sort_values("FPR (%)", ascending=True)
    fig = px.bar(
        bars,
        x="FPR (%)",
        y="display",
        orientation="h",
        text="FPR (%)",
        color="method",
        color_discrete_map=METHOD_COLORS,
        title="FPR tại operating point đã khóa — thấp hơn tốt hơn",
    )
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig.update_layout(showlegend=False, yaxis_title=None, height=390, margin=dict(r=60))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Phát lại một vết dự đoán đã đo")
    titles = [item["title"] for item in pid["scenarios"]]
    selected = st.selectbox("Tình huống", titles, index=0)
    scenario = next(item for item in pid["scenarios"] if item["title"] == selected)
    st.info(scenario["summary"])
    trace = pd.DataFrame(scenario["trace"])
    trace["display"] = trace["method"].map(method_label)

    left, right = st.columns([1.65, 1])
    with left:
        score_fig = go.Figure()
        show_methods = [
            "Static_only",
            "Dynamic_only",
            "Fixed_weight",
            "Reliability_P",
            "Reliability_full_PID",
        ]
        for method in show_methods:
            part = trace[trace["method"] == method]
            score_fig.add_trace(
                go.Scatter(
                    x=part["event_count"],
                    y=part["score"],
                    mode="lines+markers",
                    name=method_label(method),
                    line=dict(color=METHOD_COLORS[method], width=3),
                )
            )
        score_fig.update_layout(
            title="Điểm theo số sự kiện API đã quan sát",
            xaxis_title="Số sự kiện API",
            yaxis_title="Điểm malware",
            yaxis_range=[0, 1],
            height=430,
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(score_fig, width="stretch")
    with right:
        final = (
            trace.sort_values("time_step")
            .groupby("method", as_index=False)
            .tail(1)
        )
        final = final[final["method"].isin(show_methods)].copy()
        final["Phương pháp"] = final["method"].map(method_label)
        final["Điểm cuối"] = final["score"].round(4)
        final["Ngưỡng"] = final["threshold"].round(4)
        final["Quyết định"] = final["predicted_label"].map(
            {0: "Lành", 1: "Malware"}
        )
        st.dataframe(
            final[["Phương pháp", "Điểm cuối", "Ngưỡng", "Quyết định"]],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            f"Nhãn tham chiếu: {'Malware' if scenario['label'] else 'Lành'} · "
            f"row_id={scenario['row_id']} · SHA-256={scenario['sha256'][:12]}…"
        )

    weight = trace[
        trace["method"].isin(["Reliability_P", "Reliability_full_PID"])
    ]
    weight_fig = px.line(
        weight,
        x="event_count",
        y="w_static",
        color="method",
        markers=True,
        color_discrete_map=METHOD_COLORS,
        labels={"event_count": "Số sự kiện API", "w_static": "Trọng số kênh tĩnh"},
        title="Trọng số kênh tĩnh được cập nhật theo chuỗi",
    )
    weight_fig.for_each_trace(lambda item: item.update(name=method_label(item.name)))
    weight_fig.update_layout(height=330, yaxis_range=[0, 1])
    st.plotly_chart(weight_fig, width="stretch")

    presenter_note(
        "Biểu đồ cột trả lời câu hỏi ở mức cohort. Vết mẫu trả lời cơ chế: khi "
        "hai kênh bất đồng, trọng số không còn cố định mà thay đổi theo lịch sử "
        "quan sát. Con số cần chốt là Adaptive P giảm 1,28 điểm phần trăm FPR "
        "so với Fixed, đồng thời Brier cũng giảm."
    )
    scope_note(pid["notice"])


def al_page(bundle: dict):
    al = bundle["active_learning"]
    st.title("Đóng góp 2 — Học tích cực hướng dẫn bởi giải thích")
    summary = pd.DataFrame(al["summary"])
    curves = pd.DataFrame(al["learning_curves"])
    xai = summary[summary["method"] == "XAI_full"].iloc[0]
    random = summary[summary["method"] == "Random"].iloc[0]
    uh = summary[summary["method"] == "U+H"].iloc[0]
    uv = summary[summary["method"] == "U+V"].iloc[0]
    saved = int(random.mean_labels_reached - xai.mean_labels_reached)
    saved_pct = 100 * saved / random.mean_labels_reached

    a, b, c, d = st.columns(4)
    metric_card(a, "XAI-full tiết kiệm", f"{saved} nhãn")
    metric_card(b, "So với Random", f"−{saved_pct:.1f}%".replace(".", ","))
    metric_card(c, "U+H — ROC-AULC", f"{uh.auc_aulc_mean:.4f}".replace(".", ","))
    metric_card(d, "XAI-full overhead", f"{xai.query_share_percent:.2f}%".replace(".", ","))

    metric = st.radio(
        "Chỉ số trên đường học",
        ["ROC-AUC", "Average Precision"],
        horizontal=True,
    )
    selected_methods = st.multiselect(
        "Chiến lược",
        ["Random", "Uncertainty", "U+H", "U+V", "XAI_full"],
        default=["Random", "Uncertainty", "U+H", "XAI_full"],
    )
    y_col = "test_auc_mean" if metric == "ROC-AUC" else "test_ap_mean"
    sd_col = "test_auc_sd" if metric == "ROC-AUC" else "test_ap_sd"
    plot = curves[curves["method"].isin(selected_methods)].copy()
    fig = px.line(
        plot,
        x="n_labeled",
        y=y_col,
        error_y=sd_col,
        color="method",
        markers=True,
        color_discrete_map=METHOD_COLORS,
        labels={"n_labeled": "Số mẫu đã gán nhãn", y_col: metric},
        title=f"Đường học trung bình trên {al['fold_seed_pairs']} cặp fold–seed",
    )
    fig.update_layout(height=470, legend_title=None)
    st.plotly_chart(fig, width="stretch")

    table = summary[
        [
            "method",
            "auc_aulc_mean",
            "ap_aulc_mean",
            "mean_labels_reached",
            "query_share_percent",
        ]
    ].copy()
    table.columns = [
        "Chiến lược",
        "ROC-AULC",
        "AP-AULC",
        "Nhãn tới mục tiêu",
        "Query overhead (%)",
    ]
    table["ROC-AULC"] = table["ROC-AULC"].round(4)
    table["AP-AULC"] = table["AP-AULC"].round(4)
    table["Nhãn tới mục tiêu"] = table["Nhãn tới mục tiêu"].astype(int)
    table["Query overhead (%)"] = table["Query overhead (%)"].round(2)
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption(
        f"U+V cần ít nhãn nhất ({int(uv.mean_labels_reached)}); U+H có AULC "
        "cao nhất. XAI-full không mặc nhiên đứng đầu mọi tiêu chí."
    )
    presenter_note(
        "Đọc đường học từ trái sang phải: với cùng ngân sách nhãn, các tín hiệu "
        "giải thích thay đổi thứ tự mẫu được hỏi. XAI-full đạt mục tiêu với 492 "
        "nhãn thay vì 584 của Random. U+H tốt nhất về AULC, còn U+V ít nhãn "
        "nhất; đây là đánh đổi chứ không phải một phương pháp thắng mọi chỉ số."
    )
    scope_note(al["notice"])


def fidelity_page(bundle: dict):
    fidelity = bundle["fidelity"]
    st.title("Đóng góp 3 — Kiểm chứng độ trung thực của TreeSHAP")
    deletion = pd.DataFrame(fidelity["deletion"])
    stability = pd.DataFrame(fidelity["stability"])
    baseline = st.radio("Giá trị thay thế khi masking", ["mean", "median"], horizontal=True)
    selected = deletion[deletion["mask_baseline"] == baseline].copy()
    k50 = selected[selected["k"] == 50].iloc[0]
    within = stability[
        (stability["scope"] == "within_fold")
        & (stability["metric"] == "spearman_global_importance")
    ].iloc[0]
    across = stability[
        (stability["scope"] == "across_fold")
        & (stability["metric"] == "spearman_global_importance")
    ].iloc[0]

    a, b, c, d = st.columns(4)
    metric_card(a, "Top-50 — AUC drop", f"{k50.top_shap_auc_drop_mean:.4f}".replace(".", ","))
    metric_card(b, "Random-50 — AUC drop", f"{k50.random_auc_drop_mean:.4f}".replace(".", ","))
    metric_card(c, "Spearman trong fold", f"{within['mean']:.3f}".replace(".", ","))
    metric_card(d, "Spearman giữa fold", f"{across['mean']:.3f}".replace(".", ","))

    long = selected.melt(
        id_vars=["k"],
        value_vars=["top_shap_auc_drop_mean", "random_auc_drop_mean"],
        var_name="Phép che",
        value_name="AUC drop",
    )
    long["Phép che"] = long["Phép che"].map(
        {
            "top_shap_auc_drop_mean": "Top-|SHAP|",
            "random_auc_drop_mean": "Ngẫu nhiên",
        }
    )
    fig = px.bar(
        long,
        x="k",
        y="AUC drop",
        color="Phép che",
        barmode="group",
        text="AUC drop",
        color_discrete_map={"Top-|SHAP|": COLORS["green"], "Ngẫu nhiên": COLORS["orange"]},
        title=f"Deletion có đối chứng — baseline {baseline}",
    )
    fig.update_traces(texttemplate="%{text:.4f}", textposition="outside")
    fig.update_layout(height=470, xaxis_title="Số đặc trưng bị che (k)")
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### Độ ổn định thứ hạng")
    spearman = stability[stability["metric"] == "spearman_global_importance"].copy()
    spearman["Phạm vi"] = spearman["scope"].map(
        {"within_fold": "Trong cùng fold", "across_fold": "Giữa các fold"}
    )
    stable_fig = px.bar(
        spearman,
        x="Phạm vi",
        y="mean",
        error_y="sd",
        color="Phạm vi",
        color_discrete_sequence=[COLORS["green"], COLORS["blue"]],
        labels={"mean": "Spearman trung bình"},
    )
    stable_fig.update_layout(height=320, showlegend=False, yaxis_range=[0, 1])
    st.plotly_chart(stable_fig, width="stretch")
    presenter_note(
        "Nếu thứ hạng SHAP chỉ là ngẫu nhiên, che top-k và che ngẫu nhiên cùng "
        "k phải gây tác động gần nhau. Thực tế tại k=50, AUC giảm 0,3067 khi "
        "che top-SHAP nhưng chỉ giảm 0,0010 khi che random. Stability ở mức "
        "trung bình và thấp hơn khi đổi fold."
    )
    scope_note(fidelity["notice"])


def script_page():
    st.title("Kịch bản demo 4–5 phút")
    st.markdown(
        """
### 0:00–0:20 — Mở đầu
> Em không chạy lại mô hình và không đưa mã độc vào máy trình chiếu. Demo này phát
> lại các artifact đã đo, có hash và cùng nguồn với số liệu trong luận văn.

### 0:20–1:50 — Đóng góp 1
1. Mở biểu đồ FPR và chốt **Adaptive P: 11,16%**, Fixed: **12,45%**.
2. Chọn tình huống “Giảm một báo động nhầm…”. Chỉ đường điểm và trọng số.
3. Nói: “Trọng số thay đổi theo lịch sử bất đồng, nhưng ablation cho thấy P tạo
   phần lợi ích chính; I/D chưa tăng thêm ổn định.”

### 1:50–3:00 — Đóng góp 2
1. Giữ các đường Random, Uncertainty, U+H và XAI-full.
2. Chỉ trục ngân sách nhãn; chốt **492 so với 584**, tiết kiệm **92 nhãn**.
3. Nói rõ U+H tốt nhất AULC, U+V ít nhãn nhất và overhead XAI-full **5,42%**.

### 3:00–4:00 — Đóng góp 3
1. Chọn baseline `mean`, chỉ cặp cột tại `k=50`.
2. Chốt **0,3067 so với 0,0010**.
3. Chỉ stability: **0,614 trong fold; 0,551 giữa fold**.

### 4:00–4:30 — Chốt
> Ba màn hình tương ứng ba giá trị: dung hợp giảm cảnh báo nhầm tại operating
> point, học tích cực giảm ngân sách nhãn, và Fidelity cung cấp đối chứng định
> lượng cho lời giải thích. Đây là bằng chứng theo từng thành phần trên hai
> benchmark, chưa phải đánh giá end-to-end ransomware production.
"""
    )
    st.warning(
        "Nếu hội đồng hỏi phản ví dụ PID, quay lại Đóng góp 1 và chọn tình huống "
        "“Phản ví dụ…”. Việc chủ động chỉ ra mẫu thất bại làm rõ rằng kết quả là "
        "cải thiện thống kê ở cấp cohort, không phải thắng mọi mẫu."
    )


def provenance_page(bundle: dict):
    st.title("Nguồn dữ liệu và khả năng truy nguyên")
    st.success(bundle["safety"])
    sources = pd.DataFrame(bundle["sources"])
    sources["sha256"] = sources["sha256"].str.slice(0, 16) + "…"
    sources["size_bytes"] = sources["size_bytes"].map(lambda x: f"{x/1024:.1f} KiB")
    sources.columns = ["Tệp nguồn", "SHA-256", "Kích thước"]
    st.dataframe(sources, hide_index=True, width="stretch")
    st.caption(f"Bundle được tạo lúc {bundle['generated_at_utc']} · schema v{bundle['schema_version']}")
    st.markdown(
        "Dashboard chỉ chứa các bản ghi đã chọn và các bảng tổng hợp. Có thể chạy "
        "`python scripts/run_defense_demo.py --check` trước buổi bảo vệ để đối "
        "chiếu lại hash của toàn bộ nguồn."
    )


bundle = get_bundle()
with st.sidebar:
    st.markdown("## 🛡️ Demo luận văn")
    page = st.radio(
        "Điều hướng",
        [
            "Tổng quan",
            "1 · Dung hợp thích nghi",
            "2 · XAI-Guided AL",
            "3 · Fidelity",
            "Kịch bản trình bày",
            "Nguồn và hash",
        ],
    )
    st.divider()
    st.caption("OFFLINE · MEASURED ARTIFACT REPLAY")
    st.caption("Không tải hoặc thực thi PE")

if page == "Tổng quan":
    overview(bundle)
elif page == "1 · Dung hợp thích nghi":
    pid_page(bundle)
elif page == "2 · XAI-Guided AL":
    al_page(bundle)
elif page == "3 · Fidelity":
    fidelity_page(bundle)
elif page == "Kịch bản trình bày":
    script_page()
else:
    provenance_page(bundle)
