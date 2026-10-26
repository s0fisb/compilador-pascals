program SucessoParamVar;
type
  Pessoa = record
    idade : integer;
    altura : real
  end;
var
  a, b : integer;
  v : array[1..3] of integer;
  p : Pessoa;
  r : real;

procedure troca(var x, y : integer);
var t : integer;
begin
  t := x;
  x := y;
  y := t
end;

procedure dobra(var z : real; k : integer);
begin
  z := z * 2.0;
  k := k + 1
end;

function soma_e_zera(var n : integer) : integer;
begin
  soma_e_zera := n;
  n := 0
end;

begin
  a := 1;
  b := 2;
  v[1] := 10;
  v[2] := 20;
  p.idade := 30;
  r := 1.5;
  troca(a, b);
  troca(v[1], v[2]);
  troca(a, p.idade);
  dobra(r, a);
  dobra(p.altura, 3);
  b := soma_e_zera(a)
end.
