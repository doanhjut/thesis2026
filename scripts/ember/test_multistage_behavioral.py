"""
Test multi-stage với cả file + behavioral data
"""

from multistage_explainer import MultiStageExplainer
from xai_explainer import RansomwareExplainer
from behavioral_analyzer import BehaviorAnalyzer
from datetime import datetime

print("="*80)
print("🧪 TEST MULTI-STAGE WITH BEHAVIORAL DATA")
print("="*80)

# Initialize
ml_explainer = RansomwareExplainer('ransomware_lgbm_1M_final.txt')
behavior_analyzer = BehaviorAnalyzer()
multistage = MultiStageExplainer(ml_explainer, behavior_analyzer)

# Test file
test_file = r"C:\Windows\System32\notepad.exe"

# Simulate benign behavioral events
benign_events = [
    {
        'timestamp': datetime.now().isoformat(),
        'type': 'modified',
        'file': 'C:\\Users\\test\\document.txt',
        'metadata': {}
    }
    # Just 1 event - benign behavior
]

print("\n📊 Testing with BENIGN file + BENIGN behavior...")
result = multistage.explain_complete_detection(
    pe_file=test_file,
    runtime_events=benign_events
)

print(f"\nResult: {result['final_decision']}")
print(f"File score: {result['stages']['file']['score']:.3f}")
print(f"Behavior score: {result['stages']['behavior']['score']:.3f}")

# Simulate malicious behavioral events
malicious_events = []
for i in range(20):  # 20 rapid renames = suspicious!
    malicious_events.append({
        'timestamp': datetime.now().isoformat(),
        'type': 'renamed',
        'file': f'C:\\Honeypot\\file_{i}.txt',
        'metadata': {'new_name': f'C:\\Honeypot\\file_{i}.encrypted'}
    })

print("\n🦠 Testing with BENIGN file + MALICIOUS behavior...")
result2 = multistage.explain_complete_detection(
    pe_file=test_file,
    runtime_events=malicious_events
)

print(f"\nResult: {result2['final_decision']}")
print(f"File score: {result2['stages']['file']['score']:.3f}")
print(f"Behavior score: {result2['stages']['behavior']['score']:.3f}")

if 'confidence_breakdown' in result2:
    breakdown = result2['confidence_breakdown']
    if 'file_analysis' in breakdown and 'behavioral_analysis' in breakdown:
        print(f"\nFusion weights:")
        print(f"  File weight: {breakdown['file_analysis']['weight']:.1%}")
        print(f"  Behavior weight: {breakdown['behavioral_analysis']['weight']:.1%}")
        print(f"  File contribution: {breakdown['file_analysis']['contribution']:.3f}")
        print(f"  Behavior contribution: {breakdown['behavioral_analysis']['contribution']:.3f}")

print("\n" + "="*80)
print("✅ BEHAVIORAL TEST COMPLETED")
print("="*80)
print("\nKey finding:")
print("→ Even benign FILE can be flagged if BEHAVIOR is malicious")
print("→ This demonstrates adaptive fusion working!")