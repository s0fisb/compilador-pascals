program EscoposGlobalLocal;
var
  total : integer;              { global }
  taxa  : real;                 { global }
  x     : integer;              { global (vai ser sombreada) }

procedure acumula(n : integer); { n: parametro, local de acumula }
var
  parcial : integer;            { local de acumula }
begin
  parcial := n * 2;
  total := total + parcial      { usa a global total }
end;

function media(a, b : real) : real;
var
  x : real;                     { local: esconde a global x (integer) }
begin
  x := a + b;                   { aqui x e real }
  media := x / 2.0
end;

procedure externo;
var
  base : integer;               { local de externo }

  procedure interno;
  var
    extra : integer;            { local de interno }
  begin
    extra := 5;
    base := base + extra;       { usa a local do externo }
    total := total + base       { usa a global }
  end;

begin
  base := 10;
  interno
end;

begin
  total := 0;
  taxa := 1.5;
  x := 3;                       { aqui x e a global integer }
  acumula(x);
  externo;
  taxa := media(taxa, 2.5);
  writeln(total, taxa, x)
end.