#Test the function parseFilename() from coastcamDBfuncs

from coastcamDBfuncs import *

filename = "C:\\Users\\eswanson\\OneDrive - DOI\\Documents\\GitHub\\CoastCamDB\\non_CLI\\1660734000.Wed.Aug.17_11_0_0.GMT.2022.examplexx.c1.snap.jpg"

connection = DBConnectCSV("C:/Users/eswanson/OneDrive - DOI/Documents/Python/db_access.csv")

components = parseFilename(filename, conection, timezone='eastern')
#Test the function parseFilename() from coastcamDBfuncs

print(components.extrinsics)
