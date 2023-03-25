#!/bin/bash

N_CLIENTS=${1:-1}

clients_code=""

for (( i = 1; i <= N_CLIENTS ; i++ ))
do
	NL=""
	if [ $i != 1 ]; then
		NL="\n\n"
	fi

	clients_code=$(printf "%s%s%s" "$clients_code" $NL "$(cat client-template.yml | CLI_ID=$i envsubst)")
done

awk -v c="$clients_code" '{gsub(/# CLIENTS/,c)}1' docker-compose-dev.yaml
