program SucessoPonteiro;
type
  PNo = ^No;
  No = record
    valor : integer;
    prox : PNo
  end;
var
  ini, aux : PNo;
  pi : ^integer;
  n : integer;
begin
  new(ini);
  ini^.valor := 10;
  ini^.prox := nil;
  new(aux);
  aux^.valor := 20;
  aux^.prox := ini;
  ini := aux;
  n := ini^.valor + ini^.prox^.valor;
  new(pi);
  pi^ := n;
  if ini <> nil then writeln(pi^, n);
  dispose(aux)
end.
