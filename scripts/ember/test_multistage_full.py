"""
Test đầy đủ với ML explainer và behavioral analyzer
"""

from multistage_explainer import MultiStageExplainer
from xai_explainer import RansomwareExplainer
from behavioral_analyzer import BehaviorAnalyzer

print("="*80)
print("🧪 TEST MULTI-STAGE FRAMEWORK - FULL")
print("="*80)

# Step 1: Load dependencies
print("\n1️⃣ Loading ML explainer...")
try:
    ml_explainer = RansomwareExplainer('ransomware_lgbm_1M_final.txt')
    print("   ✅ ML explainer loaded")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

print("\n2️⃣ Loading behavioral analyzer...")
try:
    behavior_analyzer = BehaviorAnalyzer()
    print("   ✅ Behavioral analyzer loaded")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Step 2: Initialize multi-stage explainer
print("\n3️⃣ Initializing multi-stage explainer...")
try:
    multistage = MultiStageExplainer(ml_explainer, behavior_analyzer)
    print("   ✅ Multi-stage explainer ready")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Step 3: Test với file thật
print("\n4️⃣ Testing with real file...")

test_file = r"C:\Windows\System32\notepad.exe"

# Simulated events for behavioral analysis
simulated_events = [
    {'type': 'file', 'action': 'rename', 'path': 'doc1.docx', 'new_path': 'doc1.docx.locked'},
    {'type': 'process', 'action': 'execute', 'cmd': 'vssadmin.exe delete shadows /all'},
    {'type': 'registry', 'action': 'write', 'key': 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run', 'value': 'ransomware.exe'}
]

try:
    # Full analysis with file and behavioral data
    result = multistage.explain_complete_detection(
        pe_file=test_file,
        runtime_events=simulated_events
    )
    
    print(f"\n   Decision: {result['final_decision']}")
    print(f"   Has file explanation: {result['stages']['file'] is not None}")
    print(f"   Has behavior explanation: {result['stages']['behavior'] is not None}")
    print(f"   Has reasoning: {result['reasoning'] is not None}")
    
    print("\n   ✅ Test passed!")
    
except Exception as e:
    print(f"   ❌ Test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ FULL TEST COMPLETED")
print("="*80)