import os
import logging
import yaml

from common.client import ClientConfig, Client


def parse_time(time: str) -> int:
    m_pos = time.find("m")
    if m_pos >= 0:
        minutes = int(time[:m_pos])
        seconds = int(time[m_pos+1:-1])
    else:
        minutes = 0
        seconds = int(time[:-1])

    return 60 * minutes + seconds


def init_config() -> ClientConfig:
    # Set client ID
    id = os.environ['CLI_ID']

    try:
        config_file = open('./config.yaml')
        config = yaml.load(config_file, Loader=yaml.Loader)
        config_file.close()

        server_address = config["server"]["address"]
        loop_lapse = parse_time(config["loop"]["lapse"])
        loop_period = parse_time(config["loop"]["period"])

        log_level = config["log"]["level"]
    except Exception:
        logging.warning(
            'Could not open or read configuration file. '
            'Will try to get from envvars'
        )

        # Set server address
        try:
            server_address = os.environ['CLI_SERVER_ADDRESS']
        except Exception:
            logging.error('Could not find the server address')
            raise

        # Set loop lapse
        try:
            loop_lapse = int(os.environ.get('CLI_LOOP_LAPSE'))
        except TypeError:
            logging.error('Could not parse CLI_LOOP_LAPSE env var as int.')
            raise

        # Set loop period
        try:
            loop_period = int(os.environ.get('CLI_LOOP_PERIOD'))
        except TypeError:
            logging.error('Could not parse CLI_LOOP_PERIOD env var as int.')
            raise

    config = ClientConfig(id, server_address, loop_lapse, loop_period)

    # Set log level
    if not log_level:
        log_level = os.environ.get('CLI_LOG_LEVEL', 'INFO')
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        level=numeric_level
    )

    return config


def main() -> None:
    try:
        config = init_config()
    except Exception:
        return

    # Print program config with debugging purposes
    log_level = logging.getLevelName(logging.getLogger().getEffectiveLevel())
    logging.info(
        f'action: config | result: success | client_id: {config.id} | '
        f'server_address: {config.server_address} | '
        f'loop_lapse: {config.loop_lapse} | '
        f'loop_period: {config.loop_period} | log_level: {log_level}'
    )

    client = Client(config)
    client.start_client_loop()


if __name__ == "__main__":
    main()
