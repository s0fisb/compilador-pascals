program ErroParamVarExpr;
var a : integer;
procedure inc(var x : integer);
begin
  x := x + 1
end;
begin
  a := 1;
  inc(a + 1)
end.
