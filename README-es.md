<div align="center">

# AIM Studio DMA
### By Akumaprog

**Una interfaz Linux para controlar tu configuración CS2 · DMA · KMBox**

[🇫🇷 Français](README.md) · [🇬🇧 English](README-en.md) · [🇪🇸 Español](README-es.md) · [🇩🇪 Deutsch](README-de.md) · [🇮🇹 Italiano](README-it.md) · [🇵🇹 Português](README-pt.md)

[Instalación](#instalación) · [Conexiones](#conexiones) · [Uso](#uso) · [Solución de problemas](#solución-de-problemas)

</div>

---

## Presentación

AIM Studio DMA reúne la selección de perfil, los ajustes, el control del motor y
la actualización de offsets en una interfaz nativa. Abrir el menú no inicia el
motor: tú mantienes el control con **Iniciar**, **Suspender** y **Detener**.

- Tres perfiles: **Soft**, **Magnético**, **Rage**.
- Cinco zonas: cabeza, cuello, pecho, estómago y pelvis.
- Ajustes de radio, suavizado, frecuencia y desplazamiento máximo.
- Opciones de compensación del retroceso y de visibilidad geométrica.
- Lectura automática de la sensibilidad del juego por defecto.
- Detección automática del puerto KMBox cuando hay un único dispositivo compatible.
- Seis idiomas, preferencias guardadas y registro integrado.
- Instalación automática de dependencias, aisladas en la carpeta de la aplicación.

## Hardware y requisitos del sistema

| Elemento | Requisito |
| --- | --- |
| Equipo de control | Raspberry Pi con Raspberry Pi OS **64 bits**, o PC Linux **x86-64** con Debian/Ubuntu y escritorio gráfico |
| PC de juego | PC que ejecuta CS2, equipado con la tarjeta DMA compatible con tu instalación |
| Tarjeta DMA | Tarjeta FPGA compatible con LeechCore/MemProcFS; la instalación USB incluida apunta al puente **FT601, VID 0403 / PID 601f** |
| KMBox | Modelo B/VerB o B Pro que exponga una consola serie compatible con los comandos `km.*` usados aquí |
| Conexiones | Cables USB **de datos**, puertos y alimentación adecuados a los dispositivos |
| Primer inicio | Internet, acceso a los repositorios del sistema/PyPI/GitHub, derechos `sudo` |

El software entregado es una aplicación **Linux**. No se instala directamente en
Windows ni macOS. Un OS ARM de 32 bits no es compatible.
La referencia probada en este proyecto es una **KMBox VerB, firmware 10.3.0, a 115200 baudios**.
La compatibilidad de una B Pro depende de su firmware: el nombre comercial por sí
solo no garantiza que su consola ofrezca el mismo protocolo. Una KMBox Net no es
un sustituto directo de este enlace serie.

## Conexiones

### 1. Tarjeta DMA

1. Apaga y desconecta el PC de juego antes de instalar la tarjeta PCIe, siguiendo el manual del fabricante.
2. Instala la tarjeta en una ranura compatible; luego cierra la carcasa y vuelve a encender el PC.
3. Conecta el **puerto USB de transferencia DMA** al equipo Linux de control con un cable de datos adecuado.
4. Si la tarjeta tiene un puerto de programación separado, identifícalo en su manual: no sustituye al puerto de transferencia.
5. La tarjeta debe tener un firmware funcional y ser reconocida por LeechCore/MemProcFS.

El software no instala ni flashea el firmware FPGA. Los procedimientos de
programación, alimentación y configuración del equipo anfitrión son propios del
modelo de tarjeta: usa la documentación de su fabricante. El controlador USB
instalado en Linux no basta, por sí solo, para que cualquier tarjeta sea compatible.

### 2. KMBox B Pro / VerB

Los nombres de los puertos varían según la revisión; identifica su **función** en el manual.

1. Conecta el ratón a la entrada de periférico de la KMBox.
2. Para usar las teclas F6 a F9 desde el juego, conecta también el teclado a la entrada prevista, si tu modelo lo permite.
3. Conecta la salida USB HID de la KMBox al **PC de juego**.
4. Conecta su puerto serie de control a la **máquina Linux**.
5. Comprueba que el ratón funciona con normalidad en el PC de juego antes de iniciar el motor.

```text
PC de juego ← PCIe → Tarjeta DMA ← USB de transferencia → Equipo de control
PC de juego ← USB HID → KMBox  ← USB serie            → AIM Studio DMA
                       ↑
                Ratón / teclado
```

El motor espera una consola que incluya `km.move`, `km.left` y los comandos de
lectura de teclas, entre otros. Abrir el puerto puede reiniciar la KMBox: el
software espera su consola hasta **25 segundos**. No dejes un monitor serie u otra
herramienta KMBox abierta en el mismo puerto.

### 3. Controladores y dependencias

**No tienes que descargar estos componentes manualmente: el lanzador los instala.**

| Componente | Instalación automática |
| --- | --- |
| Interfaz y entorno Python | `python3`, `python3-venv`, `python3-tk` |
| Soporte de compilación si no hay paquete binario | `build-essential`, `python3-dev`, `libusb-1.0-0-dev` |
| Soporte USB y del sistema | `libusb-1.0-0`, `libudev1`, `util-linux`, `ca-certificates` |
| Módulos Python | `memprocfs==5.18.10`, `leechcorepyc==2.23.3`, `pyserial==3.5` |
| Bibliotecas nativas DMA | Archivo oficial MemProcFS 5.18.11 adaptado a ARM64/x86-64, verificado por SHA-256 |
| Transporte FT601 | `leechcore_ft601_driver_linux.so`, extraído con las bibliotecas nativas |
| Permisos USB/serie | Reglas udev para FT601 `0403:601f` e interfaces serie WCH `1a86` |

En Linux, las interfaces serie USB compatibles suelen estar soportadas por el
núcleo (`ch341`, `cdc_acm`, según el dispositivo). No es necesario ningún
instalador de controlador Windows CH340/CH341 o FTDI en la máquina Linux.
Un dispositivo con otro identificador USB puede requerir permisos adecuados.

## Instalación

### Primer inicio

1. En GitHub, elige **Code → Download ZIP** y extrae la archive completa en la máquina Linux.
2. Mantén la carpeta en una ubicación con permisos de escritura, por ejemplo tu carpeta personal o el Escritorio.
3. Abre **AIM Studio DMA.desktop**. Según el escritorio Linux, primero permite su ejecución en **Propiedades → Permisos** y luego **Permitir el lanzamiento** si se pide.
4. Un terminal muestra la preparación. Introduce la contraseña del sistema si `sudo` la pide y deja que la instalación termine.
5. Se abre el menú y se añade un acceso directo **AIM Studio DMA** a las aplicaciones y al Escritorio cuando está disponible.
6. Tras la primera instalación de las reglas USB, desconecta/vuelve a conectar los dispositivos USB si aún no son accesibles.

Si tu gestor de archivos no ejecuta los archivos `.desktop`, abre un terminal
**dentro de la carpeta extraída** y ejecuta:

```bash
bash START.sh
```

**Un solo lanzamiento prepara el software; no está prevista ninguna descarga
manual adicional. Se necesita Internet para esta primera instalación.**
Este repositorio no es un paquete universal sin conexión: las dependencias se eligen
y se descargan para tu sistema. Los lanzamientos siguientes reutilizan la instalación.
Si la instalación se interrumpe, vuelve a ejecutar el mismo lanzador para continuar.
En algunas configuraciones ARM64, MemProcFS y LeechCore se compilan automáticamente:
esta primera instalación puede tardar varios minutos.

### Inicios siguientes

Usa **AIM Studio DMA.desktop** de la carpeta o el acceso directo instalado.
El lanzador incluido en la carpeta encuentra `START.sh` automáticamente: puedes
mover o renombrar la carpeta completa, incluso a una ruta con espacios.
Mantén juntos el lanzador, `START.sh` y `release/`.
Los accesos directos externos creados en el Escritorio y en las aplicaciones
apuntan a la ubicación de instalación; tras mover la carpeta, usa el lanzador de la carpeta.

## Uso

1. Conecta los dispositivos y abre CS2 en el PC de juego.
2. Cierra otros programas que usen la misma tarjeta DMA o el puerto serie de la KMBox.
3. Abre AIM Studio DMA y selecciona tu idioma arriba a la derecha.
4. Elige un perfil, una zona del cuerpo y tus ajustes.
5. Entra en una partida con un jugador vivo y haz clic en **Iniciar**.
6. Consulta el registro para verificar la conexión DMA, la KMBox y la carga de la tarjeta.

| Comando | Acción |
| --- | --- |
| Iniciar | Ejecuta el motor con los ajustes del menú |
| Clic izquierdo físico mantenido | Permite las correcciones; el software no envía clic de disparo |
| Suspender / Reanudar | Alterna la asistencia desde el menú |
| F6 por defecto | Alterna la asistencia; F7/F8/F9/Ratón 4/Ratón 5 también están disponibles |
| Detener | Detiene el motor y libera los dispositivos |
| Esc en el menú | Solicita la detención |
| Cerrar la ventana | Detiene los procesos iniciados por el menú |

Detén el motor antes de modificar sus ajustes. Para recibir un acceso directo
físico durante el juego, el dispositivo correspondiente debe pasar por la KMBox.
Las preferencias y el idioma se guardan localmente.

### Perfiles y geometría

- **Soft**: adquisición dentro de un radio alrededor del punto de mira, con suavizado ajustable.
- **Magnético**: adquisición en toda la pantalla y conservación del objetivo durante el disparo.
- **Rage**: adquisición en toda la pantalla con ajustes de corrección más directos.

Se incluyen diez geometrías: Ancient, Anubis, Cache, Dust2, Inferno, Mills,
Mirage, Nuke, Train y Vertigo. Las cachés de aceleración `.bvh` se generan
localmente; la primera carga puede tardar más.
La verificación de la geometría depende de la correspondencia entre los archivos y
la versión actual del juego. Thera no está incluida: el archivo disponible era inválido.

### Sensibilidad, resolución y puerto serie

En el primer inicio se crea `release/aim-settings.conf` a partir de la plantilla incluida.

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

- **SENSITIVITY=0**: usa la sensibilidad leída en el juego. No se distribuye ninguna calibración personal del desarrollador.
- Una sensibilidad explícita fuerza ese valor. Si la lectura automática es inválida, el motor ignora los movimientos y lo indica.
- Adapta **WIDTH / HEIGHT** a la resolución del juego.
- **PORT=auto** es adecuado cuando solo hay un puerto compatible. En caso contrario, indica su ruta estable `/dev/serial/by-id/...`.
- `M_YAW` y `M_PITCH` son coeficientes independientes de la sensibilidad; el zoom o ajustes de entrada especiales pueden modificar la conversión efectiva.

### Tras una actualización de CS2

Detén el motor, cierra los otros clientes DMA y entra en una partida con un
jugador vivo. Haz clic en **Actualizar offsets**. La herramienta busca las
direcciones, verifica las lecturas y sustituye `offsets.json` tras la validación.
Se conserva una copia anterior en `.bak`. Si la validación falla, los valores
antiguos permanecen: algunas actualizaciones requieren una adaptación del software,
no solo de los offsets.

## Solución de problemas

| Síntoma | Comprobar |
| --- | --- |
| El lanzador se abre en un editor | Permite la ejecución o ejecuta `bash START.sh` desde la carpeta |
| Error de descarga | Internet, acceso a PyPI/GitHub/repositorios APT; vuelve a ejecutar para continuar |
| SO o procesador rechazado | Debian/Ubuntu/Raspberry Pi OS 64 bits, ARM64 o x86-64 |
| KMBox ausente / varios puertos | Cable de datos, puerto de control correcto y luego `PORT` en la configuración |
| La KMBox no responde | Firmware compatible con `km.*`, baudios, sin otro monitor serie; espera hasta 25 s |
| Permiso USB denegado | Reconecta el dispositivo tras la instalación; comprueba su identificador y las reglas udev |
| DMA no disponible | Puerto USB correcto, firmware compatible, tarjeta reconocida, ningún otro cliente DMA |
| Esperando `cs2.exe/client.dll` | CS2 debe estar en ejecución en la máquina conectada a la tarjeta DMA |
| Sin corrección | Clic físico, estado de suspensión, sensibilidad válida, offsets y geometría; lee el registro |
| Código de salida 75 | Otra instancia ya tiene el bloqueo DMA |

Diagnóstico de hardware sin movimiento, desde la carpeta del software:

```bash
bash release/start-aim.sh --check --duration 10
```

Verificación del entorno instalado:

```bash
bash release/setup-aim.sh --check
```

El diagnóstico de hardware requiere los dispositivos conectados. No sustituye la
validación de tu firmware ni de tu cableado.

## Contenido del repositorio

```text
AIM Studio DMA/
├── AIM Studio DMA.desktop   # Lanzador gráfico de primera instalación
├── START.sh                 # Punto de entrada
├── README.md
├── .gitignore               # Excluye instalación y datos personales
└── release/
    ├── aim_*.py             # Interfaz, traducciones y módulos
    ├── dma_aim.py           # Motor
    ├── update_aim_offsets.py
    ├── *.sh                # Instalación y lanzadores
    ├── install_aim_runtime.py
    ├── requirements-aim.txt
    ├── aim-settings.example.conf
    ├── offsets.json
    └── maps/               # Geometrías necesarias para la visibilidad
```

Puedes publicar **esta carpeta** como raíz del repositorio de GitHub. Las
dependencias instaladas, las cachés y las preferencias están excluidas por `.gitignore`.
Para los usuarios, prefiere el ZIP del repositorio o un archivo en GitHub Releases:
las geometrías hacen que el repositorio sea grande y no se adaptan a la subida web archivo por archivo.

## Componentes y créditos

- Interfaz e integración: **Akumaprog**.
- Acceso DMA: [MemProcFS](https://github.com/ufrisk/MemProcFS) y [LeechCore](https://github.com/ufrisk/LeechCore), por Ulf Frisk.
- Enlace serie: [pySerial](https://github.com/pyserial/pyserial).
- Fuentes de offsets y firmas: [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper).
- Geometrías ProCS2 tomadas del proyecto [chao-shushu/CS2-DMA](https://github.com/chao-shushu/CS2-DMA), según la procedencia documentada en el proyecto fuente.

Las licencias de las bibliotecas nativas se conservan con su instalación en
`release/.runtime/vmm/`. Los componentes de terceros conservan sus respectivas licencias.