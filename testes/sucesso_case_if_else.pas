program CaseIfElse;
var
  a, b : integer;
begin
  a := 1;
  b := 0;
  case a of
    1: if b = 0 then b := 1 else b := 2;
    2: b := 3;
  else
    b := 4;
  end;
  writeln(b)
end.
