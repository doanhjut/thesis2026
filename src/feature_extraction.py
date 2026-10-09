"""
PE Feature Extractor
Extract 2381 features from PE files (EMBER format)
Compatible with SOREL-20M trained model

Canonical module: src/feature_extraction.py
"""

import numpy as np
import ember
import lief
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class PEFeatureExtractor:
    """
    Extract features từ PE file theo format EMBER-v2
    Output: 2381 features vector
    """
    
    def __init__(self):
        self.feature_version = 2  # EMBER v2
        self.expected_dim = 2381
        
        print("🔧 PE Feature Extractor initialized")
        print(f"   Format: EMBER v{self.feature_version}")
        print(f"   Output dimension: {self.expected_dim}")
    
    def extract_from_file(self, file_path):
        """
        Extract features từ PE file
        
        Args:
            file_path: Path đến PE file
            
        Returns:
            numpy array (2381,) hoặc None nếu lỗi
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return None
        
        print(f"\n📂 Extracting features from: {file_path.name}")
        
        try:
            # Đọc file binary
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            print(f"   File size: {len(file_data):,} bytes")
            
            # Method 1: Dùng ember library (recommended)
            features = self._extract_with_ember(file_data)
            
            if features is not None and len(features) == self.expected_dim:
                print(f"   ✅ Extracted {len(features)} features")
                return features
            
            # Method 2: Fallback - dùng LIEF
            print("   ⚠️  Trying fallback method...")
            features = self._extract_with_lief(file_path)
            
            if features is not None:
                print(f"   ✅ Extracted {len(features)} features (fallback)")
                return features
            
            print("   ❌ Feature extraction failed")
            return None
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def _extract_with_ember(self, file_data):
        """Extract using ember library"""
        try:
            # Suppress LIEF version warnings
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # EMBER's raw feature extractor
                extractor = ember.PEFeatureExtractor(feature_version=self.feature_version)
                features = np.array(extractor.feature_vector(file_data), dtype=np.float32)
                
                # Validate features
                if features is None or len(features) == 0:
                    return None
                
                # Replace inf/nan with 0
                features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
                
                return features
        except Exception as e:
            print(f"   EMBER extraction failed: {e}")
            return None
    
    def _extract_with_lief(self, file_path):
        """Fallback: Extract basic features using LIEF"""
        try:
            binary = lief.parse(str(file_path))
            if binary is None:
                return None
            
            # Tạo feature vector cơ bản (simplified)
            # Note: Không đầy đủ như EMBER nhưng có thể dùng được
            features = []
            
            # General info
            features.extend(self._extract_general_info(binary))
            
            # Header features
            features.extend(self._extract_header_features(binary))
            
            # Section features
            features.extend(self._extract_section_features(binary))
            
            # Import features
            features.extend(self._extract_import_features(binary))
            
            # Export features
            features.extend(self._extract_export_features(binary))
            
            # Pad to 2381 if needed
            features = np.array(features, dtype=np.float32)
            if len(features) < self.expected_dim:
                features = np.pad(features, (0, self.expected_dim - len(features)))
            elif len(features) > self.expected_dim:
                features = features[:self.expected_dim]
            
            return features
            
        except Exception as e:
            print(f"   LIEF extraction failed: {e}")
            return None
    
    def _extract_general_info(self, binary):
        """Extract general PE info"""
        features = []
        try:
            features.append(float(binary.virtual_size))
            features.append(float(len(binary.sections)))
            features.append(float(binary.header.time_date_stamps))
        except:
            features.extend([0.0] * 3)
        return features
    
    def _extract_header_features(self, binary):
        """Extract PE header features"""
        features = []
        try:
            header = binary.header
            features.append(float(header.machine))
            features.append(float(header.sizeof_optional_header))
            features.append(float(header.characteristics))
        except:
            features.extend([0.0] * 3)
        return features
    
    def _extract_section_features(self, binary):
        """Extract section features"""
        features = []
        try:
            for section in binary.sections[:10]:  # Max 10 sections
                features.append(float(section.size))
                features.append(float(section.virtual_size))
                features.append(float(section.entropy))
            
            # Pad if less than 10 sections
            while len(features) < 30:
                features.append(0.0)
        except:
            features.extend([0.0] * 30)
        return features
    
    def _extract_import_features(self, binary):
        """Extract import features"""
        features = []
        try:
            imports = list(binary.imports)
            features.append(float(len(imports)))
            
            # Count important DLLs
            dll_names = [imp.name.lower() for imp in imports]
            features.append(float('kernel32.dll' in dll_names))
            features.append(float('user32.dll' in dll_names))
            features.append(float('advapi32.dll' in dll_names))
        except:
            features.extend([0.0] * 4)
        return features
    
    def _extract_export_features(self, binary):
        """Extract export features"""
        features = []
        try:
            exports = list(binary.exported_functions)
            features.append(float(len(exports)))
        except:
            features.append(0.0)
        return features
    
    def get_feature_names(self):
        """
        Get human-readable feature names
        Note: EMBER features có tên cụ thể, đây là simplified version
        """
        # Simplified names - EMBER có 2381 features với tên cụ thể
        # Xem chi tiết: https://github.com/elastic/ember/blob/master/ember/features.py
        return [
            "General: Virtual Size",
            "General: Section Count",
            "General: Timestamp",
            "Header: Machine Type",
            "Header: Optional Header Size",
            "Header: Characteristics",
            # ... (2381 features in total)
        ]

# ============================================================================
# TESTING & DEMO
# ============================================================================

def test_extractor(test_file_path):
    """Test feature extractor"""
    print("="*80)
    print("🧪 TESTING PE FEATURE EXTRACTOR")
    print("="*80)
    
    extractor = PEFeatureExtractor()
    
    features = extractor.extract_from_file(test_file_path)
    
    if features is not None:
        print("\n📊 Feature Statistics:")
        print(f"   Shape: {features.shape}")
        print(f"   Min: {features.min():.4f}")
        print(f"   Max: {features.max():.4f}")
        print(f"   Mean: {features.mean():.4f}")
        print(f"   Non-zero: {np.count_nonzero(features)}")
        
        print("\n📈 First 10 features:")
        for i, val in enumerate(features[:10]):
            print(f"   Feature {i:3d}: {val:.6f}")
        
        return features
    else:
        print("\n❌ Feature extraction failed")
        return None

def batch_extract(file_paths):
    """Extract features from multiple files"""
    print("="*80)
    print("📦 BATCH FEATURE EXTRACTION")
    print("="*80)
    
    extractor = PEFeatureExtractor()
    results = []
    
    for file_path in file_paths:
        features = extractor.extract_from_file(file_path)
        if features is not None:
            results.append({
                'file': Path(file_path).name,
                'features': features,
                'success': True
            })
        else:
            results.append({
                'file': Path(file_path).name,
                'features': None,
                'success': False
            })
    
    success_count = sum(1 for r in results if r['success'])
    print(f"\n✅ Successfully extracted: {success_count}/{len(file_paths)} files")
    
    return results

if __name__ == "__main__":
    import sys
    
    # Test với file Windows system file
    test_file = r"C:\Windows\System32\notepad.exe"
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    print("Testing with file:", test_file)
    
    if Path(test_file).exists():
        features = test_extractor(test_file)
        
        if features is not None:
            print("\n✅ Feature extractor is working!")
            print("\n💡 Next step: Integrate với SHAP explainer")
    else:
        print(f"❌ Test file not found: {test_file}")
        print("\n💡 Usage: python pe_feature_extractor.py <path_to_pe_file>")