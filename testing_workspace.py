from Main_vAPI import PullFromDBmain

# Test the SelectZipCodes function
zip_query = "03047"
result = PullFromDBmain(zip_query)
print(result)
