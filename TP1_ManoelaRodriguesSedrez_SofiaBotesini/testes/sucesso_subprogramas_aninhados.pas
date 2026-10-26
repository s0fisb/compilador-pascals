program SucessoAninhados;
var
  total : integer;

procedure externo(n : integer);
const
  PASSO = 2;
type
  Par = record a, b : integer end;
var
  acc : integer;
  p : Par;

  procedure soma(k : integer);
  begin
    acc := acc + k * PASSO      { usa local e constante do externo }
  end;

  function dobro(k : integer) : integer;
    function id(m : integer) : integer;
    begin
      id := m
    end;
  begin
    dobro := id(k) + id(k)
  end;

begin
  acc := 0;
  soma(n);
  p.a := dobro(acc);
  total := total + p.a
end;

begin
  total := 0;
  externo(3);
  writeln(total)
end.
