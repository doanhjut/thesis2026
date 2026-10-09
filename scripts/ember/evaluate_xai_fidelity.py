import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
from sklearn.metrics import roc_auc_score
from scipy.spatial.distance import cdist
from sklearn.metrics.pairwise import cosine_similarity
import warnings
import time

warnings.filterwarnings('ignore')

def calculate_fidelity_metrics(model_path, data_path, k_features=100, sample_size=5000):
    print("="*60)
    print("🔍 BẮT ĐẦU ĐÁNH GIÁ ĐỘ TRUNG THỰC XAI (FIDELITY FRAMEWORK)")
    print("="*60)
    
    # 1. Tải dữ liệu và mô hình (Giả lập load dữ liệu nhỏ để test nhanh)
    print(f"[*] Đang tải mô hình từ: {model_path}...")
    # LƯU Ý: Thay đổi hàm load model tùy thuộc vào định dạng bạn lưu (.pkl hay .txt)
    model = lgb.Booster(model_file=model_path) 
    
    print(f"[*] Đang tải {sample_size} mẫu từ: {data_path}...")
    # Giả định file CSV có cột cuối là 'label' (0: Benign, 1: Malware)
    df = pd.read_csv(data_path).sample(n=sample_size, random_state=42)
    X = df.drop(columns=['label'])
    y = df['label'].values
    
    # 2. Đánh giá Baseline AUC
    preds_orig = model.predict(X)
    auc_orig = roc_auc_score(y, preds_orig)
    print(f"[+] Baseline AUC ban đầu: {auc_orig:.4f}")
    
    # 3. Chạy SHAP Explainer
    print("[*] Đang khởi tạo TreeSHAP và tính toán giá trị đóng góp...")
    start_time = time.time()
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    # Lấy giá trị SHAP của class 1 (Malware) nếu là bài toán nhị phân
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    print(f"    -> Hoàn thành tính SHAP trong {time.time() - start_time:.2f}s")
    
    # 4. TÍNH CHỈ SỐ FAITHFULNESS (FF) VỚI CƠ CHẾ PE-AWARE MASKING
    print("\n[+] 4.1 Đang tính toán Chỉ số Trung thực (Faithfulness - FF)...")
    # Tìm Top K đặc trưng quan trọng nhất trên toàn tập dữ liệu
    global_shap_importance = np.abs(shap_values).mean(axis=0)
    top_k_indices = np.argsort(global_shap_importance)[-k_features:]
    
    # PE-Aware Masking: Tìm giá trị trung vị (median) của các file Benign (nhãn 0)
    X_benign = X[y == 0]
    benign_medians = X_benign.median(axis=0).values
    
    # Tạo tập dữ liệu Masked
    X_masked = X.copy()
    for idx in top_k_indices:
        X_masked.iloc[:, idx] = benign_medians[idx] # Gán bằng trung vị Benign thay vì số 0
        
    preds_masked = model.predict(X_masked)
    auc_masked = roc_auc_score(y, preds_masked)
    
    # Công thức FF
    ff_score = (auc_orig - auc_masked) / (auc_orig - 0.5)
    print(f"    -> AUC sau khi che Top {k_features} đặc trưng: {auc_masked:.4f}")
    print(f"    -> AUC Drop: {auc_orig - auc_masked:.4f}")
    print(f"    => Faithfulness Score (FF): {ff_score:.4f}")
    
    # 5. TÍNH CHỈ SỐ CONSISTENCY (EC)
    print("\n[+] 4.2 Đang tính toán Chỉ số Nhất quán (Consistency - EC)...")
    # Thêm nhiễu Gaussian nhỏ vào dữ liệu
    feature_std = X.std(axis=0).values + 1e-9
    noise = np.random.normal(0, 0.05, X.shape) * feature_std 
    X_noisy = X + noise
    shap_values_noisy = explainer.shap_values(X_noisy)
    if isinstance(shap_values_noisy, list):
        shap_values_noisy = shap_values_noisy[1]
        
    # Tính Cosine Similarity giữa giải thích gốc và giải thích có nhiễu
    similarities = [cosine_similarity([shap_values[i]], [shap_values_noisy[i]])[0][0] for i in range(len(X))]
    ec_score = np.mean(similarities)
    print(f"    => Consistency Score (EC): {ec_score:.4f}")

    # 6. TÍNH CHỈ SỐ CONTRASTIVE (CF) BẰNG KNN
    print("\n[+] 4.3 Đang tính toán Chỉ số Tương phản (Contrastive - CF)...")
    # Lấy mẫu Malware và Benign để so sánh chéo (giảm số lượng tính toán cho nhanh)
    malware_indices = np.where(y == 1)[0][:100]
    benign_indices = np.where(y == 0)[0][:100]
    
    cf_scores = []
    for m_idx in malware_indices:
        x_malware = X.iloc[m_idx].values.reshape(1, -1)
        # Tính khoảng cách Euclidean đến tất cả các mẫu Benign
        distances = cdist(x_malware, X.iloc[benign_indices].values, metric='euclidean')
        nearest_b_idx = benign_indices[np.argmin(distances)]
        x_nearest_benign = X.iloc[nearest_b_idx].values
        
        # F_diff: Top k đặc trưng có sự sai khác vật lý lớn nhất
        diff = np.abs(x_malware[0] - x_nearest_benign)
        f_diff_indices = np.argsort(diff)[-k_features:]
        
        # F_top_k: Top k đặc trưng do SHAP chỉ ra cho file Malware này
        f_top_k_indices = np.argsort(np.abs(shap_values[m_idx]))[-k_features:]
        
        # Phép giao (Intersection)
        intersection = np.intersect1d(f_diff_indices, f_top_k_indices)
        cf_scores.append(len(intersection) / k_features)
        
    cf_score = np.mean(cf_scores)
    print(f"    => Contrastive Score (CF): {cf_score:.4f}")
    
    # 7. TỔNG HỢP VÀ LƯU KẾT QUẢ (OFS)
    print("\n" + "="*60)
    ofs_score = 0.5 * ff_score + 0.3 * ec_score + 0.2 * cf_score
    print(f"🏆 ĐIỂM TRUNG THỰC TỔNG HỢP (OFS): {ofs_score:.4f}")
    print("="*60)
    
    # Lưu ra DataFrame và CSV
    results_df = pd.DataFrame([{
        "Metric": "Baseline AUC", "Value": auc_orig
    }, {
        "Metric": "Masked AUC", "Value": auc_masked
    }, {
        "Metric": f"Faithfulness (FF_{k_features})", "Value": ff_score
    }, {
        "Metric": "Consistency (EC)", "Value": ec_score
    }, {
        "Metric": "Contrastive (CF)", "Value": cf_score
    }, {
        "Metric": "Overall Fidelity Score (OFS)", "Value": ofs_score
    }])
    
    output_file = "fidelity_results.csv"
    results_df.to_csv(output_file, index=False)
    print(f"[v] Đã xuất báo cáo chi tiết ra tệp: {output_file}")

if __name__ == "__main__":
    from pathlib import Path
    _ROOT = Path(__file__).resolve().parents[2]
    MODEL_PATH = str(_ROOT / "models" / "ransomware_lgbm_1M_final.txt")
    DATA_PATH = str(_ROOT / "data" / "processed" / "train_10percent.csv")
    
    try:
        calculate_fidelity_metrics(MODEL_PATH, DATA_PATH, k_features=500)
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy file model hoặc file dữ liệu. Vui lòng kiểm tra lại đường dẫn.")