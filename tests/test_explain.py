"""SHAP must explain the FITTED trees inside a calibrated model, not the unfitted template."""
import unittest

import numpy as np

from tests._helpers import has_modules

from sklearn.calibration import CalibratedClassifierCV
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.validation import check_is_fitted


def _data(n=120, k=6, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    y = (X[:, 0] + 0.5 * X[:, 1] + rng.normal(scale=0.5, size=n) > 0).astype(int)
    return X, y


class TreeUnwrapTests(unittest.TestCase):
    def test_calibrated_model_yields_its_fitted_fold_estimators(self):
        from backend.cdss.explain import tree_estimators
        X, y = _data()
        model = CalibratedClassifierCV(DecisionTreeClassifier(max_depth=3), method="sigmoid", cv=3).fit(X, y)
        trees = tree_estimators(model)
        self.assertEqual(len(trees), 3)
        for t in trees:
            check_is_fitted(t)  # raises if we got the unfitted template

    def test_plain_model_is_returned_as_is(self):
        from backend.cdss.explain import tree_estimators
        X, y = _data()
        tree = DecisionTreeClassifier(max_depth=3).fit(X, y)
        self.assertEqual(tree_estimators(tree), [tree])


class PositiveClassTests(unittest.TestCase):
    def test_list_output_takes_positive_class(self):
        from backend.cdss.explain import positive_class_values
        neg, pos = np.zeros((1, 3)), np.ones((1, 3))
        np.testing.assert_array_equal(positive_class_values([neg, pos]), pos)

    def test_three_dimensional_output_takes_positive_class(self):
        from backend.cdss.explain import positive_class_values
        values = np.stack([np.zeros((1, 3)), np.ones((1, 3))], axis=-1)  # (rows, features, classes)
        np.testing.assert_array_equal(positive_class_values(values), np.ones((1, 3)))

    def test_two_dimensional_output_is_unchanged(self):
        from backend.cdss.explain import positive_class_values
        values = np.arange(3.0).reshape(1, 3)
        np.testing.assert_array_equal(positive_class_values(values), values)


@unittest.skipUnless(has_modules("shap", "xgboost"), "needs shap + xgboost (runs on your machine)")
class ShapIntegrationTests(unittest.TestCase):
    def test_calibrated_xgboost_gets_real_drivers(self):
        from xgboost import XGBClassifier
        from backend.cdss.explain import compute_shap_drivers
        X, y = _data()
        model = CalibratedClassifierCV(XGBClassifier(n_estimators=20, max_depth=2), method="sigmoid", cv=3).fit(X, y)
        names = [f"f{i}" for i in range(X.shape[1])]
        drivers = compute_shap_drivers(model, X[:1], names)
        self.assertEqual(len(drivers), 5)
        self.assertNotIn("SHAP Unavailable", [d["display_name"] for d in drivers])


if __name__ == "__main__":
    unittest.main()
