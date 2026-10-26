program SucessoCase;
const
  LIMITE = 4;
var
  op, total : integer;
  ativo : boolean;
begin
  op := 2;
  total := 0;
  ativo := true;
  case op of
    1: total := 10;
    2, 3: begin
      total := total + 20;
      total := total * 2
    end;
    LIMITE: ;
    -1: total := 0
  else
    total := 99
  end;
  case ativo of
    true: total := total + 1;
    false: total := total - 1
  end;
  case total of
    1: case op of
         2: total := 5
       end;
    41: writeln(total);
  end;
  writeln(total)
end.
