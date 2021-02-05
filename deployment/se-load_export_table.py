import json, boto3, sys, os, logging, dotenv
from datetime import datetime, timedelta, date
from decimal import Decimal


# Look for a .env file
if os.path.exists('.env'):
    dotenv.load_dotenv('.env')

logging.basicConfig(stream=sys.stdout, level=logging.INFO)     
logger = logging.getLogger()

actions = ['load','export']
tables = ['se-configdata','se-endpoints','se-connections','se-functions']

dynamodb = boto3.resource(
	'dynamodb',
    region_name=os.getenv("region_name"),
    aws_access_key_id=os.getenv('aws_access_key_id'),
    aws_secret_access_key=os.getenv('aws_secret_access_key')
)

# Helper class to convert a DynamoDB item to JSON.
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        elif isinstance(o, (datetime, date)):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(o, (bytes, bytearray)):
            return str(o)
        else:
            return super(JSONEncoder, self).default(o)

def getopts(argv):
    opts = {}  # Empty dictionary to store key-value pairs.
    while argv:  # While there are arguments left to parse...
        if argv[0][0] == '-':  # Found a "-name value" pair.
            opts[argv[0]] = argv[1]  # Add key and value to the dictionary.
        argv = argv[1:]  # Reduce the argument list by copying it starting from index 1.
    return opts

def main():
    args = getopts(sys.argv)
    action = None
    table = None
    if "-action" not in args.keys() or args["-action"] not in actions:
        logger.error("Please input a action ({}).".format(actions))
        sys.exit()
    else:
        action = args["-action"]
    if "-table" not in args.keys() or args["-table"] not in tables:
        logger.error("Please input a table ({}).".format(tables))
        sys.exit()
    else:
        table = args["-table"]

    if action == 'load':
        with open('{table}.json'.format(table=table)) as f:
            for item in json.load(f):
                logger.info(item)
                response = dynamodb.Table(table).put_item(Item=item)
                logger.info(response)
            logger.info('{table}.json is imported.'.format(table=table))
    elif action == 'export':
        response = dynamodb.Table(table).scan()
        items = response['Items']

        while 'LastEvaluatedKey' in response:
            response = dynamodb.Table(table).scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items = response['Items']

        with open('{table}.json'.format(table=table), 'w') as outfile:
            json.dump(items, outfile, indent=4, cls=JSONEncoder)
            logger.info('{table}.json is exported.'.format(table=table))
    else:
        logger.info('The action ({action}) is not supported.'.format(action=action))


if __name__== "__main__":
    main()