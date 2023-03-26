import json
import logging
import signal
import socket
import sys

from .utils import Bet, store_bets


class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        signal.signal(signal.SIGTERM, self.stop)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        while True:
            client_sock = self.__accept_new_connection()
            self.__handle_client_connection(client_sock)

    def stop(self, *args):
        logging.info("Received SIGTERM. Stopping gracefully...")
        self._server_socket.close()
        sys.exit(0)

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            msg = client_sock.recv(8192).rstrip().decode('utf-8')
            addr = client_sock.getpeername()
            logging.info(
                'action: receive_message | result: success | '
                f'ip: {addr[0]} | msg: {msg}'
            )

            data = json.loads(msg)
            bet = Bet(**data)
            store_bets([bet])
            logging.info(
                'action: apuesta_almacenada | result: success | '
                f'dni: {bet.document} | numero: {bet.number}'
            )

            response = {
                "success": True,
                "document": bet.document,
                "number": bet.number
            }
            client_sock.sendall(json.dumps(response).encode("utf-8"))
        except json.decoder.JSONDecodeError:
            logging.error(
                "action: receive_mesage | result: fail | "
                "error: Malformed message or short read"
            )
        except Exception as e:
            logging.error(
                f"action: receive_message | result: fail | error: {e}"
            )
        finally:
            client_sock.close()

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info(
            f'action: accept_connections | result: success | ip: {addr[0]}'
        )
        return c
