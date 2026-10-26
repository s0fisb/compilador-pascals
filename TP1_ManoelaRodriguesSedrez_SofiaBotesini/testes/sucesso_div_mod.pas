program SucessoDivMod;
var
  a, b, q, r : integer;
  x : real;
  par : boolean;
begin
  a := 17;
  b := 5;
  q := a div b;
  r := a mod b;
  q := a div b + a mod b * 2;
  par := (a mod 2) = 0;
  x := 7.0 / 2.0;
  writeln(q, r, par, x)
end.
