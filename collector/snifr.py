import socket
import redis

from time import gmtime, strftime
import pickle

import configparser
from optparse import OptionParser
from loguru import logger

import multiprocessing
from gps import GPSTerminal


class Server(object):
    def __init__(self, hostname, port, *args, **kwargs):
        self.hostname = hostname
        self.port = port
        self.config = kwargs["config"]
        self.logTime = strftime("%d %b %H:%M:%S", gmtime())
        self.identifier = "None"

        # set redis rcli
        r_host = self.config.get("redis", "host")
        r_port = int(self.config.get("redis", "port"))
        r_db = int(self.config.get("redis", "db"))
        self.rcli = redis.Redis(host=r_host, port=r_port, db=r_db)
        self.channel = self.config.get("redis", "channel")

        # logger
        self.logger = logger.bind(__name__=self.__class__.__name__)

    def start(self):
        self.logger.debug("...Started listening to devices stream")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.hostname, self.port))
        self.socket.listen(5)

        while True:
            conn, address = self.socket.accept()
            self.logger.debug("...Accpet connection from devices")
            process = multiprocessing.Process(target=self.handle, args=(conn, address))
            process.daemon = True
            process.start()
            self.logger.debug("...Started process %r", process)

    def handle(self, connection, address):
        from loguru import logger

        logger = logger.bind(__name__="process-%r" % (address,))

        # @TODO: need to check and fix this one
        terminalClient = None
        try:
            logger.debug("Connected %r at %r", connection, address)
            while True:
                terminalClient = GPSTerminal((connection, address))
                if terminalClient.isSuccess():
                    logger.debug("Socket closed remotely")
                    terminalClient.sendFalse()
                    break

                self.saveData(terminalClient.getSensorData())
                terminalClient.sendOKClient()
                self.log(
                    "Client %s data received successfully!" % terminalClient.getImei()
                )

        except:
            logger.exception("Problem handling request")
        finally:
            logger.debug("Closing socket")
            terminalClient.closeConnection()

    def saveData(self, sensorData):
        # @TODO: instead of pickle use json
        self.rcli.rpush(self.channel, pickle.dumps(sensorData))

    def log(self, msg):
        self.logger.info(
            "{logtime}\t{id}\t{msg}".format(
                logtime=self.logTime, id=self.identifier, msg=msg
            )
        )
        pass


def get_config(config_file):
    """
    Read config file by setting first default value and override them later one
    """
    config = configparser.RawConfigParser()
    # redis config section
    config.add_section("redis")
    config.set("redis", "channel", "GPSSensorsData")
    # @TODO: for some reasons this create a bug as the file is not read
    # config.set("redis", "host", "localhost")
    config.set("redis", "host", "redis")
    config.set("redis", "port", "6379")
    config.set("redis", "db", "0")

    # socket server config
    config.add_section("server")
    config.set("server", "port", "1030")
    config.read(config_file)
    return config


if __name__ == "__main__":

    optParser = OptionParser()
    # option command
    optParser.add_option(
        "-c",
        "--config",
        dest="conf_file",
        help="Config file",
        default="../conf/gps.conf",
    )
    (options, args) = optParser.parse_args()

    logger.debug(f"...Application config file: {options.conf_file}")

    config = get_config(options.conf_file)

    logger.info(
        "Gps sensors server. {time}".format(time=strftime("%d %b %H:%M:%S", gmtime()))
    )
    logger.info("Config: {conf_file}".format(conf_file=options.conf_file))

    logger.info(
        "Sensor data db: {redis_host}:{redis_port}/{redis_channel}".format(
            redis_host=config.get("redis", "host"),
            redis_port=config.get("redis", "port"),
            redis_channel=config.get("redis", "channel"),
        )
    )

    logger.info(
        "Server started at port {conf_port}".format(
            conf_port=int(config.get("server", "port"))
        )
    )

    server = Server(
        hostname="0.0.0.0", port=int(config.get("server", "port")), config=config
    )
    try:
        logger.info("...Listening")
        server.start()
    except:
        logger.exception("Unexpected exception")
    finally:
        logger.info("...Shutting down")
        for process in multiprocessing.active_children():
            logger.info("...Shutting down process %r", process)
            process.terminate()
            process.join()

    logger.info("...GPS gateway is running")
