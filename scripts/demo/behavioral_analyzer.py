"""
Behavioral Analyzer Module
Analyzes runtime events for ransomware patterns.
NOVEL CONTRIBUTION for Multi-Stage Explainability
"""

class BehaviorAnalyzer:
    """
    Analyzes system events for malicious ransomware behavior patterns.
    """
    
    def __init__(self):
        # Define common ransomware behavior patterns
        self.patterns = {
            'file_encryption': {
                'description': 'Rapid file modification or renaming with typical ransomware extensions',
                'severity': 'CRITICAL',
                'indicators': ['.encrypted', '.locked', '.crypted']
            },
            'shadow_copy_deletion': {
                'description': 'Attempt to delete volume shadow copies (vssadmin delete shadows)',
                'severity': 'HIGH',
                'indicators': ['vssadmin', 'delete', 'shadows']
            },
            'high_entropy_writes': {
                'description': 'Large volume of high-entropy (encrypted/compressed) data writes',
                'severity': 'HIGH',
                'indicators': ['write_bytes', 'entropy']
            },
            'registry_persistence': {
                'description': 'Unauthorized modification of run-once registry keys',
                'severity': 'MEDIUM',
                'indicators': ['Software\\Microsoft\\Windows\\CurrentVersion\\Run']
            }
        }
        print("🛡️ Behavioral Analyzer initialized with 4 default patterns")

    def analyze_events(self, runtime_events):
        """
        Analyze a list of runtime events against known patterns.
        
        Args:
            runtime_events: List of dicts representing system events
            
        Returns:
            dict: Analysis results compatible with MultiStageExplainer
        """
        if not runtime_events:
            return {
                'threat_detected': False,
                'patterns': self.patterns
            }

        detected_patterns = {}
        threat_detected = False
        
        # Simple pattern matching logic (can be extended)
        for name, pattern in self.patterns.items():
            pattern_match = False
            match_details = []
            
            for event in runtime_events:
                # Check if indicators exist in any event data string
                event_str = str(event).lower()
                matches = [ind for ind in pattern['indicators'] if ind.lower() in event_str]
                
                if matches:
                    pattern_match = True
                    match_details.append({
                        'event': event,
                        'matched_indicators': matches
                    })
            
            if pattern_match:
                threat_detected = True
                detected_patterns[name] = {
                    **pattern,
                    'detected': True,
                    'matches': match_details
                }
            else:
                detected_patterns[name] = {
                    **pattern,
                    'detected': False
                }

        return {
            'threat_detected': threat_detected,
            'patterns': detected_patterns
        }

if __name__ == "__main__":
    analyzer = BehaviorAnalyzer()
    test_events = [{'type': 'process', 'cmd': 'vssadmin.exe delete shadows /all'}]
    result = analyzer.analyze_events(test_events)
    print(f"Test Analysis: Threat Detected = {result['threat_detected']}")
