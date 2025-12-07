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


_DECIMAL_INF = Decimal("Infinity")


def _random_candidate_global(rng: random.Random) -> ParameterTuple:
    """Generate a random candidate within broad bounds (global exploration)."""
    b1 = rng.uniform(0.0, 20.0)
    b2 = rng.uniform(-20.0, 20.0)
    b3 = rng.uniform(-20.0, 20.0)
    b4 = rng.uniform(-20.0, 20.0)
    l1 = rng.uniform(0.1, 5.0)
    l2 = rng.uniform(0.1, 5.0)
    return (b1, b2, b3, b4, l1, l2)


def _init_population_from_scratch(
    pop_size: int, initial_params: ParameterTuple, rng: random.Random
) -> List[ParameterTuple]:
    """Population = [initial_params] + (pop_size-1) global random candidates."""
    population: List[ParameterTuple] = [initial_params]
    for _ in range(pop_size - 1):
        population.append(_random_candidate_global(rng))
    return population


def _init_population_from_current_result(
    pop_size: int,
    initial_params: ParameterTuple,
    rng: random.Random,
    beta_jitter_levels: Sequence[float] = (0.02, 0.05, 0.10, 0.20, 0.40),
    lambda_jitter_levels: Sequence[float] = (0.05, 0.10, 0.20, 0.40),
    global_injection_rate: float = 0.10,
) -> List[ParameterTuple]:
    """
    Population = [initial_params] + mostly local perturbations around it.

    - Betas get additive relative jitter: b += u(-lvl, +lvl) * scale
    - Lambdas get multiplicative jitter: l *= (1 + u(-lvl, +lvl)), clamped > 0
    - A small fraction is injected globally to help escape local minima.
    """
    population: List[ParameterTuple] = [initial_params]

    for _ in range(pop_size - 1):
        # small global injection to avoid getting stuck, but not "mostly from scratch"
        if rng.random() < global_injection_rate:
            population.append(_random_candidate_global(rng))
            continue

        b1, b2, b3, b4, l1, l2 = initial_params

        # Betas: additive jitter
        betas = []
        for base in (b1, b2, b3, b4):
            lvl = rng.choice(tuple(beta_jitter_levels))
            scale = max(abs(base), 1.0)
            betas.append(base + rng.uniform(-lvl, lvl) * scale)

        # Lambdas: multiplicative jitter, enforce positivity
        lambdas = []
        for base in (l1, l2):
            base_pos = max(float(base), 1e-6)
            lvl = rng.choice(tuple(lambda_jitter_levels))
            val = base_pos * (1.0 + rng.uniform(-lvl, lvl))
            lambdas.append(max(val, 1e-6))

        population.append((betas[0], betas[1], betas[2], betas[3], lambdas[0], lambdas[1]))

    return population


def _run_ga_then_local_search(
    current_date: object,
    initial_params: ParameterTuple,
    objective_func: ObjectiveFunc,
    *,
    pop_size: int,
    generations: int,
    mutation_rate: float,
    strategy_label: str,
    population_initializer: Callable[[int, ParameterTuple, random.Random], List[ParameterTuple]],
) -> Optional[OptimizationResult]:
    """
    Shared GA loop + local refinement for hybrid strategies.
    Only the population initialization differs between strategies.
    """
    rng = random.Random()

    # Early fail if we can't evaluate at the starting point
    initial_obj = _evaluate_objective(objective_func, current_date, initial_params)
    if initial_obj is None:
        return None

    best_obj = initial_obj
    best_params = list(initial_params)
    iterations = 0

    # Initialize population
    population = population_initializer(pop_size, initial_params, rng)
    if not population or population[0] != initial_params:
        # ensure initial_params is present and first (elitism starts from it nicely)
        population = [initial_params] + [p for p in population if p != initial_params]
        population = population[:pop_size]

    # Evaluate initial population fitness (reuse initial_obj for initial_params)
    fitness: List[Tuple[ParameterTuple, Decimal]] = [(initial_params, initial_obj)]
    iterations += 1

    for params in population[1:]:
        obj = _evaluate_objective(objective_func, current_date, params)
        iterations += 1
        if obj is None:
            fitness.append((params, _DECIMAL_INF))
        else:
            fitness.append((params, obj))
            if obj < best_obj:
                best_obj = obj
                best_params = list(params)

    # Evolve
    for _ in range(generations):
        fitness.sort(key=lambda x: x[1])
        parents = fitness[: max(1, len(fitness) // 2)]

        elite_params, elite_obj = parents[0]  # keep best without re-evaluating

        new_population: List[ParameterTuple] = [elite_params]
        while len(new_population) < pop_size:
            p1 = rng.choice(parents)[0]
            p2 = rng.choice(parents)[0]

            child: List[float] = []
            for idx in range(6):
                val = p1[idx] if rng.random() < 0.5 else p2[idx]

                # Mutation: small perturbation
                if rng.random() < mutation_rate:
                    if idx < 4:
                        base = abs(val) if abs(val) > 1e-6 else 1.0
                        val += rng.uniform(-0.02, 0.02) * base
                    else:
                        base = abs(val) if abs(val) > 1e-6 else 1e-6
                        val += rng.uniform(-0.10, 0.10) * base

                child.append(float(val))

            # Enforce λ1, λ2 > 0
            child[4] = max(child[4], 1e-6)
            child[5] = max(child[5], 1e-6)
            new_population.append(tuple(child))  # type: ignore[arg-type]

        # Evaluate new population (reuse elite objective)
        new_fitness: List[Tuple[ParameterTuple, Decimal]] = [(elite_params, elite_obj)]
        for params in new_population[1:]:
            obj = _evaluate_objective(objective_func, current_date, params)
            iterations += 1
            if obj is None:
                new_fitness.append((params, _DECIMAL_INF))
            else:
                new_fitness.append((params, obj))
                if obj < best_obj:
                    best_obj = obj
                    best_params = list(params)

        fitness = new_fitness

    # Refine with local search
    local_result = _local_search_strategy(current_date, tuple(best_params), objective_func)
    if local_result is not None:
        best_params = list(local_result.best_params)
        best_obj = local_result.best_objective
        iterations += local_result.iterations

    return OptimizationResult(
        best_params=tuple(best_params),  # type: ignore[arg-type]
        best_objective=best_obj,
        iterations=iterations,
        strategy=strategy_label,
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
    Hybrid genetic algorithm (global init) followed by local search.
    """
    return _run_ga_then_local_search(
        current_date,
        initial_params,
        objective_func,
        pop_size=pop_size,
        generations=generations,
        mutation_rate=mutation_rate,
        strategy_label="hybrid_search",
        population_initializer=_init_population_from_scratch,
    )


def _hybrid_strategy_from_current_result(
    current_date: object,
    initial_params: ParameterTuple,
    objective_func: ObjectiveFunc = calculate_objective_function,
    pop_size: int = 20,
    generations: int = 5,
    mutation_rate: float = 0.1,
) -> Optional[OptimizationResult]:
    """
    Hybrid genetic algorithm (local init around initial_params) followed by local search.

    The initial population is mostly random variations around initial_params
    (plus a small global injection), instead of being mostly "from scratch".
    """
    return _run_ga_then_local_search(
        current_date,
        initial_params,
        objective_func,
        pop_size=pop_size,
        generations=generations,
        mutation_rate=mutation_rate,
        strategy_label="hybrid_search_from_current_result",
        population_initializer=lambda ps, ip, rng: _init_population_from_current_result(ps, ip, rng),
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


# Register default strategies
register_strategy("local_search", _local_search_strategy)
register_strategy("hybrid_search", _hybrid_strategy)
register_strategy("hybrid_search_from_current_result", _hybrid_strategy_from_current_result)
