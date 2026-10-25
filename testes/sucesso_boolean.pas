program SucessoBoolean;
var
  ok, fim : boolean;
  n : integer;
  r : real;
begin
  n := 3;
  r := 2.5;
  ok := true;
  fim := (n > 2) and not ok;
  fim := ok = fim;
  if ok then writeln(n, r, ok)
end.
