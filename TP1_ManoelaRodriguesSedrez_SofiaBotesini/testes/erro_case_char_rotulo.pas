program ErroCaseCharRotulo;
var
  c : char;
begin
  c := 'x';
  case c of
    'x': writeln('x');
    1: writeln('um')
  end
end.
