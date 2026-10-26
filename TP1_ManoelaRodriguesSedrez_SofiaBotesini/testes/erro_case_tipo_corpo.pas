program CaseTipoCorpo;
var
  n : integer;
  r : real;
begin
  n := 1;
  r := 2.0;
  case n of
    1: n := 5;
    2: n := r
  end;
  writeln(n)
end.
