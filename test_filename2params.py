#Test the function filename2param() from coastcamDBfuncs

from coastcamDBfuncs import *

filename = "1636052400.Thu.Nov.04_19_00_00.GMT.2021.examplexx.Camera1.bright.jpg"

connection = DBConnectCSV("C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv")

params = filename2param(filename, connection)

print(params.extrinsics[0])
print(params.intrinsics[0])
print(params.metadata[0])
print(params.local_origin)
