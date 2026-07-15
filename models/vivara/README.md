# Vivara (VIVA3) — Fluxo de Dívida (módulo de valuation)

Motor de dívida da Vivara para acoplar ao seu modelo de valuation. Periodicidade
**trimestral do 4T25 (real) até o 4T27E** e depois **anual (2028E–2030E)**.

## Arquivos
- `build_debt_model.py` — gera a planilha (modelo vivo, só fórmulas).
- `vivara_debt_model.xlsx` — saída pronta pra usar.

Regenerar: `pip install openpyxl && python3 build_debt_model.py`

## Como acoplar
Na aba **`Modelo_Dívida`**:
1. **Amarelo = input** (CDI, spreads, amortizações, captações, dividendos e o
   **FCF livre pré-financiamento** que vem do seu modelo).
2. Ligue a linha *"FCF livre pré-financiamento (LINK)"* ao FCF do seu modelo →
   caixa e dívida líquida passam a rodar sozinhos.
3. Referencie no seu valuation as linhas **verdes** da seção 6: dívida bruta,
   dívida líquida, despesa de juros, juros após IR e escudo fiscal.
4. **Azul = dado real** reportado (âncora), não recalcula.

## Dados reais (âncoras)
| Item | Valor |
|---|---|
| Debênture VIVA11 (1ª emissão) | R$ 300 mi · 27/08/2025→2030 · 100% CDI + 0,70% · amort. 50% 2029 / 50% 2030 |
| Dívida bruta 31/12/2025 | R$ 531,3 mi |
| Caixa 31/12/2025 | R$ 398,6 mi |
| Dívida líquida 31/12/2025 | R$ 132,6 mi |
| Dívida líquida 1T26 | R$ 246,6 mi (0,3x ND/EBITDA) |

## Premissas estimadas (ajuste com o ITR quando tiver)
- **Outras dívidas** = bruta − debêntures = R$ 231,3 mi (bancos/FX/capital de giro),
  modeladas como rolagem (amortização default = 0).
- Spread outras dívidas = CDI + 2,00% a.a.
- Curva de CDI ~14,9% (2026) → ~10% (2030).
- "Despesa de juros" é só a da dívida financeira; o resultado financeiro reportado
  (−R$ 15 mi no 1T26) inclui derivativos/MtM e não bate 1:1.

## Fontes
Release de resultados 1T26 (Money Times / Nord / Análise de Ações); características
da VIVA11 (debentures.com.br / Mais Retorno / ANBIMA); emissão de R$ 300 mi p/
liquidar CCBs (Lex Legal — Lefosse/Mattos Filho); dívida bruta e caixa de
31/12/2025 (DF 2025 Vivara Participações S.A.).
