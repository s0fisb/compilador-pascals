program FuncaoComoComando;
var x : integer;
    r : real;
function dobro(n : integer) : integer;
begin
  dobro := n * 2
end;
begin
  x := dobro(3);          { correto: função dentro de expressão }
  r := sqrt(2.0);         { correto }
  dobro(3);               { erro: função usada como comando }
  sqrt(2.0);              { erro: função padrão usada como comando }
  writeln(x, r)
end.
