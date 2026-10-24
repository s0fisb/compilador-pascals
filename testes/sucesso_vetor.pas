program SucessoVetor;
var
  v : array[1..10] of integer;
  m : array[1..3, 1..3] of real;
  f : array[0..4] of boolean;
  i, j : integer;
begin
  i := 1;
  while i <= 10 do
  begin
    v[i] := i * 2;
    i := i + 1
  end;
  m[1, 2] := 3.5;
  m[2][3] := m[1, 2] + 1.0;
  f[0] := v[1] > 1;
  if f[0] then writeln(v[i - 1], m[2, 3])
end.
