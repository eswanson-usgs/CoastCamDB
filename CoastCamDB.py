'''
Access the CoastCamDB through a command line interface. After establishing a connection to the database. The user will
have the option to read data from the database, add data to the database, or create YAML calibration files that they can use
for rectifying imagery.
'''

##### IMPORTS #####
from coastcamDBfuncs import *
from coastcamDB_yaml_funcs import *


##### MAIN #####
if __name__ == "__main__":
    
    print('-------------------------------------------------')
    print('Welcome to the CoastCamDB command line interface!')
    print('-------------------------------------------------\n')
    print("Enter 'quit' to exit the program\n")
    print("To get started, let's connect to the database.")
    print("Do you want to use a csv with the necessary parameters to connect, or do you want to enter the parameters through the command line?")

    connect_choice = input("~~~Enter 'csv' or 'command line' to continue: ")

    ###user selects to enter parameters through csv or command line###
    isGoodAnswer = False
    while not isGoodAnswer:

        if connect_choice.strip() == 'csv':

            isGoodAnswer = True

            print("\nLet's use a csv file")
            csv_path = input("~~~Enter the path of the csv file you'd like to use: ")
            csv_path = csv_path.replace('\\', '/')

            isValidPath = False
            while not isValidPath:

                if csv_path.strip() == 'quit':
                    quit()
                    
                try:
                    connection = DBConnectCSV(csv_path.strip())
                    isValidPath = True
                    
                except:
                    csv_path = input('~~~Please enter valid filepath: ')
            
        
        elif connect_choice.strip() == 'command line':

            isGoodAnswer = True

            print("\nLet's step through the necessary parameters")

            areValidParameters = False
            while not areValidParameters:
                
                host = input("~~~Enter db host name (ex: localhost) : ")
                host = host.strip()
                if host == 'quit':
                    quit()


                #port must be an integer
                isNumber = False
                while not isNumber:
                    port = input("~~~Enter connection port (ex: 3306) : ")
                    if port.strip() == 'quit':
                        quit()

                    try:
                        port = int(port)
                        isNumber = True
                    except:
                        print("Invalid entry for connection port. Please enter a valid number")
                
                    
                dbname = input("~~~Enter databasename (ex: coastcamdb) : ")
                dbname = dbname.strip()
                if dbname == 'quit':
                    quit()
                    
                user = input("~~~Enter database user name (ex: admin) : ")
                user = user.strip()
                if user == 'quit':
                    quit()
                    
                password = input("~~~Enter password for user : ")
                password = password.strip()
                if password == 'quit':
                    quit()

                try:
                    
                    connection = pymysql.connect(host=host, user=user, port=port, passwd=password, db=dbname)
                    
                    areValidParameters = True
                    
                except:
                    print('\nIncorrect parameters entered, please try again')

        elif connect_choice.strip() == 'quit':
            quit()

        else:

            connect_choice = input("~~~Please enter either 'csv' or 'command line': ")
            

    print("\nYou are now connected to the database!")
    print("Now you can read data from the DB, add data to the DB, update existing data, or create YAML files")
    

    ###user selects option to read from db, insert data to db, update existing data, or create YAML files
    runLoop = True
    while runLoop:

        user_choice = input("\n~~~Enter 'read', 'add', 'update', or 'yaml': ")

        isGoodAnswer = False
        while not isGoodAnswer:

            ### READ ###
            if user_choice.strip() == 'read':

                isGoodAnswer = True

                pd.set_option('display.width' ,160)
                pd.set_option('display.max_columns', 40)

                print("Read from database. Choose to read from 'site', 'table', 'column'.\n")

                isValidChoice = False
                while not isValidChoice:

                    read_choice = input("~~~Enter 'site', 'table', or 'column': ")
                    if read_choice.strip() == 'quit':
                        runLoop = False
                        quit()

                    elif read_choice.strip() == 'site':

                        isValidChoice = True

                        query = "SELECT id, name FROM site"
                        result = pd.read_sql(query, con=connection)
                        print("vv Sites available to display are listed below vv")
                        print(result)

                        avail_sites = []
                        for ID in result.get('id'):
                            avail_sites.append(ID)

                        print("\nSelect data for a site from the database by entering a site id from the list above")

                        doRead = True
                        while doRead == True:

                            isGoodSite = False
                            while not isGoodSite:

                                siteID = input("~~~Enter a site id: ")

                                if siteID.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                    
                                if siteID.strip() in avail_sites:
                                    isGoodSite = True
                                else:
                                    print('Invalid site id, please try again.\n')

                            print("\nNow displaying tables associated with site id '{}'".format(siteID))
                            displaySite(siteID, connection)

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

                    elif read_choice.strip() == 'table':

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

                                table_name = input("\n~~~Enter a table name: ")
                                if table_name.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                
                                if table_name.strip() in validTables:
                                    isGoodTable = True
                                else:
                                    print('Invalid table name, please try again.')

                            print("Now displaying table '{}'\n".format(table_name))
                            print("---" + table_name.upper() + "---")

                            query = "SELECT * FROM {}".format(table_name)
                            result = pd.read_sql(query, con=connection)
                            blankIndex = [''] * len(result)
                            result.index = blankIndex
                            print(result)

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

                    elif read_choice.strip() == 'column':

                        isValidChoice = True

                        doRead = True

                        print("\nSelect data for a column from the database by entering a table name and column name")

                        validTables = ['site', 'station', 'gcp', 'camera', 'cameramodel', 'lensmodel' , 'ip', 'geometry', 'usedgcp']

                        doRead = True
                        while doRead == True:
                            
                            isGoodTable = False
                            while not isGoodTable:

                                table_name = input("\n~~~Enter a table name: ")
                                if table_name.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                
                                if table_name.strip() in validTables:
                                    isGoodTable = True
                                else:
                                    print('Invalid table name, please try again.')

                            query = "SELECT * FROM {}".format(table_name)
                            result = pd.read_sql(query, con=connection)

                            validColumns = []
                            for col in result.columns:
                                validColumns.append(col)

                            print("Below are the available columns to display:")
                            for column in validColumns:
                                print(column)

                            isGoodColumn = False
                            while not isGoodColumn:

                                column_name = input("\n~~~Enter a column name: ")
                                if column_name.strip() == 'quit':
                                    runLoop = False
                                    quit()
                                
                                if column_name.strip() in validColumns:
                                    isGoodColumn = True
                                else:
                                    print('Invalid column name, please try again.')

                            query = "SELECT {} FROM {}".format(column_name, table_name)
                            result = pd.read_sql(query, con=connection)
                            blankIndex = [''] * len(result)
                            result.index = blankIndex
                            print("---" + column_name + "---")
                            for row in result.get(column_name):
                                print(row)

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

            ### ADD ###
            elif user_choice.strip() == 'add':

                isGoodAnswer = True

                print("Add to the database. Choose to add a 'site', 'table', 'column'.\n")

                isValidChoice = False
                while not isValidChoice:

                    read_choice = input("~~~Enter 'site', 'table', or 'column': ")
                    if read_choice.strip() == 'quit':
                        runLoop = False
                        quit()

                    elif read_choice.strip() == 'site':

                        isValidChoice = True

                        print("\nWe'll now start adding a site to the database. Start by entering a site name.")

                        siteName = input("~~~Enter a site name: ")

                        if siteName.strip() == 'quit':
                                runLoop = False
                                quit()

                        #create site object
                        newSite = Site(siteName, 'coastcamdb', connection)
                        newSite.site = Table('site', 'coastcamdb', site=newSite, connection=connection)
                        newSite.site.name = Column('name', value=siteName, table=newSite.site)

                        print("\nNow enter a siteID for this site. It should be between 1 and 7 characters.")

                        isGoodSite = False
                        while not isGoodSite:

                            siteID = input("~~~Enter a site id: ")

                            if siteID.strip() == 'quit':
                                runLoop = False
                                quit()
                                
                            if (len(siteID) < 1) or (len(siteID) > 7):
                                print('Invalid site id. Site id must be between 1 and 7 characters.\n')
                            elif check_duplicate_id('site', siteID, connection):
                                print("id '{}' already exists in the 'site' table. Please try again.".format(siteID))
                            else:
                                isGoodSite = True
                                newSite.site.id = idColumn(table=newSite.site, value=siteID)

                        print(newSite.site.showFields())

                        
                       

##                        print("\nNow displaying tables associated with site id '{}'".format(siteID))
##                        displaySite(siteID, connection)
##
##                        print("\nRead data for another site?")
##
##                        isYesNo = False
##                        while not isYesNo:
##
##                            keepReading = input("~~~Enter 'yes' or 'no': ")
##
##                            if keepReading.strip() == 'quit':
##                                runLoop = False
##                                quit()
##
##                            if keepReading.strip() == 'yes':
##                                isYesNo = True
##                                doRead = True
##                            elif keepReading.strip() == 'no':
##                                isYesNo = True
##                                doRead = False
##                            else:
##                                print("Invalid choice. Please enter 'yes' or 'no'")

                        ####add in option to add another site
                        ####add in 'next' option to skip that table for now

                    elif read_choice.strip() == 'table':

                        isValidChoice = True

                        validTables = ['site', 'station', 'gcp', 'camera', 'cameramodel', 'lensmodel' , 'ip', 'geometry', 'usedgcp']
                        fk_column_list = ['siteID', 'stationID', 'modelID', 'lensmodelID', 'li_IP', 'cameraID', 'siteID', 'gcpID', 'geometrySequence']
                        
                        print("\nSelect data for a table from the database by entering a table name")
                        print("Below are the available tables to display:")
                        for table in validTables:
                            print(table)

                        isGoodTable = False
                        while not isGoodTable:

                            table_name = input("\n~~~Enter a table name: ")
                            if table_name.strip() == 'quit':
                                runLoop = False
                                quit()
                            
                            if table_name.strip() in validTables:
                                isGoodTable = True
                            else:
                                print('Invalid table name, please try again.')

                        ###FOR COLUMNS IN TABLE ADD VALUE TO QUEUES FOR COLUMN (OR SKIP)
                         #create temp Table object to hold Column objects
                        table = Table(table_name, 'coastcamdb', connection)

                        query = "SELECT * FROM {}".format(table_name)
                        result = pd.read_sql(query, con=connection)
                        validColumns = []
                        for col in result.columns:
                            if col != 'seq':
                                validColumns.append(col)

                        print("Below are the columns in the {} table:".format(table_name))
                        for column in validColumns:
                            if column in fk_column_list:
                                print(column, "[FOREIGN KEY]")
                            else:
                                print(column)

                        print("\nWe'll now step through each column in the table to insert a new value.")
                        print("At any time, you can enter 'skip' to skip the current column. This can not be done for foreign key columns.\n")

                        for column in validColumns:
                            print("Current column: {}".format(column))
                            
                            #this uses the Table object's attribute dictionary to add a Column object directly as a Table attribute
                            if column in fk_column_list:
                                print("^ Foreign key column, not skippable. ^")
                                table.__dict__[column] = fkColumn(column, table=table)
                            elif column == 'id':
                                table.__dict__[column] = idColumn(table=table)
                            else:
                                table.__dict__[column] = Column(column, table=table)
                        
                        
                    elif read_choice.strip() == 'column':

                        isValidChoice = True

                        print("\nSelect a column from the database to insert data into by entering a table name and column name")
                        print("\nLet's get a table name")
                        validTables = ['site', 'station', 'gcp', 'camera', 'cameramodel', 'lensmodel' , 'ip', 'geometry', 'usedgcp']
                        print("Below are the available tables:")
                        for table in validTables:
                            print(table)
                
                        isGoodTable = False
                        while not isGoodTable:

                            table_name = input("\n~~~Enter a table name: ")
                            if table_name.strip() == 'quit':
                                runLoop = False
                                quit()
                            
                            if table_name.strip() in validTables:
                                isGoodTable = True
                            else:
                                print('Invalid table name, please try again.')

                        #create temp Table object to hold Column object
                        table = Table(table_name, 'coastcamdb', connection)

                        query = "SELECT * FROM {}".format(table_name)
                        result = pd.read_sql(query, con=connection)
                        validColumns = []
                        for col in result.columns:
                            validColumns.append(col)

                        print("\nLet's get the column you'd like to insert data into")
                        print("Below are the available columns:")
                        for column in validColumns:
                            print(column)

                        isGoodColumn = False
                        while not isGoodColumn:

                            column_name = input("\n~~~Enter a column name: ")
                            if column_name.strip() == 'quit':
                                runLoop = False
                                quit()
                            
                            if column_name.strip() in validColumns:
                                isGoodColumn = True
                            else:
                                print('Invalid column name, please try again.')

                        fk_column_list = ['siteID', 'stationID', 'modelID', 'lensmodelID', 'li_IP', 'cameraID', 'siteID', 'gcpID', 'geometrySequence']

                        #create Column object
                        id_list = []
                        seq_list = []
                        fk_args = {}
                        if column_name in fk_column_list:
                            table.newColumn = fkColumn(column_name, table=table)

                            print("You've chosen a foreign key column. Please ener a valid value from the linked table.")
                            table.newColumn.display_linked_key()
                            
                        elif column_name == 'id':
                            table.newColumn = idColumn(table=table)

                            #tables besides site, lensmodel, cameramodel, and ip need foreign keys
                            if (table_name != 'site') and (table_name != 'lensmodel') and (table_name != 'cameramodel') and (table_name != 'ip'):
                                print("\nThis column requires a key value to specify the row of the table to update.")
                                fk_args = table.newColumn.get_fk_args()
                            else:
                                fk_args = []

                        else:
                            table.newColumn = Column(column_name, table)

                            #some tables require foreign key to insert new value
                            if (table_name != 'site') and (table_name != 'ip') and (table_name != 'lensmodel') and (table_name != 'cmaeramodel'):
                                print('\nBefore adding a value to this column, a key value must be specified')
                                fk_args = table.newColumn.get_fk_args()
                            else:
                                fk_args = []


                        print("\nNow let's add data to this column.")

                        isGoodValue = False
                        while not isGoodValue:

                            column_value = input("~~~Enter new value to insert into column: ")

                            if column_value.strip() == 'quit':
                                runLoop = False
                                quit()

                            try:
                                table.newColumn.add2queue(column_value)

                                table.newColumn.insert2db(fk_args=fk_args)

                                isGoodValue = True
                            except:
                                print("Invalid data value. Please try again.")

                    else:
                        print("Invalid choice. Please enter 'site', 'table', or 'column'")

                    ######option to add another column


            ### UPDATE ###
            elif user_choice.strip() == 'update':

                isGoodAnswer = True
                
                print("\nUpdate a database value. Please note only one column of data can be updated at a time.")
                print("We'll update a column by specifying the table name and column name.")
                print("\nLet's get a table name")
                validTables = ['site', 'station', 'gcp', 'camera', 'cameramodel', 'lensmodel' , 'ip', 'geometry', 'usedgcp']
                print("Below are the available tables:")
                for table in validTables:
                    print(table)

                isGoodTable = False
                while not isGoodTable:

                    table_name = input("\n~~~Enter a table name: ")
                    if table_name.strip() == 'quit':
                        runLoop = False
                        quit()
                    
                    if table_name.strip() in validTables:
                        isGoodTable = True
                    else:
                        print('Invalid table name, please try again.')

                #create temp Table object to hold Column object
                table = Table(table_name, 'coastcamdb', connection)

                query = "SELECT * FROM {}".format(table_name)
                result = pd.read_sql(query, con=connection)

                fk_column_list = ['siteID', 'stationID', 'modelID', 'lensmodelID', 'li_IP', 'cameraID', 'siteID', 'gcpID', 'geometrySequence']

                validColumns = []
                for col in result.columns:
                    #not allowed to update foregin key or seq columns
                    if (col not in fk_column_list) and (col != 'seq'):
                        validColumns.append(col)

                print("\nLet's get the column you'd like to insert data into")
                print("Below are the available columns:")
                for column in validColumns:
                    print(column)

                isGoodColumn = False
                while not isGoodColumn:

                    column_name = input("\n~~~Enter a column name: ")
                    if column_name.strip() == 'quit':
                        runLoop = False
                        quit()
                    
                    if column_name.strip() in validColumns:
                        isGoodColumn = True
                    else:
                        print('Invalid column name, please try again.')

                #create Column object
                if column_name == 'id':
                    table.updateColumn = idColumn(table=table)

                else:
                    table.updateColumn = Column(column_name, table)

                #for non-id columns, need to get id/seq to pass into update2db()
                id_list = []
                seq_list = []

                print("To update, first select a value to replace.")
                query = "SELECT {} FROM {}".format(column_name, table_name)
                result = get_formatted_result(query, connection)
                result_str = result.to_string(header=False, na_rep='None')
                print("Please enter a {} value listed from the values below to replace.".format(column_name))
                print("vv  Available options are listed below vv")
                print(result_str, "\n")              

                validValues = []
                dup_list = []
                hasDuplicate = False
                for val in result.get(column_name):                        
                    #special case for NaN values
                    if str(val) == 'nan':
                        val = 'None'
                        
                    validValues.append(str(val))
                        
                    #check for duplicates
                    count = validValues.count(str(val))
                    if count > 1:
                        hasDuplicate = True
                        dup_list.append(str(val))

                isGoodValue = False
                while not isGoodValue:

                    old_value = input("~~~Enter a {} value to replace: ".format(column_name))

                    if old_value.strip() == 'quit':
                        runLoop = False
                        quit()

                    if old_value.strip() in validValues:
                        isGoodValue = True
                    else:
                        print("Invalid value. Please try again.")

                #if user selects one of duplicate values
                if old_value in dup_list:
                    print("\nThere are multiple {} values in this column, please specify which on to update by selecting an id/seq")
                    idseq = table.updateColumn.input_id_seq(value=old_value)

                    if isinstance(idseq, str):
                        id_list.append(idseq)
                    elif isinstance(idseq, int):
                        seq_list.append(idseq)

                print("\nNow let's update the column with a new value")

                isGoodValue = False
                while not isGoodValue:

                    column_value = input("~~~Enter new value: ")

                    if column_value.strip() == 'quit':
                        runLoop = False
                        quit()
                        
                    try:
                        table.updateColumn.add2queue(column_value)
                        table.updateColumn.update2db(old_value, id_list=id_list, seq_list=seq_list)
                        isGoodValue = True
                    except:
                        print("Invalid data value. Please try again.")

                ######option to update another column

                        
    
            ### YAML ###
            elif user_choice.strip() == 'yaml':

                isGoodAnswer = True

                print('\nPlease specify the CoastCam station ID to create YAML files for and path to save files')

                #get station id and verify it is in table
                isValidID = False
                while not isValidID:
                    stationID = input("~~~Enter station ID (ex: exampID) : ")
                    if stationID.strip() == 'quit':
                        runLoop = False
                        quit()

                    try:
                        #check that station id exists in database. If check fails, exception is returned. Otherwise, None is retruned
                        check = check_id(stationID, 'station', connection)
                        if check != None:
                            raise Exception
                        
                        isValidID = True
                        print("Station '{}' found in the database\n".format(stationID))
                        
                    except:
                        print("Station id '{}' not found in the database. PLease try again.".format(stationID))

                #get output path
                isValidPath = False
                while not isValidPath:
                    yaml_path = input("~~~Enter path to save YAMl files to (ex: ./yaml_files) : ")
                    if yaml_path.strip() == 'quit':
                        runLoop = False
                        quit()

                    try:
                        createYAMLfiles(stationID, yaml_path, connection)
                        isValidPath = True

                    except:
                        print("Invalid path, could not write YAML files. Please try again.")
               
                
            elif user_choice.strip() == 'quit':
                runLoop = False
                quit()

            else:

                user_choice = input("~~~Please enter 'read', 'add', or 'yaml': ")

            

            



        

            
    
