'''
Access the CoastCamDB through a command line interface. After establishing a connection to the database. The user will
have the option to read data from the database, add data to the database, or create YAML calibration files that they can use
for rectifying imagery.
'''

##### IMPORTS #####
from coastcamDBfuncsCLI import *
from coastcamDBYAMLFuncsCLI import *


##### MAIN #####
if __name__ == "__main__":
    
    print('-------------------------------------------------')
    print('Welcome to the CoastCamDB command line interface!')
    print('------------- ------------------------------------\n')
    print("Enter 'quit' at any time to exit the program\n")

    #auomatically connect to database with read-only permissions
    host = 'cch-spcmsc-coastcamdb.cdlb2l00dt2l.us-west-2.rds.amazonaws.com'
    port = 3306
    dbname = 'coastcamdb'
    user = 'ReadOnlyUser'
    password = ''
    connection = pymysql.connect(host=host, user=user, port=port, passwd=password, db=dbname)

    print("Using this command line interface, you can read data from the DB or create YAML files")
    
    ###user selects option to read from db or create YAML files
    runLoop = True
    while runLoop:

        userChoice = input("\n~~~Enter 'read' or 'yaml': ")

        isGoodAnswer = False
        while not isGoodAnswer:

            ### READ ###
            if userChoice.strip() == 'read':

                isGoodAnswer = True

                pd.set_option('display.width' ,160)
                pd.set_option('display.max_columns', 40)

                print("Read from database. Choose to read from 'site', 'table', 'column'.\n")

                isValidChoice = False
                while not isValidChoice:

                    readChoice = input("~~~Enter 'site', 'table', or 'column': ")
                    if readChoice.strip() == 'quit':
                        runLoop = False
                        quit()

                    elif readChoice.strip() == 'site':

                        isValidChoice = True

                        query = "SELECT id, name FROM site"
                        result = pd.read_sql(query, con=connection)
                        print("vv Sites available to display are listed below vv")
                        print(result)

                        availSites = []
                        for ID in result.get('id'):
                            availSites.append(ID)

                        print("\nSelect data for a site from the database by entering a site id from the list above")

                        doRead = True
                        while doRead == True:

                            isGoodSite = False
                            while not isGoodSite:

                                siteID = input("~~~Enter a site id: ")

                                if siteID.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                    
                                if siteID.strip() in availSites:
                                    isGoodSite = True
                                else:
                                    print('Invalid site id, please try again.\n')

                            print("\nNow displaying tables associated with site id '{}'".format(siteID))
                            #returns list of table dataframes to be used when storing the read data
                            dfList = displaySite(siteID, connection)

                            print("\nStore read data in a csv?")
                            isYesNo = False
                            while not isYesNo:

                                keepReading = input("~~~Enter 'yes' or 'no': ")

                                if keepReading.strip() == 'quit':
                                    runLoop = False
                                    quit()

                                if keepReading.strip() == 'yes':
                                    isYesNo = True
                                    storeCSV = True
                                elif keepReading.strip() == 'no':
                                    isYesNo = True
                                    storeCSV = False
                                else:
                                    print("Invalid choice. Please enter 'yes' or 'no'")
                                    
                            if storeCSV:
                                print("\nPlease enter the filepath to the folder where you'd like to store the csv: ")
                                csvPath = input("~~~Enter a filepath: ")

                                dataDict = {}
                                for dfTuple in dfList:
                                    table = dfTuple[0]
                                    df = dfTuple[1]
                                    dataDict = storeReadData(df, 'site', table=table, csvPath=csvPath, dataDict=dataDict)

                                sitePath = csvPath + 'sites/' + siteID
                                print("Saved csv to", sitePath)
                            else:
                                dataDict = {}
                                for dfTuple in dfList:
                                    table = dfTuple[0]
                                    df = dfTuple[1]
                                    dataDict = storeReadData(df, 'site', table=table, dataDict=dataDict)

                            print("\nRead data for another site?")

                            isYesNo = False
                            while not isYesNo:

                                keepReading = input("~~~Enter 'yes' or 'no': ")

                                if keepReading.strip() == 'quit':
                                    runLoop = False
                                    quit()

                                if keepReading.strip() == 'yes':
                                    isYesNo = True
                                    doRead = True
                                elif keepReading.strip() == 'no':
                                    isYesNo = True
                                    doRead = False
                                else:
                                    print("Invalid choice. Please enter 'yes' or 'no'") 

                    elif readChoice.strip() == 'table':

                        isValidChoice = True

                        doRead = True

                        validTables = ['site', 'station', 'gcp', 'camera', 'cameramodel', 'lensmodel' , 'ip', 'geometry', 'usedgcp']

                        print("\nSelect data for a table from the database by entering a table name")
                        print("Below are the available tables to display:")
                        for table in validTables:
                            print(table)

                        doRead = True
                        while doRead == True:

                            isGoodTable = False
                            while not isGoodTable:

                                tableName = input("\n~~~Enter a table name: ")
                                if tableName.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                
                                if tableName.strip() in validTables:
                                    isGoodTable = True
                                else:
                                    print('Invalid table name, please try again.')

                            print("Now displaying table '{}'\n".format(tableName))
                            print("---" + tableName.upper() + "---")

                            query = "SELECT * FROM {}".format(tableName)
                            result = pd.read_sql(query, con=connection)
                            blankIndex = [''] * len(result)
                            result.index = blankIndex
                            print(result)

                            print("\nStore read data in a csv?")
                            isYesNo = False
                            while not isYesNo:

                                keepReading = input("~~~Enter 'yes' or 'no': ")

                                if keepReading.strip() == 'quit':
                                    runLoop = False
                                    quit()

                                if keepReading.strip() == 'yes':
                                    isYesNo = True
                                    storeCSV = True
                                elif keepReading.strip() == 'no':
                                    isYesNo = True
                                    storeCSV = False
                                else:
                                    print("Invalid choice. Please enter 'yes' or 'no'")
                                    
                            if storeCSV:
                                print("\nPlease enter the filepath to the folder where you'd like to store the csv: ")
                                csvPath = input("~~~Enter a filepath: ")
                                dataDict = storeReadData(result, 'table', csvPath=csvPath, table=tableName)
                            else:
                                dataDict = storeReadData(result, 'table', table=tableName)

                            print("\nRead data for another table?")

                            isYesNo = False
                            while not isYesNo:

                                keepReading = input("~~~Enter 'yes' or 'no': ")

                                if keepReading.strip() == 'quit':
                                    runLoop = False
                                    quit()

                                if keepReading.strip() == 'yes':
                                    isYesNo = True
                                    doRead = True
                                elif keepReading.strip() == 'no':
                                    isYesNo = True
                                    doRead = False
                                else:
                                    print("Invalid choice. Please enter 'yes' or 'no'") 

                    elif readChoice.strip() == 'column':

                        isValidChoice = True

                        doRead = True

                        print("\nSelect data for a column from the database by entering a table name and column name")

                        validTables = ['site', 'station', 'gcp', 'camera', 'cameramodel', 'lensmodel' , 'ip', 'geometry', 'usedgcp']

                        doRead = True
                        while doRead == True:
                            
                            isGoodTable = False
                            while not isGoodTable:

                                tableName = input("\n~~~Enter a table name: ")
                                if tableName.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                
                                if tableName.strip() in validTables:
                                    isGoodTable = True
                                else:
                                    print('Invalid table name, please try again.')

                            query = "SELECT * FROM {}".format(tableName)
                            result = pd.read_sql(query, con=connection)

                            validColumns = []
                            for col in result.columns:
                                validColumns.append(col)

                            print("Below are the available columns to display:")
                            for column in validColumns:
                                print(column)

                            isGoodColumn = False
                            while not isGoodColumn:

                                columnName = input("\n~~~Enter a column name: ")
                                if columnName.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                
                                if columnName.strip() in validColumns:
                                    isGoodColumn = True
                                else:
                                    print('Invalid column name, please try again.')

                            query = "SELECT {} FROM {}".format(columnName, tableName)
                            result = pd.read_sql(query, con=connection)
                            blankIndex = [''] * len(result)
                            result.index = blankIndex
                            print("---" + columnName + "---")
                            for row in result.get(columnName):
                                print(row)

                            print("\nStore read data in a csv?")
                            isYesNo = False
                            while not isYesNo:

                                keepReading = input("~~~Enter 'yes' or 'no': ")

                                if keepReading.strip() == 'quit':
                                    runLoop = False
                                    quit()

                                if keepReading.strip() == 'yes':
                                    isYesNo = True
                                    storeCSV = True
                                elif keepReading.strip() == 'no':
                                    isYesNo = True
                                    storeCSV = False
                                else:
                                    print("Invalid choice. Please enter 'yes' or 'no'")
                                    
                            if storeCSV:
                                print("\nPlease enter the filepath to the folder where you'd like to store the csv: ")
                                csvPath = input("~~~Enter a filepath: ")
                                dataDict = storeReadData(result, 'column', csvPath=csvPath, table=tableName)
                            else:
                                dataDict = storeReadData(result, 'column')
                            
                            print("\nRead data for another column?")

                            isYesNo = False
                            while not isYesNo:

                                keepReading = input("~~~Enter 'yes' or 'no': ")

                                if keepReading.strip() == 'quit':
                                    runLoop = False
                                    quit()

                                if keepReading.strip() == 'yes':
                                    isYesNo = True
                                    doRead = True
                                elif keepReading.strip() == 'no':
                                    isYesNo = True
                                    doRead = False
                                else:
                                    print("Invalid choice. Please enter 'yes' or 'no'") 

                    else:
                        print("Invalid choice. Please enter 'site', 'table', or 'column'")

    
            ### YAML ###
            elif userChoice.strip() == 'yaml':

                isGoodAnswer = True

                print('\nPlease specify the CoastCam station ID to create YAML files for and path to save files')

                query = "SELECT id, shortName FROM station"
                result = pd.read_sql(query, con=connection)
                print("vv Available station IDs are listed below vv")
                print(result)

                availStationID = []
                for ID in result.get('id'):
                    availStationID.append(ID)

                #get station id and verify it is in table
                isValidID = False
                while not isValidID:
                    stationID = input("~~~Enter station ID (ex: exampID) : ")
                    if stationID.strip() == 'quit':
                        runLoop = False
                        quit()

                    try:
                        #check that station id exists in database. If check fails, exception is returned. Otherwise, None is retruned
                        check = checkID(stationID, 'station', connection)
                        if check != None:
                            raise Exception
                        
                        isValidID = True
                        print("Station '{}' found in the database\n".format(stationID))
                        
                    except:
                        print("Station id '{}' not found in the database. PLease try again.".format(stationID))

                #get output path
                isValidPath = False
                while not isValidPath:
                    yamlPath = input("~~~Enter path to save YAMl files to (ex: ./yaml_files) : ")
                    if yamlPath.strip() == 'quit':
                        runLoop = False
                        quit()

                    try:
                        createYAMLfiles(stationID, yamlPath, connection)
                        isValidPath = True

                    except:
                        print("Invalid path, could not write YAML files. Please try again.")
               
                
            elif userChoice.strip() == 'quit':
                runLoop = False
                quit()

            else:

                userChoice = input("~~~Please enter 'read' or 'yaml': ")

            

            



        

            
    

