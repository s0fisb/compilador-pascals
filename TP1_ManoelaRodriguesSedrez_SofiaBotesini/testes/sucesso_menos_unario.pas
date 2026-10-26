program MenosUnario;
var
  a, b : integer;
  x : real;
begin
  a := -5;
  b := +3;
  a := -a * b;        { lido como -(a * b) }
  a := b - (-a);      { dois sinais seguidos exigem parenteses }
  x := -1.5;
  x := -x;
  if -a < 0 then
    a := 1;
  writeln(a, b, x)
end.
