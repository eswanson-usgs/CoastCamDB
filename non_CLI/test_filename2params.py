#Test the function filename2param() from coastcamDBfuncs

from coastcamDBfuncs import *

filename = "1660734000.Wed.Aug.17_11_0_0.GMT.2022.examplexx.c1.snap.jpg"

connection = DBConnectCSV("C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv")

params = filename2param(filename, connection)

print(params.extrinsics[0])
print(params.intrinsics[0])
print(params.metadata[0])
print(params.local_origin)
