import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
from sklearn.metrics import roc_auc_score
from scipy.stats import entropy
import time
import warnings

warnings.filterwarnings('ignore')

def calculate_xai_uncertainty(model, X_pool):
    """
    Tính toán Độ đo bất định tổng hợp (Composite Uncertainty) dựa trên XAI
    """
    # 1. Dự đoán xác suất
    preds = model.predict(X_pool)
    
    # Tính Margin Uncertainty (Càng gần ranh giới 0.5 -> Càng bất định)
    margin = 1.0 - (np.abs(preds - 0.5) * 2)
    
    # ĐỂ TỐI ƯU TÀI NGUYÊN: Chỉ tính SHAP cho top 1000 mẫu có Margin cao nhất
    # Đây là kỹ thuật Tiền lọc (Pre-filtering) trong Active Learning thực tế
    top_margin_indices = np.argsort(margin)[-1000:]
    X_shap_pool = X_pool.iloc[top_margin_indices]
    
    print("    -> Đang tính toán SHAP Variance và Directional Entropy...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_shap_pool)
    if isinstance(shap_values, list):
        shap_values = shap_values[1] # Lấy SHAP của class Malware
        
    composite_scores = []
    
    for i in range(len(X_shap_pool)):
        phi = shap_values[i]
        
        # 2. Tính SHAP_CV (Hệ số biến thiên SHAP)
        phi_abs = np.abs(phi)
        shap_cv = np.std(phi_abs) / (np.mean(phi_abs) + 1e-9)
        # Nghịch đảo: SHAP_CV thấp nghĩa là giải thích phân tán (mô hình bối rối) -> Bất định cao
        inv_shap_cv = 1.0 / (shap_cv + 1e-9) 
        
        # 3. Tính Directional Entropy (Xung đột đặc trưng)
        pos_sum = np.sum(phi[phi > 0]) + 1e-9 # Lực kéo về Malware
        neg_sum = np.abs(np.sum(phi[phi < 0])) + 1e-9 # Lực kéo về Benign
        total_force = pos_sum + neg_sum
        
        # Phân phối xác suất của hai luồng lực
        p_pos = pos_sum / total_force
        p_neg = neg_sum / total_force
        dir_entropy = entropy([p_pos, p_neg], base=2) # Đạt Max = 1 khi hai lực giằng co bằng nhau
        
        # 4. Tính Composite Score (Công thức trong luận văn)
        # Trọng số: 0.5 cho Xung đột, 0.3 cho Phân tán, 0.2 cho Margin
        composite_score = 0.5 * dir_entropy + 0.3 * inv_shap_cv + 0.2 * margin[top_margin_indices[i]]
        composite_scores.append(composite_score)
        
    # Tạo mapping lại index ban đầu
    results = pd.Series(0, index=X_pool.index, dtype=float)
    results.iloc[top_margin_indices] = composite_scores
    
    return results

def simulate_active_learning(data_path, initial_size=2000, query_size=100, iterations=5):
    print("="*70)
    print("🔄 BẮT ĐẦU MÔ PHỎNG HỌC TÍCH CỰC HƯỚNG DẪN BỞI XAI (AL SIMULATION)")
    print("="*70)
    
    # 1. Tải và chia dữ liệu giả lập
    print(f"[*] Tải dữ liệu từ: {data_path}")
    df = pd.read_csv(data_path).sample(n=20000, random_state=42) # Lấy 20k mẫu để giả lập
    
    # Chia tập Test cố định để đánh giá độ cải thiện
    test_size = 5000
    df_test = df.iloc[:test_size]
    X_test, y_test = df_test.drop(columns=['label']), df_test['label'].values
    
    # Phần còn lại dùng làm Hồ chứa (Pool)
    df_pool = df.iloc[test_size:]
    
    # Khởi tạo tập Train ban đầu (Initial Training Set)
    train_indices = np.random.choice(df_pool.index, initial_size, replace=False)
    unlabeled_indices = list(set(df_pool.index) - set(train_indices))
    
    logs = []
    
    # 2. Bắt đầu vòng lặp Active Learning
    for i in range(iterations + 1):
        print(f"\n▶ VÒNG LẶP {i} (Tập huấn luyện: {len(train_indices)} mẫu)")
        
        # Tách tập Train hiện tại
        X_train = df_pool.loc[train_indices].drop(columns=['label'])
        y_train = df_pool.loc[train_indices]['label'].values
        
        # Huấn luyện mô hình LightGBM
        model = lgb.LGBMClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        
        # Đánh giá trên tập Test
        preds_test = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, preds_test)
        print(f"    [+] AUC trên tập Test: {auc:.4f}")
        
        logs.append({
            "Iteration": i,
            "Train_Size": len(train_indices),
            "AUC_Score": auc
        })
        
        # Dừng vòng lặp nếu là iteration cuối cùng
        if i == iterations:
            break
            
        # TÌM KIẾM MẪU MƠ HỒ TRONG TẬP CHƯA GÁN NHÃN (UNLABELED POOL)
        print(f"    [*] Đang quét {len(unlabeled_indices)} mẫu chưa gán nhãn...")
        X_unlabeled = df_pool.loc[unlabeled_indices].drop(columns=['label'])
        
        start_time = time.time()
        # Gọi hàm tính Độ bất định bằng XAI
        uncertainty_scores = calculate_xai_uncertainty(model, X_unlabeled)
        print(f"    -> Tính toán xong trong {time.time() - start_time:.2f} giây")
        
        # Chọn top `query_size` mẫu có độ bất định cao nhất
        top_k_indices = uncertainty_scores.nlargest(query_size).index.tolist()
        
        # Mô phỏng hành động "Hỏi chuyên gia / Đưa vào mồi nhử"
        print(f"    [+] Đã chọn {query_size} mẫu khó nhất (Grey-zone) thêm vào tập huấn luyện kế tiếp.")
        
        # Cập nhật danh sách index
        train_indices = np.concatenate([train_indices, top_k_indices])
        unlabeled_indices = list(set(unlabeled_indices) - set(top_k_indices))

    # 3. Lưu log thực nghiệm
    print("\n" + "="*70)
    log_df = pd.DataFrame(logs)
    output_file = "active_learning_logs.csv"
    log_df.to_csv(output_file, index=False)
    print(f"🏆 Đã hoàn tất mô phỏng! Lưu nhật ký tại: {output_file}")
    print("="*70)

if __name__ == "__main__":
    from pathlib import Path
    DATA_PATH = str(Path(__file__).resolve().parents[2] / "data" / "processed" / "train_10percent.csv") 
    
    try:
        # Giả lập: Bắt đầu với 2000 mẫu, mỗi vòng "nhặt" thêm 100 mẫu cực khó, chạy 5 vòng
        simulate_active_learning(DATA_PATH, initial_size=2000, query_size=100, iterations=5)
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy file dữ liệu. Vui lòng kiểm tra lại đường dẫn.")