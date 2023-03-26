import logging
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
        # Autoincremental msg_id to identify every message sent
        msg_id = 1

        # Send messages while the loop_lapse threshold has not been surpassed
        start_time = time.monotonic()
        past_time = 0
        while past_time < self.config.loop_lapse:
            # Create the connection to the server
            self.create_client_socket()

            # Send a message to the server
            try:
                self.conn.sendall(
                    f'[CLIENT {self.config.id}] Message N°{msg_id}\n'.encode()
                )
            except Exception as e:
                logging.error(
                    f'action: send_message | result: fail | '
                    f'client_id: {self.config.id} | error: {e}'
                )
                break

            # Receive a message from the server
            try:
                msg = self.conn.recv(4096).decode()
                if msg[-1] == '\n':
                    msg = msg[:-1]
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
