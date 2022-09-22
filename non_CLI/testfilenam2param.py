#Test the function parseFilename() from coastcamDBfuncs

from coastcamDBfuncs import *

filename = "1660734000.Wed.Aug.17_11_0_0.GMT.2022.examplexx.c1.snap.jpg"

connection = DBConnectCSV("C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access_readonly.csv")

components = filename2param(filename, connection, timezone='eastern')
#Test the function parseFilename() from coastcamDBfuncs

print(components.extrinsics)
