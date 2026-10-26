program ErroAninhadoEscopo;
var
  t : integer;

procedure externo;
  procedure interno;
  var
    escondida : integer;
  begin
    escondida := 1
  end;
begin
  interno;
  t := escondida
end;

begin
  externo
end.
