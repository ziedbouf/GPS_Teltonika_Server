import psycopg2
from psycopg2 import OperationalError, errorcodes, errors
import json

class remoteDB():
    def __init__(self, config):
        self.errors = []
        self.host = config.get('postgresql_db', 'host')
        self.port = config.get('postgresql_db', 'port')
        self.user = config.get('postgresql_db', 'user')
        self.password = config.get('postgresql_db', 'password')
        self.database = config.get('postgresql_db', 'database')
        self.DB = None
        self.connectDB()

    def save(self, sensorsBlocksData):
        count = 0
        for block in sensorsBlocksData:
            if self.saveBlock(block):
                count+=1
        return len(sensorsBlocksData) == count

    def saveBlock(self, sensorData):
        IMEI = sensorData['imei']
        Timestamp = sensorData['date']
        Lng = sensorData['lng']
        Lat = sensorData['lat']
        Alt = sensorData['alt']
        Course = sensorData['course']
        Sats = sensorData['sats']
        Speed = sensorData['speed']
        IOEvents = sensorData['sensorData']
        GpsQuery = "INSERT INTO public.gps_data (imei, timestamp, latitude, longitude, altitude, course, satellites, speed, ioevents) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        GpsParams = (IMEI, Timestamp, Lat, Lng, Alt, Course, Sats, Speed, json.dumps(IOEvents))

        try:
            self.getDB().execute( GpsQuery, GpsParams )
            self.DB.commit()
        except Exception as err:
            self.errors.append('Postgresql error detail: %s' % err)
            return False
        return True

    def getDB(self):
        if not self.DB:
            self.connectDB()
        return  self.DB.cursor()
    def connectDB(self):
        try:
            self.DB = psycopg2.connect(host = self.host, port = self.port, user = self.user, password = self.password, database = self.database)
            self.DB.autocommit = True
        except OperationalError as err:
            self.errors.append('DB Error: %s' % err)
