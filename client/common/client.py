import json
import logging
import os
import signal
import socket
import sys
import time


# ClientConfig Configuration used by the client
class ClientConfig:
    def __init__(self, id: str, server_address: str,
                 loop_lapse: int, loop_period: int):
        self.id = id
        self.server_address = server_address
        self.loop_lapse = loop_lapse
        self.loop_period = loop_period


# Client Entity that encapsulates how
class Client:
    def __init__(self, config: ClientConfig):
        self.config = config
        self.conn = None
        signal.signal(signal.SIGTERM, self.exit)

    def exit(self, *args):
        logging.info(
            f'[CLIENT {self.config.id}] Received SIGTERM. '
            'Stopping gracefully...'
        )
        self.conn.close()
        sys.exit(0)

    # create_client_socket Initializes client socket. In case of
    # failure, error is printed in stdout/stderr and exit 1 is returned
    def create_client_socket(self) -> None:
        try:
            self.conn = socket.create_connection(
                self.config.server_address.split(":")
            )
        except socket.error as e:
            logging.error(
                f'action: connect | result: fail | '
                f'client_id: {self.config.id} | error: {e}'
            )
            sys.exit(1)

    # start_client_loop Send messages to the client until
    # some time threshold is met
    def start_client_loop(self):
        # Send messages while the loop_lapse threshold has not been surpassed
        start_time = time.monotonic()
        past_time = 0
        while past_time < self.config.loop_lapse:
            # Create the connection to the server
            self.create_client_socket()

            # Send a message to the server
            try:
                msg = {
                    "agency": self.config.id,
                    "first_name": os.environ["NOMBRE"],
                    "last_name": os.environ["APELLIDO"],
                    "document": os.environ["DOCUMENTO"],
                    "birthdate": os.environ["NACIMIENTO"],
                    "number": os.environ["NUMERO"]
                }
                encoded_msg = json.dumps(msg).encode("utf-8")
                encoded_size = len(encoded_msg).to_bytes(2, "little",
                                                         signed=False)
                self.conn.sendall(encoded_size + encoded_msg)
            except Exception as e:
                logging.error(
                    f'action: send_message | result: fail | '
                    f'client_id: {self.config.id} | error: {e}'
                )
                break

            # Receive a message from the server
            try:
                msg = self.conn.recv(8192).rstrip().decode("utf-8")
                data = json.loads(msg)
                if data["success"]:
                    logging.info(
                        'action: apuesta_enviada | result: success | '
                        f'dni: {data["document"]} | numero: {data["number"]}'
                    )
                else:
                    logging.warning(
                        'action: apuesta_enviada | result: fail | '
                        f'dni: {data["document"]} | numero: {data["number"]} |'
                        f' error: {data["error"]}'
                    )
            except json.decoder.JSONDecodeError:
                logging.error(
                    'action: receive_mesage | result: fail | '
                    f'client_id: {self.config.id} | '
                    'error: Malformed message'
                )
            except Exception as e:
                logging.error(
                    f'action: receive_message | result: fail | '
                    f'client_id: {self.config.id} | error: {e}'
                )
                break

            # Log the received message
            logging.info(
                f'action: receive_message | result: success | '
                f'client_id: {self.config.id} | msg: {msg}'
            )

            # Wait a time between sending one message and the next one
            time.sleep(self.config.loop_period)

            # Update the past time
            past_time = time.monotonic() - start_time

            # Close the connection to the server
            self.conn.close()

        logging.info(
            f'action: timeout_detected | result: success | '
            f'client_id: {self.config.id}'
        )
