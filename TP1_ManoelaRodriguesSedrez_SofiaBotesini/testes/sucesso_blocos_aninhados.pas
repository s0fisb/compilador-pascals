PROGRAM BlocosAninhados;  // palavras reservadas em maiúsculas
VAR i, soma : Integer;
    media : REAL;
BEGIN
  i := 0; soma := 0;
  WHILE i < 3 DO
  BEGIN
    BEGIN
      soma := soma + i
    END;
    i := i + 1
  END;
  media := 1.5;
  Writeln(soma, media)
END.
