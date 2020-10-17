# csv-to-influxdb

forked from original version: https://github.com/fabio-miranda/csv-to-influxdb

## 2020-10-17 by Flo Kra

* fixes/improvements:
    * detect data format (float or integer) not only by python .is_integer() method, but also check if raw data contains a dot. 
	Don´t treat float values with decimals all 0s as integer as it probable is not the case when the csv contains decimals in that column. 
    * detect data formats only in first data row as it should not change within a csv file, and importing different data types with the same field name to InfluxDB is problematic
    * does not import datasets which do not meet the datatype specified/detected. 
	i.e. when a csv contains empty cells in some rows which would be treated as string ("") or int with value 0
    * do not exit script/stop importing on inserting errors (although this was mostly caused by different/wrong data in csv and should not happen as now the data types are checked before importing)

* added features:
    * --dryrun switch: 
	Do not change anything in the DB. Also enables --showdata.

    * --showdata switch: 
    Print detailed information to the console what will be done with the data (or is intended to, when using --dryrun).
	
    * --tspass (or -tp) switch: 
    do not convert timestamps, instead pass them as they are in the csv (for use i.e. with csv exports made with Chronograf, when timestamps are for sure already in an InfluxDB compatible format)

    * --datatypes parameter: 
    Force data type for each column specified in the --fieldcolumns parameter. 
    The following data types can be specified: int, float, string
    usage example: --fieldcolumns temperature,humidity,barometer --datatypes temperature=float,humidity=int,barometer=float
    
    * allow to specify to which **retention policy** the data should be imported. 
    specify with --dbname database.retentionpolicy as you would in InfluxQL. 
    I missed that possibility when importing old, already aggregated data which I didn´t want to be in the default RP. 

  

