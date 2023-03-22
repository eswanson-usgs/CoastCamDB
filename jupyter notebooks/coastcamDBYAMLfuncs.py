##### IMPORTS #####
from coastcamDBfuncs import *
import mysql.connector

##### FUNCTIONS #####
def DBdict2yaml(dictionary, descriptorDict, path, fileName):
    '''
    Create YAML file from a  dictionary.
    Inputs:
        dictionary (dict) - dictionary object used to create YAML file
        descriptorDict (dict) - dictionary of descriptors for fields from the DB
        path (string) - path to directory where YAML files will be saved
        fileName (string) - filename for the new YAML file, ".yaml" not included
    Outputs:
        none, but YAML files are created
    '''

    filepath = path+"/"+fileName+".yaml"
        
    with open(filepath, 'w') as file:
        for field in dictionary:
            #manually write in YAML formatting. YAML dump sometimes writes out of order
            file.write(field + ': ' + str(dictionary[field]) + '\n')
        
        #leave comments in yaml with text descriptions of the fields
        #ex. #x - x location of camera
        for field in dictionary:
            file.write('#' + field + ' - ' + descriptorDict[field]+ '\n')

    return


def createYAMLfiles(stationID, outputPath, connection):
    '''
    Create YAML files given a stationID.
    Inputs:
        stationID (string) - specifies the "id" field for the "station" table, which is also the "stationID" field in the
                             "camera" table
        outputPath (string) - specifies the folder where the YAML files will be saved to
        connection (pymysql.connections.Connection object) - Object representing connection to DB
    Outputs:
        none (but YAML files are created)
    '''

    extrinsics, intrinsics, metadata, localOrigin = getParameterDicts(stationID, connection)

    query = "SELECT * FROM camera WHERE stationID = '{}'".format(stationID)
    result = pd.read_sql(query, con=connection)
    cameraList = []
    for ID in result.get('id'):
        cameraList.append(ID)

    #need to query station table before going through camera list
    query = "SELECT shortName FROM station WHERE id = '{}'".format(stationID)
    result = pd.read_sql(query, con=connection)
    #station short name for YAML file name formatting. 
    shortName = result.get('shortName')[0]

    ###CREATE DESCRIPTOR DICTS###
    metadataDescriptorDict = {}
    metadataDescriptorDict['name'] = 'name of the camera station'
    metadataDescriptorDict['serial_number'] = 'camera serial number'
    metadataDescriptorDict['cameraNumber'] = 'camera number for the corresponding station'
    metadataDescriptorDict['calibration_date'] = 'date when the camera was calibrated'
    metadataDescriptorDict['coordinate_system'] = 'coordinate system for extrinsic parameters. Either "geo" or "xyz"'
    
    extrinsicDescriptorDict = {}
    extrinsicDescriptorDict['x'] = 'x location of camera'
    extrinsicDescriptorDict['y'] = 'y location of camera'
    extrinsicDescriptorDict['z'] = 'z location of camera'
    extrinsicDescriptorDict['a'] = 'camera azimuth orientation'
    extrinsicDescriptorDict['t'] = 'camera tilt orientation'
    extrinsicDescriptorDict['r'] = 'camera roll orientation'

    intrinsicDescriptorDict = {}
    intrinsicDescriptorDict['NU'] = 'number of pixel columns'
    intrinsicDescriptorDict['NV'] = 'number of pixel rows'
    intrinsicDescriptorDict['c0U'] = 'first component of the principal point'
    intrinsicDescriptorDict['c0V'] = 'second component of the principal point'
    intrinsicDescriptorDict['c0U'] = 'first component of the principal point'
    intrinsicDescriptorDict['fx'] = 'x component of the focal length (pixels)'
    intrinsicDescriptorDict['fy'] = 'y component of the focal length (pixels)'
    intrinsicDescriptorDict['d1'] = 'first radial distortion coefficient'
    intrinsicDescriptorDict['d2'] = 'second radial distortion coefficient'
    intrinsicDescriptorDict['d3'] = 'third radial distortion coefficient'
    intrinsicDescriptorDict['t1'] = 'first tangential distortion coefficient'
    intrinsicDescriptorDict['t2'] = 'second tangential distortion coefficient'

    localOriginDescriptorDict = {}
    localOriginDescriptorDict['x'] = 'x location of site origin'
    localOriginDescriptorDict['y'] = 'y location of site origin'
    localOriginDescriptorDict['angd'] = 'orientation of the local grid'

    #write to YAML files
    for i in range(0, len(cameraList)):

        path = './yaml_files'
        cameraNumber = metadata[i]['cameraNumber']

        #extrinsics
        fileName = shortName.replace(' ', '_') + '_C' + str(cameraNumber) + '_extr'
        DBdict2yaml(extrinsics[i], extrinsicDescriptorDict, outputPath, fileName)

        #intrinsics
        fileName = shortName.replace(' ', '_') + '_C' + str(cameraNumber) + '_intr'
        DBdict2yaml(intrinsics[i], intrinsicDescriptorDict, outputPath, fileName)

        #metadata
        fileName = shortName.replace(' ', '_') + '_C' + str(cameraNumber) + '_metadata'
        DBdict2yaml(metadata[i], metadataDescriptorDict, outputPath, fileName)

    #local origin
    fileName = shortName.replace(' ', '_') + '_localOrigin'
    DBdict2yaml(localOrigin, localOriginDescriptorDict, outputPath, fileName)

    return


if __name__ == "__main__":
    print('hi')

    filepath = "C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv"
    conn = DBConnectCSV(filepath)

    createYAMLfiles('7654321', './yaml_files', conn)


    
    
    

    

    
