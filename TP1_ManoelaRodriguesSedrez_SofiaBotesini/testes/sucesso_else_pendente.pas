program ElsePendente;
var a, b, x : integer;
begin
  a := 1;
  b := 2;
  { o else pertence ao if mais interno }
  if a < b then
    if b < a then x := 1
    else x := 2;
  writeln(x)
end.
