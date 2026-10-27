"""
Repositório central de atributos:
  * cada identificador vira UM objeto Symbol; o token ID carrega uma
    REFERÊNCIA a esse objeto (ponteiro), não a string;
  * ambientes encadeados via `parent:
    entrar em bloco -> nova tabela filha; sair -> volta ao pai;
  * lookup procura do escopo atual em direção ao global.
"""

# Largura em bytes de cada tipo e usada para calcular offset
WIDTH = {"integer": 4, "real": 8, "boolean": 1, "char": 1, "string": 8}


class ArrayType:
    """Tipo vetor: array[lo..hi] of elem. Matriz = vetor de vetor (elem e ArrayType)."""

    def __init__(self, lo, hi, elem):
        self.lo, self.hi, self.elem = lo, hi, elem

    def size(self):
        n = max(self.hi - self.lo + 1, 0)
        return n * type_size(self.elem)

    def __eq__(self, other):
        return (isinstance(other, ArrayType) and self.lo == other.lo
                and self.hi == other.hi and self.elem == other.elem)

    def __hash__(self):
        return hash((self.lo, self.hi, self.elem))

    def __str__(self):
        return f"array[{self.lo}..{self.hi}] of {self.elem}"

    __repr__ = __str__


class RecordType:
    """Tipo registro (record ... end): lista ordenada de campos (nome, tipo)."""

    def __init__(self, name, fields):
        self.name = name                    # nome do 'type' que o declarou (ou None se anônimo)
        self.fields = fields                # [(nome, tipo), ...]

    def field(self, fname):
        for n, t in self.fields:
            if n.casefold() == fname.casefold():
                return True, t
        return False, None

    def size(self):
        return sum(type_size(t) for _, t in self.fields)

    def __eq__(self, other):
        # equivalência por NOME quando ambos são nomeados (evita recursão infinita em listas encadeadas)
        if not isinstance(other, RecordType):
            return False
        if self is other:
            return True
        if self.name and other.name:
            return self.name.casefold() == other.name.casefold()
        return self.fields == other.fields

    def __hash__(self):
        return hash(self.name.casefold()) if self.name else hash(tuple(n for n, _ in self.fields))

    def __str__(self):
        if self.name:
            return self.name
        return "record(" + "; ".join(f"{n}: {t}" for n, t in self.fields) + ")"

    __repr__ = __str__


class ForwardRef:
    """Nome de tipo ainda não declarado, aceito apenas como alvo de ponteiro (PNo = ^No; No = record ...)."""

    def __init__(self, sym, lineno):
        self.sym, self.lineno = sym, lineno

    def resolved(self):
        return self.sym.declared and self.sym.kind == "type"

    def size(self):
        return 0

    def __str__(self):
        return self.sym.name

    __repr__ = __str__


class PointerType:
    """Tipo ponteiro ^T. O alvo pode ser resolvido tardiamente (referência adiante)."""

    def __init__(self, target=None, ref=None):
        self._target = target
        self.ref = ref                      # Symbol do tipo-alvo quando ainda não estava declarado

    @property
    def target(self):
        if self.ref is not None:
            return self.ref.type if (self.ref.declared and self.ref.kind == "type") else None
        return self._target

    def size(self):
        return 8

    def __eq__(self, other):
        if not isinstance(other, PointerType):
            return False
        a, b = self.target, other.target
        return a is not None and b is not None and a == b

    def __hash__(self):
        return hash("ptr")

    def __str__(self):
        t = self.target
        return "^" + (str(t) if t is not None else (self.ref.name if self.ref else "?"))

    __repr__ = __str__


def type_size(t):
    if t is None:
        return 0
    return t.size() if isinstance(t, (ArrayType, RecordType, PointerType, ForwardRef)) else WIDTH[t]


class Symbol:
    """Entrada da tabela de símbolos."""

    def __init__(self, name, var_type=None, lineno=0, scope=None):
        self.name = name            # lexema
        self.type = var_type        # 'integer' | 'real' | 'boolean' | 'char' | ... | None (ainda sem declaração)
        self.lineno = lineno        # linha da declaração (ou do 1° uso, se não declarado)
        self.scope = scope          # SymbolTable onde a entrada vive
        self.offset = None          # deslocamento relativo no escopo
        self.declared = False       # True após aparecer em um `var`
        self.kind = "var"           # 'var' | 'const' | 'type' | 'func' | 'proc'
        self.params = []            # tipos dos parâmetros (func/proc)
        self.refs = []              # True para parâmetro por referência (var), alinhado a params
        self.value = None           # valor da constante (kind == 'const')

    def __repr__(self):
        if not self.declared:
            return f"<Symbol {self.name} (nao declarado)>"
        return f"<Symbol {self.name}:{self.type} @{self.offset}>"


class SymbolTable:
    #Um ambiente (tabela hash) ligado ao ambiente pai

    def __init__(self, parent=None, name="global"):
        self.symbols = {}
        self.parent = parent
        self.name = name
        self.level = 0 if parent is None else parent.level + 1
        self.next_offset = 0

    @staticmethod
    def key(name):
        # Pascal-S: identificadores não diferenciam maiúsculas/minúsculas
        return name.casefold()

    def insert(self, name, symbol):
        key = self.key(name)
        if key in self.symbols:
            return False            # dupla declaração no escopo atual
        self.symbols[key] = symbol
        return True

    def lookup_local(self, name):
        return self.symbols.get(self.key(name))

    def lookup(self, name):
        #Busca incremental: escopo atual -> pai -> ... -> global
        table = self
        while table is not None:
            found = table.lookup_local(name)
            if found is not None:
                return found
            table = table.parent
        return None

    def alloc(self, width):
        off = self.next_offset
        self.next_offset += width
        return off


class ScopeManager:
    #Pilha de ambientes usada pelo lexer e pelo parser

    def __init__(self):
        self.top = SymbolTable(None, "global")
        self.tables = [self.top]    # só para imprimir o dump no final

    # escopos
    def enter_scope(self, name="bloco"):
        self.top = SymbolTable(self.top, name)
        self.tables.append(self.top)

    def exit_scope(self):
        if self.top.parent is not None:
            self.top = self.top.parent

    def reset_to_global(self):
        #Volta ao ambiente global sem apagar os ambientes já registrados
        while self.top.parent is not None:
            self.exit_scope()

    # usado pelo LEXER (token ID -> ponteiro)
    def lookup_or_install(self, name, lineno):
        #Devolve a entrada de `name`; se não existir, cria uma entrada
        #ainda NÃO declarada no escopo atual 
        #('instalar' o lexema). O parser decide depois se é erro.
        sym = self.top.lookup(name)
        if sym is None:
            sym = Symbol(name, None, lineno, self.top)
            self.top.insert(name, sym)
        return sym

    # usado pelo PARSER (declarações)
    def declare(self, sym, var_type, lineno, kind="var"):
        #Registra a declaração de `sym`.
        #Retorna o Symbol declarado, ou None se for REDECLARAÇÃO no mesmo escopo
        existing = self.top.lookup_local(sym.name)
        if existing is not None and existing.declared:
            return None
        if existing is not None:
            sym = existing
        elif sym.scope is not self.top:
            # Nome existe só em escopo externo: cria entrada local nova.
            sym = Symbol(sym.name, None, lineno, self.top)
            self.top.insert(sym.name, sym)
        sym.type = var_type
        sym.lineno = lineno
        sym.declared = True
        sym.kind = kind
        if kind == "var":
            sym.offset = self.top.alloc(type_size(var_type))
        return sym

    # depuração / log 
    def dump(self, units=()):
        lines = [""]
        if units:
            lines.append("UNIDADES (uses): " + ", ".join(units))
            lines.append("")
        lines.append("TABELA DE SIMBOLOS")
        for t in self.tables:
            declared = [s for s in t.symbols.values() if s.declared]
            if not declared and t.parent is not None:
                continue            # blocos sem declarações não entram no log
            lines.append(f"[escopo '{t.name}' nivel {t.level}]")
            rows = []
            for s in declared:
                if s.kind in ("func", "proc"):
                    refs = s.refs or [False] * len(s.params)
                    plist = ", ".join(("var " if r else "") + str(t) for t, r in zip(s.params, refs))
                    desc = f"{'function' if s.kind == 'func' else 'procedure'}({plist})"
                    if s.kind == "func":
                        desc += f": {s.type}"
                elif s.kind == "type":
                    desc = f"type = {s.type}"
                elif s.kind == "const":
                    v = s.value
                    v = ("true" if v else "false") if s.type == "boolean" else (f"'{v}'" if s.type in ("string", "char") else v)
                    desc = f"const {s.type} = {v}"
                else:
                    desc = str(s.type)
                rows.append((s.name, desc, "-" if s.offset is None else s.offset, s.lineno))
            w = max([len(r[1]) for r in rows] + [4]) + 2
            lines.append(f"  {'nome':<18}{'tipo':<{w}}{'offset':<8}{'linha':<6}")
            for n, d, o, l in rows:
                lines.append(f"  {n:<18}{d:<{w}}{o!s:<8}{l!s:<6}")
        return "\n".join(lines)
