# Bem vindo à solução do case!

Vou, ao longo desse README.md, falar sobre 4 assuntos:

- A. Como executar o código;
- B. Como o código soluciona o que foi pedido;
- C. Explicar decisões técnicas (essa parte vai estar ao longo de "A." e "B.");

## A. Como executar o código

1. Em uma pasta à qual você tem acesso, clone o repositório com o seguinte comando:

```
git clone https://github.com/JeanRabelo/poligono_capital.git
```

2. Ao clonar esse repositório, vá, por meio da linha de comando, até a pasta "solucao". Se você ainda estiver na linha de comando anterior do git, é só usar o seguinte comando:

Linux:

```
cd poligono_capital/solucao
```

Windows:

```
cd poligono_capital\solucao
```

3. Agora, crie um ambiente virtual para executar a aplicação (a solução foi feita em Python 3.13.3) (se "python3" abaixo não funcionar, experimente "python" ou "python3.xx" (com "3.xx" sendo a versão de python que está instalada no seu PC)):

```
python3 -m venv venv
```

4. Ative o ambiente virtual

Linux:

```
. venv/bin/activate
```

Windows:

```
venv\Scripts\activate.bat
```

5. Instale as dependências

```
pip3 install -r requirements.txt
```

6. Rode as migrations do django

```
python3 manage.py migrate
```

7. Agora rode a aplicação em um servidor local

```
python3 manage.py runserver
```

8. No seu browser, vá no endereço http://127.0.0.1:8000/

9. Se você ver a imagem abaixo, está tudo certo!

![Tela inicial](<assets/Tela inicial.png>)

🟢❗ **Decisão relevante:** seria bem mais prático colocar tudo em um Docker. Economizaria bastante tempo com os passos acima. Porém, além de exigir que no computador em que você está rodando a aplicação tenha Docker (o que não é tão comum), algumas empresas proíbem o uso dele. Os passos acima supõem que você tem python no computador, o que é bem mais provável do que Docker.

## B. Como o código soluciona o que foi pedido

1. Coleta de dados.

A ETL dos dados da B3 é a página inicial da aplicação.

![ETL - escolha de datas](<assets/ETL - escolha de datas.png>)

Na tela acima, basta escolher a data e clicar em "Buscar curva DI x PRÉ". Os dados são organizados de forma tabular.

![ETL - dados](<assets/ETL - dados.png>)

Nessa ETL estão as taxas de juros considerando 360 dias corridos e 252 dias úteis, conforme gráfico abaixo:

![ETL - gráficos](<assets/ETL - gráficos.png>)

2. Implementação do modelo de Svensson

Clicando no "Estimativas Svensson", botão acima do controle de datas, podemos ir para o app usado para fazer estimativas dos parâmetros do modelo de Svensson.

![Svensson - página inicial](<assets/Svensson - página inicial.png>)

Selecionando uma das datas com dados disponíveis, temos:

![Svensson - data escolhida](<assets/Svensson - data escolhida.png>)

Para cada data, temos tentativas de encontrar bons parâmetros para a curva de svensson. Abaixo dessa tela de escolha de tentativas, temos também um gráfico dos mesmos dados que tínhamos na ETL, mas somente considerando o "DI x PRÉ 252".

🟢❗ **Decisão relevante:** os motivos pelos quais escolhi somente considerar essa taxa de juros são 2.

```
i. Primeiramente, como o "DI x PRÉ 252" e o "DI x PRÉ 360" representam a mesma grandeza em bases de dias diferentes, não pareceu muito necessário incluir os 2;
ii. O "Gabarito" da ANBIMA leva em consideração essa taxa de base 252 no cálculo que ela divulga (link: https://www.anbima.com.br/pt_br/informar/curvas-de-juros-fechamento.htm) (um dos vértices do que ela expõe no site dela é 252 dias, o outro é 504, assim por diante...). Logo, para comparar com os resultados da ANBIMA, seria mais prático usar 252 do qe 360;
```

Para criar uma curva de Svensson nova e começar a tentar encontrar bons parâmetros para ela, basta clicar em "Nova Tentativa".

![Svensson - nova tentativa](<assets/Svensson - nova tentativa.png>)

Nesse modal que aparece no site, basta escrever os parâmetros iniciais da tentativa. Os índices dos "betas" estão com uma convenção um pouco diferente (começando em "0" em vez de "1"), mas o uso da aplicação continua intuitivo. É recomendado usar o campo de observações também, para identificar essa tentativa.

Obs: os "beta" dessa tela estão com unidade de porcentagem e usando vírgula pare decimais. Então se você quiser preencher algo como "10,5%", não use algo como "0.105", mas "10,5".

Também é possível escolher, como parâmetros, os parâmetros do dia útil anterior com a melhor (menor) função objetivo, para dar ao método de otimização um "warm start".

Há um exemplo de preenchimento abaixo:

![Svensson - exemplo de preenchimento inicial](<assets/Svensson - exemplo de preenchimento inicial.png>)

Depois de preencher, é só clicar na tentativa para selecioná-la.

![Svensson - tentativa selecionada](<assets/Svensson - tentativa selecionada.png>)

Ao ser selecionada uma tentativa, a curva de Svensson associada a ela é exibida (em amarelo se essa curva está levando em consideração os parâmetros iniciais da tentativa e em verde se forem os parâmetros finais).

🟡❗ **Possibilidade de melhoria:** salvar os pontos calculados da curva e os 2 tipos de resíduos em uma solução cache. Devido ao fato de que são muitos pontos, decidi não armazená-los de maneira perene no banco de dados e sim calculá-los toda vez que uma tentativa é selecionada. Essa decisão economiza espaço em disco, mas aumenta o tempo de exibição desses gráficos após o clique. Se for implementada uma ferramenta simples de cache, isso pode significar o melhor dos 2 mundos, pois o caching pode armazenar somente os pontos das curvas vistas com mais frequência ou mais recentemente.

🟡❗ **Possibilidade de melhoria:** criar uma calculadora em javascript, só no frontend, que permite ao usuário checar, em tempo real, como fica o formato da curva com alguns ajustes manuais e visuais. Assim, o usuário tem mais uma opção de escolha de parâmetros iniciais a serem melhorados: uma escolha de parâmetros que siga o que o usuário visualmente percebeu ser adequado.

À direita, temos as métricas de erro pedidas (RMSE, MAE, R^2) e a função objetivo (a função erro ponderada a ser minimizada) para aquela tentativa.

Temos também a opção de mostrar o gráfico em dias corridos ou dias úteis (só o que muda é o eixo "x", pois o "y" está sempre considerando juros anual com com base de 252 dias úteis).

🟢❗ **Decisão relevante:** foi considerado que os dias úteis são os "corretos", contando os feriados caso a caso, finais de semana etc. A própria documentação da Anbima considera assim, aparentemente. Isso faz com que anos tenham durações variáveis em dias úteis (e dias corridos também), mas o denominador da potência é sempre a mesma, 252.

Além disso, temos 2 gráficos de Resíduos:

```
i. um simples, chamado de "Resíduo", que é a simples diferença entre a taxa de juros real e a calculada;
ii. um que leva em consideração exatamente o cálculo da função objetivo (sqrt((1/duration) * (erro_de_preço) ^ 2));
```

Obs: como esses resíduos são representados por barras e são muitos pontos no gráfico, eles ficam praticamente invisíveis no cômputo geral. Porém, se for dado um zoom no gráfico, vai ser possível vê-los com mais detalhes.

3. Estimativa dos parâmetros da curva utilizando otimização

Para melhorar os parâmetros, temos o botão "Melhorar estimativa".

Ao clicar nele, podemos ver algumas alternativas de métodos de melhoria dos parâmetros da curva de Svensson, de modo que ela se adeque melhor aos dados.

![Svensson - métodos de melhoria de estimativas](<assets/Svensson - métodos de melhoria de estimativas.png>)

Explicando cada um deles:

### i. Local Search

O **Local Search** é um método determinístico de “busca por vizinhança” (coordinate search). A ideia é simples: partindo de um conjunto inicial de parâmetros, ele tenta melhorar a função objetivo ajustando **um parâmetro por vez**, testando pequenos movimentos para cima e para baixo (±) e aceitando qualquer mudança que reduza o erro. No meu código, isso é feito em *coordenadas*: escolhe-se um índice (um beta ou lambda), gera-se um candidato alterando só aquele parâmetro, avalia-se a função objetivo e, se melhorar, o candidato vira o novo “melhor atual”.

Para ficar estável em escalas diferentes (betas podem ser bem maiores que lambdas), os passos são **relativos ao tamanho do parâmetro** (step * base), e o algoritmo usa uma sequência de passos decrescentes (ex.: 0.05 → 0.02 → 0.01), refinando a solução à medida que vai “apertando” o passo. Além disso, ele garante a restrição do modelo mantendo **λ1 e λ2 sempre positivos** (clamp em `> 0`). É rápido e bom para refinar uma solução já razoável, mas pode ficar preso em mínimos locais.

---

### ii. Hybrid Search

O **Hybrid Search** combina duas ideias: exploração global + refinamento local. Primeiro, ele roda um **Algoritmo Genético (GA)** com uma população inicial composta por `initial_params` e vários candidatos **aleatórios em limites amplos** (ou seja, ele tenta “varrer” regiões diferentes do espaço de parâmetros). A cada geração, ele avalia a função objetivo, seleciona os melhores indivíduos (metade superior), faz recombinação (o “filho” herda cada parâmetro de um dos pais) e aplica **mutação** com certa probabilidade (pequenas perturbações nos betas e lambdas), sempre forçando λ1 e λ2 a permanecerem positivos.

Depois que o GA termina, entra a parte “hybrid”: ele pega o melhor candidato encontrado e aplica um **Local Search** em cima dele para “polir” a solução. Em geral, esse método é mais demorado do que o Local Search puro, mas tende a ser mais robusto para escapar de mínimos locais, já que começa com uma busca mais ampla antes de refinar.

---

### iii. Hybrid Search From Current Result

O **Hybrid Search From Current Result** é quase o mesmo pipeline do Hybrid Search (GA + Local Search no final), mas muda um detalhe crucial: **a população inicial não é majoritariamente aleatória**. Em vez de começar “do nada”, ele cria uma população “perto” do resultado atual (`initial_params`) aplicando **pequenas perturbações (jitter)**: nos betas, o jitter é aditivo e relativo à escala; nos lambdas, é multiplicativo (e depois clamp para manter positividade). Com isso, ele explora melhor a vizinhança do ponto atual, fazendo uma busca mais “direcionada” e eficiente quando você já tem uma estimativa decente.

Para não ficar preso caso a vizinhança seja ruim, ele ainda injeta uma pequena fração de candidatos totalmente aleatórios (**global injection**, ex.: 10%), o que ajuda a escapar de mínimos locais sem perder o foco no refinamento a partir do resultado atual. Em resumo: é um híbrido “mais quente” (warm start), ótimo quando você quer melhorar incrementalmente uma solução que já está próxima do ideal.

🟡❗ **Possibilidade de melhoria:** usar métodos mais avançados de otimização, principalmente ao final da otimização, como métodos quasi-newton.

🟡❗ **Possibilidade de melhoria:** usar bibliotecas Scipy, Scikit Learn etc para fazer alguns desses cálculos de otimização, pois elas têm muito mais maturidade para fazer algumas dessas tarefas (e eventualmente utilizam melhor os recursos do PC, como a GPU, por exemplo).

É bem fácil expandir para colocar mais métodos: é só incluí-los no código optimizers.py e registrá-lo ao final do script.

Ao se usar um dos métodos para a melhoria dos parâmetros utilizados, o botão "Melhorar estimativa" fica travado como "Melhorando" e não é recomendado usar o site durante esse momento.

Depois de algum tempo, há uma mensagem de sucesso ou fracasso da tentativa de melhoria.

![Svensson - mensagem de tentativa de melhoria](<assets/Svensson - mensagem de tentativa de melhoria.png>)

Essa questão do tempo é relevante, pois pode parecer que o site não funciona, mas é só que o computador está trabalhando no backend, mesmo. Em uma máquina com processador core I5 de 13ª geração, 16GB de RAM e placa de vídeo Geforce RTX 4050 de 6GB de RAM as estratégias mais demoradas ("Hybrid Search" e "Hybrid Search From Current Result") levam um pouco menos de 2 min.

4. Validação dos resultados

Comparando os resultados que obtive com algumas iterações de Hybrid Search com os dados da data 04/12/2025 com os parâmetros encontrados pela ANBIMA, temos:

![Validação - resultados ANBIMA](<assets/Validação - resultados ANBIMA.png>)

(a curva acima foi obtida usado os resultados alcançados pela ANBIMA para os dados da data 04/12/2025)

![Validação - resultados próprios](<assets/Validação - resultados próprios.png>)

(a curva acima foi obtida procurando melhorar várias vezes alguns dados iniciais)

Foi possível encontrar uma função objetivo menor que a da ANBIMA (4.2863e-7 < 1.8883e-6).

Dado que é improvável que um indivíduo sozinho, com pouca experiência no assunto e o poder computacional de um notebook pessoal seja mais eficiente que a ANBIMA, é possível pensar em algumas hipóteses:

1. Os dados que a ANBIMA usa para fazer sua curva são um pouco diferentes do que usei, pois ela pode usar os dados de mercado originais, não eventuais dados já calculados pela B3.
2. Como as maiores diferenças são nos pontos de mais longo prazo, pode ser que a ANBIMA não considere esses dados na sua otimização (e isso faz sentido, dado que o gráfico que a anbima divulga "para" muito antes do meu, conforme exemplo do site da ANBIMA abaixo).

![Validação - resultado da ANBIMA para dia 04-12-2025](<assets/Validação - resultado da ANBIMA para dia 04-12-2025.png>)