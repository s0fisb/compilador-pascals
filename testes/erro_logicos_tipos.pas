program LogicosComTipos;
var a, b : integer;
begin
  a := 1; b := 2;
  if a and b then a := 0;
  if not a then a := 0;
  a := a or b
end.
