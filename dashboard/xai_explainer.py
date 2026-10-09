"""
XAI Explainer Module
Giải thích predictions của ransomware detection model
Sử dụng SHAP
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from feature_extraction import PEFeatureExtractor
except ImportError:
    try:
        from pe_feature_extractor import PEFeatureExtractor
    except ImportError:
        print("Warning: feature_extraction not found")
        PEFeatureExtractor = None

class RansomwareExplainer:
    """
    Explainable AI cho ransomware detection
    Giải thích tại sao model cho rằng file là malware/benign
    """
    
    def __init__(self, model_path, feature_names_path=None):
        """
        Args:
            model_path: Path to LightGBM model
            feature_names_path: Optional JSON file với feature names
        """
        print("🔧 Initializing XAI Explainer...")
        
        # Load model
        self.model = lgb.Booster(model_file=str(model_path))
        print(f"   ✅ Model loaded: {model_path}")
        
        # Load feature names
        if feature_names_path and Path(feature_names_path).exists():
            with open(feature_names_path) as f:
                self.feature_names = json.load(f)
        else:
            # Default feature names
            self.feature_names = [f"Feature_{i}" for i in range(2381)]
        
        # Initialize feature extractor if available
        if PEFeatureExtractor:
            self.extractor = PEFeatureExtractor()
        else:
            self.extractor = None
            print("   ⚠️ Feature extractor not available")
        
        # SHAP explainer (tree-based model)
        print("   🔧 Initializing SHAP explainer...")
        self.shap_explainer = shap.TreeExplainer(self.model)
        print("   ✅ SHAP ready")
        
        self.threshold = 0.5  # Classification threshold
    
    def predict_from_features(self, features):
        """
        Predict từ feature vector đã có
        
        Args:
            features: numpy array (2381,)
        Returns:
            probability float
        """
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        return self.model.predict(features)[0]
    
    def explain_features(self, features, top_n=10):
        """
        Giải thích prediction từ feature vector
        
        Args:
            features: numpy array (2381,)
            top_n: Số features quan trọng nhất
        Returns:
            dict với explanation
        """
        if len(features.shape) == 1:
            features_2d = features.reshape(1, -1)
        else:
            features_2d = features
            features = features[0]
        
        # Predict
        prob = self.model.predict(features_2d)[0]
        prediction = "MALWARE" if prob >= self.threshold else "BENIGN"
        
        # SHAP explanation
        shap_values = self.shap_explainer.shap_values(features_2d)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        shap_values = shap_values[0]
        
        # Get top contributing features
        top_indices = np.argsort(np.abs(shap_values))[-top_n:][::-1]
        
        explanations = []
        for rank, idx in enumerate(top_indices, 1):
            feature_name = self.feature_names[idx] if idx < len(self.feature_names) else f"Feature_{idx}"
            feature_value = features[idx]
            shap_value = shap_values[idx]
            
            explanations.append({
                'rank': rank,
                'feature_name': feature_name,
                'feature_value': float(feature_value),
                'shap_value': float(shap_value),
                'contribution_pct': float(abs(shap_value) / np.abs(shap_values).sum() * 100)
            })
        
        # Summary
        malware_contribution = float(sum(sv for sv in shap_values if sv > 0))
        benign_contribution = float(sum(sv for sv in shap_values if sv < 0))
        
        return {
            'success': True,
            'prediction': prediction,
            'probability': float(prob),
            'features': features.tolist(),
            'shap_values': shap_values.tolist(),
            'top_explanations': explanations,
            'malware_contribution': malware_contribution,
            'benign_contribution': benign_contribution,
            'base_value': float(self.shap_explainer.expected_value)
        }
    
    def explain_file(self, file_path, top_n=10):
        """
        Giải thích prediction cho một PE file
        
        Args:
            file_path: Path to PE file
            top_n: Số lượng features quan trọng nhất
        Returns:
            dict với explanation details
        """
        print("\n" + "="*80)
        print("🔍 EXPLAINING PREDICTION")
        print("="*80)
        
        if self.extractor is None:
            return {
                'success': False,
                'error': 'Feature extractor not available'
            }
        
        # Extract features
        features = self.extractor.extract_from_file(file_path)
        
        if features is None:
            return {
                'success': False,
                'error': 'Feature extraction failed'
            }
        
        result = self.explain_features(features, top_n)
        result['file'] = str(file_path)
        
        # Print results
        print(f"\n📊 Prediction Result:")
        print(f"   File: {Path(file_path).name}")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Confidence: {result['probability']:.2%}")
        
        print(f"\n🎯 Top {top_n} Contributing Features:")
        print(f"   {'Rank':<6} {'Feature':<40} {'Value':<12} {'Impact':<12} {'Direction'}")
        print("   " + "-"*76)
        
        for exp in result['top_explanations']:
            direction = "→ MALWARE" if exp['shap_value'] > 0 else "→ BENIGN"
            print(f"   {exp['rank']:<6} {exp['feature_name'][:38]:<40} {exp['feature_value']:<12.4f} {exp['shap_value']:<+12.4f} {direction}")
        
        return result
    
    def generate_report(self, file_path, output_path):
        """
        Tạo báo cáo HTML đầy đủ
        """
        explanation = self.explain_file(file_path)
        
        if not explanation['success']:
            return False
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>XAI Report: {Path(file_path).name}</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .prediction {{ font-size: 24px; font-weight: bold; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .malware {{ background: #ffebee; color: #c62828; }}
        .benign {{ background: #e8f5e9; color: #2e7d32; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f0f0f0; font-weight: bold; }}
        .positive {{ color: #c62828; }}
        .negative {{ color: #2e7d32; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Explainable AI Report</h1>
        <h2>File: {Path(file_path).name}</h2>
        
        <div class="prediction {'malware' if explanation['prediction'] == 'MALWARE' else 'benign'}">
            Prediction: {explanation['prediction']} ({explanation['probability']:.2%} confidence)
        </div>
        
        <h3>🎯 Top Contributing Features</h3>
        <table>
            <tr>
                <th>Rank</th>
                <th>Feature</th>
                <th>Value</th>
                <th>SHAP Impact</th>
                <th>Contribution %</th>
            </tr>
"""
        
        for exp in explanation['top_explanations']:
            impact_class = 'positive' if exp['shap_value'] > 0 else 'negative'
            html_content += f"""
            <tr>
                <td>{exp['rank']}</td>
                <td>{exp['feature_name']}</td>
                <td>{exp['feature_value']:.4f}</td>
                <td class="{impact_class}">{exp['shap_value']:+.4f}</td>
                <td>{exp['contribution_pct']:.1f}%</td>
            </tr>
"""
        
        html_content += f"""
        </table>
        
        <h3>📊 Summary</h3>
        <p><strong>Total Malware Contribution:</strong> <span class="positive">{explanation['malware_contribution']:+.4f}</span></p>
        <p><strong>Total Benign Contribution:</strong> <span class="negative">{explanation['benign_contribution']:+.4f}</span></p>
        
        <p><em>Report generated by XAI Explainer</em></p>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ HTML report saved: {output_path}")
        return True

# Test if run directly
if __name__ == "__main__":
    print("="*80)
    print("XAI Explainer Module")
    print("="*80)
    print("\nThis module should be imported, not run directly.")
    print("\nUsage:")
    print("  from xai_explainer import RansomwareExplainer")
    print("  explainer = RansomwareExplainer('model.txt')")
    print("  result = explainer.explain_file('file.exe')")