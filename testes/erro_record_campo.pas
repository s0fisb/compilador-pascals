program ErroRecordCampo;
type
  Pessoa = record
    nome : string;
    idade : integer
  end;
var p : Pessoa;
begin
  p.idade := 'vinte';
  p.peso := 70
end.
