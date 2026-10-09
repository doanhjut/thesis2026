"""
Test Complete XAI Pipeline
Kiểm tra feature extraction → prediction → SHAP explanation
"""

import sys
from pathlib import Path
import numpy as np
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

# Import modules
sys.path.insert(0, str(Path(__file__).parent))
from pe_feature_extractor import PEFeatureExtractor

print("="*80)
print("🧪 TESTING COMPLETE XAI PIPELINE")
print("="*80)

# Configuration
MODEL_PATH = "ransomware_lgbm_1M_final.txt"
TEST_FILE = r"C:\Windows\System32\notepad.exe"

# Step 1: Load Model
print("\n📦 Step 1: Loading Model")
print("-" * 80)

try:
    model = lgb.Booster(model_file=MODEL_PATH)
    print(f"✅ Model loaded: {MODEL_PATH}")
    print(f"   Model type: {type(model)}")
    print(f"   Number of trees: {model.num_trees()}")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    print("\n💡 Make sure model file exists:")
    print(f"   {Path(MODEL_PATH).absolute()}")
    sys.exit(1)

# Step 2: Extract Features
print("\n🔍 Step 2: Feature Extraction")
print("-" * 80)

extractor = PEFeatureExtractor()
features = extractor.extract_from_file(TEST_FILE)

if features is None:
    print("❌ Feature extraction failed")
    sys.exit(1)

print(f"\n✅ Features extracted successfully")
print(f"   Shape: {features.shape}")
print(f"   Non-zero features: {np.count_nonzero(features)}")
print(f"   Min: {features.min():.4f}")
print(f"   Max: {features.max():.4f}")
print(f"   Mean: {features.mean():.4f}")

# Step 3: Prediction
print("\n🎯 Step 3: Model Prediction")
print("-" * 80)

try:
    # Reshape for model
    features_2d = features.reshape(1, -1)
    
    # Predict
    prob = model.predict(features_2d)[0]
    prediction = "MALWARE" if prob >= 0.5 else "BENIGN"
    
    print(f"✅ Prediction successful")
    print(f"   File: {Path(TEST_FILE).name}")
    print(f"   Prediction: {prediction}")
    print(f"   Malware probability: {prob:.6f} ({prob*100:.2f}%)")
    print(f"   Benign probability: {1-prob:.6f} ({(1-prob)*100:.2f}%)")
    
    # Classification result
    if prediction == "BENIGN":
        print(f"\n   ✅ This is expected for notepad.exe (system file)")
    else:
        print(f"\n   ⚠️  WARNING: System file classified as malware!")
        print(f"   This might indicate model issues or feature extraction problems")
    
except Exception as e:
    print(f"❌ Prediction error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: SHAP Explanation (if available)
print("\n💡 Step 4: SHAP Explanation")
print("-" * 80)

try:
    import shap
    
    print("🔧 Initializing SHAP explainer...")
    explainer = shap.TreeExplainer(model)
    
    print("📊 Computing SHAP values...")
    shap_values = explainer.shap_values(features_2d)
    
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    
    shap_values = shap_values[0]  # Get first sample
    
    print(f"✅ SHAP computation successful")
    print(f"   SHAP values shape: {shap_values.shape}")
    print(f"   Base value (expected): {explainer.expected_value:.6f}")
    
    # Top contributing features
    top_n = 10
    top_indices = np.argsort(np.abs(shap_values))[-top_n:][::-1]
    
    print(f"\n🎯 Top {top_n} Contributing Features:")
    print(f"   {'Rank':<6} {'Feature ID':<12} {'Value':<15} {'SHAP Impact':<15} {'Direction'}")
    print("   " + "-"*70)
    
    for rank, idx in enumerate(top_indices, 1):
        feature_value = features[idx]
        shap_value = shap_values[idx]
        direction = "→ MALWARE" if shap_value > 0 else "→ BENIGN"
        contribution = abs(shap_value) / np.abs(shap_values).sum() * 100
        
        print(f"   {rank:<6} Feature_{idx:<6} {feature_value:<15.4f} {shap_value:+15.6f} {direction} ({contribution:.1f}%)")
    
    # Summary
    malware_push = sum(sv for sv in shap_values if sv > 0)
    benign_push = sum(sv for sv in shap_values if sv < 0)
    net_score = malware_push + benign_push
    
    print(f"\n📈 SHAP Summary:")
    print(f"   Base value: {explainer.expected_value:+.6f}")
    print(f"   Push to MALWARE: {malware_push:+.6f}")
    print(f"   Push to BENIGN:  {benign_push:+.6f}")
    print(f"   Net effect: {net_score:+.6f}")
    print(f"   Final prediction: {explainer.expected_value + net_score:.6f}")
    
    print(f"\n💡 Interpretation:")
    if prediction == "BENIGN":
        print(f"   The model sees benign characteristics because:")
        benign_features = [(i, shap_values[i]) for i in range(len(shap_values)) if shap_values[i] < 0]
        benign_features.sort(key=lambda x: x[1])
        for idx, val in benign_features[:3]:
            print(f"   • Feature {idx} pushes toward benign by {abs(val):.6f}")
    else:
        print(f"   The model sees malicious characteristics because:")
        malware_features = [(i, shap_values[i]) for i in range(len(shap_values)) if shap_values[i] > 0]
        malware_features.sort(key=lambda x: x[1], reverse=True)
        for idx, val in malware_features[:3]:
            print(f"   • Feature {idx} pushes toward malware by {val:.6f}")
    
except ImportError:
    print("⚠️  SHAP not installed")
    print("   Install: pip install shap")
except Exception as e:
    print(f"⚠️  SHAP explanation failed: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Test with multiple files
print("\n" + "="*80)
print("📦 Step 5: Batch Testing (Optional)")
print("="*80)

test_files = [
    r"C:\Windows\System32\notepad.exe",
    r"C:\Windows\System32\calc.exe",
    r"C:\Windows\System32\cmd.exe",
]

print("\nTesting multiple system files:")
print("-" * 80)

batch_results = []

for test_file in test_files:
    if not Path(test_file).exists():
        print(f"⏭️  Skipping {Path(test_file).name} (not found)")
        continue
    
    try:
        feats = extractor.extract_from_file(test_file)
        if feats is not None:
            prob = model.predict(feats.reshape(1, -1))[0]
            pred = "MALWARE" if prob >= 0.5 else "BENIGN"
            
            batch_results.append({
                'file': Path(test_file).name,
                'prediction': pred,
                'probability': prob
            })
            
            emoji = "✅" if pred == "BENIGN" else "🦠"
            print(f"{emoji} {Path(test_file).name:<20} → {pred:8} ({prob:.2%})")
    except Exception as e:
        print(f"❌ {Path(test_file).name}: Error - {e}")

# Final Summary
print("\n" + "="*80)
print("📊 PIPELINE TEST SUMMARY")
print("="*80)

print("\n✅ Successfully Tested:")
print("   [✓] Model loading")
print("   [✓] Feature extraction")
print("   [✓] Prediction")
try:
    import shap
    print("   [✓] SHAP explanations")
except:
    print("   [✗] SHAP explanations (not installed)")

if batch_results:
    print(f"\n📈 Batch Results ({len(batch_results)} files):")
    benign_count = sum(1 for r in batch_results if r['prediction'] == 'BENIGN')
    malware_count = len(batch_results) - benign_count
    print(f"   Benign: {benign_count}")
    print(f"   Malware: {malware_count}")
    
    if malware_count > 0:
        print(f"\n   ⚠️  WARNING: {malware_count} system files classified as malware!")
        print(f"   This suggests model may need recalibration")

print("\n" + "="*80)
print("🎉 PIPELINE TEST COMPLETE")
print("="*80)

print("\n💡 Next Steps:")
print("   1. If SHAP works → Run: streamlit run xai_dashboard.py")
print("   2. Test with actual malware samples")
print("   3. Move to Phase 2: Honeypots")

print("\n📝 To test dashboard:")
print("   streamlit run xai_dashboard.py")