import requests
import gzip
import argparse
import csv
import datetime
import json
from pytz import timezone

from influxdb import InfluxDBClient

epoch_naive = datetime.datetime.utcfromtimestamp(0)
epoch = timezone('UTC').localize(epoch_naive)

def unix_time_millis(dt):
    return int((dt - epoch).total_seconds() * 1000)

##
## Check if data type of field is float
##
def isfloat(value):
        try:
            float(value)
            return True
        except:
            return False

def isbool(value):
    try:
        return value.lower() in ('true', 'false')
    except:
        return False

def str2bool(value):
    return value.lower() == 'true'

##
## Check if data type of field is int
##
def isinteger(value):
        try:
            if(float(value).is_integer()):
                # changed, don't only "guess" if it is int with .is_integer() as this also returns true for a float number with 0 decimal (ie 20.0)
                # instead we also check the actual data and do not return it is int if contains a dot
                if value.find('.') == -1:
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False


def loadCsv(inputfilename, servername, user, password, dbname, metric, 
    timecolumn, timeformat, tagcolumns, fieldcolumns, usegzip, 
    delimiter, batchsize, create, datatimezone, usessl, showdata, dryrun, datatypes, tspass):

    host = servername[0:servername.rfind(':')]
    port = int(servername[servername.rfind(':')+1:])
    
    if dryrun:
        showdata = True
    
    rpname = False
    if dbname.find('.') != -1:
        print("dbname contains a retention policy.")
        tmpdbname = dbname.split('.')
        dbname = tmpdbname[0]
        rpname = tmpdbname[1]
        print("dbname: " + dbname)
        print("rpname: " + rpname)
    
    client = InfluxDBClient(host, port, user, password, dbname, ssl=usessl)

    if(create == True and dryrun == False):
        print('Deleting database %s'%dbname)
        client.drop_database(dbname)
        print('Creating database %s'%dbname)
        client.create_database(dbname)

    client.switch_user(user, password)

    # format tags and fields
    if tagcolumns:
        tagcolumns = tagcolumns.split(',')
    if fieldcolumns:
        fieldcolumns = fieldcolumns.split(',')
    
    print()
    
    fields_datatypes = dict()
    
    if datatypes:
        tmpdatatypes = datatypes.split(',')
        print("specified data types:")
        for tmpdatatype in tmpdatatypes:
            dt = tmpdatatype.split('=')
            fields_datatypes[dt[0]] = dt[1]
            print("column '" + dt[0] + "' => " + dt[1])
    else:
        print("guessing data types from data in CSV row 2...")
        
    # open csv
    datapoints = []
    inputfile = open(inputfilename, 'r')
    count = 0
    
    with inputfile as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        
        for row in reader:
            
            if showdata:
                print("Input: ", row)
            
            if not tspass:
                datetime_naive = datetime.datetime.strptime(row[timecolumn],timeformat)
                
                if datetime_naive.tzinfo is None:
                    datetime_local = timezone(datatimezone).localize(datetime_naive)
                else:
                    datetime_local = datetime_naive
                    
                timestamp = unix_time_millis(datetime_local) * 1000000 # in nanoseconds
            else:
                timestamp = row[timecolumn]
            
            tags = {}
            for t in tagcolumns:
                v = 0
                if t in row:
                    v = row[t]
                tags[t] = v
            
            fields = {}
            for f in fieldcolumns:
                v = 0
                if f in row:
                    skipfield = False
                    if count == 0 and not datatypes:
                        # first row, guess data types ONLY from there and remember them for the following rows
                        if (isinteger(row[f])):
                            print("column '" + f + "' = '" + str(row[f]) + "' => int")
                            fields_datatypes[f] = "int"
                            v = int(float(row[f]))
                        elif (isfloat(row[f])):
                            print("column '" + f + "' = '" + str(row[f]) + "' => float")
                            fields_datatypes[f] = "float"
                            v = float(row[f])
                        elif (isbool(row[f])):
                            print("column '" + f + "' = '" + str(row[f]) + "' => bool")
                            fields_datatypes[f] = "bool"
                            v = str2bool(row[f])
                        else:
                            print("column '" + f + "' = '" + str(row[f]) + "' => str")
                            fields_datatypes[f] = "str"
                            v = row[f]
                    else:
                        # from 2nd row only use data types guessed from row 1. 
                        # check if datatype for each column fits and skip value if not (useful if there are a few missing values in the CSV)
                        if (fields_datatypes[f] == "int"):
                            if (isinteger(row[f])):
                                v = int(float(row[f]))
                            else:
                                skipfield = True
                                print("CSV row " + str(count+2) + ": skipped field '" + f + "' as it has a different data type.")
                        elif (fields_datatypes[f] == "float"):
                            if (isfloat(row[f])):
                                v = float(row[f])
                            else:
                                skipfield = True
                                print("CSV row " + str(count+2) + ": skipped field '" + f + "' as it has a different data type.")
                        elif (fields_datatypes[f] == "bool"):
                            if (isbool(row[f])):
                                v = str2bool(row[f])
                            else:
                                skipfield = True
                                print("CSV row " + str(count+2) + ": skipped field '", f, "' as it has a different data type.")
                        elif (fields_datatypes[f] == "str"):
                            v = row[f]
                        
                if not skipfield:
                    fields[f] = v
                
            if len(fields) > 0:
                point = {"measurement": metric, "time": timestamp, "fields": fields, "tags": tags}
                if showdata:
                    print("Output: ", json.dumps(point, indent=3))
    
                datapoints.append(point)
                count+=1
            else:
                print("CSV row " + str(count+2) + ": skipped as it contains no field values.")
                count+=1
            
            if len(datapoints) % batchsize == 0:
                print('Read %d lines'%count)
                print('Inserting %d datapoints...'%(len(datapoints)))
                
                #if showdata:
                #    print(json.dumps(datapoints, indent=3))
                if not dryrun:
                    if rpname:
                        response = client.write_points(datapoints, retention_policy=rpname)
                    else:
                        response = client.write_points(datapoints)
                
                    if not response:
                        print('Problem inserting points, exiting...')
                        exit(1)
    
                    print("Wrote %d points, up to %s, response: %s" % (len(datapoints), datetime_local, response))

                datapoints = []
            

    # write rest
    if len(datapoints) > 0:
        print('Read %d lines'%count)
        print('Inserting %d datapoints...'%(len(datapoints)))
        
        #if showdata:
        #    print(json.dumps(datapoints, indent=3))
        if not dryrun:
            if rpname:
                response = client.write_points(datapoints, retention_policy=rpname)
            else:
                response = client.write_points(datapoints)
            
            if response == False:
                print('Problem inserting points, exiting...')
                exit(1)
            print("Wrote %d, response: %s" % (len(datapoints), response))


    print('Done')
    if dryrun:
        print('(actually did not change anything on the database, as --dryrun parameter was given.)')
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Csv to influxdb.')

    parser.add_argument('-i', '--input', nargs='?', required=True,
                        help='Input csv file.')

    parser.add_argument('-d', '--delimiter', nargs='?', required=False, default=',',
                        help='Csv delimiter. Default: \',\'.')

    parser.add_argument('-s', '--server', nargs='?', default='localhost:8086',
                        help='Server address. Default: localhost:8086')

    parser.add_argument('--ssl', action='store_true', default=False,
                        help='Use HTTPS instead of HTTP.')

    parser.add_argument('-u', '--user', nargs='?', default='root',
                        help='User name.')

    parser.add_argument('-p', '--password', nargs='?', default='root',
                        help='Password.')

    parser.add_argument('--dbname', nargs='?', required=True,
                        help='Database name. Specify target Retention Policy: [DBNAME].[RPNAME]')
    
    parser.add_argument('--create', action='store_true', default=False,
                        help='Drop database and create a new one.')

    parser.add_argument('-m', '--metricname', nargs='?', default='value',
                        help='Metric column name. Default: value')

    parser.add_argument('-tc', '--timecolumn', nargs='?', default='timestamp',
                        help='Timestamp column name. Default: timestamp.')

    parser.add_argument('-tf', '--timeformat', nargs='?', default='%Y-%m-%d %H:%M:%S',
                        help='Timestamp format. Default: \'%%Y-%%m-%%d %%H:%%M:%%S\' e.g.: 1970-01-01 00:00:00')

    parser.add_argument('-tz', '--timezone', default='UTC',
                        help='Timezone of supplied data. Default: UTC')

    parser.add_argument('--fieldcolumns', nargs='?', default='value',
                        help='List of csv columns to use as fields, separated by comma, e.g.: value1,value2. Default: value')

    parser.add_argument('--tagcolumns', nargs='?', default='host',
                        help='List of csv columns to use as tags, separated by comma, e.g.: host,data_center. Default: host')

    parser.add_argument('-g', '--gzip', action='store_true', default=False,
                        help='Compress before sending to influxdb.')

    parser.add_argument('-b', '--batchsize', type=int, default=5000,
                        help='Batch size. Default: 5000.')
    
    parser.add_argument('--showdata', action='store_true', default=False,
                        help='Print detailed information to the console what will be done with the data (or is intended to, when using --dryrun).')
    
    parser.add_argument('--dryrun', action='store_true', default=False,
                        help='Do not change anything in the DB. Also enables --showdata.')
    
    parser.add_argument('--datatypes', default=False,
                        help='Force specify data types for fields specified in --fieldcolumns: value1=int,value2=float,value3=bool,name=str ... Valid types: int, float, str, bool')

    parser.add_argument('-tp', '--tspass', action='store_true', default=False,
                        help='Pass the timestamp from CSV directly to InfluxDB (do no conversion) - use only if the format is compatible to InfluxDB.')

    args = parser.parse_args()
    loadCsv(args.input, args.server, args.user, args.password, args.dbname, 
        args.metricname, args.timecolumn, args.timeformat, args.tagcolumns, 
        args.fieldcolumns, args.gzip, args.delimiter, args.batchsize, args.create, 
        args.timezone, args.ssl, args.showdata, args.dryrun, args.datatypes, args.tspass)
