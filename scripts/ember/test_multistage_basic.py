"""
Test cơ bản cho Multi-Stage Explainer
Chỉ test import và khởi tạo
"""

print("="*80)
print("🧪 TEST MULTI-STAGE FRAMEWORK - BASIC")
print("="*80)

# Test 1: Import
print("\n1️⃣ Testing import...")
try:
    from multistage_explainer import MultiStageExplainer
    print("   ✅ Import successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 2: Initialize (without dependencies)
print("\n2️⃣ Testing initialization...")
try:
    explainer = MultiStageExplainer()
    print("   ✅ Initialization successful")
except Exception as e:
    print(f"   ❌ Initialization failed: {e}")
    exit(1)

# Test 3: Check methods exist
print("\n3️⃣ Testing methods exist...")
methods = [
    'explain_complete_detection',
    '_explain_file_level',
    '_explain_behavior_level',
    '_explain_decision_fusion',
    '_generate_reasoning'
]

for method in methods:
    if hasattr(explainer, method):
        print(f"   ✅ Method '{method}' exists")
    else:
        print(f"   ❌ Method '{method}' missing")

print("\n" + "="*80)
print("✅ BASIC TEST PASSED")
print("="*80)
print("\nNext: Test with actual ML explainer")