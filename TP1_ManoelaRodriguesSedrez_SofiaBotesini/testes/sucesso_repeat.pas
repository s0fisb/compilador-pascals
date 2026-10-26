program SucessoRepeat;
var
  n, f : integer;
begin
  n := 5;
  f := 1;
  repeat
    f := f * n;
    n := n - 1
  until n <= 1;
  writeln(f)
end.
