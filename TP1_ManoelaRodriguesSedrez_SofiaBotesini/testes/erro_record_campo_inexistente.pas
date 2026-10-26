program ErroRecordCampoInexistente;
type
  Pessoa = record
    nome : string;
    idade : integer
  end;
var p : Pessoa;
    n : integer;
begin
  p.peso := 70;
  n := p.altura;
  n.x := 1
end.
