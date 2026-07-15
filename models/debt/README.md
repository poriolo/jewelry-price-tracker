# Fluxos de Dívida (módulos de valuation)

Motores de dívida montados para acoplar ao seu modelo de valuation.
Periodicidade **trimestral (aberto até 4T27)** e depois **anual até 2037**.

## Arquivos
- `build_debt_model.py` — gera as planilhas (config-driven, só fórmulas).
- `vivara_debt_model.xlsx` — Vivara (VIVA3).
- `smartfit_debt_model.xlsx` — Smart Fit (SMFT3).

Regenerar: `pip install openpyxl && python3 build_debt_model.py`

## Como acoplar (aba `Modelo_Dívida`)
1. **Amarelo = input** (CDI, spreads, amortizações, captações, dividendos e o
   **FCF livre pré-financiamento** que vem do seu modelo).
2. Ligue a linha *"FCF livre pré-financiamento (LINK)"* ao FCF do seu modelo →
   caixa e dívida líquida rodam sozinhos.
3. Referencie no seu valuation as linhas **verdes** da seção Interface: dívida
   bruta, dívida líquida, despesa de juros, juros após IR e escudo fiscal.
4. **Azul = dado real** reportado (âncora), não recalcula.

## Vivara (VIVA3) — âncoras reais
| Item | Valor |
|---|---|
| Debênture VIVA11 (1ª emissão) | R$ 300 mi · 27/08/2025→2030 · 100% CDI + 0,70% · amort. 50% 2029 / 50% 2030 |
| Dívida bruta / caixa / DL — 31/12/2025 | R$ 531,3 mi / R$ 398,6 mi / R$ 132,6 mi |
| Dívida líquida 1T26 | R$ 246,6 mi (0,3x ND/EBITDA) |
| Estimado | Outras dívidas R$ 231,3 mi (rolagem, CDI+2,00%) |

## Smart Fit (SMFT3) — âncoras reais (1T26)
| Item | Valor |
|---|---|
| Dívida líquida | R$ 4,2 bi (1,1x EBITDA) |
| Caixa + títulos | R$ 1,7 bi |
| Dívida bruta financeira (derivada) | ≈ R$ 5,9 bi |
| Custo médio | CDI + 2,09% a.a. |
| Vencimentos até fim de 2026 | R$ 1,2 bi (caixa cobre 1,4x) |
| Emissões recentes | 13ª (out/25, ≥R$ 1 bi) e 14ª (mar/26, R$ 1,32 bi) |

**Estimado:** dívida modelada como tranche única em rolagem (preencha o cronograma
real de amortização nas células amarelas). Não inclui arrendamento IFRS 16 nem a
dívida financeira ampliada (R$ 5,6 bi c/ aquisições a pagar e antecipação de recebíveis).

## Observação comum
"Despesa de juros" é só a da dívida financeira; o resultado financeiro reportado
inclui derivativos/MtM/receita de juros e não bate 1:1. No default o caixa fica
negativo nos anos finais porque o FCF está zerado — ligue o FCF do seu modelo.

## Fontes
Releases de resultados 1T26; características das debêntures (debentures.com.br /
Mais Retorno / ANBIMA); notícias de emissões (Lex Legal, Investidor10, CNN Brasil,
ADVFN); demonstrações financeiras e RI das companhias.
