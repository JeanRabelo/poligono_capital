"""
ANBIMA-style Svensson (Nelson–Siegel–Svensson) calibration demo
==============================================================

What this script includes
- Cashflow pricing off a Svensson zero curve
- ANBIMA-style weights: Wi = 1 / Duration_i (duration computed from each bond's own YTM)
- Two calibration regimes:
    (A) "Lambda-fixo": fix tau1,tau2 and fit betas via nonlinear least squares
    (B) "GA + local refinement": global population search (differential evolution) then local least squares
- Three charts:
    1) Zero curve(s) + observed bond YTMs
    2) Market price vs model price (with 45° perfect-fit line)
    3) Price residuals vs maturity

How to plug in your real data
- Build `bonds` as a list of Bond(name, times_years, cashflows, observed_price)
- If you want true ANBIMA conventions, compute times_years with 252 business-day year fractions + B3 holiday calendar.
"""

from dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import least_squares, differential_evolution, brentq


# -----------------------------
# Svensson curve + discounting
# -----------------------------
def svensson_zero_rate(T, beta0, beta1, beta2, beta3, tau1, tau2):
    """
    Svensson zero rate r(T), params in decimals (0.12 = 12%), T in years.
    """
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
    Convert zero rates to discount factors.
    - comp="annual": b(T) = (1+r)^(-T)
    - comp="continuous": b(T) = exp(-r*T)
    """
    T = np.asarray(T, dtype=float)
    r = np.asarray(r, dtype=float)

    if comp == "continuous":
        return np.exp(-r * T)

    if comp == "annual":
        # Protect the optimizer: invalid (1+r) <= 0 yields NaNs/complex
        if np.any(1.0 + r <= 1e-10):
            return np.full_like(r, np.nan, dtype=float)
        return np.power(1.0 + r, -T)

    raise ValueError("comp must be 'annual' or 'continuous'")


# -----------------------------
# Bond container + pricing
# -----------------------------
@dataclass(frozen=True)
class Bond:
    """
    times: cashflow times in years (float array)
    cfs:   cashflow amounts (float array)
    price: observed (indicative) price in the same unit as PV (e.g., per 100 notional)
    """
    name: str
    times: np.ndarray
    cfs: np.ndarray
    price: float


def price_from_curve(bond: Bond, theta, comp="annual") -> float:
    beta0, beta1, beta2, beta3, tau1, tau2 = theta
    r = svensson_zero_rate(bond.times, beta0, beta1, beta2, beta3, tau1, tau2)
    df = discount_factor_from_zero(bond.times, r, comp=comp)
    if not np.all(np.isfinite(df)):
        return np.nan
    return float(np.dot(bond.cfs, df))


# -----------------------------
# ANBIMA weights Wi = 1/Duration
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
    """
    Solve y such that PV(y)=price using robust bracketing.
    """
    def f(y): 
        return pv_from_yield(times, cfs, y, comp=comp) - price

    lo, hi = -0.95, 5.0  # widen if needed
    flo, fhi = f(lo), f(hi)

    if flo * fhi > 0:
        hi2 = 20.0
        fhi2 = f(hi2)
        if flo * fhi2 > 0:
            raise ValueError("Could not bracket YTM root. Check cashflows/price.")
        hi = hi2

    return float(brentq(f, lo, hi, maxiter=200))


def macaulay_duration(times, cfs, y, price, comp="annual") -> float:
    """
    Macaulay duration in years, computed consistently with compounding.
    """
    if comp == "continuous":
        df = np.exp(-y * times)
    else:
        df = np.power(1.0 + y, -times)
    pv_cf = cfs * df
    return float(np.dot(times, pv_cf) / price)


def anbima_weights(bonds, comp="annual"):
    """
    ANBIMA-style weight: Wi = 1 / Duration_i
    """
    w = []
    for b in bonds:
        y = ytm_from_price(b.times, b.cfs, b.price, comp=comp)
        D = macaulay_duration(b.times, b.cfs, y, b.price, comp=comp)
        w.append(1.0 / max(D, 1e-8))
    return np.array(w, dtype=float)


# -----------------------------
# Calibration residuals/objectives
# -----------------------------
def residuals_weighted(theta, bonds, w, comp="annual"):
    """
    Residual vector: sqrt(Wi) * (P_obs - P_model)
    Uses a finite penalty when theta implies invalid discount factors.
    """
    theta = np.asarray(theta, dtype=float)
    res = np.empty(len(bonds), dtype=float)
    for i, b in enumerate(bonds):
        p_hat = price_from_curve(b, theta, comp=comp)
        res[i] = 1e6 if not np.isfinite(p_hat) else np.sqrt(w[i]) * (b.price - p_hat)
    return res


# -----------------------------
# Calibrator A: fix taus (lambda-fixo style) and fit betas
# -----------------------------
def calibrate_fixed_taus(
    bonds, tau1, tau2, comp="annual",
    beta_init=(0.10, -0.05, 0.02, 0.01),
    beta_bounds=((-0.5,-1.0,-1.0,-1.0),(0.8,1.0,1.0,1.0))
):
    """
    Given fixed tau1,tau2, fit betas by weighted nonlinear least squares.
    """
    w = anbima_weights(bonds, comp=comp)

    def fun_b(betas):
        theta = np.array([betas[0], betas[1], betas[2], betas[3], tau1, tau2], dtype=float)
        return residuals_weighted(theta, bonds, w, comp=comp)

    lb, ub = np.array(beta_bounds[0]), np.array(beta_bounds[1])
    sol = least_squares(fun_b, x0=np.array(beta_init), bounds=(lb, ub), max_nfev=8000)

    theta = np.array([*sol.x, tau1, tau2], dtype=float)
    unweighted = residuals_weighted(theta, bonds, w, comp=comp) / np.sqrt(w)
    rmse = float(np.sqrt(np.mean(unweighted**2)))

    return theta, rmse, bool(sol.success), sol.message


# -----------------------------
# Calibrator B: "GA-like" global + local refinement (ANBIMA idea)
# -----------------------------
def calibrate_all6_ga_then_local(
    bonds, comp="annual",
    bounds=((0.0, 0.5), (-0.5,0.5), (-0.5,0.5), (-0.5,0.5), (0.05, 10.0), (0.05, 15.0)),
    seed=7
):
    """
    Global population search (differential evolution) + local least squares refinement.
    """
    w = anbima_weights(bonds, comp=comp)

    def sse(theta):
        r = residuals_weighted(theta, bonds, w, comp=comp)
        return float(np.dot(r, r))

    de = differential_evolution(
        sse,
        bounds=bounds,
        seed=seed,
        maxiter=250,
        popsize=18,
        tol=1e-7,
        polish=False,
    )

    theta0 = de.x
    lb = np.array([b[0] for b in bounds], dtype=float)
    ub = np.array([b[1] for b in bounds], dtype=float)

    ls = least_squares(
        lambda th: residuals_weighted(th, bonds, w, comp=comp),
        x0=theta0,
        bounds=(lb, ub),
        max_nfev=12000
    )

    theta = ls.x
    unweighted = residuals_weighted(theta, bonds, w, comp=comp) / np.sqrt(w)
    rmse = float(np.sqrt(np.mean(unweighted**2)))

    return theta, rmse, bool(ls.success), ls.message


# -----------------------------
# Charting
# -----------------------------
def plot_zero_curves_and_ytm_points(bonds, labeled_thetas, comp="annual"):
    Tmax = max(float(b.times.max()) for b in bonds)
    T_grid = np.linspace(1/252, Tmax, 600)

    plt.figure()
    for label, theta in labeled_thetas.items():
        r = svensson_zero_rate(T_grid, *theta)
        plt.plot(T_grid, 100 * r, label=label)  # % p.a.

    # Observed points: bond YTMs plotted at final cashflow maturity
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


def plot_residuals_vs_maturity(bonds, labeled_thetas, comp="annual"):
    mats = np.array([float(b.times.max()) for b in bonds])
    p_mkt = np.array([b.price for b in bonds], dtype=float)

    plt.figure()
    for label, theta in labeled_thetas.items():
        p_model = np.array([price_from_curve(b, theta, comp=comp) for b in bonds], dtype=float)
        resid = p_mkt - p_model
        plt.scatter(mats, resid, label=label)

    plt.axhline(0.0, label="Zero error")
    plt.xlabel("Maturity (years)")
    plt.ylabel("Price residual (Market - Model)")
    plt.title("Pricing residuals vs maturity (where the fit is worst)")
    plt.grid(True, alpha=0.3)
    plt.legend()


# -----------------------------
# Demo dataset (replace with real data)
# -----------------------------
def make_coupon_bond(name, maturity_years, coupon_rate, freq=2, notional=100.0):
    """
    Simple fixed-rate coupon bond (demo).
    For real ANBIMA replication, build the exact schedules for LTN/NTN-F/NTN-B.
    """
    n = int(np.round(maturity_years * freq))
    times = np.arange(1, n + 1) / freq
    cfs = np.full_like(times, notional * coupon_rate / freq, dtype=float)
    cfs[-1] += notional
    return times, cfs


def demo_bonds_from_true_curve(seed=0, comp="annual"):
    """
    Creates a synthetic "market" dataset so the script runs end-to-end.
    """
    rng = np.random.default_rng(seed)
    theta_true = np.array([0.12, -0.08, 0.03, 0.02, 1.2, 4.5], dtype=float)

    bonds = []
    for T in [0.5, 1, 2, 3, 5, 7, 10, 15]:
        times, cfs = make_coupon_bond(f"B{T}Y", float(T), coupon_rate=0.10, freq=2)
        p_true = price_from_curve(Bond(f"B{T}Y", times, cfs, 0.0), theta_true, comp=comp)
        p_obs = p_true * (1.0 + rng.normal(0, 0.0008))  # small noise
        bonds.append(Bond(f"B{T}Y", times, cfs, float(p_obs)))

    return bonds, theta_true


# -----------------------------
# Main
# -----------------------------
def main():
    comp = "annual"  # set to "continuous" if you prefer exp(-rT)

    # --- replace this block with your real bonds/prices ---
    bonds, theta_true = demo_bonds_from_true_curve(seed=0, comp=comp)

    # Calibrate
    theta_fixed, rmse_fixed, ok_fixed, msg_fixed = calibrate_fixed_taus(
        bonds, tau1=1.2, tau2=4.5, comp=comp
    )
    theta_all6, rmse_all6, ok_all6, msg_all6 = calibrate_all6_ga_then_local(
        bonds, comp=comp
    )

    print("Fixed taus fit:", theta_fixed, "RMSE(price)=", rmse_fixed, "ok=", ok_fixed)
    print("All-6 fit     :", theta_all6, "RMSE(price)=", rmse_all6, "ok=", ok_all6)
    print("True (demo)   :", theta_true)

    labeled = {
        f"Fit (tau fixed)  RMSE={rmse_fixed:.4f}": theta_fixed,
        f"Fit (all 6)      RMSE={rmse_all6:.4f}": theta_all6,
    }

    # Charts
    plot_zero_curves_and_ytm_points(bonds, labeled, comp=comp)
    plot_price_fit(bonds, labeled, comp=comp)
    plot_residuals_vs_maturity(bonds, labeled, comp=comp)

    plt.show()


if __name__ == "__main__":
    main()
