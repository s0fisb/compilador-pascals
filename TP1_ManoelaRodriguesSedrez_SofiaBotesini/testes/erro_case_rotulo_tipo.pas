program CaseRotuloTipo;
var
  n, y : integer;
begin
  n := 1;
  case n of
    1: y := 1;
    true: y := 2
  end;
  writeln(y)
end.
