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
| `lex.py` | Scanner: tokens, palavras reservadas (case-insensitive), comentários `(* *)`, `{ }` e `//`, aviso de `maxint`, linha/coluna, `getNextToken()` |
| `symtab.py` | `Symbol`, `SymbolTable` (ambientes encadeados por `parent`) e `ScopeManager` |
| `yacc.py` | Gramática LALR(1), verificação de tipos, `p_error` com modo pânico e `main` |
| `run_tests.py` | Executa `testes/*.pas` e grava a saída real em `logs/*.log` |
| `testes/` | Programas de entrada (sucesso, erro léxico, sintático e semântico) |
| `logs/` | Saída do compilador para cada teste |
| `parser.out` | Tabelas LALR geradas pelo PLY (usado na análise de conflitos) |
| `relatorio_compiladores.pdf` | Relatório técnico |

## Decisões principais (gerais)

- **Léxico sob demanda:** o parser consome tokens um a um por `tokenfunc=stream.getNextToken`;
  não existe vetor de tokens.
- **Token ID → ponteiro:** o valor do token `ID` é o objeto `Symbol` da tabela de símbolos
  (`lookup_or_install` no lexer; `declare` no parser).
- **Escopos:** cada bloco `begin ... end` e cada subprograma abre um ambiente filho e, ao concluir,
  retorna ao ambiente pai; a busca percorre a cadeia `parent` até encontrar o símbolo.
- **Tipagem forte:** `integer`, `real`, `boolean` e `char` são tipos distintos, sem nenhuma coerção entre eles.
  Relacionais produzem `boolean`, exigido por `if`, `while`, `repeat`, `and`, `or` e `not`. `None` marca subexpressão
  já com erro, para não gerar mensagens em cascata.
- **Conflitos:** o único conflito shift/reduce é o do `else` pendente (estado 247 do `parser.out`, regras 86 e 87),
  resolvido como *shift* por precedência (`IFX < ELSE`). O arquivo `parser.out` desta versão contém 156 regras
  numeradas de 0 a 155 e 306 estados numerados de 0 a 305.
- **Modo pânico:** descarta tokens até `;`, `end` **ou `until`**. O `end` e o `until` foram acrescentados porque o último
  comando de um bloco (ou de um `repeat`) não termina em `;` (ver `testes/sync_end.pas`).
  Se o parser voltar a falhar no mesmo token (ex.: `else` solto, que não é sincronizador), ele é
  descartado para evitar loop infinito (ver `testes/erro_else_solto.pas`).

## Pascal-S

O que segue faz parte do Pascal-S de Wirth (1975).

- **Tipos simples:** `integer`, `real`, `boolean` (`true`/`false`) e `char`. O literal `'a'` (um caractere) é `char`;
  `char` aceita os relacionais (`=`, `<>`, `<`, ...) e é convertido de/para inteiro só por `ord(c)` e `chr(i)`.
- **Comentários:** `(* ... *)` (formato clássico do Pascal-S, pode ocupar várias linhas), além de `{ }` e `//`.
  Comentário `(*` ou `{` sem fechamento é erro léxico.
- **`maxint`:** constante padrão igual a 2147483647 (o `integer` ocupa 4 bytes na tabela de símbolos). Serve em
  expressões, em `const` e como limite de vetor. Literal inteiro maior que `maxint` gera **aviso** (não é erro).
- **Vetores e matrizes:** `array[lo..hi] of tipo` e `array[1..3, 1..3] of real` (matriz = vetor de vetor, `ArrayType`
  em `symtab.py`). Acesso `v[i]`, `m[i, j]` ou `m[i][j]`. Verificações: índice deve ser `integer`; só vetor pode ser
  indexado; tipo do elemento entra na checagem de atribuição/operadores; índice constante fora dos limites é erro;
  vetor inteiro não entra em aritmética nem em `write`.
- **`type` / `record`:** `type Pessoa = record nome: string; idade: integer end;`, aliases (`type Notas = array[1..3] of real`),
  registro anônimo em `var`, acesso `p.idade` (inclusive aninhado e combinado com `[ ]`). Verifica campo inexistente,
  campo repetido, tipo não declarado e tipo do campo na atribuição/operadores. Registros nomeados são equivalentes por nome; os anônimos, por estrutura.
- **`const`:** `const MAX = 10; PI = 3.14; LETRA = 'A'; ATIVO = true; NEG = -4; OUTRO = MAX;` O tipo vem do valor; constante
  não pode receber atribuição, ser lida por `read`, ser variável de `for` nem argumento `var`; constante inteira serve de
  limite de vetor (`array[1..MAX]`) e, como índice, tem o valor checado contra os limites.
- **`function` / `procedure`:** parâmetros por valor, retorno por `nome := valor` dentro da função, recursão, locais em
  ambiente filho (a tabela de símbolos mostra um escopo por subprograma). Verifica número e tipo dos argumentos, tipo do
  retorno, procedimento usado como valor e função/procedimento não declarado. Chamada sem parênteses é aceita para `f` sem parâmetros.
  Parâmetros por referência (`var x: integer`) exigem como argumento uma **variável** (inclusive `v[i]` e `p.campo`) de tipo
  idêntico; constante, literal ou expressão é erro (o parser roda com `tracking=True` para reconhecer variável pura).
- **Subprogramas aninhados:** cada subprograma pode ter seus próprios `const`, `type`, `var` e subprogramas internos
  (`procedure` dentro de `procedure`, em qualquer profundidade). O interno enxerga os locais do externo pela cadeia
  `parent`; o externo não enxerga os locais do interno (ver `testes/sucesso_subprogramas_aninhados.pas` e
  `testes/erro_aninhado_escopo.pas`).
- **Funções padrão** (com checagem de tipo do argumento):

  | Função | Argumento | Resultado |
  |---|---|---|
  | `abs`, `sqr` | `integer` ou `real` | mesmo tipo |
  | `sqrt`, `sin`, `cos`, `exp`, `ln`, `arctan` | `integer` ou `real` | `real` |
  | `odd` | `integer` | `boolean` |
  | `succ`, `pred` | `integer`, `char` ou `boolean` | mesmo tipo |
  | `round`, `trunc` | `real` | `integer` |
  | `ord` | `integer`, `char` ou `boolean` | `integer` |
  | `chr` | `integer` | `char` |

  `round` e `trunc` são as únicas formas de passar de `real` para `integer`. Um subprograma declarado com o mesmo
  nome tem prioridade sobre a função padrão.
- **Entrada e saída:** `write(...)`, `writeln(...)` e `writeln` sem argumentos; `read(v1, v2, ...)`, `readln(...)` e
  `readln` sem argumentos. `write` aceita largura de campo `x:w` e casas decimais `x:w:d` (largura `integer`; `:d` só
  para `real`); não aceita vetor, registro ou ponteiro inteiros. `read` exige **variáveis** (inclusive `v[i]` e `p.campo`)
  dos tipos `integer`, `real`, `char` ou `string`; constante ou `boolean` é erro.
- **`for` / `repeat` / `while` / `if`:** `for i := a to b do ...` e `downto` (variável de controle e limites devem ser `integer`);
  `repeat ... until cond` e `while cond do` (condição `boolean`).
- **`case`:** `case expr of rótulos: comando; ... [else comando] end`. O seletor deve ser ordinal (`integer`, `char` ou
  `boolean`); os rótulos são constantes (literais, negativos, `'c'`, `true`/`false` ou constantes nomeadas) do mesmo tipo do
  seletor, separados por vírgula; rótulo repetido é erro. `;` antes do `else` e antes do `end` é opcional, e o braço pode ser
  vazio ou um bloco `begin ... end`. Não há intervalos (`1..5`). O `else` de um `if` sem `else` dentro de um braço casa com
  esse `if` (mesma regra do `else` pendente).
- **Operadores aritméticos:** `+`, `-`, `*` exigem o mesmo tipo numérico nos dois lados e mantêm o tipo. `/` é **sempre** a
  divisão real: só aceita operandos `real` e devolve `real` (`1 / 2` é erro; use `1 div 2`). `div` e `mod` exigem dois
  operandos `integer` e devolvem `integer`.
- **Sinal unário (`-a`, `+a`):** como no Pascal padrão, o sinal fica no início de `simple_expr` (`simple_expr : MINUS term`), então `-a * b` é `-(a * b)` e `b - -a` é erro sintático (escreva `b - (-a)`). O operando deve ser `integer` ou `real` e o tipo é mantido; `-3` continua constante para a checagem de índice (ver `testes/sucesso_menos_unario.pas` e `testes/erro_menos_unario.pas`).

## Extensões fora do Pascal-S

Estes recursos **não existem no Pascal-S** de Wirth; vêm do Pascal padrão/Turbo Pascal e foram mantidos como extensões
(estão implementados e testados).

- **`uses` (Turbo Pascal):** `uses crt, math;` registra as unidades (repetição é erro) e lista no log. Não há biblioteca real por trás.
- **Tipo `string` (Turbo Pascal):** no Pascal-S, texto só aparece como literal dentro de `write`. Aqui `string` é um tipo
  declarável, com literais `'texto'`; `+` concatena e `=`/`<>` comparam. Um `char` pode ser atribuído a uma `string` e
  concatenado/comparado com ela (`s := 'letra: ' + c`); misturar `string` com outros tipos é erro.
- **Ponteiros (Pascal padrão):** `^tipo`, desreferência `p^` (encadeável: `p^.prox^.valor`), `nil`, `new(p)` e `dispose(p)`.
  Ponteiros só são compatíveis com o mesmo tipo-alvo ou `nil`; aritmética e `<`/`>` em ponteiros é erro; `new`/`dispose`
  em não-ponteiro é erro. Aceita referência adiante (`PNo = ^No; No = record ... prox: PNo end`), resolvida via ponteiro
  para a entrada da tabela de símbolos; alvo que nunca é declarado gera erro ao final. Registros nomeados usam equivalência por nome.
- **Comentário `//`** (Delphi/Free Pascal).
