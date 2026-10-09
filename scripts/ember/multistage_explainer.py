"""
Multi-Stage Explainability Framework
NOVEL CONTRIBUTION for Master's Thesis
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path

class MultiStageExplainer:
    """
    NOVEL: Unified explainability framework cho ransomware detection
    """
    
    def __init__(self, ml_explainer=None, behavioral_analyzer=None):
        self.ml_explainer = ml_explainer
        self.behavioral_analyzer = behavioral_analyzer
        self.confidence_threshold = 0.7
        
        print("🔬 Multi-Stage Explainer initialized")
    
    def explain_complete_detection(self, pe_file=None, runtime_events=None):
        """
        CORE NOVEL METHOD: Explain toàn bộ detection process
        """
        print("\n" + "="*80)
        print("🔬 MULTI-STAGE DETECTION EXPLANATION")
        print("="*80)
        
        explanations = {
            'timestamp': datetime.now().isoformat(),
            'stages': {},
            'final_decision': None,
            'confidence_breakdown': {},
            'reasoning': None
        }
        
        # Stage 1: File-level Analysis
        if pe_file and self.ml_explainer:
            print("\n📊 Stage 1: File-Level Analysis")
            file_explanation = self._explain_file_level(pe_file)
            explanations['stages']['file'] = file_explanation
            
            if file_explanation:
                print(f"   Score: {file_explanation['score']:.3f}")
                print(f"   Confidence: {file_explanation['confidence']:.3f}")
        else:
            explanations['stages']['file'] = None
        
        # Stage 2: Behavior-level Analysis
        if runtime_events and self.behavioral_analyzer:
            print("\n🏃 Stage 2: Behavioral Analysis")
            behavior_explanation = self._explain_behavior_level(runtime_events)
            explanations['stages']['behavior'] = behavior_explanation
            
            if behavior_explanation:
                print(f"   Score: {behavior_explanation['score']:.3f}")
                print(f"   Confidence: {behavior_explanation['confidence']:.3f}")
        else:
            explanations['stages']['behavior'] = None
        
        # Stage 3: Decision Fusion
        print("\n🎯 Stage 3: Decision Fusion")
        fusion_explanation = self._explain_decision_fusion(
            explanations['stages']['file'],
            explanations['stages']['behavior']
        )
        
        explanations['final_decision'] = fusion_explanation['decision']
        explanations['confidence_breakdown'] = fusion_explanation['breakdown']
        explanations['fusion_method'] = fusion_explanation['method']
        
        # Stage 4: Natural Language Reasoning
        print("\n💬 Stage 4: Generating Explanation")
        reasoning = self._generate_reasoning(explanations)
        explanations['reasoning'] = reasoning
        
        print(f"\n{'='*80}")
        print(f"FINAL DECISION: {explanations['final_decision']}")
        print(f"{'='*80}")
        print(f"\n{reasoning}")
        
        return explanations
    
    def _explain_file_level(self, pe_file):
        """Explain static ML detection"""
        result = self.ml_explainer.explain_file(pe_file, top_n=10)
        
        if not result['success']:
            return None
        
        shap_values = np.array(result['shap_values'])
        
        # NOVEL: Confidence metric based on SHAP consistency
        top_shap = np.abs(shap_values).argsort()[-10:]
        top_values = shap_values[top_shap]
        
        positive_count = (top_values > 0).sum()
        negative_count = (top_values < 0).sum()
        
        agreement = max(positive_count, negative_count) / len(top_values)
        magnitude = np.abs(top_values).mean()
        
        confidence = agreement * min(magnitude / 0.5, 1.0)
        
        return {
            'score': result['probability'],
            'confidence': float(confidence),
            'top_features': result['top_explanations'][:5],
            'shap_values': result['shap_values'],
            'method': 'LightGBM + SHAP'
        }
    
    def _explain_behavior_level(self, runtime_events):
        """Explain behavioral detection"""
        analysis = self.behavioral_analyzer.analyze_events(runtime_events)
        
        if not analysis['threat_detected']:
            return {
                'score': 0.1,
                'confidence': 0.9,
                'patterns': [],
                'method': 'Behavioral Pattern Matching'
            }
        
        severity_scores = {
            'CRITICAL': 1.0,
            'HIGH': 0.8,
            'MEDIUM': 0.5,
            'LOW': 0.2
        }
        
        pattern_scores = [
            severity_scores.get(p['severity'], 0.5)
            for p in analysis['patterns'].values()
            if p.get('detected', False)
        ]
        
        if len(pattern_scores) == 0:
            score = 0.1
            confidence = 0.5
        else:
            score = np.mean(pattern_scores)
            confidence = min(len(pattern_scores) / 3.0, 1.0)
        
        top_patterns = []
        for name, pattern in analysis['patterns'].items():
            if pattern.get('detected', False):
                top_patterns.append({
                    'name': name,
                    'severity': pattern['severity'],
                    'details': pattern
                })
        
        return {
            'score': float(score),
            'confidence': float(confidence),
            'patterns': top_patterns,
            'method': 'Behavioral Pattern Matching'
        }
    
    def _explain_decision_fusion(self, file_exp, behavior_exp):
        """
        NOVEL: Explain how final decision was made from both stages
        """
        if file_exp is None and behavior_exp is None:
            return {
                'decision': 'UNKNOWN',
                'breakdown': {},
                'method': 'No data available'
            }
        
        if file_exp is None:
            return {
                'decision': 'MALWARE' if behavior_exp['score'] > 0.5 else 'BENIGN',
                'breakdown': {
                    'behavior_only': {
                        'score': behavior_exp['score'],
                        'weight': 1.0,
                        'contribution': behavior_exp['score']
                    }
                },
                'method': 'Behavioral-only (no file analysis)'
            }
        
        if behavior_exp is None:
            return {
                'decision': 'MALWARE' if file_exp['score'] > 0.5 else 'BENIGN',
                'breakdown': {
                    'file_only': {
                        'score': file_exp['score'],
                        'weight': 1.0,
                        'contribution': file_exp['score']
                    }
                },
                'method': 'Static-only (no runtime data)'
            }
        
        # NOVEL: Adaptive weighting based on confidence
        total_confidence = file_exp['confidence'] + behavior_exp['confidence']
        
        if total_confidence > 0:
            file_weight = file_exp['confidence'] / total_confidence
            behavior_weight = behavior_exp['confidence'] / total_confidence
        else:
            file_weight = 0.5
            behavior_weight = 0.5
        
        file_contribution = file_weight * file_exp['score']
        behavior_contribution = behavior_weight * behavior_exp['score']
        
        final_score = file_contribution + behavior_contribution
        
        decision = 'MALWARE' if final_score > 0.5 else 'BENIGN'
        
        return {
            'decision': decision,
            'final_score': float(final_score),
            'breakdown': {
                'file_analysis': {
                    'score': file_exp['score'],
                    'confidence': file_exp['confidence'],
                    'weight': float(file_weight),
                    'contribution': float(file_contribution),
                    'top_reasons': [
                        f"{r['feature_name']}: {r['shap_value']:+.3f}"
                        for r in file_exp['top_features'][:3]
                    ]
                },
                'behavioral_analysis': {
                    'score': behavior_exp['score'],
                    'confidence': behavior_exp['confidence'],
                    'weight': float(behavior_weight),
                    'contribution': float(behavior_contribution),
                    'top_reasons': [
                        f"{p['name']} ({p['severity']})"
                        for p in behavior_exp['patterns'][:3]
                    ]
                }
            },
            'method': 'Adaptive Confidence-Weighted Fusion'
        }
    
    def _generate_reasoning(self, explanations):
        """NOVEL: Generate natural language explanation"""
        decision = explanations['final_decision']
        breakdown = explanations.get('confidence_breakdown', {})
        
        if decision == 'MALWARE':
            reasoning = f"🦠 This file was classified as MALWARE.\n\n"
        else:
            reasoning = f"✅ This file was classified as BENIGN.\n\n"
        
        if 'file_analysis' in breakdown and 'behavioral_analysis' in breakdown:
            file_contrib = breakdown['file_analysis']['contribution']
            behavior_contrib = breakdown['behavioral_analysis']['contribution']
            
            if behavior_contrib > file_contrib:
                primary = "behavioral evidence"
                primary_pct = behavior_contrib * 100
                secondary = "static analysis"
                secondary_pct = file_contrib * 100
            else:
                primary = "static analysis"
                primary_pct = file_contrib * 100
                secondary = "behavioral evidence"  
                secondary_pct = behavior_contrib * 100
            
            reasoning += f"Decision was primarily based on {primary} ({primary_pct:.1f}% contribution), "
            reasoning += f"with supporting {secondary} ({secondary_pct:.1f}% contribution).\n\n"
            
            if 'file_analysis' in breakdown:
                reasoning += "📊 Static Analysis indicates:\n"
                for reason in breakdown['file_analysis']['top_reasons']:
                    reasoning += f"  • {reason}\n"
                reasoning += "\n"
            
            if 'behavioral_analysis' in breakdown:
                reasoning += "🏃 Behavioral Analysis detected:\n"
                for reason in breakdown['behavioral_analysis']['top_reasons']:
                    reasoning += f"  • {reason}\n"
                reasoning += "\n"
        
        elif 'file_only' in breakdown:
            reasoning += "Decision based solely on static file analysis.\n"
            reasoning += "(No runtime behavioral data available)\n"
        
        elif 'behavior_only' in breakdown:
            reasoning += "Decision based solely on runtime behavior.\n"
            reasoning += "(No static file analysis available)\n"
        
        reasoning += "---\n"
        if decision == 'MALWARE':
            reasoning += "⚠️ RECOMMENDATION: Quarantine this file and investigate further."
        else:
            reasoning += "✅ RECOMMENDATION: File appears safe based on current analysis."
        
        return reasoning
    
    def generate_report(self, explanations, output_path):
        """Generate comprehensive HTML report"""
        report_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Stage Detection Report</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .decision {{ font-size: 28px; font-weight: bold; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center; }}
        .malware {{ background: #ffebee; color: #c62828; }}
        .benign {{ background: #e8f5e9; color: #2e7d32; }}
        .stage {{ border-left: 4px solid #2196F3; padding-left: 20px; margin: 20px 0; }}
        .breakdown {{ display: flex; justify-content: space-around; margin: 30px 0; }}
        .breakdown-item {{ flex: 1; padding: 20px; margin: 10px; background: #f9f9f9; border-radius: 5px; }}
        pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 Multi-Stage Detection Report</h1>
        <p><strong>Generated:</strong> {explanations['timestamp']}</p>
        
        <div class="decision {'malware' if explanations['final_decision'] == 'MALWARE' else 'benign'}">
            {explanations['final_decision']}
        </div>
        
        <h2>Detection Stages</h2>
"""
        
        if explanations['stages'].get('file'):
            file_exp = explanations['stages']['file']
            report_html += f"""
        <div class="stage">
            <h3>📊 Stage 1: Static File Analysis</h3>
            <p><strong>Score:</strong> {file_exp['score']:.3f}</p>
            <p><strong>Confidence:</strong> {file_exp['confidence']:.3f}</p>
        </div>
"""
        
        if explanations['stages'].get('behavior'):
            behavior_exp = explanations['stages']['behavior']
            report_html += f"""
        <div class="stage">
            <h3>🏃 Stage 2: Behavioral Analysis</h3>
            <p><strong>Score:</strong> {behavior_exp['score']:.3f}</p>
            <p><strong>Confidence:</strong> {behavior_exp['confidence']:.3f}</p>
        </div>
"""
        
        breakdown = explanations.get('confidence_breakdown', {})
        if breakdown:
            report_html += "<h2>🎯 Decision Fusion</h2><div class='breakdown'>"
            
            if 'file_analysis' in breakdown:
                fa = breakdown['file_analysis']
                report_html += f"""
            <div class="breakdown-item">
                <h3>Static Analysis</h3>
                <p><strong>Weight:</strong> {fa['weight']:.1%}</p>
                <p><strong>Contribution:</strong> {fa['contribution']:.3f}</p>
            </div>
"""
            
            if 'behavioral_analysis' in breakdown:
                ba = breakdown['behavioral_analysis']
                report_html += f"""
            <div class="breakdown-item">
                <h3>Behavioral Analysis</h3>
                <p><strong>Weight:</strong> {ba['weight']:.1%}</p>
                <p><strong>Contribution:</strong> {ba['contribution']:.3f}</p>
            </div>
"""
            
            report_html += "</div>"
        
        report_html += f"""
        <h2>💬 Explanation</h2>
        <pre>{explanations.get('reasoning', 'No reasoning available')}</pre>
        
        <hr>
        <p><em>Generated by Multi-Stage Explainability Framework</em></p>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        print(f"\n📄 Report saved: {output_path}")
        return output_path

if __name__ == "__main__":
    print("Multi-Stage Explainability Framework")
    print("NOVEL contribution for Master's Thesis")