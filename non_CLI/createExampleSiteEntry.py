#Create an example site entry in CoastCamDB


###### IMPORTS ######
from coastcamDBfuncs import *
import datetime
import mysql.connector
from mysql.connector import errorcode


##### MAIN ######
#connect to db
filepath = "C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv"
csv_parameters = parseCSV(filepath)
host = csv_parameters[0]
port = int(csv_parameters[1])
dbname = csv_parameters[2]
user = csv_parameters[3]
password = csv_parameters[4]
connection = pymysql.connect(host=host, user=user, port=port, passwd=password, db=dbname)

exampleSite = Site('Example Site', 'coastcamdb', connection=connection)

'''
create and populate site 
From DB Toolbox Users Manual p 14:
The site table contains information speci?c to each site. In this usage, 
a site is a geographic location, such as Yaquina Head, which may contain 
one or more stations. This table de?nes the mapping of the local Argus 
coordinate system to the real world, and all stations at that site will 
use the same conversion.
'''
exampleSite.site = Table('site', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.site.id = idColumn(value='7654321', table=exampleSite.site)
exampleSite.site.siteID = Column('siteID', value='exampleSite', table=exampleSite.site)
exampleSite.site.name = Column('name', value='Example Site, USA', table=exampleSite.site)
exampleSite.site.lat = Column('lat', value=10.00, table=exampleSite.site)
exampleSite.site.lon =  Column('lon', value=-10.00, table=exampleSite.site)
exampleSite.site.elev = Column('elev', value=0.0, table=exampleSite.site)
exampleSite.site.zDatumNote = Column('zDatumNote', value='sea level', table=exampleSite.site)
exampleSite.site.TZOffset = Column('TZOffset', value=-240, table=exampleSite.site)
exampleSite.site.tideSource = Column('tideSource', value=9759394, table=exampleSite.site)
exampleSite.site.waveSource = Column('waveSource', value=12345, table=exampleSite.site)
exampleSite.site.degFromN = Column('degFromN', value=255, table=exampleSite.site)
exampleSite.site.TZName = Column('TZName', value='EST', table=exampleSite.site)
exampleSite.site.useLocalNames = Column('useLocalNames', value=0, table=exampleSite.site)
exampleSite.site.sortLocalTime = Column('sortLocalTime', value=0, table=exampleSite.site)
exampleSite.site.UTMEasting = Column('UTMEasting', value=10.00, table=exampleSite.site)
exampleSite.site.UTMNorthing = Column('UTMNorthing', value=10.00, table=exampleSite.site)
exampleSite.site.UTMZone = Column('UTMZone', value='EST', table=exampleSite.site)
exampleSite.site.horizontalDatumNames = Column('horizontalDatumName', value='D WGS 1984', table=exampleSite.site)
exampleSite.site.EllipsoidName = Column('EllipsoidName', value='WGS 1984', table=exampleSite.site)
exampleSite.site.SemimajorAxis = Column('SemimajorAxis', value=149598023, table=exampleSite.site)
exampleSite.site.DenominatorOfFlatteningRatio = Column('DenominatorOfFlatteningRatio', value=12, table=exampleSite.site)
exampleSite.site.GeoID = Column('GeoID', value='exID', table=exampleSite.site)
exampleSite.site.AltitudeDatumName = Column('AltitudeDatumName', value='North American Vertical Datum 1988', table=exampleSite.site)
exampleSite.site.AltitudeDistanceUnits = Column('AltitudeDistanceUnits', value='meters', table=exampleSite.site)
exampleSite.site.ContactOrganization = Column('ContactOrganization', value='USGS', table=exampleSite.site)
exampleSite.site.ContactPerson = Column('ContactPerson', value='John Doe', table=exampleSite.site)
exampleSite.site.ContactEmail = Column('ContactEmail', value='johndoe@usgs.gov', table=exampleSite.site)
exampleSite.site.ContactVoiceTelephone = Column('ContactVoiceTelephone', value='12345678910', table=exampleSite.site)
exampleSite.site.ContactAddress = Column('ContactAddress', value='600 4th St S, Saint Petersburg, FL 33701', table=exampleSite.site)
exampleSite.site.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.site)

'''
create and populate station
From DB Toolbox Users Manual p16:
Each site (geographical location) may have one or more stations associated 
with it. In addition, as stations are updated each version is recorded as a seperate station. 
'''
exampleSite.station = Table('station', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.station.id  =  idColumn(value='7654321', table=exampleSite.station)
exampleSite.station.shortName  = Column('shortName', value='examplexx', table=exampleSite.station)
exampleSite.station.name  =  Column('name', value='example site station', table=exampleSite.station)
exampleSite.station.siteID = fkColumn('siteID', value=exampleSite.site.id.value_list[0], table=exampleSite.station)
exampleSite.station.stationID = Column('stationID', value='EXSTATX', table=exampleSite.station)
exampleSite.station.timeIN = Column('timeIN', value=int(datetime.datetime(2019,8,28,14,0, 0).timestamp()), table=exampleSite.station)
exampleSite.station.timeOUT = Column('timeOUT', value=int(datetime.datetime(2021,8,16,9,18,15).timestamp()), table=exampleSite.station)
exampleSite.station.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.station)

#create and populate cameramodel table
exampleSite.cameramodel = Table('cameramodel', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.cameramodel.id = idColumn(value='XXXXX', table=exampleSite.cameramodel)
exampleSite.cameramodel.make = Column('make', value='FLIR', table=exampleSite.cameramodel)
exampleSite.cameramodel.model = Column('model', value='blackflyS', table=exampleSite.cameramodel)
exampleSite.cameramodel.color = Column('color', value=1, table=exampleSite.cameramodel)
exampleSite.cameramodel.size = Column('size', value=0.25, table=exampleSite.cameramodel)
exampleSite.cameramodel.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.cameramodel)

#create and populate lensmodel table
exampleSite.lensmodel = Table('lensmodel', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.lensmodel.id = idColumn(value='XXXXX', table=exampleSite.lensmodel)
exampleSite.lensmodel.make = Column('make', value='Fujinon', table=exampleSite.lensmodel)
exampleSite.lensmodel.model = Column('model', value='HF9HA-1S', table=exampleSite.lensmodel)
exampleSite.lensmodel.f = Column('f', value=0.0125, table=exampleSite.lensmodel)
exampleSite.lensmodel.aperture = Column('aperture', value=0.0125, table=exampleSite.lensmodel)
exampleSite.lensmodel.autoIris = Column('autoIris', value=1, table=exampleSite.lensmodel)
exampleSite.lensmodel.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.lensmodel)

#create and populate IP table
exampleSite.ip = Table('ip', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.ip.id = idColumn(value='XXXXX', table=exampleSite.ip)
exampleSite.ip.make = Column('make', value='ip make example', table=exampleSite.ip)
exampleSite.ip.model = Column('model', value='ip model example', table=exampleSite.ip)
exampleSite.ip.name = Column('name', value='human readable ip', table=exampleSite.ip)
exampleSite.ip.width = Column('width', value=500, table=exampleSite.ip)
exampleSite.ip.height = Column('height', value=500, table=exampleSite.ip)
exampleSite.ip.pixelWidth = Column('pixelWidth', value=1.0, table=exampleSite.ip)
exampleSite.ip.pixelHeight = Column('pixelHeight', value=1.0, table=exampleSite.ip)
exampleSite.ip.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.ip)

#Create and populate camera table
exampleSite.camera = Table('camera', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.camera.id = idColumn(value='example', table=exampleSite.camera)
exampleSite.camera.stationID = fkColumn('stationID', value=exampleSite.station.id.value_list[0], table=exampleSite.camera)
exampleSite.camera.modelID = fkColumn('modelID', value=exampleSite.cameramodel.id.value_list[0], table=exampleSite.camera)
exampleSite.camera.syncsToID = Column('syncsToID', value='none', table=exampleSite.camera)
exampleSite.camera.lensmodelID = fkColumn('lensmodelID', value=exampleSite.lensmodel.id.value_list[0], table=exampleSite.camera)
exampleSite.camera.li_IP = fkColumn('li_IP', value=exampleSite.ip.id.value_list[0], table=exampleSite.camera)
exampleSite.camera.lensSN = Column('lensSN', value='12345', table=exampleSite.camera)
exampleSite.camera.cameraSN = Column('cameraSN', value='12345', table=exampleSite.camera)
exampleSite.camera.filters = Column('filters', value='fisheye', table=exampleSite.camera)
exampleSite.camera.orientation = Column('orientation', value='n', table=exampleSite.camera)
exampleSite.camera.cameraNumber = Column('cameraNumber', value=1, table=exampleSite.camera);
exampleSite.camera.timeIN = Column('timeIN', value=int(datetime.datetime(2022,6,6,14,0,0).timestamp()), table=exampleSite.camera)
exampleSite.camera.timeOUT = Column('timeOUT', value=int(datetime.datetime(2022,6,7,9,18,15).timestamp()), table=exampleSite.camera)
exampleSite.camera.x = Column('x', value=1.1, table=exampleSite.camera)
exampleSite.camera.y = Column('y', value=2.2, table=exampleSite.camera)
exampleSite.camera.z = Column('z', value=3.3, table=exampleSite.camera)
exampleSite.camera.polarizerFlag = Column('polarizerFlag', value=0, table=exampleSite.camera)
exampleSite.camera.polAngle = Column('polAngle', value=999, table=exampleSite.camera)
exampleSite.camera.K = Column('K', value=np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), table=exampleSite.camera)
exampleSite.camera.kc = Column('kc', value=np.array([1, 2, 3, 4, 5]), table=exampleSite.camera)
exampleSite.camera.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.camera)

#create and populate geometry table
exampleSite.geometry = Table('geometry', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.geometry.cameraID = fkColumn('cameraID', value=exampleSite.camera.id.value_list[0], table=exampleSite.geometry)
exampleSite.geometry.m = Column('m', value=np.array([210.2936, -765.3697, -194.0322, 809.1383, 0.2564, -0.0394, -0.1578, -101.2408, 17.5729, -786.8411, 7.2383e+3]), table=exampleSite.geometry)
exampleSite.geometry.azimuth = Column('azimuth', value=1.0, table=exampleSite.geometry)
exampleSite.geometry.tilt = Column('tilt', value=2.0, table=exampleSite.geometry)
exampleSite.geometry.roll = Column('roll', value=3.0, table=exampleSite.geometry)
exampleSite.geometry.fov = Column('fov', value=10.0, table=exampleSite.geometry)
exampleSite.geometry.imagePath = Column('imagePath', value='/home/images/example.jpg', table=exampleSite.geometry)
exampleSite.geometry.whenDone = Column('whenDone', value=int(datetime.datetime.now().timestamp()), table=exampleSite.geometry)
exampleSite.geometry.whenValid = Column('whenValid', value=int(datetime.datetime.now().timestamp()), table=exampleSite.geometry)
exampleSite.geometry.err = Column('err', value=0.05, table=exampleSite.geometry)
exampleSite.geometry.version = Column('version', value=1.2, table=exampleSite.geometry)
exampleSite.geometry.solvedVars = Column('solvedVars', value='tarfxyz', table=exampleSite.geometry)
exampleSite.geometry.user = Column('user', value='John Doe', table=exampleSite.geometry)
exampleSite.geometry.tiltCI = Column('tiltCI', value=0.5, table=exampleSite.geometry)
exampleSite.geometry.azimuthCI = Column('azimuthCI', value=0.5, table=exampleSite.geometry)
exampleSite.geometry.rollCI = Column('rollCI', value=0.5, table=exampleSite.geometry)
exampleSite.geometry.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.geometry)

#create and populate a single gcp table
exampleSite.gcp = Table('gcp', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.gcp.id = idColumn(value='YXXXY', table=exampleSite.gcp)
exampleSite.gcp.name = Column('name', value='example gcp', table=exampleSite.gcp)
exampleSite.gcp.siteID = fkColumn('siteID', value=exampleSite.site.id.value_list[0], table=exampleSite.gcp)
exampleSite.gcp.x = Column('x', value=1.0, table=exampleSite.gcp)
exampleSite.gcp.y = Column('y', value=2.0, table=exampleSite.gcp)
exampleSite.gcp.z = Column('z', value=3.0, table=exampleSite.gcp)
exampleSite.gcp.timeIN = Column('timeIN', value=int(datetime.datetime.now().timestamp()), table=exampleSite.gcp)
exampleSite.gcp.timeOUT = Column('timeOUT', value=int(datetime.datetime.now().timestamp()), table=exampleSite.gcp)
exampleSite.gcp.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.gcp)

#create and populate a single usedgcp table
exampleSite.usedgcp = Table('usedgcp', 'coastcamdb', site=exampleSite, connection=exampleSite.connection)
exampleSite.usedgcp.gcpID = fkColumn('gcpID', value=exampleSite.gcp.id.value_list[0], table=exampleSite.usedgcp)
exampleSite.usedgcp.geometrySequence = fkColumn('geometrySequence', value=2, table=exampleSite.usedgcp) #seq is created automatically by MySQL
exampleSite.usedgcp.U = Column('U', value=-1.0, table=exampleSite.usedgcp)
exampleSite.usedgcp.V = Column('V', value=-2.0, table=exampleSite.usedgcp)
exampleSite.usedgcp.timestamp = Column('timestamp', value=int(datetime.datetime.now().timestamp()), table=exampleSite.usedgcp)

#####TEST###
if __name__ == "__main__":
    exampleSite.usedgcp.insertTable2db()
