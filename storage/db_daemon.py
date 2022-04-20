import threading

import redis
from db_writer import remoteDB

import pickle

from datetime import datetime
from time import gmtime, strftime

import configparser
from optparse import OptionParser
from loguru import logger


class Listener(threading.Thread):
    def __init__(self, r, channels, config=None, identifier=0):
        threading.Thread.__init__(self)
        self.redis = r
        self.channels = channels
        self.writer = remoteDB(config)
        self.identifier = identifier

    def work(self, serialized_data):
        try:
            sensorsDataArray = pickle.loads(serialized_data)
            if not self.writer.save(sensorsDataArray):
                self.log("save_error_test", self.writer.errors)
                self.writer.errors = []
        except pickle.UnpicklingError as e:
            self.log("unpack_error_test", serialized_data)

    def run(self):
        logger.info(
            "Starting listener {list_id} at channel: {channel}".format(
                list_id=self.identifier, channel=self.channels
            )
        )
        while True:
            item = self.redis.blpop(self.channels, 0)[1]
            if item == "KILL":
                break
            else:
                self.work(item)
        logger.info(
            "{self}, [{id}] unsubscribed and finished".format(
                self=self, id=self.identifier
            )
        )

    def log(self, key, item):
        logger.info(key, item)
        self.redis.hset(key, str(datetime.now()), pickle.dumps(item))


def get_config(config_file):

    config = configparser.RawConfigParser()
    config.add_section("redis")
    config.set("redis", "channel", "GPSSensorsData")
    config.set("redis", "host", "localhost")
    config.set("redis", "port", "6379")
    config.set("redis", "db", "0")

    config.add_section("server")
    config.set("server", "port", "5432")

    config.read(config_file)
    return config


if __name__ == "__main__":

    logger.info(
        "Db sensors data server. {time}".format(
            time=strftime("%d %b %H:%M:%S", gmtime())
        )
    )

    optParser = OptionParser()
    optParser.add_option(
        "-c",
        "--config",
        dest="conf_file",
        help="Config file",
        default="../conf/gps.conf",
    )
    (options, args) = optParser.parse_args()
    config = get_config(options.conf_file)

    r_host = config.get("redis", "host")
    r_port = int(config.get("redis", "port"))
    r_db = int(config.get("redis", "db"))
    r = redis.Redis(host=r_host, port=r_port, db=r_db)

    ps_channel = config.get("redis", "channel")
    db_workers_count = int(config.get("db_daemon", "workers"))
    logger.info(
        "{redis_host}:{redis_post}/{redis_channel}?workers={workers_num}".format(
            redis_host=r_host,
            redis_post=r_port,
            redis_channel=ps_channel,
            workers_num=db_workers_count,
        )
    )

    for i in range(1, db_workers_count + 1):
        client = Listener(r, ps_channel, config=config, identifier=i)
        client.start()
