# Projeto final de Sistemas Operacionais I (Noturno)
## Integrantes:
- Guilherme Caetano
- Thiago Inouye Miyazaki

## Execução do programa
- Adicionar permissão de execução: `chmod +x main.py`
- Invocar o programa:
```bash
# 05 carros / 02 espaços / 20 pacotes / 6 pts.distro
./main -c=5 -a=2 -p=20 -s=6
```

## Breve Descrição do Funcionamento

O programa inicia fazendo o parsing dos argumentos fornecidos para conseguir
parametrizar o funcionamento do programa - fornecendo os valores para a 
quantidade de carros, de encomendas, pontos de distribuição e espaço disponível em cada carro.

Em seguida os objetos são criados e as threads iniciadas. Inicialmente criamos os objetos e threads
dos pontos de distribuição, em seguida das encomendas, onde fornecemos seu ponto de origem e destino,
junto com o horário de criação da encomenda. Depois, iniciamos os carros, fornecendo um ponto de distribuição
inicial de partida. Estas atribuições são feitas de forma aleatória.

Cada Ponto de Distribuição contém duas filas/listas de encomendas - de chegada e saída. Na fila de chegada
armazenamos os itens que são descarregados dos carros, e na fila de saída deixamos os itens que vão ser carregados
para os carros.

Os carros circulam em uma fila circular de pontos de distribuição, caminhando sequencialmente, por exemplo:
    - Em um cenário onde temos 4 pontos: pt0 -> pt1 -> pt2 -> pt3 -> pt0 -> pt1 -> (...)

Quando um carro chega em um dado ponto de distribuição P ele faz duas verificações:
    - Verifica se em seu "porta-malas" existe algum pacote para ser deixado em p
    - Verifica se tem espaço no "porta-malas" para carregar mais algum pacote e se existem pacotes disponíveis
    para serem carrehados na fila de saída do ponto P.

Caso alguma das verificações acima é positiva, então ele envia uma requisição para o Ponto de Distribuição - adicionando
um item no buffer de requisições do Ponto de Distribuição.

A requisição pode ser para **entregar um pacote** ou **receber um pacote**. As requisições são verificadas **uma por vez** 
*através de um lock condicional*. Quando uma requisição é adicionada ao buffer de requisições, a thread do Carro que fez 
a requisição é **colocada em espera**, e fica aguardando uma mensagem da Thread do Ponto de Distribuição para que 
possa continuar seu processamento. O Ponto de Distribuição somente envia a mensagem depois de processar a requisição. E
assim é feita a sincronização das mensagens.

Quando a Thread do Carro é notificada que pode continuar, isto é indicativo que recebeu uma resposta à sua requisição.
A resposta pode ser:
    - Uma mensagem "received", indicando que o item entregue foi recebido
    - Um objeto Package, indicando que lhe foi entre uma encomenda. Esta é então inserida nos itens presente no carro ("porta-malas).

Existe uma thread que controla o término da execução do programa, que roda a função ContextManager.check_termination:
    - Dada uma quantidade de encomendas N requisitada na invocação do programa e E, o valor dado pela soma da quantidade
    de itens na fila de entrada de todos os Pontos de Distribuição - caso E == N, então check_termination muda o valor
    do atributo ContextManager.shutdown para True, indicando para as outras threads que elas devem terminar suas execuções.

    - Note que, caso E < N, então ainda existem encomendas que precisam ser entregues.
