'''
Funcs and classes for connecting to coastcamDB and creating entries.
uses Table class to represent tables in the DB. The attributes in the Table class
are equivalent to the fields in the Db table
'''

##### IMPORTS #####
import pandas as pd
import pymysql
import csv
import os
import sys
import ast
import random
import numpy as np
import mysql.connector
from mysql.connector import errorcode
from tabulate import tabulate



##### FUNCTIONS #####
def parseCSV(filepath):
    '''
    Read and parse a CSV to obtain list of parameters used to access database.
    The csv file should have the column headers "host", "port", "dbname", "user",
    and "password" with one row of data containing the user's values
    Inputs:
        filepath (string) - filepath of the csv
    Outputs:
        db_list (list) - list of paramters used to access database
    '''
    
    db_list = []

    with  open(filepath, 'r') as csv_file:
        csvreader = csv.reader(csv_file)

        #extract data from csv. Have to use i to track row because iterator object csvreader is not subscriptable
        i = 0
        for row in csvreader:
            #i = 0 is column headers. i = 1 is data 
            if i == 1:
                db_list = row
            i = i + 1
                
    return db_list


def DBConnectCSV(filepath):
    '''
    Connect to the DB using parameters stored in a CSV. If the user doesn't want to use a csv
    they can use the pymysql.connect() function directly.
    Inputs:
        filepath (string) - filepath of the csv
    Outputs:
        connection (pymysql.connections.Connection object) - Object representing connection to DB
    '''

    csv_parameters = parseCSV(filepath)
    host = csv_parameters[0]
    port = int(csv_parameters[1])
    dbname = csv_parameters[2]
    user = csv_parameters[3]
    password = csv_parameters[4]

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

        check_id(ID, table, connection)
        query = "SELECT {} FROM {} WHERE id = '{}'".format(column, table, ID)

    elif (seq != 0):

        check_seq(seq, table, connection)
        query = "SELECT {} FROM {} WHERE seq = {}".format(column, table, seq)

    else:

        raise NoIDError("NoIDError: No id or seq value given to specify what row to insert data into column {} in table '{}'".format(column, table))
    #print(query)

    result = pd.read_sql(query, con=connection)
    result = result.get(column)[0]


    #Number of dimnesions of array equal the number of ']' brackets at the end of the array.
    #Split the text on '[' bracket and check the last element of the resulting list for ']'
    dim_count = 0
    split = result.split('[')
    dim_count = split[-1].count(']')

    if dim_count == 1:
        #format for np.fromstring()
        array = result.replace('[', '')
        array = array.replace(']', '')
        array = np.fromstring(array, dtype=float, sep=' ')

    elif dim_count == 2:        
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


def id_seq_match(ID, seq, table, connection):
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
        

def check_id(ID, table, connection):
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


def check_seq(seq, table, connection):
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


def check_linked_key(value, column, linked_table, connection):
    '''
    Check that the value actually exists in the id/seq column of the linked table
    Inputs:
        value (string or int) - seq/id value to be checked
        column (string) - name of the fk column
        linked_table (string) - table that the fk links to
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

        query = "SELECT id FROM {} WHERE id = '{}'".format(linked_table, value)

        print(query)

        try:
            
            result = pd.read_sql(query, con=connection)
            
            #NULL return, no id found
            if result.size == 0:
                raise NoIDError("NoSeqError: No 'id' {} found in table '{}'".format(value, linked_table))
        
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

def get_formatted_result(query, connection):
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
        df_list (list) - list of tuples where the first element of the tuple is the table name and the
                         second element is the table dataframe.
    outputs:
        df_list (list) - list of Pandas dataframe obuects, one for each table corresponding to the site.
    '''

    pd.set_option('display.width' ,160)
    pd.set_option('display.max_columns', 40)

    df_list = []

    #site
    query = "SELECT * FROM site WHERE id = '{}'".format(siteID)
    result = get_formatted_result(query, connection)
    print('---SITE---')
    print(result)

    #don't add empty tables to the dataframe list
    if not result.empty:
        df_tuple = ('site', result)
        df_list.append(df_tuple)

    #station
    query = "SELECT * FROM station WHERE siteID = '{}'".format(siteID)
    result = get_formatted_result(query, connection)
    stationID = result.get('id')
    try:
        if result.empty:
            raise Exception
        print('\n---STATION---')
        print(result)

        if not result.empty:
            df_tuple = ('station', result)
            df_list.append(df_tuple)
    except:
        pass

    #camera
    camera_result = []
    try:
        for ID in stationID:
            query = "SELECT * FROM camera WHERE stationID = '{}'".format(ID)
            camera_result.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(stationID) > 1:
            result = pd.concat(camera_result, axis=0)
        else:
            result = camera_result[0]
        cameraID = result.get('id')
        modelID = result.get('modelID')
        lensmodelID = result.get('lensmodelID')
        li_IP = result.get('li_IP')
        blankIndex = [''] * len(result)
        result.index = blankIndex
        print('\n---CAMERA---')
        print(result)

        if not result.empty:
            df_tuple = ('camera', result)
            df_list.append(df_tuple)
    except:
        pass

    #cameramodel
    cameramodel_result = []
    try:
        for ID in modelID:
            query = "SELECT * FROM cameramodel WHERE id = '{}'".format(ID)
            cameramodel_result.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(modelID) > 1:
            result = pd.concat(cameramodel_result, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = cameramodel_result[0]
        print('\n---CAMERAMODEL---')
        print(result)

        if not result.empty:
            df_tuple = ('cameramodel', result)
            df_list.append(df_tuple)
    except:
        pass

    #lensmodel
    lensmodel_result = []
    try:
        for ID in lensmodelID:
            query = "SELECT * FROM lensmodel WHERE id = '{}'".format(ID)
            lensmodel_result.append(pd.read_sql(query, con=connection))
        if len(lensmodelID) > 1:
            result = pd.concat(lensmodel_result, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = lensmodel_result[0]
        print('\n---LENSMODEL---')
        print(result)

        if not result.empty:
            df_tuple = ('lensmodel', result)
            df_list.append(df_tuple)
    except:
        pass

    #ip
    li_IP_result = []
    try:
        for ID in li_IP:
            query = "SELECT * FROM ip WHERE id = '{}'".format(ID)
            li_IP_result.append(pd.read_sql(query, con=connection))
        if len(li_IP) > 1:
            result = pd.concat(li_IP_result, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = li_IP_result[0]
        print('\n---IP---')
        print(result)

        if not result.empty:
            df_tuple = ('ip', result)
            df_list.append(df_tuple)
    except:
        pass
    
    #gcp
    query = "SELECT * FROM gcp WHERE siteID = '{}'".format(siteID)
    result = get_formatted_result(query, connection)
    gcpID = result.get('id')
    try:
        if result.empty:
            raise Exception
        print('\n---GCP---')
        print(result)

        if not result.empty:
            df_tuple = ('gcp', result)
            df_list.append(df_tuple)
    except:
        pass

    #geometry
    geometry_result = []
    try:
        for ID in cameraID:
            query = "SELECT * FROM geometry WHERE cameraID = '{}'".format(ID)
            geometry_result.append(pd.read_sql(query, con=connection))
        if len(cameraID) > 1:
            result = pd.concat(geometry_result, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = geometry_result[0]
        geometrySequence = result.get('seq')
        print('\n---GEOMETRY---')
        print(result)

        if not result.empty:
            df_tuple = ('geometry', result)
            df_list.append(df_tuple)
    except:
        pass

    #usedgcp
    try:
        usedgcp_result = []
        for ID in gcpID:
            for seq in geometrySequence:
                query = "SELECT * FROM usedgcp WHERE gcpID = '{}' AND geometrySequence = {}".format(ID, seq)
                usedgcp_result.append(pd.read_sql(query, con=connection))
        if (len(gcpID) > 1) or (len(geometrySequence) > 1):
            result = pd.concat(usedgcp_result, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = usedgcp_result[0]
        print('\n---USEDGCP---')
        print(result)

        if not result.empty:
            df_tuple = ('usedgcp', result)
            df_list.append(df_tuple)
    except:
        pass

    return df_list

def getParameterDicts(stationID, unix_time, connection):
    '''
    Given a stationID, return parameter dictionaries for extrinsics, intrinsics, metadata, and local origin.
    Extrinsics, intrinsics, and metadata will be stored as lists, where each item in the list is a dictionary of
    parameters. There will be one dictionary for each camera at the station.
    Inputs:
        stationID (string) - specifies the "id" field for the "station" table, which is also the "stationID" field in the
                             "camera" table
        unix_time (int) - timestamp of the filename needed for searching relevant data
        connection (pymysql.connections.Connection object) - Object representing connection to DB
    Outputs:
        extrinsics (list) - list of extrinsic paramater dictionaries. One dictionary for each camera.
        intrinsics (list) - list of intrinsic parameter dictionaries. One dictionary for each camera.
        metadata (list) - list of metadata parameter dictionaries. One dictionary for each camera.
        local_origin (dictionary) - dictionary of local origin parameters
    '''

    query = "SELECT * FROM camera WHERE stationID = '{}' AND timeIN <= {} AND timeOUT >= {} ".format(stationID, unix_time, unix_time)
    print(query)

    result = pd.read_sql(query, con=connection)
    camera_list = []
    for ID in result.get('id'):
        camera_list.append(ID)

    #lists of dictionaries. One dictionary in every list for each camera.
    metadata_dict_list = []
    extrinsic_dict_list = []
    intrinsic_dict_list = []

    #need to query station table before going through camera list
    query = "SELECT siteID, name FROM station WHERE id = '{}'".format(stationID)
    result = pd.read_sql(query, con=connection)
    #siteID for querying site table 
    siteID = result.get('siteID')[0]
    #name for metadata dict
    name = result.get('name')[0]

    if len(camera_list) != 0:

        for i in range(0, len(camera_list)):

            ###GET METADATA###
            #yaml_metadata_dict is dict of YAML field names and corresponding values
            metadata_dict = {}

            metadata_dict['name'] = name

            query = "SELECT cameraSN, cameraNumber,timeIN, li_IP FROM camera WHERE id = '{}'".format(camera_list[i])
            result = pd.read_sql(query, con=connection)
            metadata_dict['serial_number'] = result.get('cameraSN')[0]
            metadata_dict['camera_number'] = result.get('cameraNumber')[0]
            metadata_dict['calibration_date'] = result.get('timeIN')[0]

            #key for accessing IP table
            IP = result.get('li_IP')[0]

            metadata_dict['coordinate_system'] = 'geo'

            metadata_dict_list.append(metadata_dict)
            

            ###GET INTRINSICS###
            intrinsic_dict = {}

            query = "SELECT width, height FROM ip WHERE id = '{}'".format(IP)
            result = pd.read_sql(query, con=connection)
            intrinsic_dict['NU'] = result.get('width')[0]
            intrinsic_dict['NV'] = result.get('height')[0]

            #get matrices for rest of intrinsics
            K = db2np(connection, 'camera' , 'K', ID=camera_list[i])
            kc = db2np(connection, 'camera', 'kc', ID=camera_list[i])
            intrinsic_dict['fx'] = K[0][0]
            intrinsic_dict['fy'] = K[1][1]
            intrinsic_dict['c0U'] = K[0][2]
            intrinsic_dict['c0V'] = K[1][2]
            intrinsic_dict['d1'] = kc[0]
            intrinsic_dict['d2'] = kc[1]
            intrinsic_dict['d3'] = kc[2]
            intrinsic_dict['t1'] = kc[3]
            intrinsic_dict['t2'] = kc[4]

            intrinsic_dict_list.append(intrinsic_dict)
            

            ###GET EXTRINSICS###
            extrinsic_dict = {}

            query = "SELECT x, y, z FROM camera WHERE id = '{}'".format(camera_list[i])
            result = pd.read_sql(query, con=connection)
            extrinsic_dict['x'] = result.get('x')[0]
            extrinsic_dict['y'] = result.get('y')[0]
            extrinsic_dict['z'] = result.get('z')[0]

            query = "SELECT azimuth, tilt, roll FROM geometry WHERE cameraID = '{}'".format(camera_list[i])
            result = pd.read_sql(query, con=connection)
            extrinsic_dict['a'] = result.get('azimuth')[0]
            extrinsic_dict['t'] = result.get('tilt')[0]
            extrinsic_dict['r'] = result.get('roll')[0]

            extrinsic_dict_list.append(extrinsic_dict)
            

        ###GET LOCAL ORIGIN DICT###
        local_origin_dict = {}
        query = "SELECT UTMEasting, UTMNorthing, degFromN FROM site WHERE id = '{}'".format(siteID)
        result = pd.read_sql(query, con=connection)
        local_origin_dict['x'] = result.get('UTMEasting')[0]
        local_origin_dict['y'] = result.get('UTMNorthing')[0]
        local_origin_dict['angd'] = result.get('degFromN')[0]

        extrinsics = extrinsic_dict_list
        intrinsics = intrinsic_dict_list
        metadata = metadata_dict_list
        local_origin = local_origin_dict

        return extrinsics, intrinsics, metadata, local_origin

    
def filename2param(filename, connection):
    '''
    Given the filename of a CoastCam image (with the short name of the station in the filename), create a Python object
    that stores important rectification parameters: extrinsics, intrinsics, metadata, local origin. Extrinsics, intrinsics, and
    metadata will be stored as lists, where each item in the list is a dictionary of parameters. There will be one dictionary for
    each camera at the station. Is the unix time in the filename to search the database for data that corresponds to this time--this
    will use timeIN and timeOUT fields.
    Inputs:
        filename(string) - image filename
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        params (Paramater object) - Python object storing the parameters associated with the station
        return None if the filename doesn't match any existing station short names
    '''

    filename_elements = filename.split('.')
    unix_time = int(filename_elements[0])
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

                extrinsics, intrinsics, metadata, local_origin = getParameterDicts(stationID, unix_time, connection)

                params = Parameter(extrinsics=extrinsics, intrinsics=intrinsics, metadata=metadata, local_origin=local_origin)
                return params

            else:
                #whole list has been checked
                if i == len(shortName) - 1:
                    print('no existing station short names match the given filename')
                    return None
    except:
        print("unable to get parameters")
        return None


def check_duplicate_id(table, ID, connection):
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


def column2csv(column, table, csv_path, connection):
    '''
    Store a data read from a column in the database into a csv file. There will be a single file for the column.
    Inputs:
        column (string) - column name
        csv_path (string) - optional input specified by the user for where they'd like to store csvs of the data read from
                                 the database.
        table (string) - input needed when writing  to csv because nott every column name in the database is unique.
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        result (Pandas dataframe) - resultant dataframe containing column data
    '''

    query = "SELECT {} FROM {}".format(column, table)
    result = get_formatted_result(query, connection)

    filename = table + '_' + column + '.csv'
    folder_path = csv_path + 'columns/'

    #if folders for saving csv does not exist, create directory
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    full_path = folder_path + filename
    result.to_csv(full_path, encoding='utf-8', index=False)

    print("Saved csv file to", full_path)
    
    return result


def table2csv(table, csv_path, connection):
    '''
    Store a data read from a table in the database into a csv file. There will be a single file for the table.
    Inputs:
        csv_path (string) - optional input specified by the user for where they'd like to store csvs of the data read from
                                 the database.
        table (string) - table name
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        result (Pandas dataframe) - resultant dataframe containing column data
    '''

    query = "SELECT * FROM {}".format(table)
    result = get_formatted_result(query, connection)

    filename = table + '.csv'
    folder_path = csv_path + 'tables/'

    #if folders for saving csv does not exist, create directory
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    full_path = folder_path + filename
    result.to_csv(full_path, encoding='utf-8', index=False)

    print("Saved csv file to", full_path)
    
    return result


def site2csv(siteID, csv_path, connection):
    '''
    Store a data read from a site in the database into a csv file using a specific siteID. There will be a folder for the site
    where there's one csv file per table.
    Inputs:
        csv_path (string) - optional input specified by the user for where they'd like to store csvs of the data read from
                                 the database.
        table (string) - table name
        connection (pymysql.connections.Connection object) - object representing the connection to the DB
    Outputs:
        output_list (list) - list of Pandas datframes, one for each non-empty table associated with the given siteID
    '''

    df_list = []

    #site
    query = "SELECT * FROM site WHERE id = '{}'".format(siteID)
    result = get_formatted_result(query, connection)

    #don't add empty tables to the dataframe list
    if not result.empty:
        df_tuple = ('site', result)
        df_list.append(df_tuple)

    #station
    query = "SELECT * FROM station WHERE siteID = '{}'".format(siteID)
    result = get_formatted_result(query, connection)
    stationID = result.get('id')
    try:
        if result.empty:
            raise Exception

        df_tuple = ('station', result)
        df_list.append(df_tuple)
    except:
        pass

    #camera
    camera_result = []
    try:
        for ID in stationID:
            query = "SELECT * FROM camera WHERE stationID = '{}'".format(ID)
            camera_result.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(stationID) > 1:
            result = pd.concat(camera_result, axis=0)
        else:
            result = camera_result[0]
        cameraID = result.get('id')
        modelID = result.get('modelID')
        lensmodelID = result.get('lensmodelID')
        li_IP = result.get('li_IP')
        blankIndex = [''] * len(result)
        result.index = blankIndex

        if not result.empty:
            df_tuple = ('camera', result)
            df_list.append(df_tuple)
    except:
        pass

    #cameramodel
    cameramodel_result = []
    try:
        for ID in modelID:
            query = "SELECT * FROM cameramodel WHERE id = '{}'".format(ID)
            cameramodel_result.append(pd.read_sql(query, con=connection))
        #account for multiple stations. Concatenate all results into 1 dataframe
        if len(modelID) > 1:
            result = pd.concat(cameramodel_result, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = cameramodel_result[0]

        if not result.empty:
            df_tuple = ('cameramodel', result)
            df_list.append(df_tuple)
    except:
        pass

    #lensmodel
    lensmodel_result = []
    try:
        for ID in lensmodelID:
            query = "SELECT * FROM lensmodel WHERE id = '{}'".format(ID)
            lensmodel_result.append(pd.read_sql(query, con=connection))
        if len(lensmodelID) > 1:
            result = pd.concat(lensmodel_result, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = lensmodel_result[0]

        if not result.empty:
            df_tuple = ('lensmodel', result)
            df_list.append(df_tuple)
    except:
        pass

    #ip
    li_IP_result = []
    try:
        for ID in li_IP:
            query = "SELECT * FROM ip WHERE id = '{}'".format(ID)
            li_IP_result.append(pd.read_sql(query, con=connection))
        if len(li_IP) > 1:
            result = pd.concat(li_IP_result, axis=0)
            result = result.drop_duplicates(subset='id', keep='first')
        else:
            result = li_IP_result[0]

        if not result.empty:
            df_tuple = ('ip', result)
            df_list.append(df_tuple)
    except:
        pass
    
    #gcp
    query = "SELECT * FROM gcp WHERE siteID = '{}'".format(siteID)
    result = get_formatted_result(query, connection)
    gcpID = result.get('id')
    try:
        if result.empty:
            raise Exception

        if not result.empty:
            df_tuple = ('gcp', result)
            df_list.append(df_tuple)
    except:
        pass

    #geometry
    geometry_result = []
    try:
        for ID in cameraID:
            query = "SELECT * FROM geometry WHERE cameraID = '{}'".format(ID)
            geometry_result.append(pd.read_sql(query, con=connection))
        if len(cameraID) > 1:
            result = pd.concat(geometry_result, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = geometry_result[0]
        geometrySequence = result.get('seq')

        if not result.empty:
            df_tuple = ('geometry', result)
            df_list.append(df_tuple)
    except:
        pass

    #usedgcp
    try:
        usedgcp_result = []
        for ID in gcpID:
            for seq in geometrySequence:
                query = "SELECT * FROM usedgcp WHERE gcpID = '{}' AND geometrySequence = {}".format(ID, seq)
                usedgcp_result.append(pd.read_sql(query, con=connection))
        if (len(gcpID) > 1) or (len(geometrySequence) > 1):
            result = pd.concat(usedgcp_result, axis=0)
            result = result.drop_duplicates(subset='seq', keep='first')
        else:
            result = usedgcp_result[0]

        if not result.empty:
            df_tuple = ('usedgcp', result)
            df_list.append(df_tuple)
    except:
        pass

    #list of dataframes to output
    output_list = []

    #add tables to csv files
    for df_tuple in df_list:
        table = df_tuple[0]
        df = df_tuple[1]

        output_list.append(df)

        filename = table + '.csv'
        folder_path = csv_path + '/sites/' + siteID + '/tables/'

        #if folders for saving csv does not exist, create directory
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        full_path = folder_path + filename
        df.to_csv(full_path, encoding='utf-8', index=False)

    print("Saved csv files to", folder_path)

    return output_list
        
         
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
        table_list = [None] * 9 
        for table in self.__dict__:
            if isinstance(self.__dict__[table], Table):

                if self.__dict__[table].table_name == 'site':
                    table_list[0] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'cameramodel':
                    table_list[1] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'lensmodel':
                    table_list[2] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'ip':
                    table_list[3] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'station':
                    table_list[4] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'gcp':
                    table_list[5] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'camera':
                    table_list[6] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'geometry':
                    table_list[7] = self.__dict__[table]

                elif self.__dict__[table].table_name == 'usedgcp':
                    table_list[8] = self.__dict__[table]

        for table in table_list:
            table.addTable2db()

    
class Table:
    '''
    This class represents a table in the CoastCamDB. The attributes of this class represent the columns in the table.
    This Table object can be added to a Site object as an attribute
    '''

    def __init__(self, table_name, database, connection, site=None):
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

        self.table_name = table_name
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

        print('TABLE:', self.table_name, '\n---------------------')
        for column in self.__dict__:
            #don't print unless it's a Column object
            if isinstance(self.__dict__[column], Column) or isinstance(self.__dict__[column], idColumn) or isinstance(self.__dict__[column], fkColumn):
                self.__dict__[column].showColumn()

    def getTableSeqs(self):
        '''
        Query the database and get all the entries in the seq column in this table
        '''

        query = "SELECT seq FROM {}".format(self.table_name)
        print(query)

        results = pd.read_sql(query, con=self.connection)
        results = results.get('seq')
        seq_list = []
        for result in results:
            seq_list.append(result)

        return seq_list


    def insertMultipleFK(self, returnSeqListFlag=False):
        '''
        Insert multiple foreign key values into the database at the same time. Used for the special case tables camera and usedgcp
        Inputs:
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seq_list. This
                                          seq_list is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seq_list (list) - optional output argument that is a list of seq values from the database
        '''

        if (self.table_name != 'camera') and (self.table_name != 'usedgcp'):
            print("table not eligible to insert multiple foreign key values")
            return

        fk_columns = []
        multi_fk_dict = {} #store fk columns and list of values
        for column in self.__dict__:
            
            #get list of fkColumn objects
            if isinstance(self.__dict__[column], fkColumn):
                fk_columns.append(self.__dict__[column])
                multi_fk_dict[self.__dict__[column].column_name] = self.__dict__[column].value_list

        #error checking
        try:
            if (self.table_name == 'camera') and (len(fk_columns) != 4):
                raise FKError("FKError: Incorrect number of foreign key columns attributed to this table")
            elif (self.table_name == 'usedgcp') and (len(fk_columns) != 2):
                raise FKError("FKError: Incorrect number of foreign key columns attributed to this table")
            
            for i in range(0, len(fk_columns)):
                if len(fk_columns[i - 1].value_list) != len(fk_columns[i].value_list):
                    raise FKError("FKError: foreign key column object value lists have unequal lengths")

                #check value of each foreign key
                for j in range(0, len(fk_columns[i].value_list)):
                    linked_table = fk_columns[i].get_linked_table(fk_columns[i].column_name)
                    
                    #special case: check that geometrySequence matches a seq value in geometry table. If not, set geometrySequence to most recently inserted seq value in geometry.
                    #this is because seq auto increments for each new insertion in geometry
                    if fk_columns[i].column_name == 'geometrySequence':

                        query = "SELECT seq FROM geometry WHERE seq = {}".format(fk_columns[i].value_list[j])
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
                            seq_query = "SELECT MAX(seq) FROM {}".format(linked_table)
                            result = pd.read_sql(seq_query, con=self.connection)
                            seq = result.get('MAX(seq)')[0]
                            fk_columns[i].value_list[j] = seq
                            print('new seq', fk_columns[i].value_list[j])
                            
                    else:
                        check_linked_key(fk_columns[i].value_list[j], fk_columns[i].column_name, linked_table, fk_columns[i].connection)
                    
        except Exception as e:
            sys.exit(e.message)

        #insert all foreign keys
        seq_list = []
        for j in range(0, len(fk_columns[0].value_list)):

            hasBlankID = False

            #can only insert one fk for per row with blank id value, so check for blank id and create placeholder id
            if self.table_name != 'usedgcp':
                hasBlankID = fk_columns[0].check_for_blank_id()
            
            if hasBlankID:

                placeholder_id = str(random.randint(0, 9999999))
                isDuplicate = fk_columns[0].check_duplicate_id(placeholder_id)
                
                while isDuplicate:
                    placeholder_id = str(random.randint(0, 9999999))
                    isDuplicate = fk_columns[0].check_duplicate_id(placeholder_id)

                #insert placeholder so there's no error for having blank id values when inserting fk
                query = "UPDATE {} SET id = '{}' WHERE id = ''".format(self.table_name, placeholder_id)

                print(query)
                cursor = self.connection.cursor()
                try:
                    cursor.execute(query)
                    self.connection.commit()
                except mysql.connector.Error as err:
                    print(err.msg) 

            if self.table_name == 'camera':
                
                query = "INSERT INTO camera (stationID, li_IP, lensmodelID, modelID) VALUES ('{}', '{}', '{}', '{}')".format(multi_fk_dict['stationID'][j], multi_fk_dict['modelID'][j], multi_fk_dict['lensmodelID'][j], multi_fk_dict['li_IP'][j]) 

            if self.table_name == 'usedgcp':

                query = "INSERT INTO usedgcp (gcpID, geometrySequence) VALUES ('{}', {})".format(multi_fk_dict['gcpID'][j], multi_fk_dict['geometrySequence'][j])

            print(query)

            cursor = self.connection.cursor()
            try:
                cursor.execute(query)
                self.connection.commit()
            except mysql.connector.Error as err:
                print(err.msg)

            #get the seq of the most recently added database entry. Since seq auto-increments most recent value is the max
            seq_query = "SELECT MAX(seq) FROM {}".format(self.table_name)
            result = pd.read_sql(seq_query, con=self.connection)
            seq = result.get('MAX(seq)')[0]
            seq_list.append(seq)

        #clear value_lists
        for column in fk_columns:
            column.value_list = []

        if returnSeqListFlag == True:
            return seq_list
        

    def insertTable2db(self):
        '''
        Insert all columns in this table to the database.
        '''
        
        fk_columns = []
        id_column = None
        other_columns = []
        for column in self.__dict__:

            if isinstance(self.__dict__[column], fkColumn):
                fk_columns.append(self.__dict__[column])

            elif isinstance(self.__dict__[column], idColumn):
                id_column = self.__dict__[column]

            elif isinstance(self.__dict__[column], Column):
                other_columns.append(self.__dict__[column])

        #vvv ADD FOREIGN KEY(S) TO TABLE vvv#
        fk_args = []
        returnSeqListFlag = False
        seq_list = []
        if len(fk_columns) > 1:
            print('mulitple fk')

            #check value list for all fk columns have the same length
            try:
                for i in range(0, len(fk_columns)):
                    if len(fk_columns[i - 1].value_list) != len(fk_columns[i].value_list):
                        raise FKError("FKError: foreign key column object value lists have unequal lengths")

            except Exception as e:
                sys.exit(e.message)
                
            for i in range(0, len(fk_columns[0].value_list)):

                fk_dict = {}
                fk_args.append(fk_dict)
                
                for column in fk_columns:

                    fk_args[i][column.column_name] = column.value_list[i]

            if (self.table_name == 'usedgcp') or (self.table_name == 'geometry'):
                returnSeqListFlag = True

            seq_list = self.insertMultipleFK(returnSeqListFlag=returnSeqListFlag)
            
        elif len(fk_columns) == 1:
            print('1 fk')

            for i in range(0, len(fk_columns[0].value_list)):

                fk_args.append({fk_columns[0].column_name : fk_columns[0].value_list[i]})

            if (self.table_name == 'usedgcp') or (self.table_name == 'geometry'):
                returnSeqListFlag = True

            seq_list = fk_columns[0].insert2db(returnSeqListFlag=returnSeqListFlag)
            
        else:
            print('no fk')
            pass

        print('SEQLIST', seq_list)

        #vvv ADD ID TO TABLE vvv#
        if id_column != None:
            print('has id column')
            id_list = id_column.value_list
            id_column.insert2db(fk_args=fk_args)

        else:
            print('no id column')
            pass

        #vvv ADD ALL OTHER COLUMNS vvv#
        if (self.table_name == 'geometry') or (self.table_name == 'usedgcp'):
            for i in range(0, len(other_columns)):
                other_columns[i].insert2db(fk_args=fk_args)
        else:
            for i in range(0, len(other_columns)):
                other_columns[i].insert2db(fk_args=fk_args)
                
    def disp_db_table(self):
        '''
        Query the database and display all rows for the associated table
        '''
        
        query = "SELECT * FROM {}".format(self.table_name)
        print(query)

        result = pd.read_sql(query, con=self.connection)
        df = pd.DataFrame(result)
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
            print(df)

    def tableFromDB(self, id_seq):
        '''
        Retrieve all columns in a row in a table given a unique id/seq. Return as a dictionary object.
        Inputs:
            id_seq (string or int) - id (string) or seq (int) value used to specify which row of the column to get the value from.
        Outputs:
            value_dict (dict) - dictonary of values retrieved from the row in the table. The key is column name, the value is the column
                                value.
        '''

        column_list = []
        for column in self.__dict__:
            if isinstance(self.__dict__[column], Column):
                column_list.append(self.__dict__[column])

        value_dict = {}
        for column in column_list:
            value = column.valueFromDB(id_seq)
            value_dict[column.column_name] = value

        return value_dict
        

class Column:
    '''
    This class represents a column in the CoastCamDB. This Column can be added to a Table object as an attribute.
    The value_list attribute acts as a queue of values to be added to the column in the DB.
    '''

    '''
    Foreign key (fk) dictionary. Necessary for inserting values into most tables.
    The key is the name of the table, and the value is a tuple where the 1st element is the table the fk links to
    and the 2nd element is the fk column. Every fk links to the 'id' column of the upper-level table, except for
    the fk geometrySequence in the 'usedgcp' table, which links to the 'seq' column in the 'geometry' table. If the
    table has multiple foreign keys, the value will be a list of tuples with one tuple per fk.
    '''
    fk_dict = {'station': ('site', 'siteID'),
               'camera': [('station', 'stationID'), ('cameramodel', 'modelID'), ('lensmodel', 'lensmodelID'), ('ip', 'li_IP')],
               'geometry': ('camera', 'cameraID'),
               'gcp': ('site', 'siteID'),
               'usedgcp': [('gcp', 'gcpID'), ('geometry', 'geometrySequence')] }

    '''list of all possible foregin key volumns'''
    fk_column_list = ['siteID', 'stationID', 'modelID', 'lensmodelID', 'li_IP', 'cameraID', 'siteID', 'gcpID', 'geometrySequence']

    def __init__(self, column_name, table, value=None):
        '''
        Initialize the Column object. Assign name and Table. Additionally, Append value to the column's value_list (queue).
        Inputs:
            column_name (string) - name of the Column
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
            table (Table) - Table object that this column is associated with. Represents the table the column is in in the DB.
        '''

        self.column_name = column_name
        self.table = table
        self.database = table.database

        self.value_list = []
        self.value_list.append(value)

        self.connection = table.connection


    def showColumn(self):
        '''
        Print Column object value
        '''
        print('COLUMN "{}" in TABLE "{}" ----- value(s) = {}'.format(self.column_name, self.table.table_name, [value for value in self.value_list]))


    def add2queue(self, value):
        '''
        Add a value to this Column's value_list (aka queue for data to be entered into DB)
        Inputs:
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
        Outputs:
            none
        '''

        if self.value_list[0] == None:
            self.value_list[0] = value
        else:
            self.value_list.append(value)

    def check_list_length(self, idseq_list):
        '''
        Check to make sure that the length of the list of ids or seqs is the same length as the value list of this Column object.
        Raise exception if the number of given id/seq values to insert into table isn't the same as the number of values to insert
        Inputs:
            idseq_list (list) - list of id or seq values corresponding to multiple values in this object's value list
        Outputs:
            none
        '''

        try:
            if len(idseq_list) != len(self.value_list):
                raise ListLengthError("ListLengthError: number of given id/seq values is not the same as the number of values to be inserted into table '{}'\nlength of id/seq list: {}\nlength of values: {}".format(self.table.table_name, len(idseq_list), len(self.value_list)))
    
        except Exception as e:
            sys.exit(e.message)

    def get_foreign_key(self):
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
            return self.fk_dict[self.table.table_name]
        
        except Exception:
            print("No foreign keys for table '{}'".format(self.table.table_name))
            return ''
            

    def get_linked_table(self, fk_column):
        '''
        Return the name of a foreign key (fk), return the name of the table that the fk links to.
        Inputs:
            fk_column (string) - name of the foreign key column in the this Column object's associated table
        Outputs:
            linked_table (string) - name of the table the fk links to
        '''

        if self.column_name not in self.fk_column_list:
            print('column does not link to another table')
            return ''

        if self.table.table_name == 'camera':

            if fk_column == 'stationID':

                linked_table = 'station'

            elif fk_column == 'modelID':

                linked_table = 'cameramodel'

            elif fk_column == 'lensmodelID':

                linked_table = 'lensmodel'

            elif fk_column == 'li_IP':

                linked_table = 'ip'

        elif self.table.table_name == 'usedgcp':

            if fk_column == 'gcpID':

                linked_table = 'gcp'

            elif fk_column == 'geometrySequence':

                linked_table = 'geometry'

        else:
            linked_table = self.fk_dict[self.table.table_name][0]

        return linked_table

    def check_foreign_key(self, fk_column, fk_value):
        '''
        Check that the foreign key is valid and exists in the same table as this column
        Inputs:
            fk_column (string) - name of the foregin key column to be checked
            fk_value (string or int) - id/seq value of the foreign key
        Outputs:
            none
        '''

        #check that foreign key is valid and exists
        try:
            if fk_column not in self.fk_column_list:
                raise FKError("FKError: invalid foreign key '{}'".format(fk_column))

            if isinstance(fk_value, str):
                query = "SELECT {} FROM {} WHERE {} = '{}'".format(fk_column, self.table.table_name, fk_column, fk_value)
                #ex: select modelID from camera where modelID = 'XXXXX'

            elif isinstance(fk_value, int):
                query = "SELECT {} FROM {} WHERE {} = {}".format(fk_column, self.table.table_name, fk_column, fk_value)
                #ex: select geometrySequence from usedgcp where geometrySequence = 1
                
            print(query)

            result = pd.read_sql(query, con=self.connection)
            
            #NULL return, no seq/id found
            if result.size == 0:
                raise NoIDError("NoSeqError: No foreign_key '{}' with value '{}' found in table '{}'".format(fk_column, fk_value, self.table.table_name))
            
        except Exception as e:
            sys.exit(e.message)


    def fk_from_id(self, ID):
        '''
        Given an ID value in a database table, find the corresponding foreign key value (same row).
        Inputs:
            ID (string) - id column value
        Outputs:
            fk_column (string) - name of the foreign key column in the table
            fk_value (string) - foreign key value for corresponding id
        '''

        fk_pair = self.get_foreign_key()

        #for tables that have multiple fk columns, fk_pair is a list of tuples
        if isinstance(fk_pair, list):
            #only need 1 fk value  for purposes of inserting values into database
            fk_column = fk_pair[0][1]

        #table only has 1 foreign key column, fk_pair is a tuple
        else:
            print(fk_pair)
            fk_column = fk_pair[1]
            
        check_id(ID, self.table.table_name, self.connection)
        
        query = "SELECT {} FROM {} WHERE id = '{}'".format(fk_column, self.table.table_name, ID)
        print(query)

        result = pd.read_sql(query, con=self.connection)
        fk_value = result.get(fk_column)[0]
        return fk_column, fk_value
    

    def fk_from_seq(self, seq):
        '''
        Given a seq value in a database table, find the corresponding foreign key value (same row).
        Inputs:
            seq (int) - seq column value
        Outputs:
            fk_column (string) - name of the foreign key column in the table
            fk_value (int) - foreign key value for corresponding seq
        '''

        fk_pair = self.get_foreign_key()

        #for tables that have multiple fk columns, fk_pair is a list of tuples
        if isinstance(fk_pair, list):
            #only need 1 fk value  for purposes of inserting values into database
            fk_column = fk_pair[0][1]

        #table only has 1 foreign key column, fk_pair is a tuple
        else:
            fk_column = fk_pair[1]
            
        check_seq(seq, self.table.table_name, self.connection)
        
        query = "SELECT {} FROM {} WHERE seq = {}".format(fk_column, self.table.table_name, seq)
        print(query)

        result = pd.read_sql(query, con=self.connection)
        fk_value = result.get(fk_column)[0]
        return fk_column, fk_value
    

    def check_duplicate_id(self, ID):
        '''
        check if id already exists in the column's associated table. Designed to be used with the random placeholder name.
        Inputs:
            ID (string) - ID to be checked
        Outputs:
            isDuplicate (boolean) - true/false variable stating whether or not the id is a duplicate
        '''

        query = "SELECT * FROM {} WHERE id = '{}'".format(self.table.table_name, ID)

        result = pd.read_sql(query, con=self.connection)

        if result.size == 0:
            isDuplicate = False
        else:
            isDuplicate = True

        return isDuplicate
    

    def check_for_blank_id(self):
        '''
        Check if any rows in the column's associated table have a blank id value. Used for inserting new foreign keys.
        Can only have one blank id per table or else inserting a new fk will fail.
        Inputs:
            none
        Outputs:
            hasBlankID (boolean) - true or flase result whether id is blank
        '''

        query = "SELECT * FROM {} WHERE id = ''".format(self.table.table_name)
        
        result = pd.read_sql(query, con=self.connection)
            
        if result.size == 0:
            hasBlankID = False
        else:
            hasBlankID = True

        return hasBlankID


    def input_id_seq(self, value):
        '''
        Given an existing value in a column, prompt the user to select an id/seq value. There are two modes: 'insert' and 'update'.
        In 'insert' mode, no value argument is needed and all id/seq values for the table aare displayed to user to select from.
        In 'update' mode, the value is used in the query to get id/seq associated with that value.
        Inputs:
            value (string) - exisitng value in the table used to search the table
        Outputs:
            idseq (string or int) - id (string) or seq (int) that the user selects
        '''

        idseq = ''

        if (self.table.table_name == 'usedgcp') or (self.table.table_name == 'geometry'):
            key = "seq"
            #account for NULL values
            if value == 'None':
                query = "SELECT seq, {} FROM {} WHERE {} IS NULL".format(self.column_name, self.table.table_name, self.column_name)
            else:
                query = "SELECT seq, {} FROM {} WHERE {} = '{}'".format(self.column_name, self.table.table_name, self.column_name, value)
        else:
            key = "id"
            if value == 'None':
                query = "SELECT id, {} FROM {} WHERE {} IS NULL".format(self.column_name, self.table.table_name, self.column_name)
            else:
                query = "SELECT id, {} FROM {} WHERE {} = '{}'".format(self.column_name, self.table.table_name, self.column_name, value)

        result = get_formatted_result(query, self.connection)
        print("Please enter a {} listed from the values below.".format(key))
        print("vv  Available options are listed below vv")
        print(result)

        avail_idseq = []
        for identifier in result.get(key):
            avail_idseq.append(str(identifier))

        isGoodIDSeq = False
        while not isGoodIDSeq:
            
            idseq = input("~~~Enter an id/seq value: ")

            if idseq.strip() == 'quit':
                quit()

            if idseq in avail_idseq:
                isGoodIDSeq = True
                #special cases to return seq as int for usedgcp and geometry tables
                if (self.table.table_name == 'usedgcp') or (self.table.table_name == 'geometry'):
                    idseq = int(idseq)
                return idseq
            else:
                print("Invalid id/seq value. Please try again.")


    def get_fk_args(self):
        '''
        Get fk args for this column--used for inserting/updating this column with the command line interface.
        Inputs:
            none
        Outputs:
            fk_args (list) - list of dictionaries used for foreign key arguments. Each dictionary will correspond to an
                             id being inserted into the table. Only one key/value of an fk column/value pair per id is actually
                             needed in each dictionary. The key will be the fk column name and the value will be the column value.
        '''
        fk_args = []

        if (self.table.table_name == 'station') or (self.table.table_name == 'gcp'):
            key = 'siteID'

            try:
                #if empty foreign key columns, throw error
                if self.table.table_name == 'station':
                    query = "SELECT siteID FROM station"
                else:
                    query = "SELECT siteID FROM gcp"

                result = pd.read_sql(query, con=self.connection)
                if result.size == 0:
                    raise FKError(message="no foreign key values in table '{}'".format(self.table.table_name))
            except FKError as e:
                sys.exit(e.message)
            
        elif self.table.table_name == 'camera':
            key = 'stationID'

            try:
                #check if stationID blank in table
                query = "SELECT stationID FROM camera"
                result = pd.read_sql(query, con=self.connection)
                if result.size == 0:
                    key = 'cameramodelID'

                    #need to check if cameramodelID is blank too
                    query = "SELECT cameramodelID FROM camera"
                    result = pd.read_sql(query, con=self.connection)
                    if result.size == 0:
                        key = 'lensmodelID'

                        #need to check if lensmodelID is blank too
                        query = "SELECT lensmodelID FROM camera"
                        result = pd.read_sql(query, con=self.connection)
                        if result.size == 0:
                            key = 'li_IP'

                            #li_IP is last line of defense. If empty, throw error
                            query = "SELECT li_IP FROM camera"
                            result = pd.read_sql(query, con=self.connection)
                            if result.size == 0:
                                raise FKError(message="no foreign key values in table 'camera'")
            except FKError as e:
                sys.exit(e.message)
                            
        elif self.table.table_name == 'geometry':
            key = 'cameraID'

            try:
                #if empty foregin key columns, throw error
                query = "SELECT cameraID FROM geometry"
                result = pd.read_sql(query, con=self.connection)
                if result.size == 0:
                    raise FKError(message="no foreign key values in table 'geometry'")
            except FKError as e:
                sys.exit(e.message)
                
        elif self.table.table_name == 'usedgcp':
            key = 'gcpID'

            try:
                #check if gcpID blank in table
                query = "SELECT gcpID FROM usedgcp"
                result = pd.read_sql(query, con=self.connection)
                if result.size == 0:
                    key = 'geometrySequence'

                    #need to check if geometrySequence is blank too
                    query = "SELECT geometrySequence FROM usedgcp"
                    result = pd.read_sql(query, con=self.connection)
                    if result.size == 0:
                        raise FKError(message="no foreign key values in table 'usedgcp'")
            except FKError as e:
                sys.exit(e.message)

        #get available foreign key options for user to select
        query = "SELECT {} FROM {} ".format(key, self.table.table_name)
        result = get_formatted_result(query, self.connection)
        result = result.drop_duplicates(subset=key, keep='first')
        result_str = result.to_string(header=False)
        print("Please enter a {} listed from the values below.".format(key))
        print("vv  Available options are listed below vv")
        print(result_str)

        avail_id = []
        for ID in result.get(key):
            avail_id.append(ID)

        isGoodID = False
        while not isGoodID:

            fk_value = input("~~~Enter a {}: ".format(key))

            if fk_value.strip() == 'quit':
                quit()
                
            if fk_value.strip() in avail_id:
                isGoodID = True
                fk_args.append({key : fk_value})
            else:
                print('Invalid {}, please try again.\n'.format(key))

        query = "SELECT {} FROM {} WHERE {} = '{}'".format(self.column_name, self.table.table_name, key, fk_value)
        result = get_formatted_result(query, self.connection)
        result_str = result.to_string(header=False)
        print("\nCurrent value(s) in {} for {} where {} = {}".format(self.table.table_name, self.column_name, key, fk_value))
        print(result_str)

        return fk_args       


    def check_blank_value(self, idseq):
        '''
        Given an id/seq value, check if the value is blank for this column for the given row.
        Inputs:
            idseq (string) - id or seq value used to specify the row
        Outputs:
            hasBlankValue (bool) - True or False value describing if there is a blank value for the column in the specified row
        '''

        hasBlankValue = False
        
        if (self.table.table_name == 'geometry') or (self.table.table_name == 'usedgcp'):
            query = "SELECT {} FROM {} WHERE seq = {}".format(self.column_name, self.table.table_name, idseq)
        else:
            query = "SELECT {} FROM {} WHERE id = '{}'".format(self.column_name, self.table.table_name, idseq)

        result = pd.read_sql(query, con=self.connection)
        for res in result.get(self.column_name):
            if res == '':
                hasBlankValue = True
                print('BLANK VALUE')

        return hasBlankValue


    def insert2db(self, fk_args=[], returnSeqListFlag=False):
        '''
        insert new value into for this column into the database. Depending on the table, specify a foreign key
        Inserts:
            fk_args (list) - list of dictionaries used for foreign key arguments. Used when this function calls insertNewID().
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seq_list. This
                                          seq_list is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seq_list (list) - optional output argument that is a list of seq values from the database
        '''

        try:

            if len(self.value_list) == 0:
                raise EmptyValueError(message="EmptyValueError: Empty value list for column '{}'".format(self.column_name))
        except Exception as e:
            sys.exit(e.message)


        #if column is foreign key, insert using the special subclass function for fk instead
        if isinstance(self, fkColumn):
            
            seq_list = self.insertNewFK(returnSeqListFlag)
            return seq_list
            
        #if column is id, use subclass function
        elif isinstance(self, idColumn):

            self.insertNewID(fk_args)

        else:

            fk = self.get_foreign_key()

            #does not need foreign key
            if fk == '':

                for i, value in enumerate(self.value_list):
                    
                    try:
                        if isinstance(value, str):
                            
                            query = "INSERT INTO {} ({}) VALUES ('{}')".format(self.table.table_name, self.column_name, value)

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "INSERT INTO {} ({}) VALUES ({})".format(self.table.table_name, self.column_name, value)

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
            elif (self.table.table_name == 'usedgcp') or (self.table.table_name == 'geometry'):                    

                for i, value in enumerate(self.value_list):

                    for dict_key, dict_value in fk_args[i].items():
                        fk_column = dict_key
                        fk_value = dict_value

                    #don't need to check for blank id. Seq updates automatically with everynew insertion

                    if fk_column == 'geometrySequence':
                        linked_table = 'geometry'
                    elif fk_column == 'gcpID':
                        linked_table = 'gcp'
                    elif fk_column == 'cameraID':
                        linked_table = 'camera'

                    check_linked_key(fk_value, fk_column, linked_table, self.connection)
                    
                    try:
                        if isinstance(value, str):
                            query = "INSERT INTO {} ({}, {}) VALUES ('{}', '{}')".format(self.table.table_name, fk_column, self.column_name, fk_value, value)

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "INSERT INTO {} ({}, {}) VALUES ('{}', {})".format(self.table.table_name, fk_column, self.column_name, fk_value, value)

                        elif isinstance(value, np.ndarray):
                            blob = np2text(value)
                            query = query = "INSERT INTO {} ({}, {}) VALUES ('{}', '{}')".format(self.table.table_name, fk_column, self.column_name, fk_value, blob)
                        
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

                for i, value in enumerate(self.value_list):

                    for dict_key, dict_value in fk_args[i].items():
                        fk_column = dict_key
                        fk_value = dict_value

                    #check for blank ID correpsonding to fk arg
                    query = "SELECT id FROM {} WHERE {} = '{}'".format(self.table.table_name, fk_column, fk_value)
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
                                query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' AND id = ''".format(self.table.table_name, self.column_name, value, fk_column, fk_value)
                            elif isinstance(value, int) or isinstance(value, float):
                                query = "UPDATE {} SET {} = {} WHERE {} = '{}' AND id = ''".format(self.table.table_name, self.column_name, value, fk_column, fk_value)
                            elif isinstance(value, np.ndarray):
                                blob = np2text(value)
                                query = query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' AND id = ''".format(self.table.table_name, self.column_name, blob, fk_column, fk_value)
                            else:
                                raise TypeError
                        else:
                            if isinstance(value, str):
                                query = "INSERT INTO {} ({}, {}) VALUES ('{}', '{}')".format(self.table.table_name, fk_column, self.column_name, fk_value, value)

                            elif isinstance(value, int) or isinstance(value, float):
                                query = "INSERT INTO {} ({}, {}) VALUES ('{}', {})".format(self.table.table_name, fk_column, self.column_name, fk_value, value)

                            elif isinstance(value, np.ndarray):
                                blob = np2text(value)
                                query = "INSERT INTO {} ({}, {') VALUES ('{}', '{}')".format(self.table.table_name, fk_column, self.column_name, fk_value, blob)
                            
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
        self.value_list = []
        

    def update2db(self, old_value, id_list=[], seq_list=[], fk_args=[], returnSeqListFlag=False):
        '''
        Update a value in for this column in the database. Specify the row using a value for id or seq
        Inserts:
            id_list (list) - list of id (string) values. Used if there are multiple values in self.value_list to be inserted.
                             The id values are used for specifying specifying the id(s) of the associated row(s) in the DB that the value(s)
                             will be inserted into. Used with the SQL 'WHERE' clause
            seq_list  (list) - list of seq (int) values. Used if there are multiple values in self.value_list to be inserted.
                               The id values are used for specifying specifying the seq(s) of the associated row(s) in the DB that the value(s)
                               will be inserted into. Used with the SQL 'WHERE' clause. seq column only used with the geometry and
                               usedgcp tables.
            fk_args (list) - list of dictionaries used for foreign key arguments. Used when this function calls insertNewID().
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seq_list. This
                                          seq_list is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seq_list (list) - optional output argument that is a list of seq values from the database
        '''

        try:

            if len(self.value_list) == 0:
                raise EmptyValueError(message="EmptyValueError: Empty value list for column '{}'".format(self.column_name))
        except Exception as e:
            sys.exit(e.message)
            
        #if column is id, use subclass function
        if isinstance(self, idColumn):
            
            self.updateID(old_value)

        else:

            fk = self.get_foreign_key()
            
            if fk == '':
                #does not need foreign key
                self.check_list_length(id_list)

                for i, value in enumerate(self.value_list):

                    check_id(id_list[i], self.table.table_name, self.connection)
                    
                    try:
                        if isinstance(value, str):
                            query = "UPDATE {} SET {} = '{}' WHERE id = '{}'".format(self.table.table_name, self.column_name, value, id_list[i])

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "UPDATE {} SET {} = {} WHERE id = '{}'".format(self.table.table_name, self.column_name, value, id_list[i])

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
            elif (self.table.table_name == 'usedgcp') or (self.table.table_name == 'geometry'):                    

                self.check_list_length(seq_list)

                for i, value in enumerate(self.value_list):

                    #don't need to check_seq because that is already done in fk_from_seq
                    fk_column, fk_value = self.fk_from_seq(seq_list[i])
                    
                    try:
                        if isinstance(value, str):
                            query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and seq = {}".format(self.table.table_name, self.column_name, value, fk_column, fk_value, seq_list[i])

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "UPDATE {} SET {} = {} WHERE {} = '{}' and seq  = {}".format(self.table.table_name, self.column_name, value, fk_column, fk_value, seq_list[i])

                        elif isinstance(value, np.ndarray):
                            blob = np2text(value)
                            query = query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and seq = {}".format(self.table.table_name, self.column_name, blob, fk_column, fk_value, seq_list[i])
                        
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

                self.check_list_length(id_list)

                for i, value in enumerate(self.value_list):

                    #don't need to check_seq because that is already done in fk_from_seq
                    fk_column, fk_value = self.fk_from_id(id_list[i])
                    
                    try:
                        if isinstance(value, str):
                            query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and id = '{}'".format(self.table.table_name, self.column_name, value, fk_column, fk_value, id_list[i])

                        elif isinstance(value, int) or isinstance(value, float):
                            query = "UPDATE {} SET {} = {} WHERE {} = '{}' and id = '{}'".format(self.table.table_name, self.column_name, value, fk_column, fk_value, id_list[i])

                        elif isinstance(value, np.ndarray):
                            blob = np2text(value)
                            query = query = "UPDATE {} SET {} = '{}' WHERE {} = '{}' and id = '{}'".format(self.table.table_name, self.column_name, blob, fk_column, fk_value, id_list[i])
                        
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
        self.value_list = []


    def valueFromDB(self, id_seq):
        '''
        Retrieve the value of the column from the database given a specfified id or seq value.
        Inputs:
            id_seq (string or int) - id (string) or seq (int) value used to specify which row of the column to get the value from.
        Outputs:
            value (object) - value of the given column in the same row as the specified id/seq. Value type depends on the value
                             type in the database. Can be string, int, double.
        '''

        if (self.column_name == 'K') or (self.column_name == 'm') or (self.column_name == 'kc'):
            if isinstance(id_seq, str):
                result = db2np(connection=self.connection, table=self.table.table_name, column=self.column_name, ID=id_seq)

            elif isinstance(id_seq, int):
                result = db2np(connection=self.connection, table=self.table.table_name, column=self.column_name, seq=id_seq)

        else:
            if isinstance(id_seq, str):   
                check_id(id_seq, self.table.table_name, self.connection)
                query = "SELECT {} FROM {} WHERE id = '{}'".format(self.column_name, self.table.table_name, id_seq)

            elif isinstance(id_seq, int):
                check_seq(id_seq, self.table.table_name, self.connection)
                query = "SELECT {} FROM {} WHERE seq = {}".format(self.column_name, self.table.table_name, id_seq)

            result = pd.read_sql(query, con=self.connection)
            result = result.get(self.column_name)[0]
            
        return result
  


class idColumn(Column):
    '''
    Defines the class related to the id column in the database. This is a subclass of the Column class. ids are primary keys
    in the database so they have special properties and usually act as points of reference for inserting data into the database.
    '''

    def __init__(self, table, value=None):
        '''
        Initialize the Column object. Assign name and Table. Additionally, Append value to the column's value_list (queue).
        Inputs:
            column_name (string) - name of the Column
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
            table (Table) - Table object that this column is associated with. Represents the table the column is in in the DB.
        '''

        Column.__init__(self, column_name='id', table=table, value=value)


    def insertNewID(self, fk_args = []):
        '''
        Insert new id column value(s) into the database. USes foreign keys where necessary.
        Inputs:
            fk_args (list) - list of dictionaries used for foreign key arguments. Each dictionary will correspond to an
                             id being inserted into the table. Only one key/value of an fk column/value pair per id is actually
                             needed in each dictionary. The key will be the fk column name and the value will be the column value.
        Outputs:
            none
        '''

        fk = self.get_foreign_key()
            
        if fk != '':
            #needs foreign key

            try:
                if len(fk_args) == 0:
                    raise FKError("FKError: foreign keys required but no foreign keys passed as arguments")

                elif len(fk_args) != len(self.value_list):
                    raise FKError("FKError: Incorrect number of foreign keys for number of values to be inserted")

            except Exception as e:
                sys.exit(e.message)

        i = 0
        for ID in self.value_list:

            isDuplicate = self.check_duplicate_id(ID)

            if isDuplicate:
                print("Duplicate id value. Value not inserted.")

            else:
                if len(fk_args) > 0:
                    fks = fk_args[i]

                    for fk_column in fks:
                        #check for valid foreign key value. Don't need to check linked table because foreign key in table
                        #already needs to have same value as id/seq in linked table
                        value = fks[fk_column]
                        self.check_foreign_key(fk_column, value)

                    #If function makes it here, foreign keys/values don't throw errors. Only need one fk for query   
                    #check for blank id. If blank ID, replace with blankid (that has same fk_args) instead of insertiung new value
                    hasBlankID = self.check_for_blank_id()
                    if hasBlankID:
                        query = "UPDATE {} SET id = '{}' WHERE {} = '{}' and id = ''".format(self.table.table_name, ID, fk_column, fks[fk_column])
                        #ex: "UPDATE camera SET id = '1234567' WHERE stationID = '1234567' and id = ''
                    else:
                        query = "INSERT INTO {} ({}, id) VALUES ('{}', '{}')".format(self.table.table_name, fk_column, fks[fk_column], ID)
                        #ex: "INSERT INTO camera (stationID, id) VALUES ('statID', 'camID')

                else:
                    query = "INSERT INTO {} (id) VALUES ('{}')".format(self.table.table_name, ID)
                    #ex: INSERT INTO site (id) VALUES ('EXXXXXX')
                    
                print(query)     
                cursor = self.connection.cursor()
                try:
                    cursor.execute(query)
                    self.connection.commit()
                except mysql.connector.Error as err:
                    print(err.msg)
                    
            i = i + 1
            

    def updateID(self, old_id):
        '''
        Update exsiting id column value in the database. Uses foregin keys where necessary.
        Inputs:
            old_id (string) - old id value to be updated (replaced)
        Outputs:
            none
        '''

        i = 0
        for ID in self.value_list:

            isDuplicate = self.check_duplicate_id(ID)

            if isDuplicate:
                print("Duplicate id value. Value not updated.")

            else:
                query = "UPDATE {} SET id = '{}' WHERE id = '{}'".format(self.table.table_name, ID, old_id)
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

    def __init__(self, column_name, table, value=None):
        '''
        Initialize the Column object. Assign name and Table. Additionally, Append value to the column's value_list (queue).
        Inputs:
            column_name (string) - name of the Column
            value - Value to be inserted in the column in the database. Can be one of a number of possible data types.
            table (Table) - Table object that this column is associated with. Represents the table the column is in in the DB.
        '''

        Column.__init__(self, column_name=column_name, table=table, value=value)

        #assign variable saying what table this fk links to
        linked_table = self.get_linked_table(column_name)
        self.linked_table = linked_table

    def display_linked_key(self):
        '''
        Display the values for the corresponding id/seq column in this Column's linked table
        Inputs:
            none
        Outputs:
            none
        '''

        print("Below are the valid values for {}".format(self.column_name))

        #special case for geometrySequence foreign key
        if self.linked_table == 'geometry':
            query = "SELECT seq FROM geometry"
        else:
            query = "SELECT id FROM {}".format(self.linked_table)

        result = get_formatted_result(query, self.connection)
        result_str = result.to_string(header=False)
        print(result_str)

    def insertNewFK(self, returnSeqListFlag=False):
        '''
        Insert new value(s) for this foreign key column into the database.
        Inputs:
            returnSeqListFlag (boolean) - Optional argument specifying whether or not the function will return a seq_list. This
                                          seq_list is a list of seq values from the database associated with each new foreign key
                                          inserted into the database
        Outputs:
            seq_list (list) - optional output argument that is a list of seq values from the database
        '''

##        #special case for tables with multiple foreign keys
##        if (self.table.table_name == 'camera') or (self.table.table_name == 'usedgcp'):
##            self.table.insertMultipleFK()
##
##        else:
        seq_list = []
        for value in self.value_list:

            #can only insert one fk for per row with blank id value, so check for blank id and create placeholder id
            if (self.table.table_name != 'geometry') and (self.table.table_name != 'usedgcp'):
                hasBlankID = self.check_for_blank_id()

                if hasBlankID:

                    placeholder_id = str(random.randint(0, 9999999))
                    isDuplicate = self.check_duplicate_id(placeholder_id)
                    
                    while isDuplicate:
                        placeholder_id = str(random.randint(0, 9999999))
                        isDuplicate = self.check_duplicate_id(placeholder_id)

                    #insert placeholder so there's no error for having blank id values when inserting fk
                    query = "UPDATE {} SET id = '{}' WHERE id = ''".format(self.table.table_name, placeholder_id)

                    print(query)
                    cursor = self.connection.cursor()
                    try:
                        cursor.execute(query)
                        self.connection.commit()
                    except mysql.connector.Error as err:
                        print(err.msg)                    

            check_linked_key(value, self.column_name, self.linked_table, self.connection)

            #special case because geometrySequence is only fk that links to a 'seq' column
            if self.column_name == 'geometrySequence':

                query = "INSERT INTO usedgcp (geometrySequence) VALUES ({})".format(value)

            else:
                
                query = "INSERT INTO {} ({}) VALUES ('{}')".format(self.table.table_name, self.column_name, value)

            print(query)

            cursor = self.connection.cursor()
            try:
                cursor.execute(query)
                self.connection.commit()
            except mysql.connector.Error as err:
                print(type(err))
                print(err.msg)

            #get the seq of the most recently added database entry. Since seq auto-increments most recent value is the max
            seq_query = "SELECT MAX(seq) FROM {}".format(self.table.table_name)
            result = pd.read_sql(seq_query, con=self.connection)
            seq = result.get('MAX(seq)')[0]
            seq_list.append(seq)

        if returnSeqListFlag == True:
            return seq_list


class Parameter:
    '''
    Class designed to hold parameters used for image rectification: extrinsics, intrinsics, metadata, and local_origin.
    '''

    def __init__(self, extrinsics=None, intrinsics=None, metadata=None, local_origin=None):
        
        self.extrinsics = extrinsics #list
        self.intrinsics = intrinsics #list
        self.metadata = metadata #list
        self.local_origin = local_origin #dict
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
