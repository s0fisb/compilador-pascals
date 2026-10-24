program ErroEscopoLocal;
var g : integer;
function f(x : integer) : integer;
var local : integer;
begin
  local := x;
  f := local + g
end;
begin
  g := 1;
  g := f(2);
  local := 3
end.
