import tempfile
import unittest
from pathlib import Path
import json
import sqlite3

import numpy as np
import pandas as pd

from src.experiments.common import choose_threshold, evaluate, load_dataset, sha256
from src.experiments.fidelity import mask_metrics
from src.experiments.fusion import sequence_scores
from src.experiments.gating import gate_counts, select_gate
from src.experiments.provenance import audit
from src.experiments.recovery import (SOREL_TAGS, inspect_npz, recover,
                                      recover_sorel_metadata, sampled_source_indices)
from src.experiments.signals import normalize, shap_signals
from src.experiments.temporal import validate as validate_temporal
from src.pid_fusion import PIDController, fuse_scores


class ExperimentMathTests(unittest.TestCase):
    def test_threshold_meets_validation_target(self):
        y = np.array([0, 0, 1, 1, 1, 1])
        p = np.array([0.9, 0.1, 0.8, 0.7, 0.6, 0.2])
        threshold = choose_threshold(y, p, 0.75)
        self.assertEqual(threshold, 0.6)
        self.assertGreaterEqual(evaluate(y, p, threshold)['tpr'], 0.75)

    def test_shap_signal_definition(self):
        phi = np.array([[1.0, -1.0], [2.0, 0.0], [0.0, 0.0]])
        entropy, variance = shap_signals(phi)
        np.testing.assert_allclose(entropy, [1.0, 0.0, 0.0])
        np.testing.assert_allclose(variance, [1.0, 1.0, 0.0])
        np.testing.assert_allclose(normalize(np.ones(3)), np.zeros(3))

    def test_pid_step_and_reset(self):
        pid = PIDController(0.85, 0.12, 0.35)
        first = pid.update(0.4)
        second = pid.update(0.4)
        self.assertNotEqual(first, second)
        pid.reset()
        self.assertAlmostEqual(first, pid.update(0.4))
        self.assertAlmostEqual(fuse_scores(0.8, 0.2, 0.5), 0.5)

    def test_sequence_scores_preserve_filtered_row_order(self):
        frame = pd.DataFrame({
            'sequence_id': ['b', 'a', 'b'],
            'sequence_order': [2, 1, 1],
            'probability': [0.8, 0.4, 0.7],
            'p_dynamic': [0.2, 0.3, 0.1],
        }, index=[8, 2, 5])
        scores, weights = sequence_scores(frame, (0.85, 0.12, 0.35))
        self.assertEqual(scores.shape, (3,))
        self.assertEqual(weights.shape, (3,))
        np.testing.assert_allclose(scores, weights * frame.probability.to_numpy() +
                                   (1 - weights) * frame.p_dynamic.to_numpy())

    def test_mask_metrics_are_directly_recomputable(self):
        y = np.array([0, 0, 1, 1])
        before = np.array([0.1, 0.3, 0.7, 0.9])
        after = np.array([0.2, 0.4, 0.6, 0.8])
        result = mask_metrics(y, before, after)
        self.assertAlmostEqual(result['auc_before'], 1.0)
        self.assertAlmostEqual(result['auc_after'], 1.0)
        self.assertAlmostEqual(result['mean_absolute_probability_change'], 0.1)

    def test_gate_selection_respects_early_error_constraints(self):
        y = np.array([0, 0, 0, 1, 1, 1])
        p = np.array([0.01, 0.1, 0.45, 0.55, 0.9, 0.99])
        low, high, selected, _ = select_gate(y, p, max_early_fnr=0, max_early_fpr=0)
        self.assertLessEqual(low, 0.55)
        self.assertGreaterEqual(high, 0.45)
        self.assertEqual(selected['early_false_negatives'], 0)
        self.assertEqual(selected['early_false_positives'], 0)
        self.assertEqual(gate_counts(y, p, low, high), selected)


class DatasetGuardTests(unittest.TestCase):
    def test_duplicate_feature_vectors_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'data.csv'
            pd.DataFrame({'x': [1.0, 1.0, 2.0, 3.0], 'label': [0, 1, 0, 1]}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, 'Duplicate feature vectors'):
                load_dataset(path)

    def test_fractional_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'data.csv'
            pd.DataFrame({'x': np.arange(10), 'label': [0, 1, 0, 1, 0.5, 1, 0, 1, 0, 1]}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, 'binary classes'):
                load_dataset(path)

    def test_pid_input_audit_reports_missing_identity_and_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            path = root / 'data/features.csv'
            pd.DataFrame({'x': [1.0, 2.0], 'label': [0, 1]}).to_csv(path, index=False)
            result = audit(path, repo=root)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['dataset']['identifier_columns'], [])
            self.assertGreaterEqual(len(result['blockers']), 3)

    def test_temporal_schema_requires_multiple_ordered_observations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'dynamic.csv'
            provenance = root / 'provenance.json'
            report = root / 'report.json'
            report.write_text('{"events": []}')
            pd.DataFrame({
                'row_id': [1, 1], 'execution_id': ['run1', 'run1'],
                'time_step': [0, 1], 'elapsed_seconds': [5.0, 15.0],
                'p_dynamic': [0.2, 0.7], 'evidence_status': ['observed', 'observed'],
                'report_path': ['report.json', 'report.json'], 'report_sha256': [sha256(report), sha256(report)],
            }).to_csv(data, index=False)
            provenance.write_text(json.dumps({
                'signal_origin': 'observed', 'no_target_label_in_score': True,
                'dataset_sha256': 'abc', 'measurements_sha256': sha256(data),
                'label_definition': 'test', 'dynamic_feature_definition': 'test',
                'dynamic_score_definition': 'test', 'dynamic_model_training_source': 'test',
                'calibration_method': 'test', 'sandbox_or_honeypot': 'test', 'collection_period': 'test',
            }))
            result = validate_temporal(data, provenance, 'abc')
            self.assertEqual(result['status'], 'valid_schema')
            self.assertEqual(result['scored_rows'], 2)

    def test_source_manifest_recovery_replays_sampling_and_metadata_alignment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, mini, metadata, output = root / 'source.npz', root / 'mini.csv', root / 'metadata.jsonl', root / 'out'
            labels = np.array([0] * 10 + [1] * 5)
            features = np.arange(len(labels) * 3, dtype=np.float32).reshape(len(labels), 3) / 10
            np.savez_compressed(source, features, labels)
            inspected = inspect_npz(source)
            self.assertEqual(inspected['rows'], 15)
            self.assertEqual(inspected['features'], 3)
            self.assertEqual(inspected['label_counts'], {'0': 10, '1': 5})
            selected = sampled_source_indices(labels, 4, 2, 42)
            permutation = pd.DataFrame({'position': np.arange(len(selected))}).sample(frac=1, random_state=42).position.to_numpy()
            source_ids = selected[permutation]
            frame = pd.DataFrame(features[source_ids], columns=['0', '1', '2'])
            frame['label'] = labels[source_ids]
            frame.to_csv(mini, index=False)
            with metadata.open('w') as stream:
                for index, label in enumerate(labels):
                    stream.write(json.dumps({'sha256': f'{index:064x}', 'appeared': '2026-01',
                                             'label': int(label), 'avclass': 'test'}) + '\n')
            result = recover(source, mini, output, [metadata], n_negative=4, n_positive=2, seed=42)
            self.assertEqual(result['status'], 'recovered')
            self.assertEqual(result['metadata_status'], 'row_order_and_label_verified')
            manifest = pd.read_csv(output / 'row_manifest.csv', dtype={'sha256': str})
            np.testing.assert_array_equal(manifest.source_index, source_ids)
            self.assertTrue(manifest.sha256.str.len().eq(64).all())

    def test_sorel_metadata_recovery_replays_test_order_and_missing_filter(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db, manifest, inspection = root / 'meta.db', root / 'row_manifest.csv', root / 'inspection.json'
            source = root / 'test-features.npz'
            missing, output = root / 'missing.json', root / 'out'
            tag_schema = ','.join(f'{tag} integer' for tag in SOREL_TAGS)
            connection = sqlite3.connect(db)
            connection.execute(
                f'create table meta(sha256 text, is_malware integer, rl_fs_t real, '
                f'rl_ls_const_positives integer,{tag_schema})')
            placeholders = ','.join(['?'] * (4 + len(SOREL_TAGS)))
            connection.execute(f'insert into meta values({placeholders})',
                               [f'{999:064x}', 0, 5.0, 0, *([0] * len(SOREL_TAGS))])
            for index in range(2):
                connection.execute(f'insert into meta values({placeholders})',
                                   [f'{1000 + index:064x}', index % 2, 10.0, 1, *([0] * len(SOREL_TAGS))])
            raw_test = []
            for index in range(15):
                sha = f'{index:064x}'
                label = index % 2
                tags = [0] * len(SOREL_TAGS)
                tags[SOREL_TAGS.index('ransomware')] = int(index in {5, 13})
                connection.execute(f'insert into meta values({placeholders})',
                                   [sha, label, 20.0 + index, label * 3, *tags])
                raw_test.append((sha, label, tags))
            connection.commit()
            connection.close()
            missing.write_text(json.dumps([raw_test[3][0]]))
            filtered = [item for i, item in enumerate(raw_test) if i != 3]
            np.savez(source, np.zeros((len(filtered), 3), dtype=np.float32),
                     np.asarray([item[1] for item in filtered], dtype=np.int64))
            source_indices = np.array([4, 0, 12])
            pd.DataFrame({
                'row_id': [0, 1, 2], 'source_index': source_indices,
                'label': [filtered[i][1] for i in source_indices],
                'feature_sha256': ['a' * 64, 'b' * 64, 'c' * 64],
            }).to_csv(manifest, index=False)
            inspection.write_text(json.dumps({'rows': len(filtered), 'features': 3, 'label_entry': 'arr_1.npy'}))
            report = recover_sorel_metadata(manifest, inspection, db, missing, output,
                                            test_split=10.0, source=source)
            self.assertEqual(report['status'], 'sorel_metadata_recovered')
            self.assertEqual(report['official_order_replay']['test_rows_after_missing_filter'], 14)
            self.assertEqual(report['official_order_replay']['inclusive_rows_after_missing_filter'], 16)
            self.assertEqual(report['official_order_replay']['boundary_rows_after_missing_filter'], 2)
            self.assertEqual(report['official_order_replay']['selected_split_operator'], '>')
            self.assertEqual(report['official_order_replay']['all_npz_labels_matching'], 14)
            augmented = pd.read_csv(output / 'sorel_row_manifest.csv', dtype={'sha256': str})
            self.assertEqual(augmented.sha256.tolist(), [filtered[i][0] for i in source_indices])
            self.assertEqual(int(augmented.tag_ransomware.sum()), 2)


if __name__ == '__main__':
    unittest.main()
