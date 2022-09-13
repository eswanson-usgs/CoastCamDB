'''
The purpose of this script is to create the YAML calibration files--necessary to perform rectification--from values in the
CoastCamDB. Given a site ID and station ID as input on the command line, this script queries the database, creates dictionaries of
values, and then creates the YAML calibration files. There will be 1 local origin file for the station. There will be 1 metadata file,
1 intrinsic file, and 1 extrinsic file per camera at the station.
'''

##### IMPORTS #####
from coastcamDBfuncs import *
import datetime
import mysql.connector


##### MAIN #####
if __name__ == "__main__":
    
    filepath = sys.argv[1]
    stationID = sys.argv[2]

    connection = DBConnectCSV(filepath)

    query = "SELECT * FROM camera WHERE stationID = '{}'".format(stationID)

    result = pd.read_sql(query, con=connection)
    camera_list = []
    for ID in result.get('id'):
        camera_list.append(ID)

    #lists of dictionaries. One dictionary in every list for each camera.
    metadata_dict_list = []
    extrinsic_dict_list = []
    intrinsic_dict_list = []

    #need to query station table before going through camera list
    query = "SELECT shortName, siteID, name FROM station WHERE id = '{}'".format(stationID)
    result = pd.read_sql(query, con=connection)
    #station short name for YAML file name formatting. 
    short_name = result.get('shortName')[0]
    #siteID for querying site table 
    siteID = result.get('siteID')[0]
    #name for metadata dict
    name = result.get('name')[0]

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


    ###CREATE DESCRIPTOR DICTS###
    metadata_descriptor_dict = {}
    metadata_descriptor_dict['name'] = 'name of the camera station'
    metadata_descriptor_dict['serial_number'] = 'camera serial number'
    metadata_descriptor_dict['camera_number'] = 'camera number for the corresponding station'
    metadata_descriptor_dict['calibration_date'] = 'date when the camera was calibrated'
    metadata_descriptor_dict['coordinate_system'] = 'coordinate system for extrinsic parameters. Either "geo" or "xyz"'
    
    extrinsic_descriptor_dict = {}
    extrinsic_descriptor_dict['x'] = 'x location of camera'
    extrinsic_descriptor_dict['y'] = 'y location of camera'
    extrinsic_descriptor_dict['z'] = 'z location of camera'
    extrinsic_descriptor_dict['a'] = 'camera azimuth orientation'
    extrinsic_descriptor_dict['t'] = 'camera tilt orientation'
    extrinsic_descriptor_dict['r'] = 'camera roll orientation'

    intrinsic_descriptor_dict = {}
    intrinsic_descriptor_dict['NU'] = 'number of pixel columns'
    intrinsic_descriptor_dict['NV'] = 'number of pixel rows'
    intrinsic_descriptor_dict['c0U'] = 'first component of the principal point'
    intrinsic_descriptor_dict['c0V'] = 'second component of the principal point'
    intrinsic_descriptor_dict['c0U'] = 'first component of the principal point'
    intrinsic_descriptor_dict['fx'] = 'x component of the focal length (pixels)'
    intrinsic_descriptor_dict['fy'] = 'y component of the focal length (pixels)'
    intrinsic_descriptor_dict['d1'] = 'first radial distortion coefficient'
    intrinsic_descriptor_dict['d2'] = 'second radial distortion coefficient'
    intrinsic_descriptor_dict['d3'] = 'third radial distortion coefficient'
    intrinsic_descriptor_dict['t1'] = 'first tangential distortion coefficient'
    intrinsic_descriptor_dict['t2'] = 'second tangential distortion coefficient'

    local_origin_descriptor_dict = {}
    local_origin_descriptor_dict['x'] = 'x location of site origin'
    local_origin_descriptor_dict['y'] = 'y location of site origin'
    local_origin_descriptor_dict['angd'] = 'orientation of the local grid'


    #write to YAML files
    for i in range(0, len(camera_list)):

        path = './yaml_files'
        camera_number = metadata_dict_list[i]['camera_number']

        #extrinsics
        file_name = short_name.replace(' ', '_') + '_C' + str(camera_number) + '_extr'
        DBdict2yaml(extrinsic_dict_list[i], extrinsic_descriptor_dict, path, file_name)

        #intrinsics
        file_name = short_name.replace(' ', '_') + '_C' + str(camera_number) + '_intr'
        DBdict2yaml(intrinsic_dict_list[i], intrinsic_descriptor_dict, path, file_name)

        #metadata
        file_name = short_name.replace(' ', '_') + '_C' + str(camera_number) + '_metadata'
        DBdict2yaml(metadata_dict_list[i], metadata_descriptor_dict, path, file_name)

    #local origin
    file_name = short_name.replace(' ', '_') + '_localOrigin'
    DBdict2yaml(local_origin_dict, local_origin_descriptor_dict, path, file_name)

    

    
    
    

    

    

