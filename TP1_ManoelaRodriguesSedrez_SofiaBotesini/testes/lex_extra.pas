PROGRAM Extra;   // palavras reservadas em maiúsculas
{ comentário de bloco
  em varias linhas }
Var x_1, Y : Integer;   (* comentário clássico do Pascal-S *)
    taxa2 : REAL;
Begin
  x_1 := 314;
  taxa2 := 3.14;
  if x_1 <= 10 then Y := x_1 else Y := 1;
  $ # ! 
  WriteLn(x_1, Y, taxa2)
End.
{ comentario que nunca fecha
