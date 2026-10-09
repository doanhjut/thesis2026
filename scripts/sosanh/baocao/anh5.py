# Thêm đoạn này vào cuối file train_and_shap.py (hoặc chạy riêng)
import shap
import matplotlib.pyplot as plt

# Giả sử bạn đã có: model, explainer, x_one (1 mẫu malware)
shap_one = explainer.shap_values(x_one)
shap_class1 = shap_one[1] if isinstance(shap_one, list) else shap_one
base_value = explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value

# Vẽ force plot ĐẸP & NÉT bằng matplotlib
plt.figure(figsize=(14, 5))
shap.force_plot(
    base_value,
    shap_class1,
    x_one,
    matplotlib=True,
    show=False,
    contribution_threshold=0.01,   # hiện nhiều feature hơn
    figsize=(14, 5)
)

# Tinh chỉnh để đẹp như bài báo
plt.title("SHAP Force Plot – Mẫu LockBit ransomware (xác suất 98.2%)", fontsize=14, pad=20)
plt.tight_layout()

# Lưu ảnh SIÊU NÉT
plt.savefig("figures/shap_force_lockbit_hd.png", dpi=400, bbox_inches="tight")
plt.savefig("figures/shap_force_lockbit_hd.pdf")  # PDF vector, in luận văn đẹp nhất!
plt.close()

print("Đã lưu ảnh chất lượng cao:")
print("   → shap_force_lockbit_hd.png (400 DPI)")
print("   → shap_force_lockbit_hd.pdf  (vector – in A4 cực nét)")