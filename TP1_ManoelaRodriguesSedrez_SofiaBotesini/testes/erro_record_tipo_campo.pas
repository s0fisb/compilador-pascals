program ErroRecordTipoCampo;
type
  Pessoa = record
    nome : string;
    idade : integer
  end;
var p : Pessoa; r : real;
begin
  r := 2.5;
  p.idade := r
end.
