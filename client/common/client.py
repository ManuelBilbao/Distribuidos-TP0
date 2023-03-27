import csv
import json
import logging
import signal
import socket
import sys


# ClientConfig Configuration used by the client
class ClientConfig:
    def __init__(self, id: str, server_address: str, chunk_size: int):
        self.id = id
        self.server_address = server_address
        self.chunk_size = chunk_size


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
        try:
            file = open(f"/data/agency-{self.config.id}.csv")
            reader = csv.reader(file, delimiter=',')

            bets = [{
                "first_name": row[0],
                "last_name": row[1],
                "document": row[2],
                "birthdate": row[3],
                "number": row[4]
            } for row in reader]
        except Exception as e:
            logging.error(
                f'action: read_file | result: fail | '
                f'client_id: {self.config.id} | error: {e}'
            )
            return
        finally:
            file.close()

        bets_sent = 0
        while bets_sent < len(bets):
            # Create the connection to the server
            self.create_client_socket()

            # Send a message to the server
            try:
                msg = {
                    "agency": self.config.id,
                    "bets": bets[bets_sent:bets_sent+self.config.chunk_size]
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
                msg = self.conn.recv(2)
                length = int.from_bytes(msg, "little", signed=False)
                if length > 8190:
                    logging.warning(
                        'action: receive_message | result: fail | '
                        'error: Message exceeded maximum length'
                    )
                    continue

                msg = self.conn.recv(length).rstrip().decode("utf-8")
                data = json.loads(msg)

                if data["success"]:
                    logging.info(
                        'action: apuesta_enviada | result: success | '
                        f'quantity: {data["quantity"]}'
                    )
                    bets_sent += self.config.chunk_size
                else:
                    logging.error(
                        'action: apuesta_enviada | result: fail | '
                        f' error: {data["error"]}'
                    )
            except json.decoder.JSONDecodeError:
                logging.error(
                    'action: receive_message | result: fail | '
                    f'client_id: {self.config.id} | '
                    'error: Malformed message'
                )
            except Exception as e:
                logging.error(
                    'action: receive_message | result: fail | '
                    f'client_id: {self.config.id} | error: {e}'
                )
                break
            finally:
                # Log the received message
                logging.info(
                    'action: receive_message | result: success | '
                    f'client_id: {self.config.id} | msg: {msg}'
                )

                # Close the connection to the server
                self.conn.close()

            logging.info(
                f'action: receive_message | result: success | '
                f'client_id: {self.config.id} | msg: {msg}'
            )
