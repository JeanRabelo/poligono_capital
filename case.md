# Estrutura a Termo da Taxa de Juros

## Contexto

A Estrutura a Termo da Taxa de Juros (ETTJ) é uma ferramenta fundamental para precificação de ativos, gestão de risco e análise macroeconômica. No mercado brasileiro, a curva de juros derivada dos contratos de swap DI x Pré é uma das principais referências para o mercado de renda fixa. Para diminuir o custo computacional de manipular todos os vértices da curva, é comum o uso de uma curva paramétrica divulgada pela ANBIMA. 

## Objetivo

Implementar um pipeline para coletar a curva DI x Pré da B3 e ajustar uma **curva Svensson** para a estrutura a termo da taxa de juros, seguindo a metodologia oficial da ANBIMA.

## Descrição da Tarefa

Seu código deverá:

1. **Coletar os dados** de taxas referenciais de swap DI x Pré da B3 e estruturá-lo como uma tabela.
2. **Implementar o modelo de Svensson** para ajuste da curva de juros
3. **Estimar os parâmetros** da curva utilizando otimização
4. **Validar os resultados** comparando as taxas ajustadas com as taxas observadas

## Fontes de Dados e Metodologia

### Dados
- **Fonte**: [Taxas Referenciais BM&F Bovespa - B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/consultas/mercado-de-derivativos/precos-referenciais/taxas-referenciais-bm-fbovespa/)
- **Instrumento**: Swap DI x Pré
- **Frequência**: Diária

### Metodologia
- **Documento de referência**: [Metodologia ANBIMA - Estrutura a Termo](https://www.anbima.com.br/data/files/18/42/65/50/4169E510222775E5A8A80AC2/est-termo_metodologia.pdf)
- **Modelo**: Svensson (extensão do modelo Nelson-Siegel)

### Equação do Modelo Svensson

A taxa spot no prazo τ é dada por:

```
y(τ) = β₀ + β₁ * [(1 - exp(-τ/τ₁))/(τ/τ₁)] 
          + β₂ * [(1 - exp(-τ/τ₁))/(τ/τ₁) - exp(-τ/τ₁)]
          + β₃ * [(1 - exp(-τ/τ₂))/(τ/τ₂) - exp(-τ/τ₂)]
```

Onde:
- **β₀, β₁, β₂, β₃**: parâmetros a serem estimados
- **τ₁, τ₂**: parâmetros de decaimento
- **τ**: prazo (em anos)

## Entregáveis Esperados

### 1. Código
- Script(s) bem documentado(s) em Python com as funcionalidades:
    - ETL dos dados da B3
    - "Fit" do modelo de Svensson 
- Comentários explicando as principais decisões técnicas

### 2. Resultados
- **Parâmetros estimados** da curva Svensson
- **Métricas de ajuste**: RMSE, MAE, R²
- **Gráficos**:
  - Curva ajustada vs. taxas observadas
  - Resíduos do ajuste
  - Componentes da curva (nível, inclinação, curvatura)

### 3. Documentação
- README explicando como executar o código
- Breve análise dos resultados obtidos
- Discussão sobre qualidade do ajuste e possíveis melhorias


## Dicas e Orientações

- Preste atenção nas unidades: taxas em % a.a., prazos em dias úteis/corridos
- Considere diferentes métodos de otimização e chutes iniciais
- Valide seus resultados comparando com curvas publicadas pela ANBIMA (quando disponível)

## Entrega

Envie o código :
    - em um repositório Git (GitHub/GitLab) **OU** 
    - em um arquivo compactado (.zip)

O prazo para envio é de até 3 dias. 
---

**Boa sorte! 🚀**