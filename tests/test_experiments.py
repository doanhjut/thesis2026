import tempfile
import unittest
from pathlib import Path
import json

import numpy as np
import pandas as pd

from src.experiments.common import choose_threshold, evaluate, load_dataset, sha256
from src.experiments.fidelity import mask_metrics
from src.experiments.fusion import sequence_scores
from src.experiments.gating import gate_counts, select_gate
from src.experiments.provenance import audit
from src.experiments.recovery import recover, sampled_source_indices
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


if __name__ == '__main__':
    unittest.main()
