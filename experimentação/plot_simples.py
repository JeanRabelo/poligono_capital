import numpy as np
import matplotlib.pyplot as plt

# ---- parameters (edit these) ----
a = 1.0
b = 2.0
c = 0.8
d = 0.5

# ---- x range (edit these) ----
x = np.linspace(-5, 5, 1000)

# ---- numerically-stable helper for (1 - exp(cx)) / (-c x) ----
z = -c * x
f = np.empty_like(z)
np.divide(-np.expm1(z), z, out=f, where=(z != 0))  # f = (1 - exp(z))/z
f[z == 0] = -1.0  # limit as z->0

# ---- curves ----
y1 = a + b * f
y_extra = d * (f - np.exp(z))
y2 = y1 + y_extra  # a + b*f + d*(f - exp(cx))

# ---- plot ----
plt.figure(figsize=(8, 5))
plt.plot(x, y1, label=r"$y_1 = a + b\frac{1-e^{cx}}{cx}$")
plt.plot(x, y2, label=r"$y_2 = a + b\frac{1-e^{cx}}{cx} + d\left(\frac{1-e^{cx}}{cx}-e^{cx}\right)$")
plt.plot(x, y_extra, "--", label=r"$y_{\mathrm{extra}} = d\left(\frac{1-e^{cx}}{cx}-e^{cx}\right)$")

plt.axhline(0, linewidth=0.8)
plt.axvline(0, linewidth=0.8)
plt.grid(True, alpha=0.3)
plt.legend()
plt.xlabel("x")
plt.ylabel("y")
plt.tight_layout()
plt.show()

