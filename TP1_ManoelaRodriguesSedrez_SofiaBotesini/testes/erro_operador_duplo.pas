// erro_operador_duplo: operador binário seguido de operador (recuperação em ;)
program Mais;
var
  valor : integer;
begin
  valor := 1 + * 2;
  valor := 3 + / 4;
  valor := 2.5;
  writeln(valor)
end.