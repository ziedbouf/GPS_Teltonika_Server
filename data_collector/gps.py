import struct
import binascii
import redis
from datetime import datetime
from crc import crc16
import socket

def unpack(fmt, data):
    try:
        return struct.unpack(fmt, data)
    except struct.error:
        flen = struct.calcsize(fmt.replace('*', ''))
        alen = len(data)
        idx = fmt.find('*')
        before_char = fmt[idx-1]
        n = (alen-flen)/struct.calcsize(before_char)+1
        fmt = ''.join((fmt[:idx-1], str(n), before_char, fmt[idx+1:]))
        return struct.unpack(fmt, data)


class GPSTerminal:
    def __init__(self, socket):
        self.socket = socket[0]
        self.ip = socket[1][0]
        self.socket.settimeout(15)
        self.initVariables()

    def initVariables(self):
        self.imei = "unknown"
        self.sensorsDataBlocks = []
        self.error = []
        self.blockCount = 0
        self.success = True
        # Break in data, that was read from socket
        self.dataBreak = 0
        # If we have more than 5 try to read, connection not proceeded
        self.possibleBreakCount = 5

    def startReadData(self):
        try:
            self.proceedConnection()
        except socket.timeout as err:
            self.error.append( "Socket timeout error: %s" % err)
            self.success = False

    def proceedConnection(self):
        if self.isCorrectConnection():
            self.readIMEI()
            if self.imei:
                self.proceedData()
            else:
                self.error.append( "Can't read IMEI" )
        else:
            self.error.append( "Incorrect connection data stream" )
            self.success = False

    def proceedData(self):
        """
        Received and proceed work data of GPS Terminal
        """
        self.time = datetime.now()
        self.data = self.readData()
        if self.data:
            Hexline = binascii.hexlify(self.data)
            self.Hexline = Hexline.decode()
            self.AVL = 0 # AVL ? Looks like data reading cursor
            Zeros = self.extract(8)
            AVLLength = self.extract(8)
            CodecID = self.extract(2)
            BlockCount = self.extract_int(2)
            self.blockCount = BlockCount
            proceed = 0
            AVLBlockPos = 0

            while proceed < self.blockCount:
                try:
                    data = self.proceedBlockData()
                    self.sensorsDataBlocks.append( data )
                except ValueError as e:
                    self.error.append( "Value error: %s" % e)
                    print( "Value error: %s" % e)
                    self.dataBreak += 1
                    # In case data consistency problem, we are re-trying to read data from socket
                    self.reReadData(Hexline)
                    # If we have more than possibleBreakCount problems, stop reading
                    if self.dataBreak > self.possibleBreakCount :
                        # After one year we have 0 problem trackers, and +200k that successfully send data after more than one break
                        self.error.append( "Data break" )
                        self.success = False
                        return
                    else:
                        self.AVL = AVLBlockPos
                        # Re try read data from current block
                        proceed -= 1
                proceed += 1
                AVLBlockPos = self.AVL
        else:
            self.error.append( "No data received" )
            self.success = False

    def readData(self, length = 8192):
        data = self.socket.recv(length)
        return data

    def reReadData(self, Hexline):
        HexlineNew = unpack("s*", self.readData())
        Hexline += binascii.hexlify(HexlineNew[0])
        self.Hexline = Hexline

    def proceedBlockData(self):
        """
        Proceed block data from received data
        """
        DateV = '0x'+ self.extract(16)
        DateS = int(round(int( DateV, 16) /1000, 0))
        Prio = self.extract_int(2)
        GpsLng = self.extract_int(8)
        GpsLat = self.extract_int(8)
        Lng = str(float(GpsLng)/10000000)
        Lat = str(float(GpsLat)/10000000)
        Alt = self.extract_int(4)
        Course = self.extract_int(4)
        Sats = self.extract_int(2)
        Speed = self.extract_int(4)
        IOEventCode = self.extract_int(2)
        NumOfIO = self.extract_int(2)

        sensorDataResult = {}
        pais_count = 0
        for i in [1,2,4,8]:
            pc = 0
            data = self.readSensorDataBytes(i)
            for iocode in data.keys():
                pais_count+=1
                sensorDataResult[iocode] = data[iocode]
                pc += 1
        return {'imei' : self.imei, 'date': DateS, 'lng': Lng, 'lat': Lat, 'alt': Alt, 'course': Course, 'sats': Sats, 'speed': Speed, 'sensorData': sensorDataResult}

    def readSensorDataBytes(self, count):
        result = {}
        pairsCount = self.extract_int(2)
        i = 1
        while i <= pairsCount:
            IOCode = self.extract_int(2)
            IOVal = self.extract_int( count * 2)
            result[IOCode] = IOVal
            i+=1
        return result

    def extract(self, length):
        result = self.Hexline[ self.AVL : (self.AVL + length) ]
        self.AVL += length
        return result

    def extract_int(self, length):
        hex_number = self.extract(length)
        return int(hex_number, 16)

    def readIMEI(self):
        IMEI = self.readData(34)
        self.imei = IMEI.decode()
        self.socket.send(chr(1).encode())

    def isCorrectConnection(self):
        """
        Check data from client terminal for correct first bytes
        """
        hello = self.readData(2)
        return '(15,)' == str(
            struct.unpack("!H", hello )
        )

    def sendOKClient(self):
        """
        Reply for connected client that data correctly received
        """
        self.socket.send(struct.pack("!L", self.blockCount))
        self.closeConnection()

    def sendFalse(self):
        self.socket.send(struct.pack("!L", 0))
        self.closeConnection()

    def closeConnection(self):
        #self.socket.close()
        p = 1

    def getSensorData(self):
        return self.sensorsDataBlocks

    def getIp(self):
        return self.ip

    def getImei(self):
        return self.imei

    def isSuccess(self):
        return self.success
