program SucessoConst;
const
  MAX = 10;
  PI = 3.14;
  NEG = -4;
  NOME = 'Ana';
  ATIVO = true;
  OUTRO = MAX;
var
  v : array[1..MAX] of integer;
  i : integer;
  r : real;
  s : string;
begin
  for i := 1 to MAX do
    v[i] := i * OUTRO;
  r := PI * 2.0;
  s := NOME + 'x';
  if ATIVO then writeln(v[MAX], r, s, NEG)
end.
