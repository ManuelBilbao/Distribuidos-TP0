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
