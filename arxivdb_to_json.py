import json
import pickle

with open("db.p", "rb") as picklefile:
    db_dict = pickle.load(picklefile)

with open("db.json", "w+") as jsonfile:
    for key,val in db_dict.items():
        json.dump(val, jsonfile)
        jsonfile.write("\n")

 
