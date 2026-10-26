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
| `relatorio_compiladores.pdf` | Relatório técnico |

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
  campo repetido, tipo não declarado e tipo do campo na atribuição/operadores. Registros nomeados são equivalentes por nome; os anônimos, por estrutura.
- **`string`:** tipo e literais `'texto'`; `+` concatena e `=`/`<>` comparam; misturar com outros tipos é erro.
- **`function` / `procedure`:** parâmetros por valor, retorno por `nome := valor` dentro da função, recursão, locais em
  ambiente filho (a tabela de símbolos mostra um escopo por subprograma). Verifica número e tipo dos argumentos, tipo do
  retorno, procedimento usado como valor e função/procedimento não declarado. Chamada sem parênteses é aceita para `f` sem parâmetros.
  Parâmetros por referência (`var x: integer`) exigem como argumento uma **variável** (inclusive `v[i]` e `p.campo`) de tipo
  idêntico; constante, literal ou expressão é erro (o parser roda com `tracking=True` para reconhecer variável pura).
  Limitação: sem subprogramas aninhados.
- **`const`:** `const MAX = 10; PI = 3.14; NOME = 'Ana'; ATIVO = true; NEG = -4; OUTRO = MAX;` O tipo vem do valor; constante
  não pode receber atribuição nem ser variável de `for` ou argumento `var`; constante inteira serve de limite de vetor
  (`array[1..MAX]`) e, como índice, tem o valor checado contra os limites. As constantes são aceitas no escopo global.
- **`for` / `repeat`:** `for i := a to b do ...` e `downto` (variável de controle e limites devem ser `integer`);
  `repeat ... until cond` (condição `boolean`).
- **`case`:** `case expr of rótulos: comando; ... [else comando] end`. O seletor deve ser `integer` ou `boolean`; os rótulos são constantes
  (literais, negativos, `true`/`false` ou constantes nomeadas) do mesmo tipo do seletor, separados por vírgula; rótulo repetido é erro.
  `;` antes do `else` e antes do `end` é opcional, e o braço pode ser vazio ou um bloco `begin ... end`. Não há intervalos (`1..5`).
  O `else` de um `if` sem `else` dentro de um braço casa com esse `if` (mesma regra do `else` pendente).
- **`div` / `mod`:** exigem dois operandos `integer` e devolvem `integer`; `/` continua exigindo o mesmo tipo numérico nos dois lados.
- **Sinal unário (`-a`, `+a`):** como no Pascal padrão, o sinal fica no início de `simple_expr` (`simple_expr : MINUS term`), então `-a * b` é `-(a * b)` e `b - -a` é erro sintático (escreva `b - (-a)`). O operando deve ser `integer` ou `real` e o tipo é mantido; `-3` continua constante para a checagem de índice (ver `testes/sucesso_menos_unario.pas` e `testes/erro_menos_unario.pas`).
- **Ponteiros:** `^tipo`, desreferência `p^` (encadeável: `p^.prox^.valor`), `nil`, `new(p)` e `dispose(p)`.
  Ponteiros só são compatíveis com o mesmo tipo-alvo ou `nil`; aritmética e `<`/`>` em ponteiros é erro; `new`/`dispose`
  em não-ponteiro é erro. Aceita referência adiante (`PNo = ^No; No = record ... prox: PNo end`), resolvida via ponteiro
  para a entrada da tabela de símbolos; alvo que nunca é declarado gera erro ao final. Registros nomeados usam equivalência por nome.
- **Escopos:** cada bloco `begin ... end` abre um ambiente filho e, ao concluir o bloco,
  retorna ao ambiente pai; a busca percorre a cadeia `parent` até encontrar o símbolo.
- **Tipagem forte:** `integer`, `real` e `boolean` são tipos distintos, sem nenhuma coerção entre eles.
  `boolean` é declarável (`var b : boolean`) e tem as constantes `true`/`false`; relacionais produzem `boolean`, exigido por `if`, `while`, `and`, `or` e `not`. `None` marca subexpressão
  já com erro, para não gerar mensagens em cascata.
- **Conflitos:** mesmo com as extensões (boolean, vetor, record, uses, subprogramas, const, for, repeat, case, div/mod, parâmetros `var`), o conflito shift/reduce registrado é o do `else` pendente (estado 232 do `parser.out`, regras 84 e 85),
  resolvido como *shift* por precedência (`IFX < ELSE`). O arquivo `parser.out` desta versão contém 142 regras numeradas de 0 a 141 e 278 estados numerados de 0 a 277.
- **Modo pânico:** descarta tokens até `;`, `end` **ou `until`**. O `end` e o `until` foram acrescentados porque o último
  comando de um bloco (ou de um `repeat`) não termina em `;` (ver `testes/sync_end.pas`).
  Se o parser voltar a falhar no mesmo token (ex.: `else` solto, que não é sincronizador), ele é
  descartado para evitar loop infinito (ver `testes/erro_else_solto.pas`).


