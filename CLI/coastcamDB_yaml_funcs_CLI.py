##### IMPORTS #####
from coastcamDBfuncs_CLI import *
import mysql.connector

##### FUNCTIONS #####
def DBdict2yaml(dictionary, descriptor_dict, path, file_name):
    '''
    Create YAML file from a  dictionary.
    Inputs:
        dictionary (dict) - dictionary object used to create YAML file
        descriptor_dict (dict) - dictionary of descriptors for fields from the DB
        path (string) - path to directory where YAML files will be saved
        file_name (string) - filename for the new YAML file, ".yaml" not included
    Outputs:
        none, but YAML files are created
    '''

    filepath = path+"/"+file_name+".yaml"
        
    with open(filepath, 'w') as file:
        for field in dictionary:
            #manually write in YAML formatting. YAML dump sometimes writes out of order
            file.write(field + ': ' + str(dictionary[field]) + '\n')
        
        #leave comments in yaml with text descriptions of the fields
        #ex. #x - x location of camera
        for field in dictionary:
            file.write('#' + field + ' - ' + descriptor_dict[field]+ '\n')

    return


def createYAMLfiles(stationID, output_path, connection):
    '''
    Create YAML files given a stationID.
    Inputs:
        stationID (string) - specifies the "id" field for the "station" table, which is also the "stationID" field in the
                             "camera" table
        output_path (string) - specifies the folder where the YAML files will be saved to
        connection (pymysql.connections.Connection object) - Object representing connection to DB
    Outputs:
        none (but YAML files are created)
    '''

    extrinsics, intrinsics, metadata, local_origin = getParameterDicts(stationID, connection)

    query = "SELECT * FROM camera WHERE stationID = '{}'".format(stationID)
    result = pd.read_sql(query, con=connection)
    camera_list = []
    for ID in result.get('id'):
        camera_list.append(ID)

    #need to query station table before going through camera list
    query = "SELECT shortName FROM station WHERE id = '{}'".format(stationID)
    result = pd.read_sql(query, con=connection)
    #station short name for YAML file name formatting. 
    short_name = result.get('shortName')[0]

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
        camera_number = metadata[i]['camera_number']

        #extrinsics
        file_name = short_name.replace(' ', '_') + '_C' + str(camera_number) + '_extr'
        DBdict2yaml(extrinsics[i], extrinsic_descriptor_dict, output_path, file_name)

        #intrinsics
        file_name = short_name.replace(' ', '_') + '_C' + str(camera_number) + '_intr'
        DBdict2yaml(intrinsics[i], intrinsic_descriptor_dict, output_path, file_name)

        #metadata
        file_name = short_name.replace(' ', '_') + '_C' + str(camera_number) + '_metadata'
        DBdict2yaml(metadata[i], metadata_descriptor_dict, output_path, file_name)

    #local origin
    file_name = short_name.replace(' ', '_') + '_localOrigin'
    DBdict2yaml(local_origin, local_origin_descriptor_dict, output_path, file_name)

    return


if __name__ == "__main__":
    print('hi')

    filepath = "C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv"
    conn = DBConnectCSV(filepath)

    createYAMLfiles('7654321', './yaml_files', conn)


    
    
    

    

    

