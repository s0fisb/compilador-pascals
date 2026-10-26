program CaseDuplicado;
var
  n, y : integer;
begin
  n := 1;
  case n of
    1, 2: y := 1;
    3: y := 2;
    2: y := 3
  end;
  writeln(y)
end.
