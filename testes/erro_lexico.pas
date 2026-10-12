program TesteErroLexico;
var
  cont : integer;
begin
  cont := 10 @ 5; // Erro léxico: '@' é ilegal na linguagem Pascal-S
  writeln(cont)
end.
