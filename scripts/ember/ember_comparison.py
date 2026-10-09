import numpy as np
import pandas as pd
import lightgbm as lgb
from pathlib import Path
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, confusion_matrix
import ember

# ============================ 
# CONFIG 
# ============================ 
SOREL_MODEL_PATH = Path("ransomware_lgbm_1M_final.txt")
EMBER_DATA_DIR = Path(r"D:\Code\Luanvan\ember_test\ember2018")  # Path to EMBER 2018 dataset
OUTPUT_REPORT = Path("cross_dataset_evaluation.txt")

print("="*80)
print("🔬 CROSS-DATASET EVALUATION")
print("="*80)
print(f"Model: SOREL-20M trained LightGBM")
print(f"Test: EMBER 2018 dataset")
print(f"Goal: Measure generalization capability\n")

# ============================ 
# BƯỚC 1: LOAD MODEL VÀ DATA
# ============================ 
print(f"\n📦 Loading SOREL model...")
model = lgb.Booster(model_file=str(SOREL_MODEL_PATH))
print(f"✅ Model loaded: {model.num_trees()} trees")

print(f"\n📦 Loading EMBER 2018 test set...")
X_test, y_test = ember.read_vectorized_features(str(EMBER_DATA_DIR), subset="test")
print(f"✅ Data loaded: {X_test.shape[0]} samples, {X_test.shape[1]} features")
print(f"   Malware samples: {y_test.sum()} / {len(y_test)}")

# ============================ 
# BƯỚC 2: KIỂM TRA COMPATIBILITY
# ============================ 
print(f"\n🔍 Checking feature compatibility...")

# SOREL và EMBER đều dùng EMBER-v2 features (2381 features)
expected_features = 2381

if X_test.shape[1] != expected_features:
    print(f"⚠️  Warning: EMBER has {X_test.shape[1]} features")
    print(f"   SOREL model expects {expected_features} features")
    print(f"   This may cause prediction errors!")
else:
    print(f"✅ Feature count matches: {expected_features}")

# Handle missing values (EMBER có thể có NaN)
if np.isnan(X_test).any():
    print(f"⚠️  Found {np.isnan(X_test).sum()} NaN values")
    print(f"   Filling with 0...")
    X_test = np.nan_to_num(X_test, nan=0.0)

# ============================ 
# BƯỚC 3: PREDICTION
# ============================ 
print(f"\n🔮 Predicting on EMBER 2018 test set...")

y_pred_proba = model.predict(X_test)
y_pred = (y_pred_proba >= 0.9).astype(int) 

print(f"✅ Prediction complete")

# ============================ 
# BƯỚC 4: EVALUATION
# ============================ 
print(f"\n" + "="*80)
print(f"📊 CROSS-DATASET EVALUATION RESULTS")
print(f"="*80)

# Basic metrics
accuracy = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_pred_proba)

print(f"\n1️⃣ Overall Performance:")
print(f"   Accuracy: {accuracy:.6f} ({accuracy*100:.2f}%)")
print(f"   F1-Score: {f1:.6f}")
print(f"   AUC:      {auc:.6f}")

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()

print(f"\n2️⃣ Confusion Matrix:")
print(f"   True Negatives:  {tn:,}")
print(f"   False Positives: {fp:,}")
print(f"   False Negatives: {fn:,}")
print(f"   True Positives:  {tp:,}")

# Detection metrics
tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
precision = tp / (tp + fp) if (tp + fp) > 0 else 0

print(f"\n3️⃣ Detection Metrics:")
print(f"   True Positive Rate (Recall):  {tpr:.6f} ({tpr*100:.2f}%)")
print(f"   False Positive Rate:          {fpr:.6f} ({fpr*100:.2f}%)")
print(f"   Precision:                    {precision:.6f} ({precision*100:.2f}%)")

# ============================ 
# BƯỚC 5: GENERALIZATION ANALYSIS
# ============================ 
print(f"\n" + "="*80)
print(f"📊 GENERALIZATION ANALYSIS")
print(f"="*80)

# From training log (adjust this value based on your training results)
sorel_val_auc = 0.998867  # Từ kết quả training

print(f"\nPerformance comparison:")
print(f"   SOREL validation set: {sorel_val_auc:.6f} (same distribution)")
print(f"   EMBER test set:       {auc:.6f} (different distribution)")
print(f"   Performance drop:     {(sorel_val_auc - auc)*100:.2f}%")

generalization_score = (auc / sorel_val_auc) * 100

print(f"\n🎯 Generalization Score: {generalization_score:.2f}%")

if generalization_score >= 98:
    print(f"   ✅ EXCELLENT generalization!")
elif generalization_score >= 95:
    print(f"   ✅ GOOD generalization")
elif generalization_score >= 90:
    print(f"   ⚠️  ACCEPTABLE generalization")
else:
    print(f"   ⚠️  POOR generalization - may be overfitting")

# ============================ 
# BƯỚC 6: DETAILED ANALYSIS
# ============================ 
print(f"\n" + "="*80)
print(f"🔬 DETAILED ANALYSIS")
print(f"="*80)

# False Positive Analysis
print(f"\nFalse Positive Analysis:")
print(f"   FP Count: {fp:,}")
print(f"   FP Rate: {fpr*100:.3f}%")
if fpr < 0.01:
    print(f"   ✅ Excellent FP rate (<1%)")
elif fpr < 0.05:
    print(f"   ✅ Good FP rate (<5%)")
else:
    print(f"   ⚠️  High FP rate (>{fpr*100:.1f}%)")

# False Negative Analysis
print(f"\nFalse Negative Analysis:")
print(f"   FN Count: {fn:,}")
print(f"   FN Rate: {(fn/(tp+fn))*100:.3f}%")
print(f"   Missed malware: {fn:,} samples")

if fn / (tp + fn) < 0.05:
    print(f"   ✅ Low miss rate (<5%)")
elif fn / (tp + fn) < 0.10:
    print(f"   ⚠️  Moderate miss rate")
else:
    print(f"   ⚠️  High miss rate - dangerous!")

# ============================ 
# BƯỚC 7: SAVE REPORT
# ============================ 
print(f"\n💾 Saving detailed report...")

report_content = f"""
CROSS-DATASET EVALUATION REPORT
================================
Date: {pd.Timestamp.now()}

MODEL INFORMATION:
- Training dataset: SOREL-20M (subset 1M samples)
- Model type: LightGBM
- Features: 2381 (EMBER-v2 format)

TEST DATASET:
- Dataset: EMBER 2018 Test Set
- Samples: {X_test.shape[0]:,}
- Malware: {(y_test == 1).sum():,}
- Benign: {(y_test == 0).sum():,}

PERFORMANCE METRICS:
- Accuracy: {accuracy:.6f}
- F1-Score: {f1:.6f}
- AUC: {auc:.6f}
- Precision: {precision:.6f}
- Recall (TPR): {tpr:.6f}
- False Positive Rate: {fpr:.6f}

CONFUSION MATRIX:
                Predicted
              Benign  Malware
Actual Benign   {tn:,}    {fp:,}
       Malware  {fn:,}    {tp:,}

GENERALIZATION ANALYSIS:
- SOREL validation AUC: {sorel_val_auc:.6f}
- EMBER test AUC: {auc:.6f}
- Performance drop: {(sorel_val_auc - auc)*100:.2f}%
- Generalization score: {generalization_score:.2f}%

CONCLUSION:
{"EXCELLENT - Model generalizes well across datasets!" if generalization_score >= 98
else "GOOD - Reasonable cross-dataset performance" if generalization_score >= 95
else "ACCEPTABLE - Some generalization gap" if generalization_score >= 90
else "POOR - Significant overfitting to SOREL dataset"}

RECOMMENDATIONS:
1. {"Continue with this model" if generalization_score >= 95 else "Consider retraining with more diverse data"}
2. {"FP rate is good" if fpr < 0.05 else "Investigate false positives"}
3. {"FN rate is acceptable" if fn/(tp+fn) < 0.05 else "Critical: Too many missed malware samples"}
"""

OUTPUT_REPORT.write_text(report_content, encoding='utf-8')
print(f"✅ Report saved: {OUTPUT_REPORT}")

# ============================ 
# BƯỚC 8: SUMMARY
# ============================ 
print(f"\n" + "="*80)
print(f"✅ EVALUATION COMPLETE")
print(f"="*80)
print(f"\n📊 Quick Summary:")
print(f"   SOREL → SOREL: {sorel_val_auc:.4f} AUC")
print(f"   SOREL → EMBER: {auc:.4f} AUC")
print(f"   Generalization: {generalization_score:.1f}%")
print(f"\n💡 Next Steps:")
print(f"   1. Review detailed report: {OUTPUT_REPORT}")
print(f"   2. Analyze false positives/negatives")
print(f"   3. Consider ensemble with EMBER-trained model")
print(f"="*80)

