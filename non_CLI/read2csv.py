#read data from CoastCamDB to csv file

### IMPORTS ####
from coastcamDBfuncs import *



### MAIN ###
connection = DBConnectCSV("C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv")

#define scope of what will be saved to csv
isColumn = False
isTable = True
isSite = False

# vv changeable parameter
csv_path = "C:/Users/eswanson/OneDrive - DOI/Documents/GitHub/CoastCamDB/non_CLI/saved_csv/"

#column
if isColumn:

    # vv changeable parameters vv
    table = 'camera'
    column = 'filters'

    dataframe = column2csv(column, table, csv_path, connection)

#table
if isTable:

    # vv changeable parameters vv
    table = 'camera'

    dataframe = table2csv(table, csv_path, connection)
