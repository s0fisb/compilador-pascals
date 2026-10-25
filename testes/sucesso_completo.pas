program SucessoCompleto;
uses crt, math;
type
  Pessoa = record
    nome : string;
    idade : integer;
    altura : real
  end;
  Notas = array[1..3] of real;
var
  p, q : Pessoa;
  n : Notas;
  total : real;
  i : integer;

function dobro(x : integer) : integer;
begin
  dobro := x * 2
end;

function media(a, b : real) : real;
begin
  media := (a + b) / 2.0
end;

function fat(k : integer) : integer;
begin
  if k <= 1 then fat := 1 else fat := k * fat(k - 1)
end;

procedure mostra(r : Pessoa; t : string);
var
  aux : integer;
begin
  aux := r.idade;
  writeln(t, r.nome, aux)
end;

begin
  p.nome := 'Ana';
  p.idade := dobro(15);
  p.altura := 1.70;
  q := p;
  n[1] := media(p.altura, 2.0);
  total := n[1];
  i := fat(5);
  mostra(q, 'Dados: ');
  if p.nome = q.nome then writeln('iguais', i, total)
end.
