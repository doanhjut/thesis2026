import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.experiments.common import choose_threshold, evaluate, load_dataset
from src.experiments.fidelity import mask_metrics
from src.experiments.fusion import sequence_scores
from src.experiments.signals import normalize, shap_signals
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


if __name__ == '__main__':
    unittest.main()
