<div align="center">

# AIM Studio DMA
### By Akumaprog

**Uma interface Linux para controlar sua configuração CS2 · DMA · KMBox**

[🇫🇷 Français](README.md) · [🇬🇧 English](README-en.md) · [🇪🇸 Español](README-es.md) · [🇩🇪 Deutsch](README-de.md) · [🇮🇹 Italiano](README-it.md) · [🇵🇹 Português](README-pt.md)

[Instalação](#instalação) · [Ligações](#ligações) · [Utilização](#utilização) · [Solução de problemas](#solução-de-problemas)

</div>
<img src="soft.png" alt="Logo" width="500">
---

## Apresentação

O AIM Studio DMA reúne a escolha do perfil, os ajustes, o controle do motor e a
atualização dos offsets em uma interface nativa. Abrir o menu não inicia o motor:
você mantém o controle com **Iniciar**, **Suspender** e **Parar**.

- Três perfis: **Soft**, **Magnético**, **Rage**.
- Cinco zonas: cabeça, pescoço, peito, abdômen, pelve.
- Ajustes de raio, suavização, frequência e deslocamento máximo.
- Opções de compensação do recuo e de visibilidade geométrica.
- Leitura automática da sensibilidade do jogo por padrão.
- Detecção automática da porta KMBox quando há apenas um dispositivo compatível.
- Seis idiomas, preferências salvas e registro integrado.
- Instalação automática das dependências, isoladas na pasta do aplicativo.

## Hardware e requisitos do sistema

| Elemento | Requisito |
| --- | --- |
| Máquina de controle | Raspberry Pi com Raspberry Pi OS **64 bits**, ou PC Linux **x86-64** com Debian/Ubuntu e ambiente gráfico |
| PC de jogo | PC executando CS2, equipado com a placa DMA compatível com sua instalação |
| Placa DMA | Placa FPGA compatível com LeechCore/MemProcFS; a instalação USB fornecida tem como alvo a ponte **FT601, VID 0403 / PID 601f** |
| KMBox | Modelo B/VerB ou B Pro que expõe um console serial compatível com os comandos `km.*` usados aqui |
| Ligações | Cabos USB **de dados**, portas e alimentação adequados aos dispositivos |
| Primeiro início | Internet, acesso aos repositórios do sistema/PyPI/GitHub, direitos `sudo` |

O software fornecido é um aplicativo **Linux**. Ele não é instalado diretamente no
Windows ou macOS. Um sistema operacional ARM de 32 bits não é suportado.
A referência testada neste projeto é uma **KMBox VerB, firmware 10.3.0, a 115200 baud**.
A compatibilidade de uma B Pro depende do firmware: apenas o nome comercial não
garante que o console ofereça o mesmo protocolo. Uma KMBox Net não é um substituto
direto para esse link serial.

## Ligações

### 1. Placa DMA

1. Desligue e desconecte o PC de jogo antes de instalar a placa PCIe, conforme o manual do fabricante.
2. Instale a placa em um slot compatível; em seguida, feche o gabinete e religue o PC.
3. Conecte a **porta USB de transferência DMA** à máquina Linux de controle com um cabo de dados adequado.
4. Se a placa tiver uma porta de programação separada, identifique-a no manual: ela não substitui a porta de transferência.
5. A placa deve ter um firmware funcional e ser reconhecida pelo LeechCore/MemProcFS.

O software não instala nem grava o firmware FPGA. Os procedimentos de programação,
alimentação e configuração da máquina host são específicos do modelo de placa:
use a documentação do fabricante. O driver USB instalado no Linux, por si só, não
torna qualquer placa compatível.

### 2. KMBox B Pro / VerB

Os nomes das portas variam entre as revisões; identifique a **função** delas no manual.

1. Conecte o mouse à entrada de periférico da KMBox.
2. Para usar as teclas F6 a F9 durante o jogo, conecte também o teclado à entrada prevista, se o seu modelo permitir.
3. Conecte a saída USB HID da KMBox ao **PC de jogo**.
4. Conecte a porta serial de controle à **máquina Linux**.
5. Verifique se o mouse funciona normalmente no PC de jogo antes de iniciar o motor.

```text
PC de jogo ← PCIe → Placa DMA ← USB de transferência → Máquina de controle
PC de jogo ← USB HID → KMBox  ← USB serial          → AIM Studio DMA
                       ↑
                Mouse / teclado
```

O motor espera um console que inclua `km.move`, `km.left` e os comandos de leitura
de teclas, entre outros. A abertura da porta pode reiniciar a KMBox: o software
aguarda o console por até **25 segundos**. Não deixe um monitor serial ou outra
ferramenta KMBox aberta na mesma porta.

### 3. Drivers e dependências

**Você não precisa baixar esses componentes manualmente: o launcher os instala.**

| Componente | Instalação automática |
| --- | --- |
| Interface e ambiente Python | `python3`, `python3-venv`, `python3-tk` |
| Suporte de compilação quando não há pacote binário | `build-essential`, `python3-dev`, `libusb-1.0-0-dev` |
| Suporte USB e do sistema | `libusb-1.0-0`, `libudev1`, `util-linux`, `ca-certificates` |
| Módulos Python | `memprocfs==5.18.10`, `leechcorepyc==2.23.3`, `pyserial==3.5` |
| Bibliotecas nativas DMA | Arquivo oficial MemProcFS 5.18.11 adaptado para ARM64/x86-64, verificado via SHA-256 |
| Transporte FT601 | `leechcore_ft601_driver_linux.so`, extraído com as bibliotecas nativas |
| Permissões USB/serial | Regras udev para FT601 `0403:601f` e interfaces seriais WCH `1a86` |

No Linux, as interfaces seriais USB compatíveis geralmente são suportadas pelo
kernel (`ch341`, `cdc_acm`, dependendo do dispositivo). Nenhum instalador de driver
Windows CH340/CH341 ou FTDI é necessário na máquina Linux.
Um dispositivo com outro ID USB pode exigir permissões adequadas.

## Instalação

### Primeiro início

1. No GitHub, escolha **Code → Download ZIP** e extraia totalmente o arquivo na máquina Linux.
2. Mantenha a pasta em um local gravável, por exemplo sua pasta pessoal ou a Área de trabalho.
3. Abra **AIM Studio DMA.desktop**. Dependendo do ambiente Linux, primeiro permita a execução em **Propriedades → Permissões** e, em seguida, **Permitir execução** se solicitado.
4. Um terminal mostra a preparação. Digite a senha do sistema se o `sudo` pedir e deixe a instalação terminar.
5. O menu abre e um atalho **AIM Studio DMA** é adicionado aos aplicativos e à Área de trabalho quando disponível.
6. Após a primeira instalação das regras USB, desconecte/reconecte as conexões USB se os dispositivos ainda não estiverem acessíveis.

Se o seu gerenciador de arquivos não executar arquivos `.desktop`, abra um terminal
**dentro da pasta extraída** e execute:

```bash
bash START.sh
```

**Um único início prepara o software; nenhum download manual adicional está
previsto. É necessária uma conexão com a Internet nesta primeira instalação.**
Este repositório não é um pacote universal offline: as dependências são escolhidas
e baixadas para o seu sistema. Os inícios seguintes reutilizam a instalação.
Se a instalação for interrompida, execute o mesmo launcher novamente para continuar.
Em algumas configurações ARM64, MemProcFS e LeechCore são compilados automaticamente:
esta primeira instalação pode levar vários minutos.

### Inícios seguintes

Use **AIM Studio DMA.desktop** na pasta ou o atalho instalado.
O launcher fornecido na pasta encontra o `START.sh` automaticamente: você pode
mover ou renomear a pasta inteira, inclusive para um caminho com espaços.
Mantenha o launcher, o `START.sh` e a pasta `release/` juntos.
Os atalhos externos criados na Área de trabalho e nos aplicativos apontam para o
local da instalação; após mover a pasta, use o launcher dentro dela.

## Utilização

1. Conecte os dispositivos e abra o CS2 no PC de jogo.
2. Feche outros softwares que usam a mesma placa DMA ou a porta serial KMBox.
3. Abra o AIM Studio DMA e selecione seu idioma no canto superior direito.
4. Escolha um perfil, uma zona do corpo e seus ajustes.
5. Entre em uma partida com um jogador vivo e clique em **Iniciar**.
6. Consulte o registro para verificar a conexão DMA, a KMBox e o carregamento do mapa.

| Comando | Ação |
| --- | --- |
| Iniciar | Executa o motor com os ajustes do menu |
| Clique esquerdo físico mantido | Permite as correções; o software não envia clique de disparo |
| Suspender / Retomar | Alterna a assistência pelo menu |
| F6 por padrão | Alterna a assistência; F7/F8/F9/Mouse 4/Mouse 5 também são oferecidos |
| Parar | Para o motor e libera os dispositivos |
| Esc no menu | Solicita a parada |
| Fechar a janela | Para os processos iniciados pelo menu |

Pare o motor antes de alterar os ajustes. Para receber um atalho físico durante o
jogo, o dispositivo correspondente deve passar pela KMBox.
As preferências e o idioma são salvos localmente.

### Perfis e geometria

- **Soft**: aquisição dentro de um raio ao redor da mira, com suavização ajustável.
- **Magnético**: aquisição em tela cheia e manutenção do alvo durante o disparo.
- **Rage**: aquisição em tela cheia com ajustes de correção mais diretos.

Dez geometrias estão incluídas: Ancient, Anubis, Cache, Dust2, Inferno, Mills,
Mirage, Nuke, Train e Vertigo. Os caches de aceleração `.bvh` são gerados
localmente; o primeiro carregamento pode demorar mais.
A verificação da geometria depende da correspondência entre os arquivos e a versão
atual do jogo. Thera não está incluída: o arquivo disponível era inválido.

### Sensibilidade, resolução e porta serial

No primeiro início, o `release/aim-settings.conf` é criado a partir do modelo fornecido.

```ini
PORT=auto
BAUD=115200
WIDTH=1920
HEIGHT=1080
SENSITIVITY=0
M_YAW=0.022
M_PITCH=0.022
DEVICE=fpga
```

- **SENSITIVITY=0**: usa a sensibilidade lida no jogo. Nenhuma calibração pessoal do desenvolvedor é distribuída.
- Uma sensibilidade explícita força esse valor. Se a leitura automática for inválida, o motor ignora os movimentos e o informa.
- Adapte **WIDTH / HEIGHT** à resolução do jogo.
- **PORT=auto** é adequado quando há apenas uma porta compatível. Caso contrário, indique o caminho estável `/dev/serial/by-id/...`.
- `M_YAW` e `M_PITCH` são coeficientes separados da sensibilidade; o zoom ou ajustes de entrada específicos podem alterar a conversão efetiva.

### Após uma atualização do CS2

Pare o motor, feche os outros clientes DMA e entre em uma partida com um jogador
vivo. Clique em **Atualizar offsets**. A ferramenta procura os endereços, verifica
as leituras e substitui o `offsets.json` após a validação.
Uma cópia anterior é mantida em `.bak`. Se a validação falhar, os valores antigos
permanecem: algumas atualizações exigem uma adaptação do software, não apenas dos offsets.

## Solução de problemas

| Sintoma | Verificar |
| --- | --- |
| O launcher abre em um editor | Permita a execução ou execute `bash START.sh` a partir da pasta |
| Falha no download | Internet, acesso a PyPI/GitHub/APT; execute novamente para continuar |
| SO ou processador recusado | Debian/Ubuntu/Raspberry Pi OS 64 bits, ARM64 ou x86-64 |
| KMBox ausente / várias portas | Cabo de dados, porta de controle correta e depois `PORT` na configuração |
| A KMBox não responde | Firmware compatível com `km.*`, baudrate, nenhum outro monitor serial; aguarde até 25 s |
| Permissão USB negada | Reconecte o dispositivo após a instalação; verifique o ID e as regras udev |
| DMA indisponível | Porta USB correta, firmware compatível, placa reconhecida, nenhum outro cliente DMA |
| Aguardando `cs2.exe/client.dll` | O CS2 deve estar em execução na máquina conectada à placa DMA |
| Nenhuma correção | Clique físico, estado de suspensão, sensibilidade válida, offsets e geometria; leia o registro |
| Código de saída 75 | Outra instância já está com o bloqueio DMA |

Diagnóstico de hardware sem movimento, a partir da pasta do software:

```bash
bash release/start-aim.sh --check --duration 10
```

Verificação do ambiente instalado:

```bash
bash release/setup-aim.sh --check
```

O diagnóstico de hardware requer os dispositivos conectados. Ele não substitui a
validação do firmware ou da sua fiação.

## Conteúdo do repositório

```text
AIM Studio DMA/
├── AIM Studio DMA.desktop   # Launcher gráfico de primeira instalação
├── START.sh                 # Ponto de entrada
├── README.md
├── .gitignore               # Exclui instalação e dados pessoais
└── release/
    ├── aim_*.py             # Interface, traduções e módulos
    ├── dma_aim.py           # Motor
    ├── update_aim_offsets.py
    ├── *.sh                # Instalação e launchers
    ├── install_aim_runtime.py
    ├── requirements-aim.txt
    ├── aim-settings.example.conf
    ├── offsets.json
    └── maps/               # Geometrias necessárias para a visibilidade
```

Você pode publicar **esta pasta** como raiz do repositório GitHub. As dependências
instaladas, os caches e as preferências são excluídos pelo `.gitignore`.
Para os usuários, prefira o ZIP do repositório ou um arquivo no GitHub Releases:
as geometrias tornam o repositório grande e não são adequadas para upload web arquivo por arquivo.

## Componentes e créditos

- Interface e integração: **Akumaprog**.
- Acesso DMA: [MemProcFS](https://github.com/ufrisk/MemProcFS) e [LeechCore](https://github.com/ufrisk/LeechCore), por Ulf Frisk.
- Link serial: [pySerial](https://github.com/pyserial/pyserial).
- Fontes de offsets e assinaturas: [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper).
- Geometrias ProCS2 retiradas do projeto [chao-shushu/CS2-DMA](https://github.com/chao-shushu/CS2-DMA), conforme a origem documentada no projeto-fonte.

As licenças das bibliotecas nativas são mantidas com a instalação em
`release/.runtime/vmm/`. Os componentes de terceiros mantêm suas respectivas licenças.
