import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.db.models.signals import post_save
from django.test import Client, TestCase

from .models import LinearAttempt
from .optimizers import OptimizationResult, optimize_parameters
from .signals import calculate_rmse_on_save


class OptimizerTests(TestCase):
    def test_local_search_improves_simple_quadratic(self):
        base_params = (0.0, 0.0, 0.0, 0.0, 1.0, 1.0)
        target_params = (0.5, -0.25, 0.1, 0.05, 1.1, 0.9)

        def quadratic_objective(_date, b0, b1, b2, b3, l1, l2):
            values = (b0, b1, b2, b3, l1, l2)
            return Decimal(
                str(sum((param - target) ** 2 for param, target in zip(values, target_params)))
            )

        baseline = quadratic_objective(date.today(), *base_params)
        result = optimize_parameters(
            date.today(),
            base_params,
            strategy_name="local_search",
            objective_func=quadratic_objective,
        )

        self.assertIsNotNone(result)
        self.assertLess(result.best_objective, baseline)


class ImproveAttemptViewTests(TestCase):
    def setUp(self):
        post_save.disconnect(calculate_rmse_on_save, sender=LinearAttempt)
        self.attempt = LinearAttempt.objects.create(
            date=date.today(),
            beta0_initial=Decimal("0.1"),
            beta1_initial=Decimal("0.1"),
            beta2_initial=Decimal("0.1"),
            beta3_initial=Decimal("0.1"),
            lambda1_initial=Decimal("1.0"),
            lambda2_initial=Decimal("1.0"),
        )
        self.client = Client()

    def tearDown(self):
        post_save.connect(calculate_rmse_on_save, sender=LinearAttempt)

    @patch("svensson_estimates.views.calculate_objective_function")
    @patch("svensson_estimates.views.optimize_parameters")
    def test_improve_attempt_updates_final_parameters(self, mock_optimize, mock_objective):
        mock_objective.return_value = Decimal("10.0")
        mock_optimize.return_value = OptimizationResult(
            best_params=(0.2, 0.2, 0.2, 0.2, 1.2, 1.1),
            best_objective=Decimal("5.0"),
            iterations=5,
            strategy="local_search",
        )

        response = self.client.post(
            f"/svensson/api/attempts/{self.attempt.id}/improve/",
            data=json.dumps({"strategy": "local_search"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_optimize.called)

        self.attempt.refresh_from_db()
        self.assertAlmostEqual(float(self.attempt.beta0_final), 0.2)
        self.assertAlmostEqual(float(self.attempt.lambda1_final), 1.2)
