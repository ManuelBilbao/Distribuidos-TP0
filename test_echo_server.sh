#!/bin/bash

number=$RANDOM

response=$(docker run --rm --network tp0_testing_net --entrypoint sh subfuzion/netcat -c "echo $number | nc server 12345")

if [[ $number == $response ]]; then
	echo -e "\033[0;32mSuccess!\033[0m"
else
	echo -e "\033[0;31mError!\033[0m"
	echo "Expected: \"$number\" - Response: \"$response\""
fi
