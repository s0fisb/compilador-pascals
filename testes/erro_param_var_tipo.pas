program ErroParamVarTipo;
var r : real;
procedure inc(var x : integer);
begin
  x := x + 1
end;
begin
  r := 1.0;
  inc(r)
end.
