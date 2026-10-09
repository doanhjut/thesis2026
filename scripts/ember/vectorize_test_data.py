"""
Script to vectorize EMBER 2018 test features from jsonl files
This creates X_test.dat and y_test.dat files needed for cross-dataset evaluation
"""
import ember
import numpy as np
from pathlib import Path

if __name__ == '__main__':
    # Paths
    EMBER_DATA_DIR = Path(r"D:\Code\Luanvan\ember_test\ember2018")

    print("="*80)
    print("🔧 VECTORIZING EMBER 2018 TEST DATA")
    print("="*80)

    # Vectorize test features
    print("\n📦 Reading and vectorizing test_features.jsonl...")
    print("   This may take several minutes...")

    ember.create_vectorized_features(
        str(EMBER_DATA_DIR),
        feature_version=2
    )

    print("\n✅ Vectorization complete!")
    print(f"   Created files in: {EMBER_DATA_DIR}")
    print("   - X_test.dat")
    print("   - y_test.dat")
    print("\nYou can now run ember_comparison.py")
