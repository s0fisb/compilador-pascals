program ErroFuncaoTipoArg;
var r : real;
function dobro(x : integer) : integer;
begin
  dobro := x * 2
end;
begin
  r := 1.5;
  writeln(dobro(r))
end.
