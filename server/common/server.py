import logging
import signal
import socket
import threading
import time

from .utils import Bet, store_bets, load_bets, has_won


TYPE_BETS = 1
TYPE_FINISH = 2
TYPE_ASK_WINNERS = 4
TYPE_RESPONSE_ERROR = 8
TYPE_RESPONSE_SUCCESS = 9


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

        self.keep_running = True
        while self.keep_running:
            try:
                client_sock = self.__accept_new_connection()
            except Exception as e:
                if self.keep_running:
                    logging.error(
                        'action: accept_connections | result: fail | '
                        f'error {e}'
                    )
                    self._server_socket.close()
                break

            self.thread_semaphore.acquire()
            thread = threading.Thread(
                target=self.__handle_client_connection,
                args=(client_sock,)
            )
            self.threads += [thread]
            thread.start()

            [thread.join() for thread in self.threads if not thread.is_alive()]
            self.threads = [
                thread for thread in self.threads if thread.is_alive()
            ]

    def stop(self, *args):
        logging.info("Received SIGTERM. Stopping gracefully...")
        self._server_socket.close()
        self.keep_running = False

        for thread in self.threads:
            thread.join()

    def read_until_zero(self, socket):
        stream = b""
        while len(stream) == 0 or stream[-1] != 0:
            stream += socket.recv(1)

        return stream[:-1].decode("utf-8"), len(stream)

    def make_response(self, success, message):
        type = TYPE_RESPONSE_SUCCESS if success else TYPE_RESPONSE_ERROR
        return type.to_bytes(1, "little", signed=False) + \
            len(message).to_bytes(2, "little", signed=False) + \
            message

    def __handle_bets(self, agency, client_socket):
        try:
            msg_length = client_socket.recv(2)
            length = int.from_bytes(msg_length, "little", signed=False)
            if length > 8190:
                raise TooLongException("Message exceeded maximum length")

            stream = b""
            while len(stream) < length-1:
                stream += client_socket.recv(length - len(stream))

            rows = stream.split("\n".encode("utf-8"))

            bets = []
            for row in rows:
                data = [campo.decode("utf-8") for campo in row.split(b"\0")]
                bets += [Bet(agency, *data)]

            with self.file_lock:
                # time.sleep(4)  # Con esto podemos probar la concurrencia
                store_bets(bets)

            for bet in bets:
                logging.info(
                    'action: apuesta_almacenada | result: success | '
                    f'dni: {bet.document} | numero: {bet.number}'
                )

            return self.make_response(True, str(len(bets)).encode("utf-8"))
        except TooLongException:
            error = "Message exceeded maximum length"
            logging.error(
                'action: receive_message | result: fail | '
                f'error: {error}'
            )
            return self.make_response(False, error.encode("utf-8"))
        except Exception as e:
            logging.error(
                f"action: parse_bets | result: error | error: {e}"
            )
            return self.make_response(False, "Unknown error".encode("utf-8"))

    def __handle_finish(self, agency):
        with self.agencies_finished_lock:
            self.agencies_finished.add(agency)

    def __handle_winners(self, agency):
        with self.agencies_finished_lock:
            if len(self.agencies_finished) != self.agencies:
                error = "Lottery not done yet"
                logging.warning(
                    "action: ask_winners | result: error | "
                    f"error: {error}"
                )
                return self.make_response(False, error.encode("utf-8"))

        with self.file_lock:
            bets = load_bets()
        winners = list(map(
            lambda bet: str(bet.document).encode("utf-8"),
            filter(
                lambda bet: bet.agency == agency and has_won(bet),
                bets
            )
        ))

        return self.make_response(True, b"\0".join(winners))

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            addr = client_sock.getpeername()

            type_agency = client_sock.recv(2)
            msg_type = int.from_bytes(type_agency[:1], "little", signed=False)
            agency = int.from_bytes(type_agency[1:], "little", signed=False)

            logging.debug(
                'action: receive_message | result: success | '
                f'ip: {addr[0]} | agency: {agency} | '
                f'msg_type: {msg_type}'
            )

            if msg_type == TYPE_BETS:
                response = self.__handle_bets(agency, client_sock)
            elif msg_type == TYPE_FINISH:
                response = self.__handle_finish(agency)
            elif msg_type == TYPE_ASK_WINNERS:
                response = self.__handle_winners(agency)
        except Exception as e:
            logging.error(
                f"action: receive_message | result: fail | error: {e}"
            )
            response = self.make_response(False,
                                          "Unknown error".encode("utf-8"))
            if not self.keep_running:
                response = self.make_response(False,
                                              "Server close".encode("utf-8"))

        finally:
            if response:
                client_sock.sendall(response)
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
