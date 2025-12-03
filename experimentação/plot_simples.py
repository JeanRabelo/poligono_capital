import matplotlib.pyplot as plt
import numpy as np
# Gerar dados
x = np.linspace(0, 5, 100)
y = np.exp(x)
# Criar o gráfico
plt.plot(x, y)
plt.title('Gráfico da Função Exponencial')
plt.xlabel('x')
plt.ylabel('exp(x)')
plt.grid(True)
# Mostrar o gráfico
plt.show()
