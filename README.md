# Bem vindo à solução do case!
Vou, ao longo desse README.md, falar sobre 4 assuntos:
A. Como executar o código;
B. Como o código soluciona o que foi pedido;
C. Explicar decisões técnicas (essa parte vai estar ao longo de "A." e "B.");



## A. Como executar o código
1. Em uma pasta à qual você tem acesso, clone o repositório com o seguinte comando:
git clone https://github.com/JeanRabelo/poligono_capital.git

2. Ao clonar esse repositório, vá, por meio da linha de comando, até a pasta "solucao". Se você ainda estiver na linha de comando anterior do git, é só usar o seguinte comando:

Linux:
cd poligono_capital/solucao
Windows:
cd poligono_capital\solucao

3. Agora, crie um ambiente virtual para executar a aplicação (a solução foi feita em Python 3.13.3) (se "python3" abaixo não funcionar, experimente "python" ou "python3.xx" (com "3.xx" sendo a versão de python que está instalada no seu PC)):
python3 -m venv venv

4. Ative o ambiente virtual

Linux:
. venv/bin/activate

Windows:
venv\Scripts\activate.bat

5. Instale as dependências

pip3 install -r requirements.txt

6. Rode as migrations do django
python3 manage.py migrate

7. Agora rode a aplicação em um servidor local
python3 manage.py runserver

8. No seu browser, vá no endereço http://127.0.0.1:8000/

9. Se você ver a imagem abaixo, está tudo certo!

[assets/Tela inicial.png]

!-> decisão relevante: seria bem mais prático colocar tudo em um Docker. Economizaria bastante tempo com os passos acima. Porém, além de exigir que no computador em que você está rodando a aplicação tenha Docker (o que não é tão comum), algumas empresas proíbem o uso dele. Os passos acima supõem que você tem python no computador, o que é bem mais provável do que Docker.

## B. Como o código soluciona o que foi pedido
1. Coleta de dados.

A ETL dos dados da B3 é a página inicial da aplicação.

[assets/ETL - escolha de datas.png]

Na tela acima, basta escolher a data e clicar em "Buscar curva DI x PRÉ". Os dados são organizados de forma tabular.

[assets/ETL - dados.png]

Nessa ETL estão as taxas de juros considerando 360 dias corridos e 252 dias úteis, conforme gráfico abaixo:

[assets/ETL - gráficos.png]

2. Implementação do modelo de Svensson
Clicando no "Estimativas Svensson", botão acima do controle de datas, podemos ir para o app usado para fazer estimativas dos parâmetros do modelo de Svensson.

[assets/Svensson - página inicial.png]

Selecionando uma das datas com dados disponíveis, temos:

[assets/Svensson - data escolhida.png]

Para cada data, temos tentativas de encontrar bons parâmetros para a curva de svensson. Abaixo dessa tela de escolha de tentativas, temos também um gráfico dos mesmos dados que tínhamos na ETL, mas somente considerando o "DI x PRÉ 252".

!-> decisão relevante: os motivos pelos quais escolhi somente considerar essa taxa de juros são 2.
    i. Primeiramente, como o "DI x PRÉ 252" e o "DI x PRÉ 360" representam a mesma grandeza em bases de dias diferentes, não pareceu muito necessário incluir os 2;
    ii. O "Gabarito" da ANBIMA leva em consideração essa taxa de base 252 no cálculo que ela divulga (link: https://www.anbima.com.br/pt_br/informar/curvas-de-juros-fechamento.htm) (um dos vértices do que ela expõe no site dela é 252 dias, o outro é 504, assim por diante...). Logo, para comparar com os resultados da ANBIMA, seria mais prático usar 252 do qe 360;

Para criar uma curva de Svensson nova e começar a tentar encontrar bons parâmetros para ela, basta clicar em "Nova Tentativa".

[assets/Svensson - nova tentativa.png]

Nesse modal que aparece no site, basta escrever os parâmetros iniciais da tentativa. Os índices dos "betas" estão com uma convenção um pouco diferente (começando em "0" em vez de "1"), mas o uso da aplicação continua intuitivo. É recomendado usar o campo de observações também, para identificar essa tentativa.
Obs: os "beta" dessa tela estão com unidade de porcentagem e usando vírgula pare decimais. Então se você quiser preencher algo como "10,5%", não use algo como "0.105", mas "10,5".

Também é possível escolher, como parâmetros, os parâmetros do dia útil anterior com a melhor (menor) função objetivo, para dar ao método de otimização um "warm start".

Há um exemplo de preenchimento abaixo:

[assets/Svensson - exemplo de preenchimento inicial.png]

Depois de preencher, é só clicar na tentativa para selecioná-la.

[assets/Svensson - tentativa selecionada.png]

À direita, temos as métricas de erro pedidas (RMSE, MAE, R^2) e a função objetivo (a função erro ponderada a ser minimizada) para aquela tentativa.

Temos também a opção de mostrar o gráfico em dias corridos ou dias úteis (só o que muda é o eixo "x", pois o "y" está sempre considerando juros anual com com base de 252 dias úteis).

Além disso, temos 2 gráficos de Resíduos:
i. um simples, chamado de "Resíduo", que é a simples diferença entre a taxa de juros real e a calculada;
ii. um que leva em consideração exatamente o cálculo da função objetivo (sqrt((1/duration) * (erro_de_preço) ^ 2));

Obs: como esses resíduos são representados por barras e são muitos pontos no gráfico, eles ficam praticamente invisíveis no cômputo geral. Porém, se for dado um zoom no gráfico, vai ser possível vê-los com mais detalhes.

3. Estimativa dos parâmetros da curva utilizando otimização
Para melhorar os parâmetros, temos o botão "Melhorar estimativa".

Ao clicar nele, podemos ver algumas alternativas de métodos de melhoria dos parâmetros da curva de Svensson, de modo que ela se adeque melhor aos dados.

[assets/Svensson - métodos de melhoria de estimativas.png]

Explicando cada um deles:
i. Local Search
ii. Hybrid Search
iii. Hybrid Search From Current Result

É bem fácil expandir para colocar mais métodos: é só incluí-los no código optimizers.py e registrá-lo ao final do script.

Ao se usar um dos métodos para a melhoria dos parâmetros utilizados, o botão "Melhorar estimativa" fica travado como "Melhorando" e não é recomendado usar o site durante esse momento.

Depois de algum tempo, há uma mensagem de sucesso ou fracasso da tentativa de melhoria.

[assets/Svensson - mensagem de tentativa de melhoria.png]

Essa questão do tempo é relevante, pois pode parecer que o site não funciona, mas é só que o computador está trabalhando no backend, mesmo. Em uma máquina com processador core I5 de 13ª geração, 16GB de RAM e placa de vídeo Geforce RTX 4050 de 6GB de RAM as estratégias mais demoradas ("Hybrid Search" e "Hybrid Search From Current Result") levam um pouco menos de 2 min.

4. Validação dos resultados

Comparando os resultados que obtive com algumas iterações de Hybrid Search com os dados da data 04/12/2025 com os parâmetros encontrados pela ANBIMA, temos:

[assets/Validação - resultados ANBIMA.png]
(a curva acima foi obtida usado os resultados alcançados pela ANBIMA para os dados da data 04/12/2025)

[assets/Validação - resultados próprios.png]
(a curva acima foi obtida procurando melhorar várias vezes alguns dados iniciais)

Foi possível encontrar uma função objetivo menor que a da ANBIMA (4.2863e-7 < 1.8883e-6).

Dado que é improvável que um indivíduo sozinho, com pouca experiência no assunto e o poder computacional de um notebook pessoal seja mais eficiente que a ANBIMA, é possível pensar em algumas hipóteses:
1. Os dados que a ANBIMA usa para fazer sua curva são um pouco diferentes do que usei, pois ela pode usar os dados de mercado originais, não eventuais dados já calculados pela B3.
2. Como as maiores diferenças são nos pontos de mais longo prazo, pode ser que a ANBIMA não considere esses dados na sua otimização (e isso faz sentido, dado que o gráfico que a anbima divulga "para" muito antes do meu, conforme exemplo do site da ANBIMA abaixo).

[assets/Validação - resultado da ANBIMA para dia 04-12-2025.png]