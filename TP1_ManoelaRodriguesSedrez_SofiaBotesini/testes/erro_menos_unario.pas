program ErroMenosUnario;
var
  a : integer;
  ok : boolean;
begin
  a := a - -a;        // erro sintatico: sinal no meio da expressao
  a := -1.5;          // erro semantico: real atribuido a integer
  ok := -ok
end.
