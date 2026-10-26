program SucessoReadWrite;
var
  n : integer;
  x : real;
  c : char;
  nome : string;
  v : array[1..3] of integer;
begin
  read(n);
  readln(x, c);
  readln(v[2]);
  readln;
  readln(nome);
  write('n = ', n);
  writeln;
  write(n:5, x:8:2, c);
  writeln(' fim')
end.
