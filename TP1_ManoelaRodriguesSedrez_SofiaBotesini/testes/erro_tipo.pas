program IncompatibilidadeDeTipos;
var
  cont : integer;
  acumulador, taxa : real;
begin
  acumulador := 5.5;
  taxa := 1.1;
  cont := acumulador + taxa; // Erro semântico impeditivo: float atribuído a integer
  writeln(cont)
end.
