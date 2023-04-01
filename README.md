# TP0: Docker + Comunicaciones + Concurrencia

## Parte 1: Introducción a Docker

### Ejercicio 1

> Modificar la definición del DockerCompose para agregar un nuevo cliente al proyecto.

Este ejercicio decidí resolverlo de la manera más simple posible para poder enfocarme mejor en el siguiente, donde se aborda la misma problemática pero generalizada. Por lo tanto, simplemente añadí un nuevo servicio al archivo `docker-compose-dev.yml` idéntico al cliente existente, aunque modificando el número de cliente.

### Ejercicio 1-1

> Definir un script (en el lenguaje deseado) que permita crear una definición de DockerCompose con una cantidad configurable de clientes.

Ahora sí voy a encarar el problema de un modo más general. En este caso lo que hice fue crear un _script_ en Bash que recibe por parámetro la cantidad de clientes que se desea tener, aunque este es opcional y toma por defecto el valor 1. Conociendo el número de clientes, se crea un _string_ con la declaración de todos los servicios necesarios para los mismos, partiendo de una plantilla `client-template.yml`. Por último, se toma el contendio de `docker-compose-dev.yml` y utilizando `awk` se insertan los nuevos servicios.

El resultado se imprime por salida estándar. De esta manera, se puede redirigir a un archivo o utilizar `docker compose` directamente, por ejemplo, haciendo `./build_docker_compose.sh 3 | docker compose -f - up`.

Para realizar este ejercicio se podría haber utilizado también la opción `replica` de `deploy`, pero esto implica correr los contenedores en modo `docker swarm`, lo cual considero que excede el proyecto y no es necesaria la complejidad que conlleva.

### Ejercicio 2

> Modificar el cliente y el servidor para lograr que realizar cambios en el archivo de configuración no requiera un nuevo build de las imágenes de Docker para que los mismos sean efectivos. La configuración a través del archivo correspondiente (`config.ini` y `config.yaml`, dependiendo de la aplicación) debe ser inyectada en el container y persistida afuera de la imagen (hint: `docker volumes`).

Para este ejercicio simplemente agregué a las declaraciones de servidor y clientes un volumen con el archivo de configuración correspondiente. De esta forma, no es necesario recrear las imágenes cada vez que hay un cambio, aunque esto no implica que una modificación no provoque que la imagen vaya a cambiar. Para evitar que esto pase, se podría crear un archivo `.dockerignore` en los directorios de servidor y cliente, que contengan el nombre del archivo de configuración correspondiente a cada uno. Decidí no hacer esto porque si se quiere crear la imagen para compartir por algún medio, en lugar de utilizar `docker compose`, es necesario contar con esos archivos.

### Ejercicio 3

> Crear un script que permita verificar el correcto funcionamiento del servidor utilizando el comando `netcat` para interactuar con el mismo. Dado que el servidor es un EchoServer, se debe enviar un mensaje al servidor y esperar recibir el mismo mensaje enviado. Netcat no debe ser instalado en la máquina _host_ y no se puede exponer puertos del servidor para realizar la comunicación (hint: `docker network`).

Para resolver este ejercicio nuevamente creé un _script_ en Bash que crea y lanza un contenedor muy ligero, basado en Alpine, que contiene el ejecutable de `netcat`. Este contenedor lo agrego a la red donde se encuentra el servidor (que debe estar previamente iniciado) utilizando el flag `--network`. Cuando el contenedor inicia, intenta conectarse al servidor y enviarle un número aleatorio, que luego el _script_ va a comparar con la respuesta en busca de coincidencia.

### Ejercicio 4

> Modificar servidor y cliente para que ambos sistemas terminen de forma _graceful_ al recibir la signal SIGTERM. Terminar la aplicación de forma _graceful_ implica que todos los _file descriptors_ (entre los que se encuentran archivos, sockets, threads y procesos) deben cerrarse correctamente antes que el thread de la aplicación principal muera. Loguear mensajes en el cierre de cada recurso (hint: Verificar que hace el flag `-t` utilizado en el comando `docker compose down`).

Antes de continuar, decidí que lo mejor iba a ser reescribir el cliente en Python, ya que en mi caso sería más sencillo de comprender y modificar para resolver los ejercicios que siguen.

Una vez hecho eso, modfiqué tanto el cliente como el servidor para que se dispare una función al recibir un SIGTERM. Esta función se ejecutará instantáneamente, interrumpiendo el resto del programa, y se ocupará de cerrar la conexión del socket antes de finalizar.

## Parte 2: Repaso de Comunicaciones

### Ejercicio 5

> Modificar la lógica de negocio tanto de los clientes como del servidor para nuestro nuevo caso de uso. [...]

~~Para este ejercicio pensé que una forma sencilla y confiable de transmitir los datos sería serializarlos en forma de JSON. Esto me permite recuperar fácilmente un objeto del otro lado de la comunicación. En principio, todos los datos de la apuesta se encuentran en la raíz del objeto, pero para el siguiente ejercicio será muy fácil modificarlo para que soporte varias apuestas.~~

~~El protocolo que utilizo para la comunicación es un número codificado en 2 bytes, que indica el tamaño del resto del mensaje, seguido de la serialización del JSON codificada en UTF-8. Con este protocolo logro evitar los _short reads_ ya que siempre sé exactamente cuántos bytes tengo que leer.~~

También, para evitar los _short writes_, remplacé los `send` por `sendall`, que se encarga de reintentar el envío en caso de ser necesario o devolver un error cuando no sea posible.

### Ejercicio 6

> Modificar los clientes para que envíen varias apuestas a la vez (modalidad conocida como procesamiento por _chunks_ o _batchs_). La información de cada agencia será simulada por la ingesta de su archivo numerado correspondiente, provisto por la cátedra dentro de `.data/datasets.zip`.

Lo primero que hice fue modificar el Dockerfile del cliente para que las imágenes tengan los archivos de datos de las apuestas. ~~También modfiqué el protocolo de comunicación. Ahora en la raíz del objeto JSON se envía el código de agencia y una lista con todas las apuestas.~~

La cantidad de apuestas a enviar por mensaje es configurable por el archivo de configuración o por variable de entorno. De todas formas, si se detecta que los mensajes son demasiado largos con la cantidad de apuestas establecidas, este número bajará un 5% hasta que el mensaje se puede enviar correctamente.

### Ejercicio 7

> Modificar los clientes para que notifiquen al servidor al finalizar con el envío de todas las apuestas y así proceder con el sorteo. Inmediatamente después de la notificacion, los clientes consultarán la lista de ganadores del sorteo correspondientes a su agencia. Una vez el cliente obtenga los resultados, deberá imprimir por log: `action: consulta_ganadores | result: success | cant_ganadores: ${CANT}`. [...]

En este ejercicio volví a modificar el protocolo para que se adapte mejor a las necesidades del problema. En este caso, agregué un campo _action_ que indica el tipo de acción que involucra el mensaje. Este puede ser "bets", "finish" o "winners".

Una desición que tuve que tomar fue qué hacer cuando el cliente solicita la lista de ganadores y el servidor todavía no realizó el sorteo. Lo que terminé haciendo fue utilizar la metodología de _polling_ con la cual el cliente le pregunta al servidor repetidamente (con cierta demora) y este le responde error o la lista según ya esté disponible.

### Ejercicio 8

> Modificar el servidor para que permita aceptar conexiones y procesar mensajes en paralelo. [...]

Para este último ejercicio utilicé la librería `threading` de Python, que ofrece varias herramientas útiles. Por cada nueva conexión se lanza un _thread_ nuevo, que será el encargado de manejar ese cliente. Para evitar que se desplieguen miles de _threads_ simultáneamente, usé un semáforo que define la cantidad máxima de _threads_ que pueden haber, la cual se establece en el archivo de configuración. Además, para evitar accesos simulatáneos de lectura o escritura al archivo de apuestas, utilicé un _Lock_ (_Mutex_) que debe ser adquirido por cada hilo antes de acceder al archivo.

## Protocolo

El protocolo sigue el modelo TLV aunque con una modificación menor. Para los mensajes que envía el cliente, el protocolo se basa en 1 byte para el tipo, 1 byte para el número de agencia y 2 bytes para el largo del cuerpo del mensaje. El cuerpo del mensaje y su largo se envían únicamente si el mensaje es para enviar apuestas. Si es para indicar la finalización de envío o preguntar los ganadores, estos no se envían.

Entonces, el esquema general del mensaje es: `[TYPE][AGENCY_NUMBER][LENGTH][MESSAGE]`

Los tipos disponibles son:
- `TYPE_BETS = 1`
- `TYPE_FINISH = 2`
- `TYPE_ASK_WINNERS = 4`
- `TYPE_RESPONSE_ERROR = 8`
- `TYPE_RESPONSE_SUCCESS = 9`

Por ejemplo, para indicar la finalización del envío de apuestas del cliente 1, se envía `0x0201`.

La serialización de las apuestas se basa en codificar todos los campos ordenadamente en UTF-8 y concatenarlos con un byte nulo. Para separar apuestas se usa un caracter `\n`. Entonces, por ejemplo, para enviar 2 apuestas con los siguientes campos desde el cliente 1:

|Nombre|Apellido|Documento|Nacimiento|Número|
|------|--------|---------|----------|------|
|Manuel|Bilbao|102732|1998-09-01|294|
|Juan|Perez|111111|2000-01-01|324|

Se codifica `0x010144004d616e75656c0042696c62616f0031303237333200313939382d30392d3031003239340a4a75616e00506572657a0031313131313100323030302d30312d303100333234`. Esto es, `[TYPE_BETS][AGENCIA_1][LARGO][NOMBRE1]\0[APELLIDO1]\0[DOCUMETO1]\0[NACIMIENTO1]\0[NUMERO1]\n[NOMBRE2]\0[APELLIDO2]\0[DOCUMENTO2]\0[NACIMIENTO2]\0[NUMERO2]`.

Para las respuestas del servidor, se hace algo parecido. Se utilizan los tipos `RESPONSE` y su composición es el tipo seguido del largo del cuerpo y el cuerpo.

Por ejemplo, para responder la cantidad de apuestas registradas, se envía `[TYPE_RESPONSE_SUCCESS][LARGO][NUMERO]`, con el número codificado en UTF-8. En los casos de error el cuerpo del mensaje es el mensaje de error. Para enviar las apuestas ganadoras, se codifican los documentos en UTF-8, se concatenan con bytes nulos y eso se envía en el cuerpo del mensaje.
