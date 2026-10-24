program TesteTiposAvancados;
var
    ativo, pronto : boolean;
    val : integer;
    num : real;
    vetor : array[1..10] of integer;
    matriz : array[1..3, 1..3] of real;
begin
    ativo := true;
    pronto := false;
    
    { Erro semântico 1: Atribuição de boolean para integer }
    val := ativo; 

    { Erro semântico 2: Índice de vetor não inteiro (usando real) }
    vetor[2.5] := 10; 

    { Erro semântico 3: Atribuição de real em elemento de vetor integer }
    vetor[1] := 3.14; 

    { Erro semântico 4: Atribuição de integer em matriz real (se tipagem forte proibir coerção) }
    matriz[1, 1] := 5; 

    writeln(val)
end.