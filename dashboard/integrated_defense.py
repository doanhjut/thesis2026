"""
Integrated Ransomware Defense System
Kết hợp: Honeypots + Monitoring + Behavioral Analysis + ML Detection
"""

import time
import json
from pathlib import Path
from datetime import datetime

from honeypot_generator import HoneypotGenerator
from honeypot_monitor import HoneypotMonitor, start_monitoring
from behavioral_analyzer import BehaviorAnalyzer


class IntegratedDefenseSystem:

    def __init__(self, config_path="defense_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.honeypot_generator = None
        self.monitor_observer = None
        self.monitor_handler = None
        self.behavior_analyzer = BehaviorAnalyzer()
        self.running = False
        self.alerts = []

        print("🛡️  Integrated Defense System initialized")

    def _load_config(self):
        default = {
            'honeypot_path': 'C:\\Honeypot',
            'honeypot_count': 50,
            'monitor_interval': 60,
            'analysis_window': 5,
        }
        if self.config_path.exists():
            with open(self.config_path) as f:
                default.update(json.load(f))
        return default

    def setup_honeypots(self):
        print("\n" + "="*80)
        print("🍯 SETTING UP HONEYPOTS")
        print("="*80)
        self.honeypot_generator = HoneypotGenerator(self.config['honeypot_path'])
        self.honeypot_generator.create_directory_structure()
        files = self.honeypot_generator.create_honeyfiles(self.config['honeypot_count'])
        print(f"\n✅ Honeypots deployed: {len(files)} files")
        return files

    def start_monitoring(self):
        print("\n" + "="*80)
        print("👁️  STARTING MONITORING")
        print("="*80)

        honeypot_config = Path(self.config['honeypot_path']) / 'honeypot_config.json'
        if not honeypot_config.exists():
            print("❌ Honeypot config not found. Run --setup first.")
            return False

        self.monitor_observer, self.monitor_handler = start_monitoring(
            honeypot_config,
            alert_callback=self._handle_alert
        )
        self.running = True
        return True

    def _handle_alert(self, alert):
        self.alerts.append(alert)
        recent_events = self.monitor_handler.get_recent_events(100)
        analysis = self.behavior_analyzer.analyze_events(
            recent_events, self.config['analysis_window']
        )
        threat_score = self.behavior_analyzer.calculate_threat_score(analysis)

        print(f"\n🚨 ALERT: {alert['type']} | Threat Score: {threat_score}/100")

        if threat_score >= 80:
            self._critical_response(alert, analysis)
        elif threat_score >= 50:
            self._high_response(alert, analysis)
        else:
            print("🟢 MEDIUM THREAT - Continue monitoring")

    def _critical_response(self, alert, analysis):
        print("\n" + "="*80)
        print("🔴 CRITICAL THREAT - IMMEDIATE ACTION REQUIRED")
        print("="*80)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        incident = {
            'timestamp': datetime.now().isoformat(),
            'severity': 'CRITICAL',
            'alert': alert,
            'actions_taken': []
        }

        evidence_file = f"incident_{ts}.json"
        with open(evidence_file, 'w') as f:
            json.dump(incident, f, indent=2)

        print(f"\n⚠️  RANSOMWARE DETECTED!")
        print("   1. Disconnect network immediately")
        print("   2. Kill suspicious processes")
        print("   3. Isolate affected machine")
        print("   4. Contact security team")
        print(f"\n📄 Evidence saved: {evidence_file}")

        report_path = f"critical_report_{ts}.txt"
        report = self.behavior_analyzer.generate_alert_message(analysis)
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"📄 Report saved: {report_path}")

    def _high_response(self, alert, analysis):
        print("\n🟡 HIGH THREAT - Investigate immediately")
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        analysis_file = f"analysis_{ts}.json"
        self.behavior_analyzer.save_analysis(analysis, analysis_file)
        print(f"   Analysis saved: {analysis_file}")

    def get_status(self):
        if not self.monitor_handler:
            return {'running': False, 'message': 'Not started'}
        stats = self.monitor_handler.get_statistics()
        return {
            'running': self.running,
            'alerts': len(self.alerts),
            'statistics': stats,
            'last_alert': self.alerts[-1] if self.alerts else None
        }

    def stop(self):
        print("\n🛑 Stopping defense system...")
        if self.monitor_observer:
            self.monitor_observer.stop()
            self.monitor_observer.join()
        self.running = False
        if self.monitor_handler:
            self.monitor_handler.generate_report('final_report.json')
        print("✅ Defense system stopped")

    def run(self):
        print("="*80)
        print("🛡️  INTEGRATED RANSOMWARE DEFENSE SYSTEM")
        print("="*80)

        honeypot_config = Path(self.config['honeypot_path']) / 'honeypot_config.json'
        if not honeypot_config.exists():
            print("\n⚠️  Honeypots not found. Creating...")
            self.setup_honeypots()

        if not self.start_monitoring():
            print("❌ Failed to start monitoring")
            return

        print("\n✅ Defense system running")
        print("   Press Ctrl+C to stop\n")

        try:
            while self.running:
                time.sleep(self.config['monitor_interval'])
                if self.monitor_handler:
                    recent_events = self.monitor_handler.get_recent_events(100)
                    if recent_events:
                        analysis = self.behavior_analyzer.analyze_events(
                            recent_events, self.config['analysis_window']
                        )
                        score = self.behavior_analyzer.calculate_threat_score(analysis)
                        print(f"📊 Periodic check - Threat score: {score}/100")
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            self.stop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Integrated Ransomware Defense System")
    parser.add_argument('--setup', action='store_true', help='Setup honeypots only')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--config', default='defense_config.json')
    args = parser.parse_args()

    system = IntegratedDefenseSystem(args.config)

    if args.setup:
        system.setup_honeypots()
        print("\n✅ Setup complete. Run without --setup to start monitoring.")
    elif args.status:
        status = system.get_status()
        print("\n" + "="*80)
        print("📊 SYSTEM STATUS")
        print("="*80)
        print(json.dumps(status, indent=2))
    else:
        system.run()


if __name__ == "__main__":
    print("="*80)
    print("🛡️  INTEGRATED RANSOMWARE DEFENSE SYSTEM")
    print("="*80)
    main()