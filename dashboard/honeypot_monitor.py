"""
Honeypot File System Monitor
Real-time monitoring honeypot files để detect ransomware
"""

import time
import json
import math
from pathlib import Path
from datetime import datetime
from collections import Counter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading


class HoneypotMonitor(FileSystemEventHandler):

    def __init__(self, honeypot_config_path, alert_callback=None):
        self.config_path = Path(honeypot_config_path)
        self.alert_callback = alert_callback
        self.honeypots = self._load_honeypots()
        self.honeypot_paths = {Path(h['path']) for h in self.honeypots}
        self.events = []
        self.event_lock = threading.Lock()
        self.stats = {
            'file_opened': 0,
            'file_modified': 0,
            'file_renamed': 0,
            'file_deleted': 0,
        }
        self.RENAME_RATE_THRESHOLD = 10
        self.ENTROPY_INCREASE_THRESHOLD = 1.0

        print("🔍 Honeypot Monitor initialized")
        print(f"   Watching {len(self.honeypot_paths)} honeypot files")

    def _load_honeypots(self):
        if not self.config_path.exists():
            print(f"⚠️  Config not found: {self.config_path}")
            return []
        with open(self.config_path) as f:
            config = json.load(f)
        return config.get('honeypots', [])

    def _calc_entropy(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            if len(data) == 0:
                return 0.0
            byte_counts = Counter(data)
            return -sum(
                (c / len(data)) * math.log2(c / len(data))
                for c in byte_counts.values()
            )
        except:
            return 0.0

    def _get_original_entropy(self, file_path):
        file_path = Path(file_path)
        for h in self.honeypots:
            if Path(h['path']) == file_path:
                return h.get('original_entropy', 0.0)
        return 0.0

    def _log_event(self, event_type, file_path, metadata=None):
        with self.event_lock:
            event = {
                'timestamp': datetime.now().isoformat(),
                'type': event_type,
                'file': str(file_path),
                'metadata': metadata or {}
            }
            self.events.append(event)
            if len(self.events) > 1000:
                self.events = self.events[-1000:]

    def _check_entropy_change(self, file_path):
        original = self._get_original_entropy(file_path)
        current = self._calc_entropy(file_path)
        diff = current - original
        if diff > self.ENTROPY_INCREASE_THRESHOLD:
            return True, {'original_entropy': original, 'current_entropy': current, 'increase': diff}
        return False, None

    def _check_rename_rate(self, window_minutes=1):
        cutoff = datetime.now().timestamp() - (window_minutes * 60)
        recent = [
            e for e in self.events
            if e['type'] == 'renamed'
            and datetime.fromisoformat(e['timestamp']).timestamp() > cutoff
        ]
        rate = len(recent) / window_minutes
        if rate > self.RENAME_RATE_THRESHOLD:
            return True, {'rate': rate, 'threshold': self.RENAME_RATE_THRESHOLD}
        return False, None

    def _trigger_alert(self, alert_type, details):
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'severity': 'HIGH',
            'details': details
        }
        print("\n" + "="*80)
        print("🚨 RANSOMWARE ALERT!")
        print("="*80)
        print(f"Type: {alert_type}")
        print(f"Time: {alert['timestamp']}")
        print(f"Details: {json.dumps(details, indent=2)}")
        print("="*80)

        alert_file = Path("alerts.json")
        alerts = []
        if alert_file.exists():
            with open(alert_file) as f:
                alerts = json.load(f)
        alerts.append(alert)
        with open(alert_file, 'w') as f:
            json.dump(alerts, f, indent=2)

        if self.alert_callback:
            self.alert_callback(alert)
        return alert

    def on_modified(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if file_path not in self.honeypot_paths:
            return
        start_time = time.perf_counter()
        self.stats['file_modified'] += 1
        print(f"⚠️  HONEYPOT MODIFIED: {file_path.name}")
        is_encrypted, entropy_info = self._check_entropy_change(file_path)
        if is_encrypted:
            self._log_event('modified_encrypted', file_path, entropy_info)
            self._trigger_alert('FILE_ENCRYPTED', {'file': str(file_path), 'entropy_info': entropy_info})
            latency_ms = (time.perf_counter() - start_time) * 1000
            with open("system_latency.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] Fusion Latency: {latency_ms:.2f} ms\n")
            print(f"    ⚡ [Đo lường Hệ thống] Thời gian tính toán và ra quyết định chặn: {latency_ms:.2f} mili-giây")
        else:
            self._log_event('modified', file_path)

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        honeypot_dir = self.config_path.parent
        if honeypot_dir in file_path.parents:
            print(f"⚠️  NEW FILE IN HONEYPOT DIR: {file_path.name}")
            self._log_event('created', file_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if file_path in self.honeypot_paths:
            self.stats['file_deleted'] += 1
            print(f"🚨 HONEYPOT DELETED: {file_path.name}")
            self._log_event('deleted', file_path)
            self._trigger_alert('FILE_DELETED', {'file': str(file_path)})

    def on_moved(self, event):
        if event.is_directory:
            return
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        if src_path in self.honeypot_paths:
            self.stats['file_renamed'] += 1
            print(f"⚠️  HONEYPOT RENAMED: {src_path.name} → {dest_path.name}")
            self._log_event('renamed', src_path, {'new_name': str(dest_path)})
            high_rate, rate_info = self._check_rename_rate()
            if high_rate:
                self._trigger_alert('HIGH_RENAME_RATE', rate_info)

    def get_statistics(self):
        return {
            **self.stats,
            'total_events': len(self.events),
            'monitoring_since': self.events[0]['timestamp'] if self.events else None
        }

    def get_recent_events(self, count=10):
        with self.event_lock:
            return self.events[-count:]

    def generate_report(self, output_path):
        report = {
            'generated': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'recent_events': self.get_recent_events(50),
            'honeypots': len(self.honeypot_paths)
        }
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📊 Report saved: {output_path}")
        return report


def start_monitoring(honeypot_config_path, alert_callback=None):
    print("="*80)
    print("🔍 STARTING HONEYPOT MONITOR")
    print("="*80)

    with open(honeypot_config_path) as f:
        config = json.load(f)

    base_path = config.get('base_path', 'C:\\Honeypot')
    event_handler = HoneypotMonitor(honeypot_config_path, alert_callback)
    observer = Observer()
    observer.schedule(event_handler, base_path, recursive=True)
    observer.start()

    print(f"✅ Monitoring started: {base_path}")
    print(f"   Press Ctrl+C to stop")
    return observer, event_handler


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser(description="Honeypot Monitor")
    
    # Cập nhật đường dẫn mặc định về thư mục dự án
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_config = os.path.join(repo_root, "data", "dynamic_logs", "honeypot", "honeypot_config.json")
    parser.add_argument('--config', default=default_config)
    parser.add_argument('--report', help='Generate report and exit')
    args = parser.parse_args()

    if args.report:
        monitor = HoneypotMonitor(args.config)
        monitor.generate_report(args.report)
        return

    observer, event_handler = start_monitoring(args.config)

    try:
        while True:
            time.sleep(1)
            if int(time.time()) % 60 == 0:
                stats = event_handler.get_statistics()
                print(f"\n📊 Stats: {stats['file_modified']} modified, "
                      f"{stats['file_renamed']} renamed, "
                      f"{stats['file_deleted']} deleted")
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping monitor...")
        observer.stop()
        observer.join()
        event_handler.generate_report('monitoring_report.json')
        print("✅ Monitor stopped")


if __name__ == "__main__":
    print("="*80)
    print("🍯 HONEYPOT FILE SYSTEM MONITOR")
    print("="*80)
    main()