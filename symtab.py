"""
symtab.py - Tabela de Símbolos do compilador Pascal-S.

Repositório central de atributos:
  * cada identificador vira UM objeto Symbol; o token ID carrega uma
    REFERÊNCIA a esse objeto (ponteiro), não a string;
  * ambientes encadeados via `parent:
    entrar em bloco -> nova tabela filha; sair -> volta ao pai;
  * lookup procura do escopo atual em direção ao global.
"""

# Largura em bytes de cada tipo e usada para calcular offset
WIDTH = {"integer": 4, "real": 8}


class Symbol:
    """Entrada da tabela de símbolos."""

    def __init__(self, name, var_type=None, lineno=0, scope=None):
        self.name = name            # lexema
        self.type = var_type        # 'integer' | 'real' | None (ainda sem declaração)
        self.lineno = lineno        # linha da declaração (ou do 1° uso, se não declarado)
        self.scope = scope          # SymbolTable onde a entrada vive
        self.offset = None          # deslocamento relativo no escopo
        self.declared = False       # True após aparecer em um `var`

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
        #ainda NÃO declarada no escopo atual (a Aula 3 chama isso de
        #'instalar' o lexema). O parser decide depois se é erro.
        sym = self.top.lookup(name)
        if sym is None:
            sym = Symbol(name, None, lineno, self.top)
            self.top.insert(name, sym)
        return sym

    # usado pelo PARSER (declarações)
    def declare(self, sym, var_type, lineno):
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
        sym.offset = self.top.alloc(WIDTH[var_type])
        return sym

    # depuração / log 
    def dump(self):
        lines = ["", "TABELA DE SIMBOLOS"]
        for t in self.tables:
            declared = [s for s in t.symbols.values() if s.declared]
            if not declared and t.parent is not None:
                continue            # blocos sem declarações não entram no log
            lines.append(f"[escopo '{t.name}' nivel {t.level}]")
            lines.append(f"  {'nome':<18}{'tipo':<9}{'offset':<8}{'linha':<6}")
            for s in declared:
                lines.append(f"  {s.name:<18}{s.type:<9}{s.offset:<8}{s.lineno:<6}")
        return "\n".join(lines)