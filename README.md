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
