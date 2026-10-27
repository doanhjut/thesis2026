import tempfile
import unittest
from pathlib import Path
import hashlib
import json
import sqlite3

import numpy as np
import pandas as pd

from src.experiments.common import (choose_threshold, choose_threshold_at_max_fpr,
                                    evaluate, load_dataset, low_fpr_metrics, sha256)
from src.experiments.fidelity import mask_metrics
from src.experiments.fusion import sequence_scores
from src.experiments.gating import gate_counts, select_gate
from src.experiments.gated_pid import select_gate_grid
from src.experiments.malbehavd_pid import (_bootstrap_difference, _fold_effects,
                                           _timepoint_metrics, _win_tie_loss,
                                           _write_gzip_csv,
                                           audit_collection,
                                           prepare as prepare_malbehavd,
                                           safe_static_features)
from src.experiments.provenance import audit
from src.experiments.recovery import (SOREL_TAGS, inspect_npz, recover,
                                      recover_ember_dataset, recover_sorel_metadata,
                                      sampled_source_indices)
from src.experiments.reliability_pid import reliability_pid_trajectory
from src.experiments.signals import normalize, shap_signals
from src.experiments.temporal import validate as validate_temporal
from src.experiments.temporal_fusion import pid_trajectory, run as run_temporal_fusion
from src.pid_fusion import PIDController, fuse_scores


class ExperimentMathTests(unittest.TestCase):
    def test_threshold_meets_validation_target(self):
        y = np.array([0, 0, 1, 1, 1, 1])
        p = np.array([0.9, 0.1, 0.8, 0.7, 0.6, 0.2])
        threshold = choose_threshold(y, p, 0.75)
        self.assertEqual(threshold, 0.6)
        self.assertGreaterEqual(evaluate(y, p, threshold)['tpr'], 0.75)

    def test_low_fpr_threshold_is_selected_only_from_validation(self):
        y_val = np.array([0, 0, 0, 0, 1, 1])
        p_val = np.array([.1, .2, .3, .9, .4, .8])
        threshold = choose_threshold_at_max_fpr(y_val, p_val, .25)
        measured = evaluate(y_val, p_val, threshold)
        self.assertLessEqual(measured['fpr'], .25)
        self.assertAlmostEqual(measured['tpr'], 1.0)
        result = low_fpr_metrics(y_val, p_val, y_val, p_val, limits=(.25,))
        self.assertEqual(result['test_tpr_at_val_fpr_25'], 1.0)

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

    def test_pid_uses_elapsed_time_and_clips_integral(self):
        fast = PIDController(0.0, 1.0, 0.0, integral_limits=(-.5, .5))
        slow = PIDController(0.0, 1.0, 0.0, integral_limits=(-.5, .5))
        self.assertLess(fast.update(.1, delta_t=1), slow.update(.1, delta_t=3))
        for _ in range(20):
            slow.update(1.0, delta_t=10)
        self.assertEqual(slow.integral, .5)
        derivative = PIDController(0.0, 0.0, 1.0)
        derivative.update(.2, delta_t=5)
        derivative.update(.4, delta_t=10)
        self.assertAlmostEqual(derivative.last_terms['derivative'], .02)

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

    def test_temporal_pid_uses_delta_t_and_resets_per_execution(self):
        frame = pd.DataFrame({
            'row_id': [1, 1, 2, 2], 'execution_id': ['a', 'a', 'b', 'b'],
            'time_step': [0, 1, 0, 1], 'elapsed_seconds': [5., 15., 5., 25.],
            'probability': [.8, .8, .8, .8], 'p_dynamic': [.4, .6, .4, .6],
        }, index=[9, 3, 8, 2])
        result = pid_trajectory(frame, (.85, .12, .35), integral_limits=(-1., 1.))
        self.assertTrue(result.score.between(0, 1).all())
        first = result.sort_values(['row_id', 'elapsed_seconds']).groupby('row_id').head(1)
        np.testing.assert_allclose(first.pid_derivative, 0.)
        later = result.sort_values(['row_id', 'elapsed_seconds']).groupby('row_id').tail(1)
        self.assertNotEqual(later.iloc[0].pid_derivative, later.iloc[1].pid_derivative)

    def test_pid_accepts_explicit_event_axis_without_calling_it_seconds(self):
        frame = pd.DataFrame({
            'row_id': [1, 1, 2, 2], 'execution_id': ['a', 'a', 'b', 'b'],
            'time_step': [0, 1, 0, 1], 'event_count': [5., 10., 5., 20.],
            'probability': [.8, .8, .8, .8], 'p_dynamic': [.4, .6, .4, .6],
        })
        result = pid_trajectory(frame, (.85, .12, .35), integral_limits=(-1., 1.))
        self.assertTrue(result.score.between(0, 1).all())
        first = result.sort_values(['row_id', 'event_count']).groupby('row_id').head(1)
        np.testing.assert_allclose(first.pid_derivative, 0.)

    def test_reliability_pid_tracks_target_and_resets_each_execution(self):
        frame = pd.DataFrame({
            'row_id': [1, 1, 2, 2], 'execution_id': ['a', 'a', 'b', 'b'],
            'time_step': [0, 1, 0, 1], 'event_count': [1., 2., 1., 2.],
            'probability': [.8, .8, .8, .8], 'p_dynamic': [.2, .4, .2, .4],
            'r_static': [.9, .9, .9, .9], 'r_dynamic': [.5, .7, .5, .7],
        })
        setting = {'w0': .5, 'beta': 4., 'kp': .5, 'ki': .01, 'kd': .25, 'alpha': .5}
        result = reliability_pid_trajectory(frame, setting)
        first = result.groupby('row_id', sort=False).head(1)
        self.assertTrue((first.w_static > .5).all())
        np.testing.assert_allclose(first.pid_derivative, 0.)
        np.testing.assert_allclose(
            result[result.row_id == 1].w_static.to_numpy(),
            result[result.row_id == 2].w_static.to_numpy())

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

    def test_cross_fitted_gate_grid_respects_each_error_cap(self):
        y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        p = np.array([.01, .1, .2, .8, .2, .7, .9, .99])
        low, high, measured, feasible = select_gate_grid(
            y, p, .25, lows=[.05, .15, .25], highs=[.75, .85, .95])
        self.assertLessEqual(measured['early_fnr_all_positive'], .25)
        self.assertLessEqual(measured['early_fpr_all_negative'], .25)
        self.assertGreater(feasible, 0)
        self.assertLessEqual(low, high)


class DatasetGuardTests(unittest.TestCase):
    def test_event_pid_gzip_csv_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            frame = pd.DataFrame({'row_id': [1, 2], 'score': [.2, .8]})
            first, second = root / 'first.csv.gz', root / 'second.csv.gz'
            _write_gzip_csv(frame, first)
            _write_gzip_csv(frame, second)
            self.assertEqual(sha256(first), sha256(second))

    def test_vt_collection_audit_distinguishes_deferred_from_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cohort, collection = root / 'cohort.csv', root / 'collection'
            collection.mkdir()
            rows = pd.DataFrame({
                'row_id': np.arange(10), 'sha256': [f'{i:064x}' for i in range(10)],
                'label': [0, 1] * 5, 'outer_fold': [0, 0, 1, 1, 0, 0, 1, 1, 0, 1],
            })
            rows.to_csv(cohort, index=False)
            features = rows.iloc[:6][['row_id', 'sha256', 'label']].copy()
            features['s_size'] = np.arange(6)
            features.to_csv(collection / 'static_features.csv.gz', index=False, compression='gzip')
            log = rows[['row_id', 'sha256', 'label']].copy()
            log['status'] = ['cached'] * 6 + ['deferred_quota'] * 4
            log.to_csv(collection / 'request_log.csv', index=False)
            result = audit_collection(cohort, collection, min_coverage=.9)
            self.assertEqual(result['status'], 'collection_incomplete')
            self.assertEqual(result['deferred_rows'], 4)
            self.assertEqual(result['additional_usable_rows_needed'], 3)
            self.assertFalse(result['network_requests_issued'])

    def test_event_pid_effect_outputs_replay_fold_and_timepoint_pairs(self):
        rows = []
        labels = [0, 0, 1, 1]
        for fusion, scores, predicted in [
                ('Fixed_weight', [.2, .8, .6, .7], [0, 1, 1, 1]),
                ('PID', [.1, .3, .7, .9], [0, 0, 1, 1])]:
            for row_id, (label, score, decision) in enumerate(zip(labels, scores, predicted)):
                for event_count in [5, 10]:
                    rows.append({'row_id': row_id, 'outer_fold': row_id % 2,
                                 'fusion': fusion, 'event_count': event_count,
                                 'label': label, 'score': score,
                                 'predicted_label': decision})
        predictions = pd.DataFrame(rows)
        fold_time, pooled_time = _timepoint_metrics(predictions)
        self.assertEqual(len(fold_time), 8)
        self.assertEqual(len(pooled_time), 4)
        final = predictions[predictions.event_count == 10]
        bootstrap = _bootstrap_difference(final, iterations=100, seed=4)
        self.assertEqual(bootstrap['comparison'], 'PID_minus_Fixed_weight')
        self.assertLess(bootstrap['metrics']['fpr']['mean'], 0)
        metrics = []
        for fold in [0, 1]:
            metrics.extend([
                {'outer_fold': fold, 'fusion': 'Fixed_weight', 'auc': .7,
                 'ap': .7, 'fpr': .5, 'tpr': .9, 'brier': .3},
                {'outer_fold': fold, 'fusion': 'PID', 'auc': .8,
                 'ap': .8, 'fpr': .25, 'tpr': .9, 'brier': .2},
            ])
        effects = _fold_effects(pd.DataFrame(metrics))
        counts = _win_tie_loss(effects)
        self.assertEqual(counts['auc']['pid_better_folds'], 2)
        self.assertEqual(counts['fpr']['pid_better_folds'], 2)

    def test_malbehavd_prepare_deduplicates_and_freezes_stratified_folds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / 'source.csv', root / 'prepared'
            rows = []
            for index in range(24):
                rows.append({'sha256': f'{index:064x}', 'labels': index % 2,
                             **{str(step): f'Api{step % 4}' for step in range(6)}})
            rows.append({**rows[0], '5': np.nan})  # same label/hash, shorter duplicate
            pd.DataFrame(rows).to_csv(source, index=False)
            result = prepare_malbehavd(source, output, min_events=5, folds=3, seed=7)
            manifest = pd.read_csv(output / 'cohort_manifest.csv', dtype={'sha256': str})
            self.assertEqual(result['unique_sha256'], 24)
            self.assertEqual(len(manifest), 24)
            self.assertEqual(manifest.sha256.nunique(), 24)
            self.assertEqual(set(manifest.outer_fold), {0, 1, 2})
            for _, group in manifest.groupby('outer_fold'):
                self.assertEqual(set(group.label), {0, 1})

    def test_vt_static_extractor_uses_structural_allowlist(self):
        response = {'data': {'attributes': {
            'sha256': 'a' * 64, 'size': 1000, 'type_tag': 'peexe',
            'last_analysis_stats': {'malicious': 99},
            'popular_threat_classification': {'suggested_threat_label': 'leak'},
            'pe_info': {
                'entry_point': 100, 'machine_type': 332,
                'sections': [{'name': '.text', 'entropy': 5, 'raw_size': 100,
                              'virtual_size': 120, 'chi2': 30, 'flags': 'rx'}],
                'import_list': [{'library_name': 'kernel32.dll',
                                 'imported_functions': ['CreateFileW']}],
            },
        }}}
        features = safe_static_features(response)
        self.assertGreater(len(features), 100)
        self.assertTrue(all(name.startswith('s_') for name in features))
        self.assertNotIn(99, features.values())

    def test_temporal_fusion_end_to_end_replays_observed_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            al, temporal, output = root / 'al', root / 'temporal', root / 'fusion'
            al.mkdir()
            temporal.mkdir()
            (al / 'config.json').write_text(json.dumps({
                'kind': 'active_learning', 'rounds': 0,
                'dataset': {'data_sha256': 'fixture-dataset'},
            }))
            labels = np.array([0, 1, 0, 1, 0, 1, 0, 1])
            splits = ['validation'] * 4 + ['test'] * 4
            static = np.array([.1, .8, .2, .7, .15, .75, .25, .65])
            predictions = pd.DataFrame({
                'row_id': np.arange(8), 'label': labels, 'split': splits,
                'seed': 11, 'method': 'XAI_full', 'round': 0,
                'probability': static,
            })
            predictions.to_csv(al / 'predictions.csv.gz', index=False)
            rows = []
            for row_id in range(8):
                report = temporal / f'report_{row_id}.json'
                report.write_text(json.dumps({'row_id': row_id, 'events': []}))
                for step, elapsed in enumerate([5., 15.]):
                    rows.append({
                        'row_id': row_id, 'execution_id': f'run_{row_id}',
                        'time_step': step, 'elapsed_seconds': elapsed,
                        'p_dynamic': float(.2 + .5 * ((row_id + step) % 3) / 2),
                        'evidence_status': 'observed',
                        'report_path': report.name, 'report_sha256': sha256(report),
                    })
            measurements = temporal / 'dynamic_time_series.csv'
            pd.DataFrame(rows).to_csv(measurements, index=False)
            provenance = temporal / 'provenance.json'
            provenance.write_text(json.dumps({
                'signal_origin': 'observed', 'no_target_label_in_score': True,
                'dataset_sha256': 'fixture-dataset',
                'measurements_sha256': sha256(measurements),
                'label_definition': 'fixture', 'dynamic_feature_definition': 'fixture events',
                'dynamic_score_definition': 'fixed fixture scorer',
                'dynamic_model_training_source': 'independent fixture',
                'calibration_method': 'none fixture', 'sandbox_or_honeypot': 'fixture',
                'collection_period': 'fixture', 'observation_windows_seconds': [5., 15.],
            }))
            result = run_temporal_fusion(al, measurements, provenance, output, target_tpr=.5)
            self.assertEqual(result['status'], 'measured_from_observed_temporal_reports')
            verified = json.loads((output / 'verification.json').read_text())
            self.assertEqual(verified['status'], 'passed')
            self.assertEqual(set(pd.read_csv(output / 'fusion_metrics.csv').fusion),
                             {'Static_only', 'Dynamic_only', 'Average_50_50',
                              'Fixed_weight', 'P', 'PI', 'PID'})

    def test_verified_identity_manifest_is_bound_to_rows_labels_and_features(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data, manifest = root / 'data.csv', root / 'manifest.csv'
            frame = pd.DataFrame({'0': np.arange(20, dtype=float),
                                  '1': np.arange(20, dtype=float) / 3,
                                  'label': [0, 1] * 10})
            frame.to_csv(data, index=False)
            hashes = [hashlib.sha256(np.asarray(row, dtype='<f4').tobytes()).hexdigest()
                      for row in frame[['0', '1']].to_numpy()]
            pd.DataFrame({'row_id': np.arange(20), 'label': frame.label,
                          'sha256': [f'{index:064x}' for index in range(20)],
                          'source_feature_float32_sha256': hashes}).to_csv(manifest, index=False)
            loaded = load_dataset(data, row_manifest=manifest)
            self.assertEqual(loaded.audit['provenance_status'], 'verified_static_identity')
            self.assertEqual(loaded.audit['unique_sha256'], 20)
            self.assertIsNotNone(loaded.identity_manifest)

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

    def test_ember_recovery_preserves_feature_label_and_sha_alignment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data, output = root / 'ember', root / 'out'
            data.mkdir()
            labels = np.asarray([0] * 10 + [1] * 5, dtype='<f4')
            features = np.arange(len(labels) * 3, dtype='<f4').reshape(len(labels), 3)
            labels.tofile(data / 'y_test.dat')
            features.tofile(data / 'X_test.dat')
            with (data / 'test_features.jsonl').open('w') as stream:
                for index, label in enumerate(labels.astype(int)):
                    stream.write(json.dumps({
                        'sha256': f'{index:064x}', 'appeared': '2018-01',
                        'label': int(label), 'avclass': 'family' if label else None,
                    }) + '\n')
            report = recover_ember_dataset(data, output, n_negative=4, n_positive=2,
                                           seed=42, features=3)
            self.assertEqual(report['status'], 'ember_dataset_recovered')
            self.assertEqual(report['output']['metadata_labels_matching'], 6)
            manifest = pd.read_csv(output / 'ember_row_manifest.csv', dtype={'sha256': str})
            mini = pd.read_csv(output / 'ember_mini_dataset.csv')
            self.assertEqual(manifest.sha256.tolist(), [f'{index:064x}' for index in manifest.source_index])
            np.testing.assert_array_equal(manifest.label, mini.label)
            np.testing.assert_allclose(mini.drop(columns='label').to_numpy(), features[manifest.source_index])


if __name__ == '__main__':
    unittest.main()
