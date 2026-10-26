program TesteRecuperacao;
var
  valor : integer;
begin
  valor := 1 + * 2;  // Erro sintático: '*' aparece onde deveria haver um operando.
  valor := 2.5;      // Erro semântico esperado: expressão real atribuída a integer.
  writeln(valor)
end.