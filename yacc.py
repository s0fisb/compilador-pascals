"""Parser LALR(1) e verificador semântico Pascal-S usando PLY
Uso: python yacc.py testes/sucesso_semantico.pas
"""
import sys
import ply.yacc as yacc
from lex import tokens, build_lexer, find_column
from symtab import ScopeManager, ArrayType, RecordType, PointerType, ForwardRef, Symbol

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
var_spans = {}          # (início, fim) no fonte -> Var, para saber se um argumento é uma variável pura
units = []
pointer_ctx = 0          # >0 enquanto se analisa o alvo de um ^ (permite referência adiante)
forward_refs = []
func_stack = []        # subprogramas em análise (para permitir "f := valor" dentro de f)
syntax_errors = 0
semantic_errors = 0
last_error_pos = None

# Sincronizadores do modo pânico: ';' e 'end' (para o último comando do bloco, que não termina com ';')
SYNC_TOKENS = {"SEMICOLON", "END", "UNTIL"}

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


class ConstInt(str):
    """Tipo 'integer' de uma constante literal; guarda o valor para checar limites de índice."""
    def __new__(cls, value):
        obj = super().__new__(cls, "integer")
        obj.const = value
        return obj


class Var:
    """Resultado de 'variable': símbolo base, tipo do acesso atual e linha."""
    def __init__(self, symbol, type_, lineno, text, plain=False):
        self.symbol, self.type, self.lineno, self.text = symbol, type_, lineno, text
        self.plain = plain                    # True = identificador puro (sem [ ] nem .campo)


class ArgList(list):
    """Lista de tipos de uma expr_list, com a posição (no fonte) de cada expressão."""
    spans = ()


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


# Tipos: 'integer', 'real', 'boolean' (todos distintos, sem coerção). None = subexpressão que já gerou erro
# (não gera mensagens em cascata).
def compatible(formal, actual):
    """Compatibilidade de atribuição/argumento: tipos idênticos, ou nil para qualquer ponteiro."""
    if formal is None or actual is None:
        return True
    if formal == actual:
        return True
    return isinstance(formal, PointerType) and actual == "nil"


def check_operands(op, t1, t2, lineno):
    if t1 is None or t2 is None:
        return None
    if op in ("div", "mod"):
        if t1 == "integer" and t2 == "integer":
            return "integer"
        semantic_error(f"o operador '{op}' exige operandos integer (recebeu {t1} e {t2}).", lineno, fatal=True)
        return None
    if op in ("and", "or"):
        if t1 == "boolean" and t2 == "boolean":
            return "boolean"
        semantic_error(f"o operador '{op}' exige operandos booleanos (recebeu {t1} e {t2}).", lineno, fatal=True)
        return None
    if isinstance(t1, PointerType) or isinstance(t2, PointerType) or t1 == "nil" or t2 == "nil":
        if op in ("=", "<>") and (compatible(t1, t2) or compatible(t2, t1)):
            return "boolean"
        semantic_error(f"operador '{op}' inválido para ponteiros ({t1} e {t2}); "
                       f"só = e <> entre ponteiros compatíveis ou nil.", lineno, fatal=True)
        return None
    if t1 != t2:
        semantic_error(f"operandos incompatíveis para '{op}' ({t1} e {t2}); "
                       f"não há conversão implícita entre tipos distintos.", lineno, fatal=True)
        return None
    if t1 == "boolean" and op in ("=", "<>"):
        return "boolean"                       # igualdade entre booleanos é permitida
    if t1 == "string":
        if op == "+":
            return "string"                    # concatenação
        if op in ("=", "<>"):
            return "boolean"
    if t1 not in NUMERIC:
        semantic_error(f"o operador '{op}' exige operandos numéricos (recebeu {t1} e {t2}).", lineno, fatal=True)
        return None
    return "boolean" if op in RELOPS else t1       # '/' mantém o tipo dos operandos


def check_condition(kw, t, lineno):
    if t is not None and t != "boolean":
        semantic_error(f"a condição do '{kw}' deve ser booleana (recebeu {t}).", lineno, fatal=True)


def check_call(sym, args, lineno):
    """Valida chamada de função/procedimento; devolve o tipo de retorno (None p/ procedimento)."""
    if sym.kind not in ("func", "proc"):
        semantic_error(f"'{sym.name}' não é função nem procedimento.", lineno, fatal=True)
        return None
    if len(args) != len(sym.params):
        semantic_error(f"'{sym.name}' espera {len(sym.params)} argumento(s), mas recebeu {len(args)}.", lineno)
        return sym.type if sym.kind == "func" else None
    for i, (formal, actual) in enumerate(zip(sym.params, args), 1):
        if i <= len(sym.refs) and sym.refs[i - 1]:               # parâmetro por referência (var)
            span = args.spans[i - 1] if len(getattr(args, "spans", ())) >= i else None
            v = var_spans.get(span)
            if v is None:
                semantic_error(f"argumento {i} de '{sym.name}': parâmetro 'var' exige uma variável "
                               f"(não aceita constante, literal nem expressão).", lineno, fatal=True)
            if formal is not None and actual is not None and formal != actual:
                semantic_error(f"argumento {i} de '{sym.name}': parâmetro 'var' exige tipo idêntico "
                               f"(esperado {formal}, recebido {actual}).", lineno, fatal=True)
            continue
        if not compatible(formal, actual):
            semantic_error(f"argumento {i} de '{sym.name}': esperado {formal}, recebido {actual}; "
                           f"não há conversão implícita.", lineno, fatal=True)
    return sym.type if sym.kind == "func" else None


# Programa e declarações
 
def p_program(p):
    "program : PROGRAM ID SEMICOLON uses_opt const_opt type_opt decl_list subprogram_list block DOT"
    p[0] = True


def p_program_error(p):
    "program : PROGRAM error SEMICOLON uses_opt const_opt type_opt decl_list subprogram_list block DOT"
    PARSER.errok()


# uses (importação de unidades)
def p_uses_empty(p):
    "uses_opt :"


def p_uses(p):
    "uses_opt : USES unit_list SEMICOLON"
    for name, line in p[2]:
        if name.casefold() in (u.casefold() for u in units):
            semantic_error(f"unidade '{name}' já foi importada em 'uses'.", line)
        else:
            units.append(name)


def p_unit_list_one(p):
    "unit_list : ID"
    p[0] = [(p[1].name, p.lineno(1))]


def p_unit_list_more(p):
    "unit_list : unit_list COMMA ID"
    p[0] = p[1] + [(p[3].name, p.lineno(3))]


# const (constantes nomeadas)
def p_const_opt_empty(p):
    "const_opt :"


def p_const_opt(p):
    "const_opt : CONST const_decl_list"


def p_const_decl_list_one(p):
    "const_decl_list : const_decl"


def p_const_decl_list_more(p):
    "const_decl_list : const_decl_list const_decl"


def p_const_decl(p):
    "const_decl : ID EQ const_value SEMICOLON"
    sym, (t, val) = p[1], p[3]
    d = symtab.declare(sym, t, p.lineno(1), kind="const")
    if d is None:
        semantic_error(f"'{sym.name}' declarado mais de uma vez no mesmo escopo "
                       f"(1ª declaração na linha {sym.lineno}).", p.lineno(1))
    else:
        d.value = val


def p_const_value_int(p):
    "const_value : NUM_INT"
    p[0] = ("integer", p[1])


def p_const_value_real(p):
    "const_value : NUM_REAL"
    p[0] = ("real", p[1])


def p_const_value_string(p):
    "const_value : STRING"
    p[0] = ("string", p[1])


def p_const_value_bool(p):
    """const_value : TRUE
                   | FALSE"""
    p[0] = ("boolean", p[1].lower() == "true")


def p_const_value_neg_int(p):
    "const_value : MINUS NUM_INT"
    p[0] = ("integer", -p[2])


def p_const_value_neg_real(p):
    "const_value : MINUS NUM_REAL"
    p[0] = ("real", -p[2])


def p_const_value_name(p):
    "const_value : ID"
    sym = p[1]
    if sym.declared and sym.kind == "const":
        p[0] = (sym.type, sym.value)
    else:
        semantic_error(f"'{sym.name}' não é uma constante declarada.", p.lineno(1))
        p[0] = (None, None)


# type (tipos nomeados / registros)
def p_type_opt_empty(p):
    "type_opt :"


def p_type_opt(p):
    "type_opt : TYPE type_decl_list"


def p_type_decl_list_one(p):
    "type_decl_list : type_decl"


def p_type_decl_list_more(p):
    "type_decl_list : type_decl_list type_decl"


def p_type_decl(p):
    "type_decl : ID EQ type SEMICOLON"
    sym, t = p[1], p[3]
    if isinstance(t, RecordType) and t.name is None:
        t.name = sym.name
    if symtab.declare(sym, t, p.lineno(1), kind="type") is None:
        semantic_error(f"'{sym.name}' declarado mais de uma vez no mesmo escopo "
                       f"(1ª declaração na linha {sym.lineno}).", p.lineno(1))


def p_type_named(p):
    "type : ID"
    sym = p[1]
    if sym.declared and sym.kind == "type":
        p[0] = sym.type
    elif pointer_ctx > 0 and not sym.declared:
        fr = ForwardRef(sym, p.lineno(1))          # PNo = ^No; No = record ... end
        forward_refs.append(fr)
        p[0] = fr
    else:
        semantic_error(f"tipo '{sym.name}' não declarado.", p.lineno(1))
        p[0] = None


def p_ptr_start(p):
    "ptr_start : CARET"
    global pointer_ctx
    pointer_ctx += 1


def p_type_pointer(p):
    "type : ptr_start type"
    global pointer_ctx
    pointer_ctx -= 1
    inner = p[2]
    if inner is None:
        p[0] = None
    elif isinstance(inner, ForwardRef):
        p[0] = PointerType(ref=inner.sym)
    else:
        p[0] = PointerType(target=inner)


def p_type_string(p):
    "type : STRINGTYPE"
    p[0] = "string"


def p_type_record(p):
    """type : RECORD field_decl_list END
            | RECORD field_decl_list SEMICOLON END"""
    seen, fields = set(), []
    for name, t, line in p[2]:
        if name.casefold() in seen:
            semantic_error(f"campo '{name}' repetido no registro.", line)
            continue
        seen.add(name.casefold())
        fields.append((name, t))
    p[0] = RecordType(None, fields)


def p_field_decl_list_one(p):
    "field_decl_list : field_decl"
    p[0] = p[1]


def p_field_decl_list_more(p):
    "field_decl_list : field_decl_list SEMICOLON field_decl"
    p[0] = p[1] + p[3]


def p_field_decl(p):
    "field_decl : id_list COLON type"
    p[0] = [(sym.name, p[3], line) for sym, line in p[1]]


# subprogramas (function / procedure)
def p_subprogram_list_empty(p):
    "subprogram_list :"


def p_subprogram_list_more(p):
    "subprogram_list : subprogram_list subprogram"


def p_subprogram(p):
    "subprogram : sub_header decl_list block SEMICOLON"
    symtab.exit_scope()                       # sai do ambiente do subprograma
    func_stack.pop()


def begin_subprogram(kind, sym, params, ret, line):
    """Declara o subprograma no escopo externo e abre o ambiente filho com os parâmetros."""
    d = symtab.declare(sym, ret, line, kind=kind)
    if d is None:
        semantic_error(f"'{sym.name}' declarado mais de uma vez no mesmo escopo "
                       f"(1ª declaração na linha {sym.lineno}).", line)
        d = Symbol(sym.name, ret, line)
        d.kind, d.declared = kind, True
    if kind == "func" and isinstance(ret, (ArrayType, RecordType)):
        semantic_error(f"função '{sym.name}' não pode retornar vetor ou registro.", line)
    d.params = [t for _, t, _, _ in params]
    d.refs = [r for _, _, _, r in params]
    symtab.enter_scope(name=f"{kind} {sym.name}")
    func_stack.append(d)
    for psym, ptype, pline, _ in params:
        if symtab.declare(psym, ptype, pline) is None:
            semantic_error(f"parâmetro '{psym.name}' repetido em '{sym.name}'.", pline)


def p_sub_header_func(p):
    "sub_header : FUNCTION ID LPAREN params RPAREN COLON type SEMICOLON"
    begin_subprogram("func", p[2], p[4], p[7], p.lineno(2))


def p_sub_header_func_noargs(p):
    "sub_header : FUNCTION ID COLON type SEMICOLON"
    begin_subprogram("func", p[2], [], p[4], p.lineno(2))


def p_sub_header_proc(p):
    "sub_header : PROCEDURE ID LPAREN params RPAREN SEMICOLON"
    begin_subprogram("proc", p[2], p[4], None, p.lineno(2))


def p_sub_header_proc_noargs(p):
    "sub_header : PROCEDURE ID SEMICOLON"
    begin_subprogram("proc", p[2], [], None, p.lineno(2))


def p_params_one(p):
    "params : param_group"
    p[0] = p[1]


def p_params_more(p):
    "params : params SEMICOLON param_group"
    p[0] = p[1] + p[3]


def p_param_group(p):
    "param_group : id_list COLON type"
    p[0] = [(sym, p[3], line, False) for sym, line in p[1]]


def p_param_group_ref(p):
    "param_group : VAR id_list COLON type"
    p[0] = [(sym, p[4], line, True) for sym, line in p[2]]


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
    p[0] = None
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


def p_type_boolean(p):
    "type : BOOLEAN"
    p[0] = "boolean"


def p_type_array(p):
    "type : ARRAY LBRACKET range_list RBRACKET OF type"
    t = p[6]
    for lo, hi, line in reversed(p[3]):          # a última dimensão é a mais interna
        if lo is None or hi is None:             # limite inválido já reportado: sem cascata
            t = None
            break
        if lo > hi:
            semantic_error(f"limites inválidos no vetor: {lo}..{hi} (inferior > superior).", line)
        t = ArrayType(lo, hi, t)
    p[0] = t


def p_range_list_one(p):
    "range_list : range"
    p[0] = [p[1]]


def p_range_list_more(p):
    "range_list : range_list COMMA range"
    p[0] = p[1] + [p[3]]


def p_range(p):
    "range : bound DOTDOT bound"
    p[0] = (p[1], p[3], p.lineno(2))


def p_bound_pos(p):
    "bound : NUM_INT"
    p[0] = p[1]


def p_bound_const(p):
    "bound : ID"
    sym = p[1]
    if sym.declared and sym.kind == "const" and sym.type == "integer":
        p[0] = sym.value
    else:
        semantic_error(f"limite de vetor deve ser inteiro literal ou constante inteira ('{sym.name}' não é).",
                       p.lineno(1))
        p[0] = None


def p_bound_neg(p):
    "bound : MINUS NUM_INT"
    p[0] = -p[2]


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


def p_stmt_new_dispose(p):
    """stmt : NEW LPAREN variable RPAREN
            | DISPOSE LPAREN variable RPAREN"""
    v, name = p[3], p[1].lower()
    if not v.symbol.declared:
        semantic_error(f"'{v.symbol.name}' usado em {name} sem declaração.", v.lineno)
    elif v.type is not None and not isinstance(v.type, PointerType):
        semantic_error(f"'{name}' exige uma variável ponteiro (recebeu '{v.text}' do tipo {v.type}).",
                       p.lineno(1), fatal=True)
    p[0] = None


def p_stmt_call(p):
    """stmt : ID LPAREN expr_list RPAREN
            | ID LPAREN RPAREN"""
    sym = p[1]
    args = p[3] if len(p) == 5 else []
    if not sym.declared:
        semantic_error(f"'{sym.name}' chamado sem declaração.", p.lineno(1))
    else:
        check_call(sym, args, p.lineno(1))
    p[0] = None


def p_stmt_bare(p):
    "stmt : variable"
    v = p[1]
    if not v.symbol.declared:
        semantic_error(f"'{v.symbol.name}' usado como comando sem declaração.", v.lineno)
    elif v.plain and v.symbol.kind in ("func", "proc"):
        check_call(v.symbol, [], v.lineno)       # chamada sem parênteses
    else:
        semantic_error(f"'{v.text}' não é um comando válido (esperado atribuição ou chamada).", v.lineno)
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
    "assign_stmt : variable ASSIGN expr"
    var, rhs = p[1], p[3]
    kind = var.symbol.kind
    if not var.symbol.declared:
        semantic_error(f"variável '{var.symbol.name}' usada em atribuição sem declaração.", var.lineno)
    elif kind == "type":
        semantic_error(f"'{var.symbol.name}' é um tipo e não pode receber atribuição.", var.lineno)
    elif kind == "const" and var.plain:
        semantic_error(f"'{var.symbol.name}' é uma constante e não pode receber atribuição.", var.lineno)
    elif kind in ("func", "proc") and not (kind == "func" and var.plain and func_stack and func_stack[-1] is var.symbol):
        semantic_error(f"não é possível atribuir a '{var.symbol.name}': só se atribui ao nome da função "
                       f"dentro do seu próprio corpo.", var.lineno)
    elif not compatible(var.type, rhs):
        semantic_error(f"atribuição incompatível: '{var.text}' é {var.type}, "
                       f"mas a expressão é {rhs}.", p.lineno(2), fatal=True)
    p[0] = None


def p_variable_id(p):
    "variable : ID"
    sym = p[1]
    p[0] = Var(sym, sym.type if sym.declared and sym.kind != "type" else None, p.lineno(1), sym.name, plain=True)


def p_variable_field(p):
    "variable : variable DOT ID"
    v, fname, line = p[1], p[3].name, p.lineno(2)
    t = v.type
    if t is not None:
        if not isinstance(t, RecordType):
            semantic_error(f"'{v.text}' é {t} e não é um registro; não possui campo '{fname}'.", line, fatal=True)
            t = None
        else:
            found, ft = t.field(fname)
            if not found:
                semantic_error(f"o registro '{v.text}' ({t}) não possui o campo '{fname}'.", line)
            t = ft
    p[0] = Var(v.symbol, t, v.lineno, f"{v.text}.{fname}")


def p_variable_deref(p):
    "variable : variable CARET"
    v, t = p[1], p[1].type
    if t is not None:
        if not isinstance(t, PointerType):
            semantic_error(f"'{v.text}' é {t} e não é um ponteiro; não pode ser desreferenciado com ^.",
                           p.lineno(2), fatal=True)
            t = None
        else:
            t = t.target
    p[0] = Var(v.symbol, t, v.lineno, v.text + "^")


def p_variable_index(p):
    "variable : variable LBRACKET expr_list RBRACKET"
    v, line = p[1], p.lineno(2)
    t = v.type
    for ix in p[3]:
        if t is None:
            break
        if not isinstance(t, ArrayType):
            semantic_error(f"'{v.text}' é {t} e não pode ser indexado com [ ].", line, fatal=True)
            t = None
            break
        if ix is not None:
            if ix != "integer":
                semantic_error(f"o índice de '{v.symbol.name}' deve ser integer (recebeu {ix}).", line, fatal=True)
            else:
                c = getattr(ix, "const", None)
                if c is not None and not (t.lo <= c <= t.hi):
                    semantic_error(f"índice {c} fora dos limites [{t.lo}..{t.hi}] de '{v.symbol.name}'.", line)
        t = t.elem
    p[0] = Var(v.symbol, t, v.lineno, v.symbol.name + "[...]")


def p_if_stmt(p):
    "if_stmt : IF expr THEN stmt %prec IFX"
    check_condition("if", p[2], p.lineno(1))


def p_if_else_stmt(p):
    "if_stmt : IF expr THEN stmt ELSE stmt"
    check_condition("if", p[2], p.lineno(1))


def p_while_stmt(p):
    "while_stmt : WHILE expr DO stmt"
    check_condition("while", p[2], p.lineno(1))


def p_stmt_for_repeat(p):
    """stmt : for_stmt
            | repeat_stmt"""
    p[0] = None


def p_for_stmt(p):
    """for_stmt : FOR ID ASSIGN expr TO expr DO stmt
                | FOR ID ASSIGN expr DOWNTO expr DO stmt"""
    sym, line = p[2], p.lineno(1)
    if not sym.declared:
        semantic_error(f"variável de controle '{sym.name}' do 'for' usada sem declaração.", line)
    elif sym.kind != "var":
        semantic_error(f"'{sym.name}' não pode ser variável de controle do 'for' "
                       f"({'constante' if sym.kind == 'const' else sym.kind}).", line)
    elif sym.type != "integer":
        semantic_error(f"a variável de controle '{sym.name}' do 'for' deve ser integer (é {sym.type}).",
                       line, fatal=True)
    for nome, t in (("inicial", p[4]), ("final", p[6])):
        if t is not None and t != "integer":
            semantic_error(f"o valor {nome} do 'for' deve ser integer (recebeu {t}).", line, fatal=True)
    p[0] = None


def p_repeat_stmt(p):
    "repeat_stmt : REPEAT stmt_list UNTIL expr"
    check_condition("repeat", p[4], p.lineno(3))
    p[0] = None


def p_write_stmt(p):
    "write_stmt : WRITELN LPAREN expr_list RPAREN"
    for t in p[3]:
        if isinstance(t, (ArrayType, RecordType, PointerType)) or t == "nil":
            semantic_error(f"writeln não aceita valor do tipo {t}; escreva campos ou elementos escalares.", p.lineno(1))
    p[0] = None


def p_expr_list_one(p):
    "expr_list : expr"
    a = ArgList([p[1]])
    a.spans = [p.lexspan(1)]
    p[0] = a


def p_expr_list_more(p):
    "expr_list : expr_list COMMA expr"
    a = ArgList(list(p[1]) + [p[3]])
    a.spans = list(p[1].spans) + [p.lexspan(3)]
    p[0] = a


 
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
            | term DIV factor
            | term MOD factor
            | term AND factor"""
    p[0] = check_operands(p[2].lower(), p[1], p[3], p.lineno(2))


def p_factor_var(p):
    "factor : variable"
    v = p[1]
    if not v.symbol.declared:
        semantic_error(f"variável '{v.symbol.name}' usada sem declaração.", v.lineno)
        p[0] = None
    elif v.symbol.kind == "type":
        semantic_error(f"'{v.symbol.name}' é um tipo, não pode ser usado como valor.", v.lineno)
        p[0] = None
    elif v.plain and v.symbol.kind == "func":
        p[0] = check_call(v.symbol, [], v.lineno)          # função sem parênteses
    elif v.plain and v.symbol.kind == "proc":
        semantic_error(f"o procedimento '{v.symbol.name}' não retorna valor e não pode ser usado em expressão.",
                       v.lineno, fatal=True)
        p[0] = None
    elif v.plain and v.symbol.kind == "const":
        p[0] = ConstInt(v.symbol.value) if v.symbol.type == "integer" else v.symbol.type
    else:
        if v.symbol.kind == "var":
            var_spans[p.lexspan(1)] = v                       # argumento var só aceita variável pura
        p[0] = v.type


def p_factor_call(p):
    """factor : ID LPAREN expr_list RPAREN
              | ID LPAREN RPAREN"""
    sym = p[1]
    args = p[3] if len(p) == 5 else []
    if not sym.declared:
        semantic_error(f"função '{sym.name}' chamada sem declaração.", p.lineno(1))
        p[0] = None
    elif sym.kind == "proc":
        semantic_error(f"o procedimento '{sym.name}' não retorna valor e não pode ser usado em expressão.",
                       p.lineno(1), fatal=True)
        p[0] = None
    else:
        p[0] = check_call(sym, args, p.lineno(1))


def p_factor_nil(p):
    "factor : NIL"
    p[0] = "nil"


def p_factor_string(p):
    "factor : STRING"
    p[0] = "string"


def p_factor_int(p):
    "factor : NUM_INT"
    p[0] = ConstInt(p[1])


def p_factor_real(p):
    "factor : NUM_REAL"
    p[0] = "real"


def p_factor_bool(p):
    """factor : TRUE
              | FALSE"""
    p[0] = "boolean"


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
    global symtab, lexer, stream, PARSER, errors, syntax_errors, semantic_errors, last_error_pos, pointer_ctx
    symtab = ScopeManager()
    errors, syntax_errors, semantic_errors = [], 0, 0
    units.clear()
    var_spans.clear()
    forward_refs.clear()
    pointer_ctx = 0
    func_stack.clear()
    last_error_pos = None
    with open(path, encoding="utf-8") as source_file:
        source = source_file.read()
    lexer = build_lexer(symtab)
    stream = TokenStream(lexer)
    PARSER = yacc.yacc(start=start, debug=True, write_tables=False, errorlog=yacc.NullLogger())
    try:
        PARSER.parse(source, lexer=lexer, tokenfunc=stream.getNextToken, tracking=True)
        for fr in forward_refs:                      # alvos de ponteiro que nunca foram declarados
            if not fr.resolved():
                semantic_error(f"tipo '{fr.sym.name}' (alvo de ponteiro) não declarado.", fr.lineno)
    except CompilationAbort:
        print("Compilação abortada no primeiro erro de tipo.")
    finally:
        # Se um erro fatal impedir a redução de block, não deixe o gerenciador
        # apontando para um escopo interno ao imprimir o estado final.
        while symtab.top.parent is not None:
            symtab.exit_scope()
    print(symtab.dump(units))
   
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