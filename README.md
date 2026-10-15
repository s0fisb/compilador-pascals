# Compilador Pascal-S (front-end) — TP1 de Compiladores

Front-end completo para **Pascal-S** (subconjunto de Pascal) em Python com **PLY**:
análise léxica sob demanda, tabela de símbolos com ponteiros, parser LALR(1),
verificação semântica de tipagem forte e recuperação de erros em modo pânico.

FURG · Centro de Ciências Computacionais (C3) · Compiladores 2026/2 · Prof. Dr. Gerson Alberto Leiria Nunes
Grupo: **[Nome Completo 1]** e **[Nome Completo 2]**

## Requisitos

- Python 3.8 ou superior
- PLY 3.11: `pip install ply==3.11`

## Como executar

```bash
python yacc.py testes/sucesso_semantico.pas              # compila um arquivo
python yacc.py --fail-fast testes/erro_tipo.pas          # aborta no 1º erro semântico
python lex.py testes/sucesso_semantico.pas               # só o analisador léxico
python run_tests.py                                      # roda todos os testes e regrava logs/
python testes_unitarios.py                               # testes da tabela de símbolos (sem PLY)
```

Código de saída: `0` = sucesso; `1` = houve erro léxico, sintático ou semântico.

## Estrutura

| Arquivo | Conteúdo |
|---|---|
| `lex.py` | Scanner: tokens, palavras reservadas (case-insensitive), comentários `//` e `{ }`, linha/coluna, `getNextToken()` |
| `symtab.py` | `Symbol`, `SymbolTable` (ambientes encadeados por `parent`) e `ScopeManager` |
| `yacc.py` | Gramática LALR(1), verificação de tipos, `p_error` com modo pânico e `main` |
| `run_tests.py` | Executa `testes/*.pas` e grava a saída real em `logs/*.log` |
| `testes_unitarios.py` | Testes unitários dos ambientes aninhados da tabela de símbolos |
| `testes/` | Programas de entrada (sucesso, erro léxico, sintático e semântico) |
| `logs/` | Saída do compilador para cada teste |
| `parser.out` | Tabelas LALR geradas pelo PLY (usado na análise de conflitos) |
| `relatorio_tecnico.pdf` | Relatório técnico |

## Decisões principais

- **Léxico sob demanda:** o parser consome tokens um a um por `tokenfunc=stream.getNextToken`;
  não existe vetor de tokens.
- **Token ID → ponteiro:** o valor do token `ID` é o objeto `Symbol` da tabela de símbolos
  (`lookup_or_install` no lexer; `declare` no parser).
- **Tipagem forte:** nenhuma coerção entre `integer` e `real`. Relacionais produzem um tipo
  interno `boolean`, exigido por `if`, `while`, `and`, `or` e `not`. `None` marca subexpressão
  já com erro, para não gerar mensagens em cascata.
- **Conflitos:** o único conflito shift/reduce é o do `else` pendente (estado 76 do `parser.out`),
  resolvido como *shift* por precedência (`IFX < ELSE`).
- **Modo pânico:** descarta tokens até `;` **ou `end`**. O `end` foi acrescentado porque o último
  comando de um bloco não termina em `;` (ver `testes/sync_end.pas`).
- **Escopos:** o Pascal-S só tem um bloco declarativo, então só o escopo global é usado;
  `enter_scope`/`exit_scope` implementam os ambientes aninhados e são testados em `testes_unitarios.py`.

## Testes

`sucesso_*` devem terminar com `Resultado: SUCESSO`; `erro_*` e demais, com `FALHA` e código 1.
Os três cenários obrigatórios do enunciado são `sucesso_semantico.pas`, `erro_lexico.pas` e `erro_tipo.pas`.
