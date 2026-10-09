from multistage_explainer import MultiStageExplainer
from xai_explainer import RansomwareExplainer
from behavioral_analyzer import BehaviorAnalyzer

# Initialize
ml_explainer = RansomwareExplainer('ransomware_lgbm_1M_final.txt')
behavior_analyzer = BehaviorAnalyzer()

multistage = MultiStageExplainer(ml_explainer, behavior_analyzer)

# Test với file + simulated events
explanation = multistage.explain_complete_detection(
    pe_file='test_malware.exe',
    runtime_events=simulated_events  # From monitor
)

# Generate report
multistage.generate_report(explanation, 'multistage_report.html')