#Test the function filename2param() from coastcamDBfuncs

from coastcamDBfuncs import *

connection = DBConnectCSV("C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv")

#vv changeable parameter vv
csvPath = "C:/Users/eswanson/OneDrive - DOI/Documents/GitHub/CoastCamDB/non_CLI/station.csv"

csv2db(csvPath, connection)
