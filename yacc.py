"""Parser LALR(1) e verificador semântico Pascal-S usando PLY
Uso: python yacc.py testes/sucesso_semantico.pas
"""
import sys
import ply.yacc as yacc
from lex import tokens, build_lexer, find_column
from symtab import ScopeManager

start = "program"
precedence = (
    ("nonassoc", "IFX"),
    ("nonassoc", "ELSE"),
)
# A precedência dos operadores aritméticos e lógicos é imposta pela própria estrutura da gramática

symtab = None
lexer = None
stream = None
PARSER = None
errors = []
syntax_errors = 0
semantic_errors = 0
last_error_pos = None

# Sincronizadores do modo pânico: ';' e 'end' (para o último comando do bloco, que não termina com ';')
SYNC_TOKENS = {"SEMICOLON", "END"}

NUMERIC = ("integer", "real")
RELOPS = {"=", "<>", "<", "<=", ">", ">="}

class TokenStream:
    #fonte de tokens do parser (getNextToken sob demanda) com 'pushback'
    #para devolver ao parser o token de sincronização

    def __init__(self, lx):
        self.lexer = lx
        self.pushback = []

    def getNextToken(self):
        if self.pushback:
            return self.pushback.pop()
        return self.lexer.getNextToken()


class CompilationAbort(Exception):
    pass


def semantic_error(message, lineno=None, fatal=False):
    global semantic_errors
    semantic_errors += 1
    where = f"linha {lineno}" if lineno is not None else "local desconhecido"
    msg = f"Erro semântico ({where}): {message}"
    errors.append(msg)
    print(msg)
    if fatal:
        raise CompilationAbort(msg)


# Tipos: 'integer', 'real', 'boolean'. None = subexpressão que já gerou erro
# (não gera mensagens em cascata).
def check_operands(op, t1, t2, lineno):
    if t1 is None or t2 is None:
        return None
    if op in ("and", "or"):
        if t1 == "boolean" and t2 == "boolean":
            return "boolean"
        semantic_error(f"o operador '{op}' exige operandos booleanos (recebeu {t1} e {t2}).", lineno, fatal=True)
        return None
    if t1 not in NUMERIC or t2 not in NUMERIC:
        semantic_error(f"o operador '{op}' exige operandos numéricos (recebeu {t1} e {t2}).", lineno, fatal=True)
        return None
    if t1 != t2:
        semantic_error(f"operandos incompatíveis para '{op}' ({t1} e {t2}); "
                       f"não há conversão implícita entre integer e real.", lineno, fatal=True)
        return None
    return "boolean" if op in RELOPS else t1       # '/' mantém o tipo dos operandos


def check_condition(kw, t, lineno):
    if t is not None and t != "boolean":
        semantic_error(f"a condição do '{kw}' deve ser booleana (recebeu {t}).", lineno, fatal=True)


# Programa e declarações
 
def p_program(p):
    "program : PROGRAM ID SEMICOLON decl_list block DOT"
    p[0] = True


def p_program_error(p):
    "program : PROGRAM error SEMICOLON decl_list block DOT"
    PARSER.errok()


def p_decl_list_empty(p):
    "decl_list :"
    p[0] = None


def p_decl_list_var(p):
    "decl_list : VAR decl_group_list"
    p[0] = None


def p_decl_group_list_one(p):
    "decl_group_list : decl_group"
    p[0] = None


def p_decl_group_list_more(p):
    "decl_group_list : decl_group_list decl_group"
    p[0] = None


def p_decl_group(p):
    "decl_group : id_list COLON type SEMICOLON"
    for symbol, line in p[1]:
        if symtab.declare(symbol, p[3], line) is None:
            semantic_error(f"variável '{symbol.name}' declarada mais de uma vez no mesmo escopo "
                           f"(1ª declaração na linha {symbol.lineno}).", line)


def p_decl_group_error(p):
    "decl_group : error SEMICOLON"
    PARSER.errok()
    p[0] = None


def p_id_list_one(p):
    "id_list : ID"
    p[0] = [(p[1], p.lineno(1))]


def p_id_list_more(p):
    "id_list : id_list COMMA ID"
    p[0] = p[1] + [(p[3], p.lineno(3))]


def p_type_integer(p):
    "type : INTEGER"
    p[0] = "integer"


def p_type_real(p):
    "type : REAL"
    p[0] = "real"


 
# Comandos
 
def p_block_enter(p):
    "block_enter :"
    # Redução vazia logo após BEGIN: cria um ambiente para cada bloco.
    # O lexer continua sob demanda e os identificadores declarados no escopo
    # externo continuam acessíveis pela cadeia parent.
    symtab.enter_scope(name=f"bloco_linha_{p.lineno(0) or lexer.lineno}")


def p_block(p):
    "block : BEGIN block_enter stmt_list END"
    symtab.exit_scope()
    p[0] = None


def p_stmt_list_one(p):
    "stmt_list : stmt"
    p[0] = None


def p_stmt_list_more(p):
    "stmt_list : stmt_list SEMICOLON stmt"
    p[0] = None


def p_stmt_assign(p):
    "stmt : assign_stmt"
    p[0] = None


def p_stmt_if(p):
    "stmt : if_stmt"
    p[0] = None


def p_stmt_while(p):
    "stmt : while_stmt"
    p[0] = None


def p_stmt_write(p):
    "stmt : write_stmt"
    p[0] = None


def p_stmt_block(p):
    "stmt : block"
    p[0] = None


def p_stmt_empty(p):
    "stmt :"
    p[0] = None


def p_stmt_error(p):
    "stmt : error"
    # O comando inválido vira um 'stmt' vazio. O ';' (ou 'end') que sincronizou
    # NÃO é consumido aqui: continua sendo o separador de stmt_list.
    PARSER.errok()
    print("Recuperação sintática: análise retomada no sincronizador.")
    p[0] = None


def p_assign_stmt(p):
    "assign_stmt : ID ASSIGN expr"
    symbol, rhs = p[1], p[3]
    if not symbol.declared:
        semantic_error(f"variável '{symbol.name}' usada em atribuição sem declaração.", p.lineno(1))
    elif rhs is not None and symbol.type != rhs:
        semantic_error(f"atribuição incompatível: '{symbol.name}' é {symbol.type}, "
                       f"mas a expressão é {rhs}.", p.lineno(2), fatal=True)
    p[0] = None


def p_if_stmt(p):
    "if_stmt : IF expr THEN stmt %prec IFX"
    check_condition("if", p[2], p.lineno(1))


def p_if_else_stmt(p):
    "if_stmt : IF expr THEN stmt ELSE stmt"
    check_condition("if", p[2], p.lineno(1))


def p_while_stmt(p):
    "while_stmt : WHILE expr DO stmt"
    check_condition("while", p[2], p.lineno(1))


def p_write_stmt(p):
    "write_stmt : WRITELN LPAREN expr_list RPAREN"
    p[0] = None


def p_expr_list_one(p):
    "expr_list : expr"
    p[0] = [p[1]]


def p_expr_list_more(p):
    "expr_list : expr_list COMMA expr"
    p[0] = p[1] + [p[3]]


 
# Expressões
 
def p_expr_simple(p):
    "expr : simple_expr"
    p[0] = p[1]


def p_expr_relational(p):
    "expr : simple_expr relop simple_expr"
    op, lineno = p[2]
    p[0] = check_operands(op, p[1], p[3], lineno)


def p_relop(p):
    """relop : EQ
             | NE
             | LT
             | LE
             | GT
             | GE"""
    # p.lineno() de um não-terminal vale 0 (sem tracking), então a linha
    # do operador viaja junto com o valor.
    p[0] = (p[1], p.lineno(1))


def p_simple_expr_term(p):
    "simple_expr : term"
    p[0] = p[1]


def p_simple_expr_binary(p):
    """simple_expr : simple_expr PLUS term
                   | simple_expr MINUS term
                   | simple_expr OR term"""
    p[0] = check_operands(p[2].lower(), p[1], p[3], p.lineno(2))


def p_term_factor(p):
    "term : factor"
    p[0] = p[1]


def p_term_binary(p):
    """term : term TIMES factor
            | term DIVIDE factor
            | term AND factor"""
    p[0] = check_operands(p[2].lower(), p[1], p[3], p.lineno(2))


def p_factor_id(p):
    "factor : ID"
    symbol = p[1]
    if not symbol.declared:
        semantic_error(f"variável '{symbol.name}' usada sem declaração.", p.lineno(1))
        p[0] = None
    else:
        p[0] = symbol.type


def p_factor_int(p):
    "factor : NUM_INT"
    p[0] = "integer"


def p_factor_real(p):
    "factor : NUM_REAL"
    p[0] = "real"


def p_factor_group(p):
    "factor : LPAREN expr RPAREN"
    p[0] = p[2]


def p_factor_not(p):
    "factor : NOT factor"
    t = p[2]
    if t is None:
        p[0] = None
    elif t != "boolean":
        semantic_error(f"o operador 'not' exige operando booleano (recebeu {t}).", p.lineno(1), fatal=True)
        p[0] = None
    else:
        p[0] = "boolean"


 
# Erros sintáticos: modo pânico
 
def p_error(p):
    global syntax_errors, last_error_pos
    if p is not None and p.lexpos == last_error_pos:
        # sem progresso: o parser voltou ao mesmo token ofensor (else solto,
        # que não é sincronizador), descarta-o em silêncio para não entrar em loop
        PARSER.errok()
        return None
    syntax_errors += 1
    if p is None:
        col = find_column(lexer.lexdata, len(lexer.lexdata))
        msg = f"Erro sintático [linha {lexer.lineno}, coluna {col}]: fim inesperado do arquivo."
        errors.append(msg)
        print(msg)
        return
    col = find_column(lexer.lexdata, p.lexpos)
    value = p.value.name if hasattr(p.value, "name") else p.value
    msg = f"Erro sintático [linha {p.lineno}, coluna {col}]: token inesperado {p.type} ({value!r})."
    errors.append(msg)
    print(msg)
    last_error_pos = p.lexpos
    if p.type in SYNC_TOKENS:
        return                     # já estamos no sincronizador
    # Modo pânico: descarta tokens até o próximo sincronizador e o devolve ao
    # parser; as produções `... : error` desempilham até um estado que aceite
    # 'error' e retomam a análise a partir dele.
    descartados = 0
    while True:
        tok = stream.getNextToken()
        if tok is None:
            break
        if tok.type in SYNC_TOKENS:
            stream.pushback.append(tok)
            break
        descartados += 1
    print(f"    [modo pânico] {descartados} token(s) descartado(s).")


def run_file(path):
    global symtab, lexer, stream, PARSER, errors, syntax_errors, semantic_errors, last_error_pos
    symtab = ScopeManager()
    errors, syntax_errors, semantic_errors = [], 0, 0
    last_error_pos = None
    with open(path, encoding="utf-8") as source_file:
        source = source_file.read()
    lexer = build_lexer(symtab)
    stream = TokenStream(lexer)
    PARSER = yacc.yacc(start=start, debug=True, write_tables=False, errorlog=yacc.NullLogger())
    try:
        PARSER.parse(source, lexer=lexer, tokenfunc=stream.getNextToken)
    except CompilationAbort:
        print("Compilação abortada no primeiro erro de tipo.")
    finally:
        # Se um erro fatal impedir a redução de block, não deixe o gerenciador
        # apontando para um escopo interno ao imprimir o estado final.
        while symtab.top.parent is not None:
            symtab.exit_scope()
    print(symtab.dump())
   
    print(f"\nErros léxicos: {len(lexer.errors)}")
    print(f"Erros sintáticos: {syntax_errors}")
    print(f"Erros semânticos: {semantic_errors}")
    success = not (lexer.errors or syntax_errors or semantic_errors)
    print("\nResultado:", "SUCESSO" if success else "FALHA")
    return 0 if success else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python yacc.py arquivo.pas")
    sys.exit(run_file(sys.argv[1]))