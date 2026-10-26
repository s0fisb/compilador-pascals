program SucessoChar;
const
  INICIAL = 'A';
var
  c, d : char;
  n : integer;
  s : string;
begin
  c := 'b';
  d := INICIAL;
  n := ord(c) - ord(d);
  d := chr(ord(d) + 1);
  if (c >= 'a') and (c <= 'z') then
    writeln('minuscula');
  case c of
    'a', 'e', 'i', 'o', 'u': writeln('vogal');
    'b': writeln('b')
  else
    writeln('outra')
  end;
  s := c;
  s := 'letra: ' + c;
  writeln(s, n)
end.
