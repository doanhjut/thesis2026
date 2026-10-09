"""
Honeypot Generator
Tạo fake files/folders để lure ransomware
"""

import os
import random
import math
import json
from pathlib import Path
from datetime import datetime
from collections import Counter


class HoneypotGenerator:

    def __init__(self, base_path="C:\\Honeypot"):
        self.base_path = Path(base_path)
        self.config_file = self.base_path / "honeypot_config.json"
        self.honeypots = []

    def create_directory_structure(self):
        folders = [
            "Documents/Personal",
            "Documents/Work",
            "Documents/Financial",
            "Pictures/Family",
            "Pictures/Vacation_2024",
            "Backups/Database",
            "Backups/System",
            "Projects/Source_Code",
            "Passwords"
        ]
        print("📁 Creating honeypot directory structure...")
        for folder in folders:
            folder_path = self.base_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Created: {folder}")
        return folders

    def generate_realistic_content(self, file_type, size_kb=10):
        if file_type == 'text':
            words = ["password", "confidential", "secret", "private",
                     "backup", "admin", "database", "config", "important", "account"]
            lines = []
            for _ in range(size_kb * 10):
                line = " ".join(random.choices(words, k=random.randint(5, 15)))
                lines.append(line)
            return "\n".join(lines).encode('utf-8')
        elif file_type == 'binary':
            pattern = b'\x00\x01\x02\x03' * (size_kb * 256)
            return pattern[:size_kb * 1024]
        else:
            return b'X' * (size_kb * 1024)

    def _calc_entropy(self, content):
        if len(content) == 0:
            return 0.0
        byte_counts = Counter(content)
        entropy = -sum(
            (count / len(content)) * math.log2(count / len(content))
            for count in byte_counts.values()
        )
        return entropy

    def create_honeyfiles(self, count=100):
        print(f"\n🍯 Creating honeypot files...")

        templates = {
            'Documents/Personal': [
                ('passwords.txt', 'text', 5),
                ('bank_accounts.xlsx', 'binary', 20),
                ('credit_cards.docx', 'binary', 15),
                ('personal_info.pdf', 'binary', 30),
                ('tax_return_2024.pdf', 'binary', 50),
            ],
            'Documents/Work': [
                ('salary_info.xlsx', 'binary', 25),
                ('employee_data.csv', 'text', 30),
                ('contracts.docx', 'binary', 40),
                ('confidential_report.pdf', 'binary', 35),
            ],
            'Documents/Financial': [
                ('investment_portfolio.xlsx', 'binary', 45),
                ('crypto_wallets.txt', 'text', 5),
                ('financial_statements.pdf', 'binary', 60),
            ],
            'Pictures/Family': [
                ('wedding_2023.jpg', 'binary', 100),
                ('baby_photos.jpg', 'binary', 100),
                ('vacation_memories.jpg', 'binary', 100),
            ],
            'Backups/Database': [
                ('database_backup.bak', 'binary', 200),
                ('mysql_dump.sql', 'text', 100),
                ('backup_20240107.zip', 'binary', 200),
            ],
            'Projects/Source_Code': [
                ('important_project.zip', 'binary', 100),
                ('source_code.rar', 'binary', 100),
            ],
            'Passwords': [
                ('master_passwords.kdbx', 'binary', 10),
                ('ssh_keys.txt', 'text', 5),
                ('vpn_credentials.txt', 'text', 3),
            ]
        }

        created_files = []

        for folder, file_list in templates.items():
            folder_path = self.base_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

            for filename, file_type, size_kb in file_list:
                file_path = folder_path / filename
                content = self.generate_realistic_content(file_type, size_kb)

                with open(file_path, 'wb') as f:
                    f.write(content)

                entropy = self._calc_entropy(content)

                try:
                    os.system(f'attrib +h +s "{file_path}"')
                except:
                    pass

                honeypot_info = {
                    'path': str(file_path),
                    'filename': filename,
                    'folder': folder,
                    'size': len(content),
                    'original_entropy': entropy,
                    'created': datetime.now().isoformat(),
                    'last_modified': file_path.stat().st_mtime,
                    'is_honeypot': True
                }

                created_files.append(honeypot_info)
                self.honeypots.append(honeypot_info)

                print(f"   ✓ {folder}/{filename} ({size_kb}KB, entropy={entropy:.2f})")

        self._save_config()
        print(f"\n✅ Created {len(created_files)} honeypot files")
        return created_files

    def _save_config(self):
        config = {
            'base_path': str(self.base_path),
            'created': datetime.now().isoformat(),
            'honeypots': self.honeypots
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"\n💾 Configuration saved: {self.config_file}")

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = json.load(f)
            self.honeypots = config.get('honeypots', [])
            print(f"✅ Loaded {len(self.honeypots)} honeypots from config")
            return config
        return None

    def verify_honeypots(self):
        print("\n🔍 Verifying honeypot integrity...")
        modified, deleted, encrypted = [], [], []

        for honeypot in self.honeypots:
            file_path = Path(honeypot['path'])

            if not file_path.exists():
                deleted.append(honeypot)
                print(f"   🚨 DELETED: {honeypot['filename']}")
                continue

            current_mtime = file_path.stat().st_mtime
            if abs(current_mtime - honeypot['last_modified']) > 1:
                modified.append(honeypot)
                print(f"   ⚠️  MODIFIED: {honeypot['filename']}")

                with open(file_path, 'rb') as f:
                    content = f.read()

                if len(content) > 0:
                    new_entropy = self._calc_entropy(content)
                    entropy_diff = new_entropy - honeypot['original_entropy']

                    if entropy_diff > 1.0:
                        encrypted.append({
                            **honeypot,
                            'new_entropy': new_entropy,
                            'entropy_increase': entropy_diff
                        })
                        print(f"   🦠 POSSIBLE ENCRYPTION: {honeypot['filename']}")
                        print(f"      Original: {honeypot['original_entropy']:.2f} → New: {new_entropy:.2f}")

        return {'modified': modified, 'deleted': deleted, 'encrypted': encrypted,
                'total_checked': len(self.honeypots)}

    def cleanup(self):
        print("\n🗑️  Cleaning up honeypots...")
        for honeypot in self.honeypots:
            file_path = Path(honeypot['path'])
            if file_path.exists():
                file_path.unlink()
        if self.base_path.exists():
            import shutil
            shutil.rmtree(self.base_path)
        print("✅ Cleanup complete")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Honeypot Generator")
    parser.add_argument('--create', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--cleanup', action='store_true')
    parser.add_argument('--path', default='C:\\Honeypot')
    parser.add_argument('--count', type=int, default=100)
    args = parser.parse_args()

    generator = HoneypotGenerator(args.path)

    if args.create:
        generator.create_directory_structure()
        generator.create_honeyfiles(args.count)
        print("\n✅ HONEYPOT DEPLOYMENT COMPLETE")
        print(f"   Location: {args.path}")
        print(f"   Files: {len(generator.honeypots)}")

    elif args.verify:
        generator.load_config()
        results = generator.verify_honeypots()
        print(f"\nModified: {len(results['modified'])}")
        print(f"Deleted: {len(results['deleted'])}")
        print(f"Encrypted: {len(results['encrypted'])}")
        if results['encrypted']:
            print("🚨 RANSOMWARE ACTIVITY DETECTED!")

    elif args.cleanup:
        generator.load_config()
        generator.cleanup()

    else:
        parser.print_help()


if __name__ == "__main__":
    print("="*80)
    print("🍯 HONEYPOT GENERATOR")
    print("="*80)
    main()