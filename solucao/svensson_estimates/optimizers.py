from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Sequence, Tuple
import random
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

def _hybrid_strategy(
    current_date: object,
    initial_params: ParameterTuple,
    objective_func: ObjectiveFunc = calculate_objective_function,
    pop_size: int = 20,
    generations: int = 5,
    mutation_rate: float = 0.1,
) -> Optional[OptimizationResult]:
    """
    Hybrid genetic algorithm followed by local search.

    Uses a genetic algorithm (global stochastic search) to avoid local minima:contentReference[oaicite:3]{index=3}.
    This yields more stable and accurate fits:contentReference[oaicite:4]{index=4}. The best result from the GA 
    is then refined with a traditional local search for higher precision:contentReference[oaicite:5]{index=5}.
    """
    # Initial evaluation of provided starting params
    best_obj = _evaluate_objective(objective_func, current_date, initial_params)
    if best_obj is None:
        return None
    best_params = list(initial_params)
    iterations = 0

    # Initialize population (include initial_params + random candidates)
    population: List[ParameterTuple] = [initial_params]
    for _ in range(pop_size - 1):
        # Generate a random candidate within reasonable bounds
        β1 = random.uniform(0.0, 20.0)       # β1 (level) ~ [0%, 20%] 
        β2 = random.uniform(-20.0, 20.0)     # β2 (slope) ~ [-20%, 20%]
        β3 = random.uniform(-20.0, 20.0)     # β3 (curvature) ~ [-20%, 20%]
        β4 = random.uniform(-20.0, 20.0)     # β4 (curvature) ~ [-20%, 20%]
        λ1 = random.uniform(0.1, 5.0)        # λ1 > 0 (positive decay factor)
        λ2 = random.uniform(0.1, 5.0)        # λ2 > 0 (positive decay factor)
        population.append((β1, β2, β3, β4, λ1, λ2))

    # Evaluate initial population fitness
    fitness: List[Tuple[ParameterTuple, Decimal]] = []
    for params in population:
        obj = _evaluate_objective(objective_func, current_date, params)
        iterations += 1
        if obj is None:
            # Invalid candidate, assign a very high objective (penalize)
            fitness.append((params, Decimal('Infinity')))
        else:
            fitness.append((params, obj))
            if obj < best_obj:
                best_obj = obj
                best_params = list(params)

    # Evolve population over multiple generations
    for _ in range(generations):
        # Select the top half of individuals (lowest objective) as parents
        fitness.sort(key=lambda x: x[1])
        parents = fitness[: max(1, len(fitness)//2)]

        # Create new population, keeping the best individual (elitism)
        new_population: List[ParameterTuple] = [parents[0][0]]
        # Fill the rest of the population via crossover and mutation
        while len(new_population) < pop_size:
            # Randomly choose two parents
            p1 = random.choice(parents)[0]
            p2 = random.choice(parents)[0]
            # Crossover: mix parameters from p1 and p2
            child_params: List[float] = []
            for idx in range(6):
                val = p1[idx] if random.random() < 0.5 else p2[idx]
                # Mutation: small random perturbation
                if random.random() < mutation_rate:
                    # For β parameters, add a small relative noise
                    if idx < 4:
                        base = abs(val) if abs(val) > 1e-6 else 1.0
                        val += random.uniform(-0.02, 0.02) * base
                    else:
                        # For λ parameters, perturb and ensure positivity
                        val += random.uniform(-0.1, 0.1) * val
                child_params.append(val)
            # Enforce λ1, λ2 > 0
            child_params[4] = max(child_params[4], 1e-6)
            child_params[5] = max(child_params[5], 1e-6)
            new_population.append(tuple(child_params))

        # Evaluate new population
        fitness = []
        for params in new_population:
            obj = _evaluate_objective(objective_func, current_date, params)
            iterations += 1
            if obj is None:
                fitness.append((params, Decimal('Infinity')))
            else:
                fitness.append((params, obj))
                if obj < best_obj:
                    best_obj = obj
                    best_params = list(params)
        # Continue to next generation with the new population

    # After GA loop, refine best_params with local coordinate search
    local_result = _local_search_strategy(current_date, tuple(best_params), objective_func)
    if local_result is not None:
        best_params = list(local_result.best_params)
        best_obj = local_result.best_objective
        iterations += local_result.iterations

    return OptimizationResult(
        best_params=tuple(best_params),
        best_objective=best_obj,
        iterations=iterations,
        strategy="hybrid_search",
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
register_strategy("hybrid_search", _hybrid_strategy)
