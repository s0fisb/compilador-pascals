program ErroFuncaoNumArgs;
var n : integer;
function soma(a, b : integer) : integer;
begin
  soma := a + b
end;
begin
  n := soma(1);
  n := soma(1, 2, 3)
end.
