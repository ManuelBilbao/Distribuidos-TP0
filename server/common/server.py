import json
import logging
import signal
import socket
import sys
import threading
import time

from .utils import Bet, store_bets, load_bets, has_won


class TooLongException(Exception):
    pass


class Server:
    def __init__(self, port, listen_backlog, agencies, max_threads=1):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)

        self.agencies = agencies
        self.agencies_finished = set()
        self.agencies_finished_lock = threading.Lock()

        self.threads = []
        self.thread_semaphore = threading.Semaphore(max_threads)
        self.file_lock = threading.Lock()

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
            self.thread_semaphore.acquire()
            thread = threading.Thread(
                target=self.__handle_client_connection,
                args=(client_sock,)
            )
            self.threads += [thread]
            thread.start()

    def stop(self, *args):
        logging.info("Received SIGTERM. Stopping gracefully...")
        self._server_socket.close()
        sys.exit(0)

        for thread in self.threads:
            thread.join()

    def __handle_bets(self, agency, bets):
        try:
            bets = [Bet(agency, **bet) for bet in bets]

            with self.file_lock:
                # time.sleep(4)  # Con esto podemos probar la paralelizción
                store_bets(bets)

            for bet in bets:
                logging.info(
                    'action: apuesta_almacenada | result: success | '
                    f'dni: {bet.document} | numero: {bet.number}'
                )

            return {
                "success": True,
                "quantity": len(bets)
            }
        except Exception as e:
            logging.error(
                f"action: parse_bets | result: error | error: {e}"
            )
            return {
                "success": False,
                "error": "Unknown error"
            }

    def __handle_finish(self, agency):
        with self.agencies_finished_lock:
            self.agencies_finished.add(agency)

    def __handle_winners(self, agency):
        with self.agencies_finished_lock:
            if len(self.agencies_finished) != self.agencies:
                logging.warning(
                    "action: ask_winners | result: error | "
                    "error: Not all agencies are ready yet"
                )
                return {
                    "success": False,
                    "error": "Lottery not done yet"
                }

        with self.file_lock:
            bets = load_bets()
        winners = list(map(
            lambda bet: bet.document,
            filter(
                lambda bet: bet.agency == agency and has_won(bet),
                bets
            )
        ))

        return {
            "success": True,
            "winners": winners
        }

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            addr = client_sock.getpeername()

            msg = client_sock.recv(2)
            length = int.from_bytes(msg, "little", signed=False)
            if length > 8190:
                raise TooLongException("Message exceeded maximum length")

            msg = ""
            while len(msg) < length-1:
                msg += client_sock.recv(length-len(msg)).rstrip()\
                                  .decode("utf-8")
            data = json.loads(msg)

            logging.debug(
                'action: receive_message | result: success | '
                f'ip: {addr[0]} | msg: {msg}'
            )

            if data["action"] == "bets":
                response = self.__handle_bets(int(data["agency"]),
                                              data["bets"])
            elif data["action"] == "finish":
                response = self.__handle_finish(int(data["agency"]))
            elif data["action"] == "winners":
                response = self.__handle_winners(int(data["agency"]))
        except json.decoder.JSONDecodeError:
            logging.error(
                "action: receive_message | result: fail | "
                "error: Malformed message"
            )
            response = {
                "success": False,
                "error": "Malformed message"
            }
        except TooLongException:
            logging.error(
                'action: receive_message | result: fail | '
                'error: Message exceeded maximum length'
            )
            response = {
                "success": False,
                "error": "Message exceeded maximum length"
            }
        except Exception as e:
            logging.error(
                f"action: receive_message | result: fail | error: {e}"
            )
            response = {
                "success": False,
                "error": "Unknown error"
            }
        finally:
            if response:
                encoded_response = json.dumps(response).encode("utf-8")
                encoded_size = len(encoded_response).to_bytes(2, "little",
                                                              signed=False)
                client_sock.sendall(encoded_size + encoded_response)
            client_sock.close()
            self.thread_semaphore.release()

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
