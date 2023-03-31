import csv
import json
import logging
import signal
import socket
import sys
import time


# ClientConfig Configuration used by the client
class ClientConfig:
    def __init__(self, id: str, server_address: str, chunk_size:
                 int, ask_delay: int):
        self.id = id
        self.server_address = server_address
        self.chunk_size = chunk_size
        self.ask_delay = ask_delay


# Client Entity that encapsulates how
class Client:
    def __init__(self, config: ClientConfig):
        self.config = config
        self.conn = None
        self.closing = False
        signal.signal(signal.SIGTERM, self.exit)

    def exit(self, *args):
        logging.info(
            f'[CLIENT {self.config.id}] Received SIGTERM. '
            'Stopping gracefully...'
        )
        self.conn.close()
        self.closing = True

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

    # Read file with bets and return a list with them.
    # In case of failure, error is printed in stdout/stderr
    # and exit 1 is returned
    def read_bets_file(self) -> list:
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

            return bets
        except Exception as e:
            logging.error(
                f'action: read_file | result: fail | '
                f'client_id: {self.config.id} | error: {e}'
            )
            sys.exit(1)
        finally:
            file.close()

    def send_message(self, message: dict) -> bool:
        try:
            encoded_msg = json.dumps(message).encode("utf-8")
            encoded_size = len(encoded_msg).to_bytes(2, "little",
                                                     signed=False)
            self.conn.sendall(encoded_size + encoded_msg)

            return True
        except Exception as e:
            if not self.closing:
                logging.error(
                    f'action: send_message | result: fail | '
                    f'client_id: {self.config.id} | error: {e}'
                )
            return False

    # Try to send bets to server. Return True on success
    def send_bets(self, bets: list) -> bool:
        msg = {
            "agency": self.config.id,
            "action": "bets",
            "bets": bets
        }
        return self.send_message(msg)

    def read_response(self, bets_sent: int, retries: int) -> (int, int):
        try:
            msg = self.conn.recv(2)
            length = int.from_bytes(msg, "little", signed=False)
            if length > 8190:
                logging.warning(
                    'action: receive_message | result: fail | '
                    'error: Message exceeded maximum length'
                )
                return bets_sent, retries

            msg = self.conn.recv(length).rstrip().decode("utf-8")
            data = json.loads(msg)

            if data["success"]:
                logging.info(
                    'action: apuesta_enviada | result: success | '
                    f'quantity: {data["quantity"]}'
                )
                bets_sent += self.config.chunk_size
                retries = 0
            else:
                logging.error(
                    'action: apuesta_enviada | result: fail | '
                    f' error: {data["error"]}'
                )

                if data["error"] == "Message exceeded maximum length":
                    self.config.chunk_size = int(self.config.chunk_size
                                                 * 0.95)
                else:
                    retries += 1
        except json.decoder.JSONDecodeError:
            logging.error(
                'action: receive_message | result: fail | '
                f'client_id: {self.config.id} | '
                'error: Malformed message'
            )
            retries += 1
        except Exception as e:
            if not self.closing:
                logging.error(
                    'action: receive_message | result: fail | '
                    f'client_id: {self.config.id} | error: {e}'
                )
                retries += 1
        finally:
            # Log the received message
            logging.info(
                'action: receive_message | result: success | '
                f'client_id: {self.config.id} | msg: {msg}'
            )

            # Close the connection to the server
            self.conn.close()

        return bets_sent, retries

    def send_finish(self):
        self.create_client_socket()

        msg = {
            "agency": self.config.id,
            "action": "finish"
        }
        self.send_message(msg)

        self.conn.close()

    def ask_winners(self):
        self.create_client_socket()

        msg = {
            "agency": self.config.id,
            "action": "winners"
        }
        self.send_message(msg)

        try:
            msg = self.conn.recv(2)
            length = int.from_bytes(msg, "little", signed=False)
            if length > 8190:
                raise Exception("Message exceeded maximum length")

            msg = ""
            while len(msg) < length-1:
                msg += self.conn.recv(length).rstrip().decode("utf-8")
            data = json.loads(msg)

            if not data["success"]:
                if data["error"] == "Lottery not done yet":
                    logging.info(
                        "action: consulta_ganadores | result: fail | "
                        "error: Lottery not done yet"
                    )
                    time.sleep(self.config.ask_delay)
                    if not self.closing:
                        return self.ask_winners()

                raise Exception(data["error"])

            logging.info(
                'action: consulta_ganadores | result: success | '
                f'cant_ganadores: {len(data["winners"])}'
            )
        except Exception as e:
            if not self.closing:
                logging.error(
                    f'action: consulta_ganadores | result: fail | error: {e}'
                )

        finally:
            self.conn.close()

    # start_client_loop Send messages to the client until
    # some time threshold is met
    def start_client_loop(self):
        bets = self.read_bets_file()

        bets_sent = 0
        retries = 0
        while not self.closing and bets_sent < len(bets) and retries < 3:
            # Create the connection to the server
            self.create_client_socket()

            if not self.send_bets(
                bets[bets_sent:bets_sent+self.config.chunk_size]
            ):
                continue

            bets_sent, retries = self.read_response(bets_sent, retries)

        if self.closing:
            return

        if retries == 3:
            logging.error(
                'action: apuestas_enviadas | result: fail | '
                f'client_id: {self.config.id} | '
                'error: Too many retries on error'
            )
            sys.exit(-1)

        logging.info(
            'action: apuestas_enviadas | result: success | '
            f'client_id: {self.config.id}'
        )
        self.send_finish()
        self.ask_winners()
