# Compilador Pascal-S (front-end)

Front-end completo para **Pascal-S** (subconjunto de Pascal) em Python com **PLY**:
análise léxica sob demanda, tabela de símbolos com ponteiros, parser LALR(1),
verificação semântica de tipagem forte e recuperação de erros em modo pânico.

## Requisitos

- Python 3.8 ou superior
- PLY 3.11: `pip install ply==3.11`

## Como executar

```bash
python yacc.py testes/sucesso_semantico.pas              # compila um arquivo
python lex.py testes/sucesso_semantico.pas               # só o analisador léxico
python run_tests.py                                      # roda todos os testes e regrava logs/
```

Código de saída: `0` = sucesso; `1` = houve erro léxico, sintático ou semântico.

## Estrutura

| Arquivo | Conteúdo |
|---|---|
| `lex.py` | Scanner: tokens, palavras reservadas (case-insensitive), comentários `//` e `{ }`, linha/coluna, `getNextToken()` |
| `symtab.py` | `Symbol`, `SymbolTable` (ambientes encadeados por `parent`) e `ScopeManager` |
| `yacc.py` | Gramática LALR(1), verificação de tipos, `p_error` com modo pânico e `main` |
| `run_tests.py` | Executa `testes/*.pas` e grava a saída real em `logs/*.log` |
| `testes/` | Programas de entrada (sucesso, erro léxico, sintático e semântico) |
| `logs/` | Saída do compilador para cada teste |
| `parser.out` | Tabelas LALR geradas pelo PLY (usado na análise de conflitos) |
| `relatorio_tecnico.pdf` | Relatório técnico |

## Decisões principais

- **Léxico sob demanda:** o parser consome tokens um a um por `tokenfunc=stream.getNextToken`;
  não existe vetor de tokens.
- **Token ID → ponteiro:** o valor do token `ID` é o objeto `Symbol` da tabela de símbolos
  (`lookup_or_install` no lexer; `declare` no parser).
- **Vetores e matrizes:** `array[lo..hi] of tipo` e `array[1..3, 1..3] of real` (matriz = vetor de vetor, `ArrayType`
  em `symtab.py`). Acesso `v[i]`, `m[i, j]` ou `m[i][j]`. Verificações: índice deve ser `integer`; só vetor pode ser
  indexado; tipo do elemento entra na checagem de atribuição/operadores; índice constante fora dos limites é erro;
  vetor inteiro não entra em aritmética nem em `writeln`.
- **`uses`:** `uses crt, math;` registra as unidades (repetição é erro) e lista no log. Não há biblioteca real por trás.
- **`type` / `record`:** `type Pessoa = record nome: string; idade: integer end;`, aliases (`type Notas = array[1..3] of real`),
  registro anônimo em `var`, acesso `p.idade` (inclusive aninhado e combinado com `[ ]`). Verifica campo inexistente,
  campo repetido, tipo não declarado e tipo do campo na atribuição/operadores. Registros são comparados estruturalmente.
- **`string`:** tipo e literais `'texto'`; `+` concatena e `=`/`<>` comparam; misturar com outros tipos é erro.
- **`function` / `procedure`:** parâmetros por valor, retorno por `nome := valor` dentro da função, recursão, locais em
  ambiente filho (a tabela de símbolos mostra um escopo por subprograma). Verifica número e tipo dos argumentos, tipo do
  retorno, procedimento usado como valor e função/procedimento não declarado. Chamada sem parênteses é aceita para `f` sem parâmetros.
  Limitação: sem parâmetros `var` (por referência) e sem subprogramas aninhados.
- **Ponteiros:** `^tipo`, desreferência `p^` (encadeável: `p^.prox^.valor`), `nil`, `new(p)` e `dispose(p)`.
  Ponteiros só são compatíveis com o mesmo tipo-alvo ou `nil`; aritmética e `<`/`>` em ponteiros é erro; `new`/`dispose`
  em não-ponteiro é erro. Aceita referência adiante (`PNo = ^No; No = record ... prox: PNo end`), resolvida via ponteiro
  para a entrada da tabela de símbolos; alvo que nunca é declarado gera erro ao final. Registros nomeados usam equivalência por nome.
- **Escopos:** cada bloco `begin ... end` abre um ambiente filho e, ao concluir o bloco,
  retorna ao ambiente pai; a busca percorre a cadeia `parent` até encontrar o símbolo.
- **Tipagem forte:** `integer`, `real` e `boolean` são tipos distintos, sem nenhuma coerção entre eles.
  `boolean` é declarável (`var b : boolean`) e tem as constantes `true`/`false`; relacionais produzem `boolean`, exigido por `if`, `while`, `and`, `or` e `not`. `None` marca subexpressão
  já com erro, para não gerar mensagens em cascata.
- **Conflitos:** mesmo com as extensões (boolean, vetor, record, uses, subprogramas), o único conflito shift/reduce é o do `else` pendente (estado 77 do `parser.out`),
  resolvido como *shift* por precedência (`IFX < ELSE`).
- **Modo pânico:** descarta tokens até `;` **ou `end`**. O `end` foi acrescentado porque o último
  comando de um bloco não termina em `;` (ver `testes/sync_end.pas`).
  Se o parser voltar a falhar no mesmo token (ex.: `else` solto, que não é sincronizador), ele é
  descartado para evitar loop infinito (ver `testes/erro_else_solto.pas`).


## Testes

`sucesso_*` devem terminar com `Resultado: SUCESSO`; `erro_*` e demais, com `FALHA` e código 1.
Os três cenários obrigatórios do enunciado são `sucesso_semantico.pas`, `erro_lexico.pas` e `erro_tipo.pas`.
