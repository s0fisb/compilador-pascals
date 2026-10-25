program SucessoFor;
var
  i, j, soma : integer;
  v : array[1..5] of integer;
begin
  soma := 0;
  for i := 1 to 5 do
    v[i] := i * i;
  for i := 5 downto 1 do
  begin
    soma := soma + v[i];
    for j := 1 to i do
      soma := soma + 1
  end;
  writeln(soma)
end.
