# csv-to-influxdb-ext
Simple python script that inserts data points read from a csv file into a influxdb database.

To create a new database, specify the parameter ```--create```. This will drop any database with a name equal to the one supplied with ```--dbname```.

#### Changes/Improvements compared to the original version: 

* Improved guessing of data types from the data found in the first row. 
  * number without . --> integer
  * number that contains a . --> float
  * string that is "true" or "false" --> bool
Unlike in the original version, these data types are then used for the entire file for this column. If a value in another row does not fit (i.e. is empty, is a string like "NaN" or "") it will be skipped. Unlike the original code, this does not stop the rest of the import. If a row does not contain any valid data it is entirely skipped and not written to database. 

* specify the data types on the commandline

* Possibility to have a look on what´s going on *before* actually write anything to the database, by simply specifying *--dryrun*.

* show data processed on the console

* Possibility to specify a target retention policy rather than only the database name

## Usage

```
usage: csv-to-influxdb.py [-h] -i [INPUT] [-d [DELIMITER]] [-s [SERVER]]
                          [--ssl] [-u [USER]] [-p [PASSWORD]] --dbname
                          [DBNAME] [--create] [-m [METRICNAME]]
                          [-tc [TIMECOLUMN]] [-tf [TIMEFORMAT]] [-tz TIMEZONE]
                          [--fieldcolumns [FIELDCOLUMNS]]
                          [--tagcolumns [TAGCOLUMNS]] [-g] [-b BATCHSIZE]

Csv to influxdb.

optional arguments:
  -h, --help            show this help message and exit
  -i [INPUT], --input [INPUT]
                        Input csv file.
  -d [DELIMITER], --delimiter [DELIMITER]
                        Csv delimiter. Default: ','.
  -s [SERVER], --server [SERVER]
                        Server address. Default: localhost:8086
  --ssl                 Use HTTPS instead of HTTP.
  -u [USER], --user [USER]
                        User name.
  -p [PASSWORD], --password [PASSWORD]
                        Password.
  --dbname [DBNAME]     Database name. Specify target Retention Policy: [DBNAME].[RPNAME]
  --create              Drop database and create a new one.
  -m [METRICNAME], --metricname [METRICNAME]
                        Metric column name. Default: value
  -tc [TIMECOLUMN], --timecolumn [TIMECOLUMN]
                        Timestamp column name. Default: timestamp.
  -tf [TIMEFORMAT], --timeformat [TIMEFORMAT]
                        Timestamp format. Default: '%Y-%m-%d %H:%M:%S' e.g.:
                        1970-01-01 00:00:00
  -tz TIMEZONE, --timezone TIMEZONE
                        Timezone of supplied data. Default: UTC
  -tp, --tspass         Pass the timestamp from CSV directly to InfluxDB (do no conversion).
                        Use only if the format is compatible to InfluxDB.
  --fieldcolumns [FIELDCOLUMNS]
                        List of csv columns to use as fields, separated by
                        comma, e.g.: value1,value2. Default: value
  --datatypes           Force specify data types for fields specified in --fieldcolumns: 
                        i.e. value1=int,value2=float,value3=bool,name=str ...
                        Valid types: int, float, str, bool
  --tagcolumns [TAGCOLUMNS]
                        List of csv columns to use as tags, separated by
                        comma, e.g.: host,data_center. Default: host
  -g, --gzip            Compress before sending to influxdb.
  -b BATCHSIZE, --batchsize BATCHSIZE
                        Batch size. Default: 5000.
  --showdata            Print detailed information to the console what will be done with the data (or is intended to, when using --dryrun).
  --dryrun              Do not change anything in the DB. Also enables --showdata.

```

## Examples

#### 1. Considering the csv file:


```

timestamp,value,computer
1970-01-01 00:00:00,51.374894,0
1970-01-01 00:00:01,74.562764,1
1970-01-01 00:00:02,17.833757,2
1970-01-01 00:00:03,40.125102,0
1970-01-01 00:00:04,88.160817,1
1970-01-01 00:00:05,28.401695,2
1970-01-01 00:00:06,98.670792,3
1970-01-01 00:00:07,69.532011,0
1970-01-01 00:00:08,39.198964,0

```


The following command will insert the file into a influxdb database:

```

python csv-to-influxdb.py --dbname test --input data.csv --tagcolumns computer --fieldcolumns value

```

#### 2. Another example:


```

timestamp,temperature,humidity,sensor
1970-01-01 00:00:00,17.2,55,garden
1970-01-01 00:00:01,17.3,56,garden
1970-01-01 00:00:02,17.1,57,garden
1970-01-01 00:00:03,16.9,55,garden
1970-01-01 00:00:04,16.7,53,garden
1970-01-01 00:00:05,16.8,52,garden
1970-01-01 00:00:06,17.0,55,garden
1970-01-01 00:00:07,17.1,57,garden
1970-01-01 00:00:08,17.2,60,garden

```


Command:


```
python csv-to-influxdb.py --dbname test --input data.csv --tagcolumns sensor --fieldcolumns temperature,humidity --datatypes temperature=float,humidity=int
```


Where --datatypes cam be omitted if they are clearly to identify in the first data row.


#### 3. Importing historic aggregated data to a different Retention Policy named "daily":


```

timestamp,temp_avg,hum_avg,sensor
2020-06-01 00:00:00,17.2,55,garden
2020-06-02 00:00:00,17.3,56,garden
2020-06-03 00:00:00,17.1,57,garden
2020-06-04 00:00:00,16.9,55,garden
2020-06-05 00:00:00,16.7,53,garden
2020-06-06 00:00:00,16.8,52,garden
2020-06-07 00:00:00,17.0,55,garden
2020-06-08 00:00:00,17.1,57,garden
2020-06-09 00:00:00,17.2,60,garden

```


Command:


```
python csv-to-influxdb.py --dbname test.daily --input data.csv --tagcolumns sensor --fieldcolumns temp_avg,hum_avg
```


