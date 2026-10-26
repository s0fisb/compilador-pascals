program SucessoFuncoesPadrao;
var
  i, j : integer;
  x, y : real;
  b : boolean;
  c : char;
begin
  i := -7;
  x := 2.5;
  j := abs(i) + sqr(i);
  y := abs(x) + sqr(x);
  y := sqrt(x) + sqrt(16) + sin(x) + cos(x) + exp(1.0) + ln(x) + arctan(x);
  b := odd(i);
  i := succ(i) + pred(i);
  c := succ('a');
  b := pred(true);
  i := round(x) + trunc(x);
  i := maxint;
  if i = maxint then
    writeln('maior inteiro: ', maxint)
end.
