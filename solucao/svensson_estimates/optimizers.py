from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .utils import calculate_objective_function

ParameterTuple = Tuple[float, float, float, float, float, float]
ObjectiveFunc = Callable[[object, float, float, float, float, float, float], Optional[Decimal]]
StrategyCallable = Callable[[object, ParameterTuple, ObjectiveFunc], Optional["OptimizationResult"]]


@dataclass
class OptimizationResult:
    """Container for optimizer outputs."""

    best_params: ParameterTuple
    best_objective: Decimal
    iterations: int
    strategy: str


_STRATEGY_REGISTRY: Dict[str, StrategyCallable] = {}


def register_strategy(name: str, strategy: StrategyCallable) -> None:
    """Register an optimization strategy for later use."""
    _STRATEGY_REGISTRY[name] = strategy


def available_strategies() -> List[str]:
    """Return the list of registered strategy names."""
    return list(_STRATEGY_REGISTRY.keys())


def _evaluate_objective(
    objective_func: ObjectiveFunc, current_date: object, params: Sequence[float]
) -> Optional[Decimal]:
    """Helper to evaluate the objective function safely."""
    try:
        return objective_func(
            current_date,
            float(params[0]),
            float(params[1]),
            float(params[2]),
            float(params[3]),
            float(params[4]),
            float(params[5]),
        )
    except Exception:
        return None


def _local_search_strategy(
    current_date: object,
    initial_params: ParameterTuple,
    objective_func: ObjectiveFunc = calculate_objective_function,
    step_sequence: Sequence[float] = (0.05, 0.02, 0.01),
    max_iterations: int = 200,
) -> Optional[OptimizationResult]:
    """
    Simple deterministic coordinate search.

    Moves one parameter at a time in ± directions with progressively smaller
    step sizes. Uses relative steps so it works even when parameters are on
    different scales.
    """
    best_objective = _evaluate_objective(objective_func, current_date, initial_params)
    if best_objective is None:
        return None

    best_params: List[float] = list(initial_params)
    iterations = 0

    for step in step_sequence:
        improved = True
        while improved and iterations < max_iterations:
            improved = False
            for idx in range(len(best_params)):
                base = abs(best_params[idx]) if abs(best_params[idx]) > 1e-6 else 1.0
                for direction in (-1.0, 1.0):
                    candidate = best_params.copy()
                    candidate[idx] = candidate[idx] + direction * step * base
                    if idx in (4, 5):  # λ1 and λ2 must stay positive
                        candidate[idx] = max(1e-6, candidate[idx])

                    candidate_obj = _evaluate_objective(
                        objective_func, current_date, candidate
                    )
                    iterations += 1

                    if (
                        candidate_obj is not None
                        and candidate_obj < best_objective
                        and iterations <= max_iterations
                    ):
                        best_objective = candidate_obj
                        best_params = candidate
                        improved = True
                        break
                if improved or iterations >= max_iterations:
                    break

    return OptimizationResult(
        best_params=tuple(best_params),  # type: ignore[arg-type]
        best_objective=best_objective,
        iterations=iterations,
        strategy="local_search",
    )


def optimize_parameters(
    current_date: object,
    initial_params: ParameterTuple,
    strategy_name: str = "local_search",
    objective_func: ObjectiveFunc = calculate_objective_function,
) -> Optional[OptimizationResult]:
    """
    Optimize Svensson parameters using a registered strategy.

    Returns None when no improvement path is found or when the objective
    function cannot be evaluated.
    """
    strategy = _STRATEGY_REGISTRY.get(strategy_name)
    if strategy is None:
        raise ValueError(f"Strategy '{strategy_name}' is not registered")

    return strategy(current_date, initial_params, objective_func)


# Register default strategy
register_strategy("local_search", _local_search_strategy)
