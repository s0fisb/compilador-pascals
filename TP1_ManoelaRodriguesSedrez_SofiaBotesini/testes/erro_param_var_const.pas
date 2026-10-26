program ErroParamVarConst;
const
  K = 3;
procedure inc(var x : integer);
begin
  x := x + 1
end;
begin
  inc(K)
end.
