"""
lex.py- Analisador léxico do Pascal-S

Sob demanda: nada é pré-tokenizado. O parser (yacc.py) chama getNextToken() uma vez por lookahead.

Uso isolado (para testar só o léxico):
    python3 lex.py testes/sucesso_semantico.pas
"""
import sys
import ply.lex as lex

# Tokens
reserved = {
    "program": "PROGRAM", "var": "VAR", "integer": "INTEGER", "real": "REAL",
    "begin": "BEGIN", "end": "END", "if": "IF", "then": "THEN", "else": "ELSE",
    "while": "WHILE", "do": "DO", "writeln": "WRITELN", "write": "WRITE",
    "read": "READ", "readln": "READLN", "char": "CHARTYPE",
    "not": "NOT", "and": "AND", "or": "OR",
    "boolean": "BOOLEAN", "true": "TRUE", "false": "FALSE",
    "array": "ARRAY", "of": "OF",
    "uses": "USES", "type": "TYPE", "record": "RECORD",
    "function": "FUNCTION", "procedure": "PROCEDURE", "string": "STRINGTYPE",
    "nil": "NIL", "new": "NEW", "dispose": "DISPOSE",
    "div": "DIV", "mod": "MOD", "for": "FOR", "to": "TO", "downto": "DOWNTO",
    "repeat": "REPEAT", "until": "UNTIL", "const": "CONST", "case": "CASE",
}

tokens = [
    "ID", "NUM_INT", "NUM_REAL", "STRING", "ASSIGN", "COLON", "SEMICOLON", "COMMA", "DOT", "DOTDOT",
    "LBRACKET", "RBRACKET", "CARET",
    "LPAREN", "RPAREN", "PLUS", "MINUS", "TIMES", "DIVIDE",
    "EQ", "NE", "LT", "LE", "GT", "GE",
] + list(reserved.values())

# Símbolos simples (strings: o PLY ordena pelo tamanho da regex, então
# ':=' vence ':' , '<=' e '<>' vencem '<' -> longest match.
t_ASSIGN = r":="
t_COLON = r":"
t_SEMICOLON = r";"
t_COMMA = r","
t_DOTDOT = r"\.\."   # o PLY ordena por tamanho da regex: ".." vence "."
t_DOT = r"\."
t_LBRACKET = r"\["
t_RBRACKET = r"\]"
t_CARET = r"\^"
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_DIVIDE = r"/"
t_EQ = r"="
t_NE = r"<>"
t_LE = r"<="
t_LT = r"<"
t_GE = r">="
t_GT = r">"

t_ignore = " \t\r"

MAXINT = 2147483647      # maior integer representável (integer ocupa 4 bytes, ver symtab.WIDTH)

def find_column(data, lexpos):
    #coluna (base 1) de lexpos dentro de sua linha
    last_nl = data.rfind("\n", 0, lexpos)
    return lexpos - last_nl

 
# Comentários (descartados: não retornam token)
# as funções são testadas na ORDEM em que aparecem neste arquivo
 
def t_COMMENT_LINE(t):
    r"//[^\n]*"
    pass


def t_COMMENT_BLOCK(t):
    r"\{[^}]*\}"
    t.lexer.lineno += t.value.count("\n") # comentário pode ocupar várias linhas


def t_COMMENT_PAREN(t):
    r"\(\*(.|\n)*?\*\)"
    # formato clássico do Pascal-S: (* ... *) (antes de LPAREN, que é regra-string)
    t.lexer.lineno += t.value.count("\n")


def t_COMMENT_PAREN_UNCLOSED(t):
    r"\(\*(.|\n)*"
    # só chega aqui se NÃO existe '*)' depois do '(*'
    col = find_column(t.lexer.lexdata, t.lexpos)
    msg = f"Erro Léxico [linha {t.lexer.lineno}, coluna {col}]: comentário '(*' não fechado."
    print(msg)
    t.lexer.errors.append(msg)
    t.lexer.lineno += t.value.count("\n")


def t_COMMENT_UNCLOSED(t):
    r"\{[^}]*"
    # só chega aqui se NÃO existe '}' depois do '{'
    col = find_column(t.lexer.lexdata, t.lexpos)
    msg = f"Erro Léxico [linha {t.lexer.lineno}, coluna {col}]: comentário '{{' não fechado."
    print(msg)
    t.lexer.errors.append(msg)
    t.lexer.lineno += t.value.count("\n")


# Números, identificadores, quebra de linha
 
def t_STRING(t):
    r"'([^'\n]|'')*'"
    t.value = t.value[1:-1].replace("''", "'")      # '' dentro da string = aspas literal
    return t


def t_NUM_REAL(t):
    r"\d+\.\d+"
    t.value = float(t.value)
    return t


def t_NUM_INT(t):
    r"\d+"
    t.value = int(t.value)
    if t.value > MAXINT:
        # aviso (não é erro): o valor não cabe em um integer de 4 bytes
        col = find_column(t.lexer.lexdata, t.lexpos)
        print(f"Aviso [linha {t.lexer.lineno}, coluna {col}]: literal inteiro {t.value} "
              f"excede maxint ({MAXINT}).")
    return t


def t_ID(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"
    t.type = reserved.get(t.value.lower(), "ID") # palavras reservadas case-insensitive
    if t.type == "ID" and t.lexer.symtab is not None:
        # atributo do token ID = PONTEIRO para a entrada da tabela de símbolos
        t.value = t.lexer.symtab.lookup_or_install(t.value, t.lexer.lineno)
    return t


def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


def t_error(t):
    col = find_column(t.lexer.lexdata, t.lexpos)
    msg = (f"Erro Léxico [linha {t.lexer.lineno}, coluna {col}]: "
           f"caractere ilegal '{t.value[0]}'.")
    print(msg)
    t.lexer.errors.append(msg)
    t.lexer.skip(1)    # modo pânico léxico: descarta 1 caractere e continua


# Construção do lexer
 
lexer = lex.lex()
lexer.errors = []
lexer.symtab = None


def build_lexer(symtab=None):
    #devolve um lexer novo (linha 1, sem erros) ligado a tabela de símbolos
    lx = lexer.clone()
    lx.lineno = 1
    lx.errors = []
    lx.symtab = symtab
    lx.getNextToken = lx.token
    return lx

 
# Execução isolada: lista os tokens, pedindo um por vez
 
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python lex.py arquivo.pas")
    with open(sys.argv[1], encoding="utf-8") as f:
        data = f.read()
    from symtab import ScopeManager
    lx = build_lexer(ScopeManager())
    lx.input(data)
    print(f"{'LINHA':<6}{'COL':<5}{'TOKEN':<11}VALOR")
    while True:
        tok = lx.getNextToken()
        if tok is None:
            break
        col = find_column(data, tok.lexpos)
        print(f"{tok.lineno:<6}{col:<5}{tok.type:<11}{tok.value!r}")
    print(f"\n{len(lx.errors)} erro(s) léxico(s).")