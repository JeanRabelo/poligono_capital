import numpy as np
from dataclasses import dataclass
from scipy.optimize import least_squares, differential_evolution, brentq

# -----------------------------
# Svensson curve + pricing
# -----------------------------
def svensson_zero_rate(T, beta0, beta1, beta2, beta3, tau1, tau2):
    """Svensson zero rate r(T), params in decimals (0.12 = 12%), T in years."""
    T = np.asarray(T, dtype=float)
    eps = 1e-12
    x1 = np.maximum(T / (tau1 + eps), eps)
    x2 = np.maximum(T / (tau2 + eps), eps)

    phi1 = (1.0 - np.exp(-x1)) / x1
    phi2 = phi1 - np.exp(-x1)
    phi3 = (1.0 - np.exp(-x2)) / x2 - np.exp(-x2)
    return beta0 + beta1 * phi1 + beta2 * phi2 + beta3 * phi3

def discount_factor_from_zero(T, r, comp="annual"):
    """
    annual: b(T)=(1+r)^(-T)  (close to the algebra ANBIMA presents)
    continuous: b(T)=exp(-rT)
    """
    T = np.asarray(T, dtype=float)
    r = np.asarray(r, dtype=float)
    if comp == "continuous":
        return np.exp(-r * T)
    if comp == "annual":
        # avoid invalid (1+r)<=0 (optimizer WILL try crazy params otherwise)
        if np.any(1.0 + r <= 1e-10):
            return np.full_like(r, np.nan, dtype=float)
        return np.power(1.0 + r, -T)
    raise ValueError("comp must be 'annual' or 'continuous'")

@dataclass(frozen=True)
class Bond:
    """You provide times/cashflows and observed (indicative) price."""
    name: str
    times: np.ndarray  # (K,)
    cfs: np.ndarray    # (K,)
    price: float       # observed price, e.g. per 100 notional

def price_from_curve(bond: Bond, theta, comp="annual") -> float:
    beta0, beta1, beta2, beta3, tau1, tau2 = theta
    r = svensson_zero_rate(bond.times, beta0, beta1, beta2, beta3, tau1, tau2)
    df = discount_factor_from_zero(bond.times, r, comp=comp)
    if not np.all(np.isfinite(df)):
        return np.nan
    return float(np.dot(bond.cfs, df))

# -----------------------------
# ANBIMA weights Wi = 1/Duration_i
# -----------------------------
def pv_from_yield(times, cfs, y, comp="annual"):
    if comp == "continuous":
        df = np.exp(-y * times)
    else:
        if 1.0 + y <= 1e-10:
            return np.inf
        df = np.power(1.0 + y, -times)
    return float(np.dot(cfs, df))

def ytm_from_price(times, cfs, price, comp="annual") -> float:
    """Solve y such that PV(y)=price. Robust root find."""
    def f(y): return pv_from_yield(times, cfs, y, comp=comp) - price
    lo, hi = -0.95, 5.0  # -95% to 500% (widen if you need)
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        hi2 = 20.0
        if flo * f(hi2) > 0:
            raise ValueError("Could not bracket YTM root; check cashflows/price.")
        hi = hi2
    return float(brentq(f, lo, hi, maxiter=200))

def macaulay_duration(times, cfs, y, price, comp="annual") -> float:
    if comp == "continuous":
        df = np.exp(-y * times)
    else:
        df = np.power(1.0 + y, -times)
    pv_cf = cfs * df
    return float(np.dot(times, pv_cf) / price)

def anbima_weights(bonds, comp="annual"):
    w = []
    for b in bonds:
        y = ytm_from_price(b.times, b.cfs, b.price, comp=comp)
        D = macaulay_duration(b.times, b.cfs, y, b.price, comp=comp)
        w.append(1.0 / max(D, 1e-8))
    return np.array(w, dtype=float)

# -----------------------------
# Calibration objectives
# -----------------------------
def residuals_weighted(theta, bonds, w, comp="annual"):
    """sqrt(w_i)*(P_obs - P_model). Finite penalties for invalid params."""
    theta = np.asarray(theta, dtype=float)
    res = np.empty(len(bonds), dtype=float)
    for i, b in enumerate(bonds):
        p_hat = price_from_curve(b, theta, comp=comp)
        res[i] = 1e6 if not np.isfinite(p_hat) else np.sqrt(w[i]) * (b.price - p_hat)
    return res

# -----------------------------
# 1) Lambda-fixo: fix taus, fit betas
# -----------------------------
def calibrate_fixed_taus(
    bonds, tau1, tau2, comp="annual",
    beta_init=(0.10, -0.05, 0.02, 0.01),
    beta_bounds=((-0.5,-1.0,-1.0,-1.0),(0.8,1.0,1.0,1.0))
):
    w = anbima_weights(bonds, comp=comp)

    def fun_b(betas):
        theta = np.array([betas[0], betas[1], betas[2], betas[3], tau1, tau2], dtype=float)
        return residuals_weighted(theta, bonds, w, comp=comp)

    lb, ub = np.array(beta_bounds[0]), np.array(beta_bounds[1])
    sol = least_squares(fun_b, x0=np.array(beta_init), bounds=(lb, ub), max_nfev=8000)

    theta = np.array([*sol.x, tau1, tau2], dtype=float)
    unweighted = residuals_weighted(theta, bonds, w, comp=comp) / np.sqrt(w)
    rmse = float(np.sqrt(np.mean(unweighted**2)))
    return theta, rmse, bool(sol.success)

# -----------------------------
# 2) All-6: "GA-like" global search then local refinement
# -----------------------------
def calibrate_all6_ga_then_local(
    bonds, comp="annual",
    bounds=((0.0, 0.5), (-0.5,0.5), (-0.5,0.5), (-0.5,0.5), (0.05, 10.0), (0.05, 15.0)),
    seed=7
):
    w = anbima_weights(bonds, comp=comp)

    def sse(theta):
        r = residuals_weighted(theta, bonds, w, comp=comp)
        return float(np.dot(r, r))

    # population-based global search (good stand-in for a GA)
    de = differential_evolution(sse, bounds=bounds, seed=seed, maxiter=250, popsize=18, tol=1e-7, polish=False)

    theta0 = de.x
    lb = np.array([b[0] for b in bounds], dtype=float)
    ub = np.array([b[1] for b in bounds], dtype=float)

    # local weighted least squares refinement
    ls = least_squares(lambda th: residuals_weighted(th, bonds, w, comp=comp),
                       x0=theta0, bounds=(lb, ub), max_nfev=12000)

    theta = ls.x
    unweighted = residuals_weighted(theta, bonds, w, comp=comp) / np.sqrt(w)
    rmse = float(np.sqrt(np.mean(unweighted**2)))
    return theta, rmse, bool(ls.success)

# -----------------------------
# Example usage (you replace this with real ANBIMA cashflows/prices)
# -----------------------------
if __name__ == "__main__":
    def make_coupon_bond(name, maturity_years, coupon_rate, freq=2, notional=100.0):
        n = int(np.round(maturity_years * freq))
        times = np.arange(1, n + 1) / freq
        cfs = np.full_like(times, notional * coupon_rate / freq, dtype=float)
        cfs[-1] += notional
        return Bond(name, times, cfs, price=np.nan)

    # Suppose you already filled observed prices:
    bonds = []
    for T in [0.5, 1, 2, 3, 5, 7, 10]:
        b = make_coupon_bond(f"B{T}Y", T, coupon_rate=0.10)
        # TODO: set b.price = your observed indicative price
        # bonds.append(Bond(b.name, b.times, b.cfs, price=your_price))
        pass

    theta_fixed, rmse_fixed, ok = calibrate_fixed_taus(bonds, tau1=1.2, tau2=4.5)
    theta_all6, rmse_all6, ok = calibrate_all6_ga_then_local(bonds)


import numpy as np
import matplotlib.pyplot as plt

def plot_zero_curves_and_ytm_points(bonds, labeled_thetas, comp="annual"):
    Tmax = max(float(b.times.max()) for b in bonds)
    T_grid = np.linspace(1/252, Tmax, 600)

    plt.figure()
    for label, theta in labeled_thetas.items():
        r = svensson_zero_rate(T_grid, *theta)
        plt.plot(T_grid, 100 * r, label=label)  # % p.a.

    mats = np.array([float(b.times.max()) for b in bonds])
    ytm_mkt = np.array([ytm_from_price(b.times, b.cfs, b.price, comp=comp) for b in bonds]) * 100
    plt.scatter(mats, ytm_mkt, label="Market YTM (bonds)")

    plt.xlabel("Maturity (years)")
    plt.ylabel("Rate (% p.a.)")
    plt.title("Svensson zero curve(s) + observed bond YTMs")
    plt.grid(True, alpha=0.3)
    plt.legend()

def plot_price_fit(bonds, labeled_thetas, comp="annual"):
    p_mkt = np.array([b.price for b in bonds], dtype=float)

    plt.figure()
    for label, theta in labeled_thetas.items():
        p_model = np.array([price_from_curve(b, theta, comp=comp) for b in bonds], dtype=float)
        plt.scatter(p_mkt, p_model, label=label)

    lo = float(np.nanmin(p_mkt))
    hi = float(np.nanmax(p_mkt))
    plt.plot([lo, hi], [lo, hi], label="Perfect fit (45° line)")

    plt.xlabel("Market (indicative) price")
    plt.ylabel("Model price")
    plt.title("How well the curve prices the instruments")
    plt.grid(True, alpha=0.3)
    plt.legend()

# ---- call these after calibration ----
labeled = {
    "Fit (tau fixed)": theta_fixed,
    "Fit (all 6: global+local)": theta_all6,
}

plot_zero_curves_and_ytm_points(bonds, labeled, comp="annual")
plot_price_fit(bonds, labeled, comp="annual")
plt.show()
