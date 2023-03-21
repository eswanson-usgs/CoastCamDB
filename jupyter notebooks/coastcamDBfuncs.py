'''
Funcs and classes for connecting to coastcamDB and creating entries.
uses Table class to represent tables in the DB. The attributes in the Table class
are equivalent to the fields in the Db table
'''

##### IMPORTS #####
import pandas as pd
import pymysql
import csv
import datetime
import os
import sys
import ast
import random
import numpy as np
import pytz
import mysql.connector
from mysql.connector import errorcode
from tabulate import tabulate
import mysql.connector
from mysql.connector import errorcode
from tabulate import tabulate
import dateutil
from dateutil import tz


##### FUNCTIONS #####
def parseCSV(filepath):
    '''
    Read and parse a CSV to obtain list of parameters used to access database.
    The csv file should have the column headers "host", "port", "dbname", "user",
    and "password" with one row of data containing the user's values
    Inputs:
        filepath (string) - filepath of the csv
    Outputs:
        dbList (list) - list of paramters used to access database
    '''
    
    dbList = []

    with  open(filepath, 'r') as csvFile:
        csvreader = csv.reader(csvFile)

        #extract data from csv. Have to use i to track row because iterator object csvreader is not subscriptable
        i = 0
        for row in csvreader:
            #i = 0 is column headers. i = 1 is data 
            if i == 1:
                dbList = row
            i = i + 1
                
    return dbList


def parseFilename(path, noLocal=False, timezone='utc'):
    '''
    Parse an Argus-formatted file into component parts. throw away any leading path info.
    e.g, '887065208.Mon.Feb.09_23:00:08.GMT.1998.argus00.c1.snap.jpg'
    is parsed into:
    time    887065208
    when    Mon.Feb.09_23:00:08.GMT.1998
    station argus00
    camera  1
    type    snap
    format  jpg
    localwhen 'Mon.Feb.09_15_00_08.PST.1998'
    Inputs:
        path (string) - filename in Argus format. can be filepath.
        noLocal (boolean) - Flag for determining whether to include localwhen in the
                            outputted in dictionary. Default False. If true, localwhen
                            not outputted.
        timezone (string) - string specifying the user's local time zone
    Outputs:
        components (dict) - dictionary of component parts of the filename
    '''

    path = path.replace('\\', '/')
    pathElements = path.split('/')
    filename = pathElements[-1]
    filenameElements = filename.split('.')

    components = {}

    try:
        if len(filenameElements) != 10:
            raise Exception

        components['time'] = filenameElements[0]
        
        #combine the date elements
        when = filenameElements[1] + '.' +  filenameElements[2] + '.' + filenameElements[3] + '.' + filenameElements[4] + '.' + filenameElements[5]
        components['when'] = when

        components['station'] = filenameElements[6]
        components['camera'] = filenameElements[7]
        components['type'] = filenameElements[8]
        components['format'] = filenameElements[9]

        if noLocal == False:       
            #convert from UTC to local
            datetimeStr, datetimeObj, tzone = unix2dt(filenameElements[0], timezone=timezone)
            #formatted argus date with local timezone
            localwhen = datetimeObj.strftime('%a.%b.%d_%H_%M_%S.%Z.%Y')
            components['localwhen'] = localwhen

        return components
        
    except:
        print('Error: invalid filename. Filename must follow the Argus format')
        return
    


def DBConnectCSV(filepath):
    '''
    Connect to the DB using parameters stored in a CSV. If the user doesn't want to use a csv
    they can use the pymysql.connect() function directly.
    Inputs:
        filepath (string) - filepath of the csv
    Outputs:
        connection (pymysql.connections.Connection object) - Object representing connection to DB
    '''

    csvParameters = parseCSV(filepath)
    host = csvParameters[0]
    port = int(csvParameters[1])
    dbname = csvParameters[2]
    user = csvParameters[3]
    password = csvParameters[4]

    connection = pymysql.connect(host=host, user=user, port=port, passwd=password, db=dbname)
    return connection


def np2text(array):
    '''
    Serialize a numpy array into a text blob and return the text. Makes it so that the array can be inserted into the database.
    ---assume to onlyt be working with 1D or 2D arrays---
    Inputs:
        array (numpy ndarray) - array to be inserted into the DB
    Outputs:
        blob (string) - array converted into formatted text
    '''

    blob = np.array2string(array, precision=4)
    blob = blob.replace('\n', ',')

    return blob
        

def db2np(connection, table, column, ID='', seq=0):
    '''
    Fetch an array from a TEXT field in the CoastCamDB and return it as a numpy array.
    ---assume to onlyt be working with 1D or 2D arrays---
    Inputs:
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
        table (string) - table the function will pull from
        column (string) - column the function will pull the TEXT array from
        ID (string) - associated ID (row #) for the data field where the array lives
        seq (int) - optional variable used if user wants pull data from an existing row. seq only used for
                    geometry and usedgcp tables.
    Outputs:
        array (ndarray) - numpy array pulled from the database
    '''
    
    #grab the data from the text field
    if (ID != ''):

        checkID(ID, table, connection)
        query = "SELECT {} FROM {} WHERE id = '{}'".format(column, table, ID)

    elif (seq != 0):

        checkSeq(seq, table, connection)
        query = "SELECT {} FROM {} WHERE seq = {}".format(column, table, seq)

    else:

        raise NoIDError("NoIDError: No id or seq value given to specify what row to insert data into column {} in table '{}'".format(column, table))
    #print(query)

    result = pd.read_sql(query, con=connection)
    result = result.get(column)[0]


    #Number of dimnesions of array equal the number of ']' brackets at the end of the array.
    #Split the text on '[' bracket and check the last element of the resulting list for ']'
    dimCount = 0
    split = result.split('[')
    dimCount = split[-1].count(']')

    if dimCount == 1:
        #format for np.fromstring()
        array = result.replace('[', '')
        array = array.replace(']', '')
        array = np.fromstring(array, dtype=float, sep=' ')

    elif dimCount == 2:        
        #remove outside brackets from 2D array to make it easier to grab the rows
        result = result[1 : -1]
        rows = result.split(',')

        array = []
        for row in rows:
            #Format string to use np.fromstring()
            row = row.lstrip()
            row = row.replace('[', '')
            row = row.replace(']', '')
            row = np.fromstring(row, dtype=float, sep=' ')
            array.append(row)

        #stack list of 1D arrays into single 2D array
        array = np.stack(array, axis=0)

    return array


def idSeqMatch(ID, seq, table, connection):
    '''
    Checks if the supplied id and seq match in the approporiate table in the database--a 'match' being that they belong
    to the same row. Return True if match, False if not.
    Inputs:
        ID (string) - id to check in the database table
        seq (int) - seq to check in the database table
        table (string) - name of the database table
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        True/False - true if there is a match. False if not
    '''

    query = "SELECT id FROM {} WHERE seq = {}".format(table, seq)
            #ex: SELECT id FROM site WHERE seq = 1
    try:

        result = pd.read_sql(query, con=connection)
        result = result.get('id')[0]

        if result != ID:
            raise MismatchIDError("MismatchIDError: given 'id' and 'seq' values in table '{}' are not in the same row".format(table)) 

    except Exception as e:
        sys.exit(e.message)
        

def checkID(ID, table, connection):
    '''
    Check if the given id value exists in the table. 
    Inputs:
        ID (string) - id value to check
        table (string) - database table that that the id column exists in
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        e (Exception) - return Exception if try/except hits exception
    '''

    query = "SELECT id FROM {} WHERE id = '{}'".format(table, ID)
            #ex: SELECT id FROM site WHERE id = 'EXXXXXX'
    try:
        
        result = pd.read_sql(query, con=connection)
        
        #NULL return, no id found
        if result.size == 0:
            raise NoMatchIDError("NoMatchIDError: No 'id' {} found in table '{}'".format(ID, table))
        
    except Exception as e:
        #sys.exit(e.message)
        return e


def checkSeq(seq, table, connection):
    '''
    Check if the given seq value exists in the table. 
    Inputs:
        seq (int) - seq value to check
        table (string) - database table that that the id column exists in
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        none
    '''

    query = "SELECT seq FROM {} WHERE seq = {}".format(table, seq)
            #ex: SELECT seq FROM site WHERE seq = '1'
    try:
        
        result = pd.read_sql(query, con=connection)
        
        #NULL return, no seq found
        if result.size == 0:
            raise NoSeqError("NoSeqError: No 'seq' {} found in table '{}'".format(seq, table))
        
    except Exception as e:
        sys.exit(e.message)


def checkLinkedKey(value, column, linkedTable, connection):
    '''
    Check that the value actually exists in the id/seq column of the linked table
    Inputs:
        value (string or int) - seq/id value to be checked
        column (string) - name of the fk column
        linkedTable (string) - table that the fk links to
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        e (Exception) - return execpetion if exception is raised
    '''

    if column == 'geometrySequence':

        query = "SELECT seq FROM geometry WHERE seq = {}".format(value)

        print(query)
        
        try:
            
            result = pd.read_sql(query, con=connection)
            
            #NULL return, no seq found
            if result.size == 0:
                raise NoSeqError("NoSeqError: No 'seq' {} found in table '{}'".format(value, 'geometry'))
        
        except Exception as e:
            return e
            
    else:

        query = "SELECT id FROM {} WHERE id = '{}'".format(linkedTable, value)

        print(query)

        try:
            
            result = pd.read_sql(query, con=connection)
            
            #NULL return, no id found
            if result.size == 0:
                raise NoIDError("NoSeqError: No 'id' {} found in table '{}'".format(value, linkedTable))
        
        except Exception as e:
            return e


def yaml2dict(yamlfile):
    """ Import contents of a YAML file as a dict
    Args:
        yamlfile (str): YAML file to read
    Returns:
        dict interpreted from YAML file
    """
    dictname = None
    with open(yamlfile, "r") as infile:
        try:
            dictname = yaml.safe_load(infile)
        except yaml.YAMLerror as exc:
            print(exc)
    return dictname

def getFormattedResult(query, connection):
    '''
    given a SQL query, return the result formatted without numbered indices.
    Inputs:
        query (string) - SQL query
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        result (pandas Dataframe) - resulting dataframe returned from the SQl query
    '''

    result = pd.read_sql(query, con=connection)
    blankIndex = [''] * len(result)
    result.index = blankIndex
    return result
        

def displaySite(siteID, connection):
    '''
    Display all the columns for a site given a site id. Use the site id to get 'cascading' foreign keys for every table below
    'site' in the coastcamdb hierarchy.Returns a list of tuples where the first element of the tuple is the table name and the
    second element is the table dataframe.
    Inputs:
        siteID (string) - id for site in the 'site' table
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
        dfList (list) - list of tuples where the first element of the tuple is the table name and the
                         second element is the table dataframe.
    outputs:
        dfList (list) - list of Pandas dataframe obuects, one for each table corresponding to the site.
    '''

    pd.set_option('display.width' ,160)
    pd.set_option('display.max_columns', 40)

    dfList = []

    #site
    query = "SELECT * FROM site WHERE id = '{}'".format(siteID)
    result = getFormattedResult(query, connection)
    print('---SITE---')
    print(result)

    #don't add empty tables to the dataframe list
    if not result.empty:
        dfTuple = ('site', result)
        dfList.append(dfTuple)

    #station
    query = "SELECT * FROM station WHERE siteID = '{}'".format(siteID)
    result = getFormattedResult(query, connection)
    stationID = result.get('id')
    try:
        if result.empty:
            raise Exception
        print('\n---STATION---')
        print(result)

        if not result.empty:
            dfTuple = ('station', result)
            dfList.append(dfTuple)
    except:
        pass

    #camera
    cameraResult = []
    try:
        for ID in stationID:
            query = "SELECT * FROM camera WHERE stationID = '{}'".format(ID)
            cameraResult.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(stationID) > 1:
            result = pd.concat(cameraResult, axis=0)
        else:
            result = cameraResult[0]
        cameraID = result.get('id')
        modelID = result.get('modelID')
        lensmodelID = result.get('lensmodelID')
        li_IP = result.get('li_IP')
        blankIndex = [''] * len(result)
        result.index = blankIndex
        print('\n---CAMERA---')
        print(result)

        if not result.empty:
            dfTuple = ('camera', result)
            dfList.append(dfTuple)
    except:
        pass

    #cameramodel
    cameramodelResult = []
    try:
        for ID in modelID:
            query = "SELECT * FROM cameramodel WHERE id = '{}'".format(ID)
            cameramodelResult.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(modelID) > 1:
            result = pd.concat(cameramodelResult, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = cameramodelResult[0]
        print('\n---CAMERAMODEL---')
        print(result)

        if not result.empty:
            dfTuple = ('cameramodel', result)
            dfList.append(dfTuple)
    except:
        pass

    #lensmodel
    lensmodelResult = []
    try:
        for ID in lensmodelID:
            query = "SELECT * FROM lensmodel WHERE id = '{}'".format(ID)
            lensmodelResult.append(pd.read_sql(query, con=connection))
        if len(lensmodelID) > 1:
            result = pd.concat(lensmodelResult, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = lensmodelResult[0]
        print('\n---LENSMODEL---')
        print(result)

        if not result.empty:
            dfTuple = ('lensmodel', result)
            dfList.append(dfTuple)
    except:
        pass

    #ip
    li_IPResult = []
    try:
        for ID in li_IP:
            query = "SELECT * FROM ip WHERE id = '{}'".format(ID)
            li_IPResult.append(pd.read_sql(query, con=connection))
        if len(li_IP) > 1:
            result = pd.concat(li_IPResult, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = li_IPResult[0]
        print('\n---IP---')
        print(result)

        if not result.empty:
            dfTuple = ('ip', result)
            dfList.append(dfTuple)
    except:
        pass
    
    #gcp
    query = "SELECT * FROM gcp WHERE siteID = '{}'".format(siteID)
    result = getFormattedResult(query, connection)
    gcpID = result.get('id')
    try:
        if result.empty:
            raise Exception
        print('\n---GCP---')
        print(result)

        if not result.empty:
            dfTuple = ('gcp', result)
            dfList.append(dfTuple)
    except:
        pass

    #geometry
    geometryResult = []
    try:
        for ID in cameraID:
            query = "SELECT * FROM geometry WHERE cameraID = '{}'".format(ID)
            geometryResult.append(pd.read_sql(query, con=connection))
        if len(cameraID) > 1:
            result = pd.concat(geometryResult, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = geometryResult[0]
        geometrySequence = result.get('seq')
        print('\n---GEOMETRY---')
        print(result)

        if not result.empty:
            dfTuple = ('geometry', result)
            dfList.append(dfTuple)
    except:
        pass

    #usedgcp
    try:
        usedgcpResult = []
        for ID in gcpID:
            for seq in geometrySequence:
                query = "SELECT * FROM usedgcp WHERE gcpID = '{}' AND geometrySequence = {}".format(ID, seq)
                usedgcpResult.append(pd.read_sql(query, con=connection))
        if (len(gcpID) > 1) or (len(geometrySequence) > 1):
            result = pd.concat(usedgcpResult, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = usedgcpResult[0]
        print('\n---USEDGCP---')
        print(result)

        if not result.empty:
            dfTuple = ('usedgcp', result)
            dfList.append(dfTuple)
    except:
        pass

    return dfList

def getParameterDicts(stationID, connection, useUnix=False, unixTime=None):
    '''
    Given a stationID, return parameter dictionaries for extrinsics, intrinsics, metadata, and local origin.
    Extrinsics, intrinsics, and metadata will be stored as lists, where each item in the list is a dictionary of
    parameters. There will be one dictionary for each camera at the station.
    Inputs:
        stationID (string) - specifies the "id" field for the "station" table, which is also the "stationID" field in the
                             "camera" table
        connection (pymysql.connections.Connection object) - Object representing connection to DB
        useUnix (boolean) - flag for specifying if a unix time should be used to narrow the data the user is looking for
        unixTime (int) - timestamp of the filename needed for searching relevant data
        
    Outputs:
        extrinsics (list) - list of extrinsic paramater dictionaries. One dictionary for each camera.
        intrinsics (list) - list of intrinsic parameter dictionaries. One dictionary for each camera.
        metadata (list) - list of metadata parameter dictionaries. One dictionary for each camera.
        localOrigin (dictionary) - dictionary of local origin parameters
    '''

    #accounting for unix time
    if useUnix == True:
        if unixTime != None:
            query = "SELECT * FROM camera WHERE stationID = '{}' AND timeIN <= {} AND timeOUT >= {} ".format(stationID, unixTime, unixTime)
        else:
            query = "SELECT * FROM camera WHERE stationID = '{}'".format(stationID)
    else:
        query = "SELECT * FROM camera WHERE stationID = '{}'".format(stationID)

    print(query)

    result = pd.read_sql(query, con=connection)
    cameraList = []
    for ID in result.get('id'):
        cameraList.append(ID)

    #lists of dictionaries. One dictionary in every list for each camera.
    metadataDictList = []
    extrinsicDictList = []
    intrinsicDictList = []

    #need to query station table before going through camera list
    query = "SELECT siteID, name FROM station WHERE id = '{}'".format(stationID)
    result = pd.read_sql(query, con=connection)
    #siteID for querying site table 
    siteID = result.get('siteID')[0]
    #name for metadata dict
    name = result.get('name')[0]

    if len(cameraList) != 0:

        for i in range(0, len(cameraList)):

            ###GET METADATA###
            #yaml_metadataDict is dict of YAML field names and corresponding values
            metadataDict = {}

            metadataDict['name'] = name

            query = "SELECT cameraSN, cameraNumber,timeIN, li_IP FROM camera WHERE id = '{}'".format(cameraList[i])
            result = pd.read_sql(query, con=connection)
            metadataDict['serial_number'] = result.get('cameraSN')[0]
            metadataDict['camera_number'] = result.get('cameraNumber')[0]
            metadataDict['calibration_date'] = result.get('timeIN')[0]

            #key for accessing IP table
            IP = result.get('li_IP')[0]

            metadataDict['coordinate_system'] = 'geo'

            metadataDictList.append(metadataDict)
            

            ###GET INTRINSICS###
            intrinsicDict = {}

            query = "SELECT width, height FROM ip WHERE id = '{}'".format(IP)
            result = pd.read_sql(query, con=connection)
            intrinsicDict['NU'] = result.get('width')[0]
            intrinsicDict['NV'] = result.get('height')[0]

            #get matrices for rest of intrinsics
            K = db2np(connection, 'camera' , 'K', ID=cameraList[i])
            kc = db2np(connection, 'camera', 'kc', ID=cameraList[i])
            intrinsicDict['fx'] = K[0][0]
            intrinsicDict['fy'] = K[1][1]
            intrinsicDict['c0U'] = K[0][2]
            intrinsicDict['c0V'] = K[1][2]
            intrinsicDict['d1'] = kc[0]
            intrinsicDict['d2'] = kc[1]
            intrinsicDict['d3'] = kc[2]
            intrinsicDict['t1'] = kc[3]
            intrinsicDict['t2'] = kc[4]

            intrinsicDictList.append(intrinsicDict)
            

            ###GET EXTRINSICS###
            extrinsicDict = {}

            query = "SELECT x, y, z FROM camera WHERE id = '{}'".format(cameraList[i])
            result = pd.read_sql(query, con=connection)
            extrinsicDict['x'] = result.get('x')[0]
            extrinsicDict['y'] = result.get('y')[0]
            extrinsicDict['z'] = result.get('z')[0]

            query = "SELECT azimuth, tilt, roll FROM geometry WHERE cameraID = '{}'".format(cameraList[i])
            result = pd.read_sql(query, con=connection)
            extrinsicDict['a'] = result.get('azimuth')[0]
            extrinsicDict['t'] = result.get('tilt')[0]
            extrinsicDict['r'] = result.get('roll')[0]

            extrinsicDictList.append(extrinsicDict)
            

        ###GET LOCAL ORIGIN DICT###
        localOrigin_dict = {}
        query = "SELECT UTMEasting, UTMNorthing, degFromN FROM site WHERE id = '{}'".format(siteID)
        result = pd.read_sql(query, con=connection)
        localOrigin_dict['x'] = result.get('UTMEasting')[0]
        localOrigin_dict['y'] = result.get('UTMNorthing')[0]
        localOrigin_dict['angd'] = result.get('degFromN')[0]

        extrinsics = extrinsicDictList
        intrinsics = intrinsicDictList
        metadata = metadataDictList
        localOrigin = localOrigin_dict

        return extrinsics, intrinsics, metadata, localOrigin



def unix2dt(unixnumber, timezone='utc'):
    """
    Get local time from unix number
    Input:
        unixnumber (string) - string containing unix time (aka epoch)
    Outputs:
        dateTimeString (string) - datetime string in the local user's timezone 
        dateTimeObject (datetime) - datetime object in the local user's timezone
        tzone (dateutil.tz) - dateutil timezone object
    """
    
    if timezone.lower() == 'eastern':
        tzone = tz.gettz('America/New_York')
    elif timezone.lower() == 'pacific':
        tzone = tz.gettz('America/Los_Angeles')
    elif timezone.lower() == 'utc':
        tzone = tz.gettz('UTC')
        
    # replace last digit with zero
    ts = int( unixnumber[:-1]+'0')
    dateTimeObj =  datetime.datetime.utcfromtimestamp(ts)
    #convert from UTC to local time zone on user's machine
    dateTimeObj = dateTimeObj.replace(tzinfo=datetime.timezone.utc).astimezone(tz=tzone)
    dateTimeStr = dateTimeObj.strftime('%Y-%m-%d %H:%M:%S')
    return dateTimeStr, dateTimeObj, tzone

    
def filename2param(filename, connection, timezone='utc'):
    '''
    Given the filename of a CoastCam image (with the short name of the station in the filename), create a Python object
    that stores important rectification parameters: extrinsics, intrinsics, metadata, local origin. Extrinsics, intrinsics, and
    metadata will be stored as lists, where each item in the list is a dictionary of parameters. There will be one dictionary for
    each camera at the station. Is the unix time in the filename to search the database for data that corresponds to this time--this
    will use timeIN and timeOUT fields.
    This function will also create a datetime object in the user's local timezone (they must specify in the function arguments).
    This datetime object will be assigned as an attribute of the Parameter object
    Inputs:
        filename(string) - image filename
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
        timezone (string) - user's local timezone. Used when returning the datetime object
    Outputs:
        params (Paramater object) - Python object storing the parameters associated with the station
        return None if the filename doesn't match any existing station short names
    '''

    filenameElements = filename.split('.')
    unixTime = int(filenameElements[0])
    query = "SELECT shortName FROM station"
    result = pd.read_sql(query, con=connection)
    shortName = result.get('shortName')

    try:
        #check to see if any of the station shortnames exist in the given filename
        for i, name in enumerate(shortName):

            if str(name) in filename:

                print("Short name '{}' found in filename {}".format(name, filename))

                query = "SELECT id FROM station WHERE shortName = '{}'".format(name)
                result = pd.read_sql(query, con=connection)
                stationID = result.get('id')[0]

                filename_el = filename.split('.')
                unixTime = filename_el[0]

                dateTimeStr, dateTimeObj, tzone = unix2dt(unixTime, timezone=timezone)

                extrinsics, intrinsics, metadata, localOrigin = getParameterDicts(stationID, connection, useUnix=True, unixTime=unixTime)

                params = Parameter(extrinsics=extrinsics, intrinsics=intrinsics, metadata=metadata, localOrigin=localOrigin, dateTimeObj=dateTimeObj, dateTimeStr=dateTimeStr, tzone=tzone)
                return params

            else:
                #whole list has been checked
                if i == len(shortName) - 1:
                    print('no existing station short names match the given filename')
                    return None
    except:
        print("unable to get parameters")
        return None


def checkDuplicateId(table, ID, connection):
    '''
    check if id already exists in the table
    Inputs:
        table (string) - table to be checked
        ID (string) - ID to be checked
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        isDuplicate (boolean) - true/false variable stating whether or not the id is a duplicate
    '''

    query = "SELECT * FROM {} WHERE id = '{}'".format(table, ID)

    result = pd.read_sql(query, con=connection)

    if result.size == 0:
        isDuplicate = False
    else:
        isDuplicate = True

    return isDuplicate


def column2csv(column, table, csvPath, connection):
    '''
    Store a data read from a column in the database into a csv file. There will be a single file for the column.
    Inputs:
        column (string) - column name
        csvPath (string) - optional input specified by the user for where they'd like to store csvs of the data read from
                                 the database.
        table (string) - input needed when writing  to csv because nott every column name in the database is unique.
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        result (Pandas dataframe) - resultant dataframe containing column data
    '''

    query = "SELECT {} FROM {}".format(column, table)
    result = getFormattedResult(query, connection)

    filename = table + '_' + column + '.csv'
    folderPath = csvPath + 'columns/'

    #if folders for saving csv does not exist, create directory
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)
        
    fullPath = folderPath + filename
    result.to_csv(fullPath, encoding='utf-8', index=False)

    print("Saved csv file to", fullPath)
    
    return result


def table2csv(table, csvPath, connection):
    '''
    Store a data read from a table in the database into a csv file. There will be a single file for the table.
    Inputs:
        csvPath (string) - optional input specified by the user for where they'd like to store csvs of the data read from
                                 the database.
        table (string) - table name
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        result (Pandas dataframe) - resultant dataframe containing column data
    '''

    query = "SELECT * FROM {}".format(table)
    result = getFormattedResult(query, connection)

    filename = table + '.csv'
    folderPath = csvPath + 'tables/'

    #if folders for saving csv does not exist, create directory
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)
        
    fullPath = folderPath + filename
    result.to_csv(fullPath, encoding='utf-8', index=False)

    print("Saved csv file to", fullPath)
    
    return result


def site2csv(siteID, csvPath, connection):
    '''
    Store a data read from a site in the database into a csv file using a specific siteID. There will be a folder for the site
    where there's one csv file per table.
    Inputs:
        csvPath (string) - optional input specified by the user for where they'd like to store csvs of the data read from
                                 the database.
        table (string) - table name
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        outputList (list) - list of Pandas datframes, one for each non-empty table associated with the given siteID
    '''

    dfList = []

    #site
    query = "SELECT * FROM site WHERE id = '{}'".format(siteID)
    result = getFormattedResult(query, connection)

    #don't add empty tables to the dataframe list
    if not result.empty:
        dfTuple = ('site', result)
        dfList.append(dfTuple)

    #station
    query = "SELECT * FROM station WHERE siteID = '{}'".format(siteID)
    result = getFormattedResult(query, connection)
    stationID = result.get('id')
    try:
        if result.empty:
            raise Exception

        dfTuple = ('station', result)
        dfList.append(dfTuple)
    except:
        pass

    #camera
    cameraResult = []
    try:
        for ID in stationID:
            query = "SELECT * FROM camera WHERE stationID = '{}'".format(ID)
            cameraResult.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(stationID) > 1:
            result = pd.concat(cameraResult, axis=0)
        else:
            result = cameraResult[0]
        cameraID = result.get('id')
        modelID = result.get('modelID')
        lensmodelID = result.get('lensmodelID')
        li_IP = result.get('li_IP')
        blankIndex = [''] * len(result)
        result.index = blankIndex

        if not result.empty:
            dfTuple = ('camera', result)
            dfList.append(dfTuple)
    except:
        pass

    #cameramodel
    cameramodelResult = []
    try:
        for ID in modelID:
            query = "SELECT * FROM cameramodel WHERE id = '{}'".format(ID)
            cameramodelResult.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(modelID) > 1:
            result = pd.concat(cameramodelResult, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = cameramodelResult[0]

        if not result.empty:
            dfTuple = ('cameramodel', result)
            dfList.append(dfTuple)
    except:
        pass

    #lensmodel
    lensmodelResult = []
    try:
        for ID in lensmodelID:
            query = "SELECT * FROM lensmodel WHERE id = '{}'".format(ID)
            lensmodelResult.append(pd.read_sql(query, con=connection))
        if len(lensmodelID) > 1:
            result = pd.concat(lensmodelResult, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = lensmodelResult[0]

        if not result.empty:
            dfTuple = ('lensmodel', result)
            dfList.append(dfTuple)
    except:
        pass

    #ip
    li_IPResult = []
    try:
        for ID in li_IP:
            query = "SELECT * FROM ip WHERE id = '{}'".format(ID)
            li_IPResult.append(pd.read_sql(query, con=connection))
        if len(li_IP) > 1:
            result = pd.concat(li_IPResult, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = li_IPResult[0]

        if not result.empty:
            dfTuple = ('ip', result)
            dfList.append(dfTuple)
    except:
        pass
    
    #gcp
    query = "SELECT * FROM gcp WHERE siteID = '{}'".format(siteID)
    result = getFormattedResult(query, connection)
    gcpID = result.get('id')
    try:
        if result.empty:
            raise Exception

        if not result.empty:
            dfTuple = ('gcp', result)
            dfList.append(dfTuple)
    except:
        pass

    #geometry
    geometryResult = []
    try:
        for ID in cameraID:
            query = "SELECT * FROM geometry WHERE cameraID = '{}'".format(ID)
            geometryResult.append(pd.read_sql(query, con=connection))
        if len(cameraID) > 1:
            result = pd.concat(geometryResult, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = geometryResult[0]
        geometrySequence = result.get('seq')

        if not result.empty:
            dfTuple = ('geometry', result)
            dfList.append(dfTuple)
    except:
        pass

    #usedgcp
    try:
        usedgcpResult = []
        for ID in gcpID:
            for seq in geometrySequence:
                query = "SELECT * FROM usedgcp WHERE gcpID = '{}' AND geometrySequence = {}".format(ID, seq)
                usedgcpResult.append(pd.read_sql(query, con=connection))
        if (len(gcpID) > 1) or (len(geometrySequence) > 1):
            result = pd.concat(usedgcpResult, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = usedgcpResult[0]

        if not result.empty:
            dfTuple = ('usedgcp', result)
            dfList.append(dfTuple)
    except:
        pass

    #list of dataframes to output
    outputList = []

    #add tables to csv files
    for dfTuple in dfList:
        table = dfTuple[0]
        df = dfTuple[1]

        outputList.append(df)

        filename = table + '.csv'
        folderPath = csvPath + '/sites/' + siteID + '/tables/'

        #if folders for saving csv does not exist, create directory
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
            
        fullPath = folderPath + filename
        df.to_csv(fullPath, encoding='utf-8', index=False)

    print("Saved csv files to", folderPath)

    return outputList


def csv2db(csvPath, connection):
    '''
    Use a csv file to add data to a table in a database. The csv will be taken froma  template where there is 1 row for the column
    headers and 1 row of data. id field must not be blank (if applicable) and Foreign key values must be included (if applicable).
    Filename must be [table name].csv
    Inputs:
        csvPath (string) - filepath to the csv file
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        none
    '''

    with open(csvPath, 'r') as csvFile:
        csvreader = csv.reader(csvFile)

        for i, row in enumerate(csvreader):
            #get rid of weird formatting from UTF-8 encoding
            row[0] = row[0].replace('ï»¿', '')

            if i == 0:
                columnNames = row
            elif i == 1:
                columnValues = row

    #get rid of more weird formatting from UTF-8 encoding            
    columnNames[0] = columnNames[0].replace('\ufeff', '')  

    validTables = ['site', 'station', 'gcp', 'camera', 'cameramodel', 'lensmodel' , 'ip', 'geometry', 'usedgcp']
    fkColumnList = ['siteID', 'stationID', 'modelID', 'lensmodelID', 'li_IP', 'cameraID', 'siteID', 'gcpID', 'geometrySequence']

    pathElements = csvPath.split('/')
    filename = pathElements[-1]
    filenameElements = filename.split('.')

    try:
        tableName = filenameElements[0]
        if tableName not in validTables:
            raise Exception
    except:
        print('Not a valid table name in the filename')
        return

    table = Table(tableName, 'coastcamdb', connection)
    for i, column in enumerate(columnNames):

        if column in fkColumnList:
            table.__dict__[column] = fkColumn(columnName=column, table=table, value=columnValues[i])

        elif column == 'id':
            table.__dict__[column] = idColumn(table=table, value=columnValues[i])

        else:
            table.__dict__[column] = Column(columnName=column, table=table, value=columnValues[i])

    table.insertTable2db()


            
      
         
##### CLASSES #####
class MismatchIDError(Exception):
    '''exception for id and seq mismatch'''
    def __init__(self, message="mismatch between 'id' and 'seq' in database table"):
        self.message = message
        

class NoMatchIDError(Exception):
    '''exception for if id is not found in a table'''
    def __init__(self, message="no matching value for 'id' found in the database table"):
        self.message = message
        

class NoSeqError(Exception):
    '''exception for if seq is not found in a table'''
    def __init__(self, message="no matching value for 'seq' found in the database table"):
        self.message = message
        

class ListLengthError(Exception):
    '''exception if the number of given id/seq values to insert into table isn't the same as the number of values to insert'''
    def __init__(self, message="number of given id/seq values is not the same as the number of values to be inserted"):
        self.message = message

class NoIDError(Exception):
    '''exception if no id or seq is given when inserting into the DB'''
    def __init__(self, message="no id or seq value given to specify row to insert into"):
        self.message = message

class FKError(Exception):
    '''exception raised if a function requires foreign key args but no foreign keys were given'''
    def __init__(self, message="foreign keys required but no foreign keys passed as arguments"):
        self.message = message

class EmptyValueError(Exception):
    '''exception raised if user tries to add values to database and the value list for a column is empty'''
    def __init__(self, message="value list for column is empty"):
        self.message = message
        
        
class Site:
    '''
    This class represents a CoastCam site. This object's attributes will store Table objects.
    table_dict attribute holds the names of all the tables associated with this site.
    '''

    def __init__(self, name, database, connection):
        '''
        Initialization function for this object.
        Inputs:
            name (string) - name of the site
            database (string) - name of the database this site is associated with
            connection (pymysql.connections.Connection object) - object representing the connection to the DB
        outputs:
            (none)
        '''
        
        self.name = name
        self.database = database
        self.connection = connection

    def showTables(self):
        '''
        Print all the tables and their fields connected to this site
        Inputs:
            (none)
        Outputs:
            (none)
        '''

        print('SITE:', self.name, '\n------------------------------------------')
        for table in self.__dict__:
            #don't print unless it's a Table object
            if isinstance(self.__dict__[table], Table):
                print('\n')
                self.__dict__[table].showFields()

    def addSite2db(self):
        '''
        Add this site and all it's associated tables to a DB
        Inputs:
            connection (pymysql.connections.Connection object) - object representing the connection to the DB
        Outputs:
            (none)
        '''

        #tables need to be added in specific order. Populate list accordingly
        tableList = [None] * 9 
        for table in self.__dict__:
            if isinstance(self.__dict__[table], Table):

                if self.__dict__[table].tableName == 'site':
                    tableList[0] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'cameramodel':
                    tableList[1] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'lensmodel':
                    tableList[2] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'ip':
                    tableList[3] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'station':
                    tableList[4] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'gcp':
                    tableList[5] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'camera':
                    tableList[6] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'geometry':
                    tableList[7] = self.__dict__[table]

                elif self.__dict__[table].tableName == 'usedgcp':
                    tableList[8] = self.__dict__[table]

        for table in tableList:
            table.addTable2db()

    
class Table:
    '''
    This class represents a table in the CoastCamDB. The attributes of this class represent the columns in the table.
    This Table object can be added to a Site object as an attribute
    '''

    def __init__(self, tableName, database, connection, site=None):
        '''
        Initialization function for this object.
        Inputs:
            field_name (string) - name of the Table
            database (string) - name of the database this Table is in
            connection (pymysql.connections.Connection object) - object representing the connection to the DB
            site (Site object) - site that this object corresponds to.
        Outputs:
            (none)
        '''

        self.tableName = tableName
        self.database = database
        self.site = site
        self.connection = connection


    def showFields(self):
        '''
        Print the field name and value for each field in the table
        Inputs:
            (none)
        Outputs:
            (none)
        '''

        print('TABLE:', self.tableName, '\n---------------------')
        for column in self.__dict__:
            #don't print unless it's a Column object
            if isinstance(self.__dict__[column], Column) or isinstance(self.__dict__[column], idColumn) or isinstance(self.__dict__[column], fkColumn):
                self.__dict__[column].showColumn()

    def getTableSeqs(self):
        '''
        Query the database and get all the entries in the seq column in this table
        '''

        query = "SELECT seq FROM {}".format(self.tableName)
        print(query)

        results = pd.read_sql(query, con=self.connection)
        results = results.get('seq')
        seqList = []
        for result in results:
            seqList.append(result)

        return seqList


    def insertMultipleFK(self, returnSeqListFlag=False):
        '''
        Insert multiple foreign key values into the database at the same time. Used for the special case tables camera and usedgcp
        Inputs:
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seqList. This
                                          seqList is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seqList (list) - optional output argument that is a list of seq values from the database
        '''

        if (self.tableName != 'camera') and (self.tableName != 'usedgcp'):
            print("table not eligible to insert multiple foreign key values")
            return

        fkColumns = []
        multiFkDict = {} #store fk columns and list of values
        for column in self.__dict__:
            
            #get list of fkColumn objects
            if isinstance(self.__dict__[column], fkColumn):
                fkColumns.append(self.__dict__[column])
                multiFkDict[self.__dict__[column].columnName] = self.__dict__[column].valueList

        #error checking
        try:
            if (self.tableName == 'camera') and (len(fkColumns) != 4):
                raise FKError("FKError: Incorrect number of foreign key columns attributed to this table")
            elif (self.tableName == 'usedgcp') and (len(fkColumns) != 2):
                raise FKError("FKError: Incorrect number of foreign key columns attributed to this table")
            
            for i in range(0, len(fkColumns)):
                if len(fkColumns[i - 1].valueList) != len(fkColumns[i].valueList):
                    raise FKError("FKError: foreign key column object value lists have unequal lengths")

                #check value of each foreign key
                for j in range(0, len(fkColumns[i].valueList)):
                    linkedTable = fkColumns[i].getLinkedTable(fkColumns[i].columnName)
                    
                    #special case: check that geometrySequence matches a seq value in geometry table. If not, set geometrySequence to most recently inserted seq value in geometry.
                    #this is because seq auto increments for each new insertion in geometry
                    if fkColumns[i].columnName == 'geometrySequence':

                        query = "SELECT seq FROM geometry WHERE seq = {}".format(fkColumns[i].valueList[j])
                        result = pd.read_sql(query, con=self.connection)
                        if result.size == 0:
                            
                            #check if geometry is empty
                            query = "SELECT seq FROM geometry"
                            result = pd.read_sql(query, con=self.connection)
                            if result.size == 0:
                                #if empty create placeholder value of 0 in geometry
                                query = "INSERT INTO geometry (seq) VALUES (0)"

                                cursor = self.connection.cursor()
                                try:
                                    cursor.execute(query)
                                    self.connection.commit()
                                except mysql.connector.Error as err:
                                    print(err.msg)
                            
                            print('geometrySequence reassigned to most recently inserted seq value in geometry')
                            
                            #if not empty, reassign geometrySequence to be most recently inserted seq value in the table
                            seqQuery = "SELECT MAX(seq) FROM {}".format(linkedTable)
                            result = pd.read_sql(seqQuery, con=self.connection)
                            seq = result.get('MAX(seq)')[0]
                            fkColumns[i].valueList[j] = seq
                            print('new seq', fkColumns[i].valueList[j])
                            
                    else:
                        checkLinkedKey(fkColumns[i].valueList[j], fkColumns[i].columnName, linkedTable, fkColumns[i].connection)
                    
        except Exception as e:
            sys.exit(e.message)

        #insert all foreign keys
        seqList = []
        for j in range(0, len(fkColumns[0].valueList)):

            hasBlankID = False

            #can only insert one fk for per row with blank id value, so check for blank id and create placeholder id
            if self.tableName != 'usedgcp':
                hasBlankID = fkColumns[0].check4BlankID()
            
            if hasBlankID:

                placeholderId = str(random.randint(0, 9999999))
                isDuplicate = fkColumns[0].checkDuplicateId(placeholderId)
                
                while isDuplicate:
                    placeholderId = str(random.randint(0, 9999999))
                    isDuplicate = fkColumns[0].checkDuplicateId(placeholderId)

                #insert placeholder so there's no error for having blank id values when inserting fk
                query = "UPDATE {} SET id = '{}' WHERE id = ''".format(self.tableName, placeholderId)

                print(query)
                cursor = self.connection.cursor()
                try:
                    cursor.execute(query)
                    self.connection.commit()
                except mysql.connector.Error as err:
                    print(err.msg) 

            if self.tableName == 'camera':
                
                query = "INSERT INTO camera (stationID, li_IP, lensmodelID, modelID) VALUES ('{}', '{}', '{}', '{}')".format(multiFkDict['stationID'][j], multiFkDict['modelID'][j], multiFkDict['lensmodelID'][j], multiFkDict['li_IP'][j]) 

            if self.tableName == 'usedgcp':

                query = "INSERT INTO usedgcp (gcpID, geometrySequence) VALUES ('{}', {})".format(multiFkDict['gcpID'][j], multiFkDict['geometrySequence'][j])

            print(query)

            cursor = self.connection.cursor()
            try:
                cursor.execute(query)
                self.connection.commit()
            except mysql.connector.Error as err:
                print(err.msg)

            #get the seq of the most recently added database entry. Since seq auto-increments most recent value is the max
            seqQuery = "SELECT MAX(seq) FROM {}".format(self.tableName)
            result = pd.read_sql(seqQuery, con=self.connection)
            seq = result.get('MAX(seq)')[0]
            seqList.append(seq)

        #clear valueLists
        for column in fkColumns:
            column.valueList = []

        if returnSeqListFlag == True:
            return seqList
        

    def insertTable2db(self):
        '''
        Insert all columns in this table to the database.
        '''
        
        fkColumns = []
        id_column = None
        otherColumns = []
        for column in self.__dict__:

            if isinstance(self.__dict__[column], fkColumn):
                fkColumns.append(self.__dict__[column])

            elif isinstance(self.__dict__[column], idColumn):
                id_column = self.__dict__[column]

            elif isinstance(self.__dict__[column], Column):
                otherColumns.append(self.__dict__[column])

        #vvv ADD FOREIGN KEY(S) TO TABLE vvv#
        fkArgs = []
        returnSeqListFlag = False
        seqList = []
        if len(fkColumns) > 1:
            print('mulitple fk')

            returnSeqListFlag = True

            #check value list for all fk columns have the same length
            try:
                for i in range(0, len(fkColumns)):
                    if len(fkColumns[i - 1].valueList) != len(fkColumns[i].valueList):
                        raise FKError("FKError: foreign key column object value lists have unequal lengths")

            except Exception as e:
                sys.exit(e.message)
                
            for i in range(0, len(fkColumns[0].valueList)):

                fkDict = {}
                fkArgs.append(fkDict)
                
                for column in fkColumns:

                    fkArgs[i][column.columnName] = column.valueList[i]

##            if (self.tableName == 'usedgcp') or (self.tableName == 'geometry'):
##                returnSeqListFlag = True

            seqList = self.insertMultipleFK(returnSeqListFlag=returnSeqListFlag)
            
        elif len(fkColumns) == 1:
            print('1 fk')

            returnSeqListFlag = True

            for i in range(0, len(fkColumns[0].valueList)):

                fkArgs.append({fkColumns[0].columnName : fkColumns[0].valueList[i]})

##            if (self.tableName == 'usedgcp') or (self.tableName == 'geometry'):
##                returnSeqListFlag = True

            seqList = fkColumns[0].insert2db(returnSeqListFlag=returnSeqListFlag)
            
        else:
            print('no fk')
            pass

        print('SEQLIST', seqList)

        #vvv ADD ID TO TABLE vvv#
        if id_column != None:
            print('has id column')
            idList = id_column.valueList
            id_column.insert2db(fkArgs=fkArgs)

        else:
            print('no id column')
            pass

        #vvv ADD ALL OTHER COLUMNS vvv#
        if (self.tableName == 'geometry') or (self.tableName == 'usedgcp'):
            for i in range(0, len(otherColumns)):
                otherColumns[i].update2db(seqList=seqList)
        else:
            for i in range(0, len(otherColumns)):
                otherColumns[i].update2db(idList=idList)
                
    def dispDBTable(self):
        '''
        Query the database and display all rows for the associated table
        '''
        
        query = "SELECT * FROM {}".format(self.tableName)
        print(query)

        result = pd.read_sql(query, con=self.connection)
        df = pd.DataFrame(result)
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
            print(df)

    def tableFromDB(self, idSeq):
        '''
        Retrieve all columns in a row in a table given a unique id/seq. Return as a dictionary object.
        Inputs:
            idSeq (string or int) - id (string) or seq (int) value used to specify which row of the column to get the value from.
        Outputs:
            valueDict (dict) - dictonary of values retrieved from the row in the table. The key is column name, the value is the column
                                value.
        '''

        columnList = []
        for column in self.__dict__:
            if isinstance(self.__dict__[column], Column):
                columnList.append(self.__dict__[column])

        valueDict = {}
        for column in columnList:
            value = column.valueFromDB(idSeq)
            valueDict[column.columnName] = value

        return valueDict
        

class Column:
    '''
    This class represents a column in the CoastCamDB. This Column can be added to a Table object as an attribute.
    The valueList attribute acts as a queue of values to be added to the column in the DB.
    '''

    '''
    Foreign key (fk) dictionary. Necessary for inserting values into most tables.
    The key is the name of the table, and the value is a tuple where the 1st element is the table the fk links to
    and the 2nd element is the fk column. Every fk links to the 'id' column of the upper-level table, except for
    the fk geometrySequence in the 'usedgcp' table, which links to the 'seq' column in the 'geometry' table. If the
    table has multiple foreign keys, the value will be a list of tuples with one tuple per fk.
    '''
    fkDict = {'station': ('site', 'siteID'),
               'camera': [('station', 'stationID'), ('cameramodel', 'modelID'), ('lensmodel', 'lensmodelID'), ('ip', 'li_IP')],
               'geometry': ('camera', 'cameraID'),
               'gcp': ('site', 'siteID'),
               'usedgcp': [('gcp', 'gcpID'), ('geometry', 'geometrySequence')] }

    '''list of all possible foregin key volumns'''
    fkColumnList = ['siteID', 'stationID', 'modelID', 'lensmodelID', 'li_IP', 'cameraID', 'siteID', 'gcpID', 'geometrySequence']

    def __init__(self, columnName, table, value=None):
        '''
        Initialize the Column object. Assign name and Table. Additionally, Append value to the column's valueList (queue).
        Inputs:
            columnName (string) - name of the Column
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
            table (Table) - Table object that this column is associated with. Represents the table the column is in in the DB.
        '''

        self.columnName = columnName
        self.table = table
        self.database = table.database

        self.valueList = []
        self.valueList.append(value)

        self.connection = table.connection


    def showColumn(self):
        '''
        Print Column object value
        '''
        print('COLUMN "{}" in TABLE "{}" ----- value(s) = {}'.format(self.columnName, self.table.tableName, [value for value in self.valueList]))


    def add2queue(self, value):
        '''
        Add a value to this Column's valueList (aka queue for data to be entered into DB)
        Inputs:
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
        Outputs:
            none
        '''

        if self.valueList[0] == None:
            self.valueList[0] = value
        else:
            self.valueList.append(value)

    def checkListLength(self, idseqList):
        '''
        Check to make sure that the length of the list of ids or seqs is the same length as the value list of this Column object.
        Raise exception if the number of given id/seq values to insert into table isn't the same as the number of values to insert
        Inputs:
            idseqList (list) - list of id or seq values corresponding to multiple values in this object's value list
        Outputs:
            none
        '''

        try:
            if len(idseqList) != len(self.valueList):
                raise ListLengthError("ListLengthError: number of given id/seq values is not the same as the number of values to be inserted into table '{}'\nlength of id/seq list: {}\nlength of values: {}".format(self.table.tableName, len(idseqList), len(self.valueList)))
    
        except Exception as e:
            sys.exit(e.message)

    def getForeignKey(self):
        '''
        Return the foreign key(s) associated with this column in the database
        Inputs:
            none
        Outputs:
            foreign_keys (tuple or list of tuples) - returns a tuple of the foreign key to be used in the SQL WHERE clause
                                                     when updating the column. The first element in the tuple is the table the
                                                     fk links to, and the second element is the column name of the foreign key.
                                                     If theere are multiple foregin keys, this method returns a list of tuples.
        '''
        try:
            return self.fkDict[self.table.tableName]
        
        except Exception:
            print("No foreign keys for table '{}'".format(self.table.tableName))
            return ''
            

    def getLinkedTable(self, fk_column):
        '''
        Return the name of a foreign key (fk), return the name of the table that the fk links to.
        Inputs:
            fk_column (string) - name of the foreign key column in the this Column object's associated table
        Outputs:
            linkedTable (string) - name of the table the fk links to
        '''

        if self.columnName not in self.fkColumnList:
            print('column does not link to another table')
            return ''

        if self.table.tableName == 'camera':

            if fk_column == 'stationID':

                linkedTable = 'station'

            elif fk_column == 'modelID':

                linkedTable = 'cameramodel'

            elif fk_column == 'lensmodelID':

                linkedTable = 'lensmodel'

            elif fk_column == 'li_IP':

                linkedTable = 'ip'

        elif self.table.tableName == 'usedgcp':

            if fk_column == 'gcpID':

                linkedTable = 'gcp'

            elif fk_column == 'geometrySequence':

                linkedTable = 'geometry'

        else:
            linkedTable = self.fkDict[self.table.tableName][0]

        return linkedTable

    def checkForeignKey(self, fk_column, fkValue):
        '''
        Check that the foreign key is valid and exists in the same table as this column
        Inputs:
            fk_column (string) - name of the foreign key column to be checked
            fkValue (string or int) - id/seq value of the foreign key
        Outputs:
            none
        '''

        #check that foreign key is valid and exists
        try:
            if fk_column not in self.fkColumnList:
                raise FKError("FKError: invalid foreign key '{}'".format(fk_column))

            if isinstance(fkValue, str):
                query = "SELECT {} FROM {} WHERE {} = '{}'".format(fk_column, self.table.tableName, fk_column, fkValue)
                #ex: select modelID from camera where modelID = 'XXXXX'

            elif isinstance(fkValue, int):
                query = "SELECT {} FROM {} WHERE {} = {}".format(fk_column, self.table.tableName, fk_column, fkValue)
                #ex: select geometrySequence from usedgcp where geometrySequence = 1

            result = pd.read_sql(query, con=self.connection)
            
            #NULL return, no seq/id found
            if result.size == 0:
                raise NoIDError("NoSeqError: No foreign_key '{}' with value '{}' found in table '{}'".format(fk_column, fkValue, self.table.tableName))
            
        except Exception as e:
            sys.exit(e.message)


    def fkFromId(self, ID):
        '''
        Given an ID value in a database table, find the corresponding foreign key value (same row).
        Inputs:
            ID (string) - id column value
        Outputs:
            fk_column (string) - name of the foreign key column in the table
            fkValue (string) - foreign key value for corresponding id
        '''

        fkPair = self.getForeignKey()

        #for tables that have multiple fk columns, fkPair is a list of tuples
        if isinstance(fkPair, list):
            #only need 1 fk value  for purposes of inserting values into database
            fk_column = fkPair[0][1]

        #table only has 1 foreign key column, fkPair is a tuple
        else:
            print(fkPair)
            fk_column = fkPair[1]
            
        checkID(ID, self.table.tableName, self.connection)
        
        query = "SELECT {} FROM {} WHERE id = '{}'".format(fk_column, self.table.tableName, ID)
        print(query)

        result = pd.read_sql(query, con=self.connection)
        fkValue = result.get(fk_column)[0]
        return fk_column, fkValue
    

    def fkFromSeq(self, seq):
        '''
        Given a seq value in a database table, find the corresponding foreign key value (same row).
        Inputs:
            seq (int) - seq column value
        Outputs:
            fk_column (string) - name of the foreign key column in the table
            fkValue (int) - foreign key value for corresponding seq
        '''

        fkPair = self.getForeignKey()

        #for tables that have multiple fk columns, fkPair is a list of tuples
        if isinstance(fkPair, list):
            #only need 1 fk value  for purposes of inserting values into database
            fk_column = fkPair[0][1]

        #table only has 1 foreign key column, fkPair is a tuple
        else:
            fk_column = fkPair[1]
            
        checkSeq(seq, self.table.tableName, self.connection)
        
        query = "SELECT {} FROM {} WHERE seq = {}".format(fk_column, self.table.tableName, seq)
        print(query)

        result = pd.read_sql(query, con=self.connection)
        fkValue = result.get(fk_column)[0]
        return fk_column, fkValue
    

    def checkDuplicateId(self, ID):
        '''
        check if id already exists in the column's associated table. Designed to be used with the random placeholder name.
        Inputs:
            ID (string) - ID to be checked
        Outputs:
            isDuplicate (boolean) - true/false variable stating whether or not the id is a duplicate
        '''

        query = "SELECT * FROM {} WHERE id = '{}'".format(self.table.tableName, ID)

        result = pd.read_sql(query, con=self.connection)

        if result.size == 0:
            isDuplicate = False
        else:
            isDuplicate = True

        return isDuplicate
    

    def check4BlankID(self):
        '''
        Check if any rows in the column's associated table have a blank id value. Used for inserting new foreign keys.
        Can only have one blank id per table or else inserting a new fk will fail.
        Inputs:
            none
        Outputs:
            hasBlankID (boolean) - true or flase result whether id is blank
        '''

        query = "SELECT * FROM {} WHERE id = ''".format(self.table.tableName)
        
        result = pd.read_sql(query, con=self.connection)
            
        if result.size == 0:
            hasBlankID = False
        else:
            hasBlankID = True

        return hasBlankID


    def checkBlankValue(self, idseq):
        '''
        Given an id/seq value, check if the value is blank for this column for the given row.
        Inputs:
            idseq (string) - id or seq value used to specify the row
        Outputs:
            hasBlankValue (bool) - True or False value describing if there is a blank value for the column in the specified row
        '''

        hasBlankValue = False
        
        if (self.table.tableName == 'geometry') or (self.table.tableName == 'usedgcp'):
            query = "SELECT {} FROM {} WHERE seq = {}".format(self.columnName, self.table.tableName, idseq)
        else:
            query = "SELECT {} FROM {} WHERE id = '{}'".format(self.columnName, self.table.tableName, idseq)

        result = pd.read_sql(query, con=self.connection)
        for res in result.get(self.columnName):
            if res == '':
                hasBlankValue = True
                print('BLANK VALUE')

        return hasBlankValue


    def insert2db(self, fkArgs=[], returnSeqListFlag=False):
        '''
        insert new value into for this column into the database. Depending on the table, specify a foreign key
        Inserts:
            fkArgs (list) - list of dictionaries used for foreign key arguments. Used when this function calls insertNewID().
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seqList. This
                                          seqList is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seqList (list) - optional output argument that is a list of seq values from the database
        '''

        try:

            if len(self.valueList) == 0:
                raise EmptyValueError(message="EmptyValueError: Empty value list for column '{}'".format(self.columnName))
        except Exception as e:
            sys.exit(e.message)


        #if column is foreign key, insert using the special subclass function for fk instead
        if isinstance(self, fkColumn):
            
            seqList = self.insertNewFK(returnSeqListFlag)
            return seqList
            
        #if column is id, use subclass function
        elif isinstance(self, idColumn):

            self.insertNewID(fkArgs)

        else:

            fk = self.getForeignKey()

            #does not need foreign key
            if fk == '':

                for i, value in enumerate(self.valueList):
                    
                    try:
                        if isinstance(value, str):
                            
                            query = "INSERT INTO {} ({}) VALUES ('{}')".format(self.table.tableName, self.columnName, value)

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "INSERT INTO {} ({}) VALUES ({})".format(self.table.tableName, self.columnName, value)

                        else:
                            raise TypeError

                    except TypeError:
                        print('TypeError: invalid type for column value')

                    print(query)

                    try:
                        cursor = self.connection.cursor()
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)

            #tables that use seq instead of id            
            elif (self.table.tableName == 'usedgcp') or (self.table.tableName == 'geometry'):                    

                for i, value in enumerate(self.valueList):

                    for dictKey, dictValue in fkArgs[i].items():
                        fk_column = dictKey
                        fkValue = dictValue

                    #don't need to check for blank id. Seq updates automatically with everynew insertion

                    if fk_column == 'geometrySequence':
                        linkedTable = 'geometry'
                    elif fk_column == 'gcpID':
                        linkedTable = 'gcp'
                    elif fk_column == 'cameraID':
                        linkedTable = 'camera'

                    checkLinkedKey(fkValue, fk_column, linkedTable, self.connection)
                    
                    try:
                        if isinstance(value, str):
                            query = "INSERT INTO {} ({}, {}) VALUES ('{}', '{}')".format(self.table.tableName, fk_column, self.columnName, fkValue, value)

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "INSERT INTO {} ({}, {}) VALUES ('{}', {})".format(self.table.tableName, fk_column, self.columnName, fkValue, value)

                        elif isinstance(value, np.ndarray):
                            blob = np2text(value)
                            query = query = "INSERT INTO {} ({}, {}) VALUES ('{}', '{}')".format(self.table.tableName, fk_column, self.columnName, fkValue, blob)
                        
                        else:
                            raise TypeError

                    except TypeError:
                        print('TypeError: invalid type for column value')

                    print(query)

                    try:
                        cursor = self.connection.cursor()
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)

            #tables that use id
            else:                   

                for i, value in enumerate(self.valueList):

                    for dictKey, dictValue in fkArgs[i].items():
                        fk_column = dictKey
                        fkValue = dictValue

                    #check for blank ID correpsonding to fk arg
                    query = "SELECT id FROM {} WHERE {} = '{}'".format(self.table.tableName, fk_column, fkValue)
                    result = pd.read_sql(query, con=self.connection)
                    hasBlankID = False
                    for ID in result.get('id'):
                        if ID == '':
                            hasBlankID = True
                            break

                    
                    try:
                        #if there's a blank id in the same row as the specified foreign key, update the column in that row insteasd of inserting new row
                        if hasBlankID:
                            if isinstance(value, str):
                                query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' AND id = ''".format(self.table.tableName, self.columnName, value, fk_column, fkValue)
                            elif isinstance(value, int) or isinstance(value, float):
                                query = "UPDATE {} SET {} = {} WHERE {} = '{}' AND id = ''".format(self.table.tableName, self.columnName, value, fk_column, fkValue)
                            elif isinstance(value, np.ndarray):
                                blob = np2text(value)
                                query = query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' AND id = ''".format(self.table.tableName, self.columnName, blob, fk_column, fkValue)
                            else:
                                raise TypeError
                        else:
                            if isinstance(value, str):
                                query = "INSERT INTO {} ({}, {}) VALUES ('{}', '{}')".format(self.table.tableName, fk_column, self.columnName, fkValue, value)

                            elif isinstance(value, int) or isinstance(value, float):
                                query = "INSERT INTO {} ({}, {}) VALUES ('{}', {})".format(self.table.tableName, fk_column, self.columnName, fkValue, value)

                            elif isinstance(value, np.ndarray):
                                blob = np2text(value)
                                query = "INSERT INTO {} ({}, {') VALUES ('{}', '{}')".format(self.table.tableName, fk_column, self.columnName, fkValue, blob)
                            
                            else:
                                raise TypeError

                    except TypeError:
                        print('TypeError: invalid type for column value')

                    print(query)

                    try:
                        cursor = self.connection.cursor()
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)
            
        #clear list once all values have been inserted into DB
        self.valueList = []
        

    def update2db(self, idList=[], seqList=[], fkArgs=[], returnSeqListFlag=False):
        '''
        Update a value in for this column in the database. Specify the row using a value for id or seq
        Inserts:
            idList (list) - list of id (string) values. Used if there are multiple values in self.valueList to be inserted.
                             The id values are used for specifying specifying the id(s) of the associated row(s) in the DB that the value(s)
                             will be inserted into. Used with the SQL 'WHERE' clause
            seqList  (list) - list of seq (int) values. Used if there are multiple values in self.valueList to be inserted.
                               The id values are used for specifying specifying the seq(s) of the associated row(s) in the DB that the value(s)
                               will be inserted into. Used with the SQL 'WHERE' clause. seq column only used with the geometry and
                               usedgcp tables.
            fkArgs (list) - list of dictionaries used for foreign key arguments. Used when this function calls insertNewID().
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seqList. This
                                          seqList is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seqList (list) - optional output argument that is a list of seq values from the database
        '''

        try:

            if len(self.valueList) == 0:
                raise EmptyValueError(message="EmptyValueError: Empty value list for column '{}'".format(self.columnName))
        except Exception as e:
            sys.exit(e.message)


        #if column is foreign key, insert using the special subclass function for fk instead
        if isinstance(self, fkColumn):
            
            seqList = self.insertNewFK(returnSeqListFlag)
            return seqList
            
        #if column is id, use subclass function
        elif isinstance(self, idColumn):

            self.insertNewID(fkArgs)

        else:

            fk = self.getForeignKey()
            
            if fk == '':
                #does not need foreign key
                self.checkListLength(idList)

                for i, value in enumerate(self.valueList):

                    checkID(idList[i], self.table.tableName, self.connection)
                    
                    try:
                        if isinstance(value, str):
                            query = "UPDATE {} SET {} = '{}' WHERE id = '{}'".format(self.table.tableName, self.columnName, value, idList[i])

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "UPDATE {} SET {} = {} WHERE id = '{}'".format(self.table.tableName, self.columnName, value, idList[i])

                        else:
                            raise TypeError

                    except TypeError:
                        print('TypeError: invalid type for column value')

                    print(query)

                    try:
                        cursor = self.connection.cursor()
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)

            #tables that use seq instead of id            
            elif (self.table.tableName == 'usedgcp') or (self.table.tableName == 'geometry'):                    

                self.checkListLength(seqList)

                for i, value in enumerate(self.valueList):

                    #don't need to checkSeq because that is already done in fkFromSeq
                    fk_column, fkValue = self.fkFromSeq(seqList[i])
                    
                    try:
                        if isinstance(value, str):
                            query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and seq = {}".format(self.table.tableName, self.columnName, value, fk_column, fkValue, seqList[i])

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "UPDATE {} SET {} = {} WHERE {} = '{}' and seq  = {}".format(self.table.tableName, self.columnName, value, fk_column, fkValue, seqList[i])

                        elif isinstance(value, np.ndarray):
                            blob = np2text(value)
                            query = query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and seq = {}".format(self.table.tableName, self.columnName, blob, fk_column, fkValue, seqList[i])
                        
                        else:
                            raise TypeError

                    except TypeError:
                        print('TypeError: invalid type for column value')

                    print(query)

                    try:
                        cursor = self.connection.cursor()
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)

            #tables that use id
            else:

                self.checkListLength(idList)

                for i, value in enumerate(self.valueList):

                    #don't need to checkSeq because that is already done in fkFromSeq
                    fk_column, fkValue = self.fkFromId(idList[i])
                    
                    try:
                        if isinstance(value, str):
                            query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and id = '{}'".format(self.table.tableName, self.columnName, value, fk_column, fkValue, idList[i])

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "UPDATE {} SET {} = {} WHERE {} = '{}' and id = '{}'".format(self.table.tableName, self.columnName, value, fk_column, fkValue, idList[i])

                        elif isinstance(value, np.ndarray):
                            blob = np2text(value)
                            query = query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and id = '{}'".format(self.table.tableName, self.columnName, blob, fk_column, fkValue, idList[i])
                        
                        else:
                            raise TypeError

                    except TypeError:
                        print('TypeError: invalid type for column value')

                    print(query)

                    try:
                        cursor = self.connection.cursor()
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)
  

        #clear list once all values have been inserted into DB
        self.valueList = []

    def valueFromDB(self, idSeq):
        '''
        Retrieve the value of the column from the database given a specfified id or seq value.
        Inputs:
            idSeq (string or int) - id (string) or seq (int) value used to specify which row of the column to get the value from.
        Outputs:
            value (object) - value of the given column in the same row as the specified id/seq. Value type depends on the value
                             type in the database. Can be string, int, double.
        '''

        if (self.columnName == 'K') or (self.columnName == 'm') or (self.columnName == 'kc'):
            if isinstance(idSeq, str):
                result = db2np(connection=self.connection, table=self.table.tableName, column=self.columnName, ID=idSeq)

            elif isinstance(idSeq, int):
                result = db2np(connection=self.connection, table=self.table.tableName, column=self.columnName, seq=idSeq)

        else:
            if isinstance(idSeq, str):   
                checkID(idSeq, self.table.tableName, self.connection)
                query = "SELECT {} FROM {} WHERE id = '{}'".format(self.columnName, self.table.tableName, idSeq)

            elif isinstance(idSeq, int):
                checkSeq(idSeq, self.table.tableName, self.connection)
                query = "SELECT {} FROM {} WHERE seq = {}".format(self.columnName, self.table.tableName, idSeq)

            result = pd.read_sql(query, con=self.connection)
            result = result.get(self.columnName)[0]
            
        return result
  


class idColumn(Column):
    '''
    Defines the class related to the id column in the database. This is a subclass of the Column class. ids are primary keys
    in the database so they have special properties and usually act as points of reference for inserting data into the database.
    '''

    def __init__(self, table, value=None):
        '''
        Initialize the Column object. Assign name and Table. Additionally, Append value to the column's valueList (queue).
        Inputs:
            columnName (string) - name of the Column
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
            table (Table) - Table object that this column is associated with. Represents the table the column is in in the DB.
        '''

        Column.__init__(self, columnName='id', table=table, value=value)


    def insertNewID(self, fkArgs = [], seqList = []):
        '''
        Insert new id column value(s) into the database. USes foreign keys where necessary.
        Inputs:
            fkArgs (list) - list of dictionaries used for foreign key arguments. Each dictionary will correspond to an
                             id being inserted into the table. Only one key/value of an fk column/value pair per id is actually
                             needed in each dictionary. The key will be the fk column name and the value will be the column value.
            seqList (list) - list of seq values used to specify which row to insert the id into. Used for cases where multiple
                              rows in a table have the same foregin key value
        Outputs:
            none
        '''

        fk = self.getForeignKey()
            
        if fk != '':
            #needs foreign key

            try:
                if len(fkArgs) == 0:
                    raise FKError("FKError: foreign keys required but no foreign keys passed as arguments")

                elif len(fkArgs) != len(self.valueList):
                    raise FKError("FKError: Incorrect number of foreign keys for number of values to be inserted")

            except Exception as e:
                sys.exit(e.message)

        i = 0
        for ID in self.valueList:

            isDuplicate = self.checkDuplicateId(ID)

            if isDuplicate:
                print("Duplicate id value. Value not inserted.")

            else:
                if len(fkArgs) > 0:
                    fks = fkArgs[i]

                    for fk_column in fks:
                        #check for valid foreign key value. Don't need to check linked table because foreign key in table
                        #already needs to have same value as id/seq in linked table
                        value = fks[fk_column]
                        self.checkForeignKey(fk_column, value)

                    #If function makes it here, foreign keys/values don't throw errors. Only need one fk for query   
                    #check for blank id. If blank ID, replace with blankid (that has same fkArgs) instead of insertiung new value
                    hasBlankID = self.check4BlankID()
                    if hasBlankID:
                        query = "UPDATE {} SET id = '{}' WHERE {} = '{}' and id = ''".format(self.table.tableName, ID, fk_column, fks[fk_column])
                        #ex: "UPDATE camera SET id = '1234567' WHERE stationID = '1234567' and id = ''
                    else:
                        query = "INSERT INTO {} ({}, id) VALUES ('{}', '{}')".format(self.table.tableName, fk_column, fks[fk_column], ID)
                        #ex: "INSERT INTO camera (stationID, id) VALUES ('statID', 'camID')

                else:
                    query = "INSERT INTO {} (id) VALUES ('{}')".format(self.table.tableName, ID)
                    #ex: INSERT INTO site (id) VALUES ('EXXXXXX')
                    
                print(query)     
                cursor = self.connection.cursor()
                try:
                    cursor.execute(query)
                    self.connection.commit()
                except mysql.connector.Error as err:
                    print(err.msg)
                    
            i = i + 1
            

    def updateID(self, oldID):
        '''
        Update exsiting id column value in the database. Uses foregin keys where necessary.
        Inputs:
            oldID (string) - old id value to be updated (replaced)
        Outputs:
            none
        '''

        i = 0
        for ID in self.valueList:

            isDuplicate = self.checkDuplicateId(ID)

            if isDuplicate:
                print("Duplicate id value. Value not updated.")

            else:
                query = "UPDATE {} SET id = '{}' WHERE id = '{}'".format(self.table.tableName, ID, oldID)
                #ex: "UPDATE camera SET id = 'yyyyy' WHERE id = 'xxxxx'"
                    
                print(query)     
                cursor = self.connection.cursor()
                try:
                    cursor.execute(query)
                    self.connection.commit()
                except mysql.connector.Error as err:
                    print(err.msg)

            i = i + 1
            


class fkColumn(Column):
    '''
    Defines the class related to a foreign key (fk) column in the database. Foreign keys are used as contraints when inserting data into
    the database. The fk will be used as a link to another, higher level, table.
    '''

    def __init__(self, columnName, table, value=None):
        '''
        Initialize the Column object. Assign name and Table. Additionally, Append value to the column's valueList (queue).
        Inputs:
            columnName (string) - name of the Column
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
            table (Table) - Table object that this column is associated with. Represents the table the column is in in the DB.
        '''

        Column.__init__(self, columnName=columnName, table=table, value=value)

        #assign variable saying what table this fk links to
        linkedTable = self.getLinkedTable(columnName)
        self.linkedTable = linkedTable

    def displayLinkedKey(self):
        '''
        Display the values for the corresponding id/seq column in this Column's linked table
        Inputs:
            none
        Outputs:
            none
        '''

        print("Below are the valid values for {}".format(self.columnName))

        #special case for geometrySequence foreign key
        if self.linkedTable == 'geometry':
            query = "SELECT seq FROM geometry"
        else:
            query = "SELECT id FROM {}".format(self.linkedTable)

        result = getFormattedResult(query, self.connection)
        result_str = result.to_string(header=False)
        print(result_str)

    def insertNewFK(self, returnSeqListFlag=False):
        '''
        Insert new value(s) for this foreign key column into the database.
        Inputs:
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seqList. This
                                          seqList is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seqList (list) - optional output argument that is a list of seq values from the database
        '''

        seqList = []
        for value in self.valueList:

            #can only insert one fk for per row with blank id value, so check for blank id and create placeholder id
            if (self.table.tableName != 'geometry') and (self.table.tableName != 'usedgcp'):
                hasBlankID = self.check4BlankID()

                if hasBlankID:

                    placeholderId = str(random.randint(0, 9999999))
                    isDuplicate = self.checkDuplicateId(placeholderId)
                    
                    while isDuplicate:
                        placeholderId = str(random.randint(0, 9999999))
                        isDuplicate = self.checkDuplicateId(placeholderId)

                    #insert placeholder so there's no error for having blank id values when inserting fk
                    query = "UPDATE {} SET id = '{}' WHERE id = ''".format(self.table.tableName, placeholderId)

                    print(query)
                    cursor = self.connection.cursor()
                    try:
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)                    

            checkLinkedKey(value, self.columnName, self.linkedTable, self.connection)

            #special case because geometrySequence is only fk that links to a 'seq' column
            if self.columnName == 'geometrySequence':

                query = "INSERT INTO usedgcp (geometrySequence) VALUES ({})".format(value)

            else:
                
                query = "INSERT INTO {} ({}) VALUES ('{}')".format(self.table.tableName, self.columnName, value)

            print(query)

            cursor = self.connection.cursor()
            try:
                cursor.execute(query)
                self.connection.commit()
            except mysql.connector.Error as err:
                print(type(err))
                print(err.msg)

            #get the seq of the most recently added database entry. Since seq auto-increments most recent value is the max
            seqQuery = "SELECT MAX(seq) FROM {}".format(self.table.tableName)
            result = pd.read_sql(seqQuery, con=self.connection)
            seq = result.get('MAX(seq)')[0]
            seqList.append(seq)

        if returnSeqListFlag == True:
            return seqList


class Parameter:
    '''
    Class designed to hold parameters used for image rectification: extrinsics, intrinsics, metadata, and localOrigin.
    Also hold datetime information for local time
    '''

    def __init__(self, extrinsics=None, intrinsics=None, metadata=None, localOrigin=None, dateTimeObj=None, dateTimeStr=None, tzone=None):
        
        self.extrinsics = extrinsics #list
        self.intrinsics = intrinsics #list
        self.metadata = metadata #list
        self.localOrigin = localOrigin #dict
        
        self.dateTimeObj = dateTimeObj
        self.dateTimeStr = dateTimeStr
        self.tzone = tzone
        
        if extrinsics != None:
            self.num_cameras = len(extrinsics)

        if intrinsics != None:
            self.num_cameras = len(intrinsics)

        if metadata != None:
            self.num_cameras = len(metadata)

        
##### testing funcs #####
if __name__ == "__main__":
    filepath = "C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv"
    conn = DBConnectCSV(filepath)
    result = pd.read_sql('select * from camera', con=conn)
    print(result)
