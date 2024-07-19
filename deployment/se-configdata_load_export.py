import json, boto3, sys, os, logging, dotenv, csv, traceback
from datetime import datetime, timedelta, date
from decimal import Decimal


# Look for a .env file
if os.path.exists(".env"):
    dotenv.load_dotenv(".env")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

actions = ["load", "export"]


def Write_dict_to_csv(csv_file, csv_columns, dict_data):
    try:
        with open(csv_file, "w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            writer.writeheader()
            for data in dict_data:
                logger.info(
                    f"setting_id: {data['setting_id']}/variable: {data['variable']}"
                )
                writer.writerow(data)
    except Exception as e:
        log = traceback.format_exc()
        logger.exception(log)


def getopts(argv):
    opts = {}  # Empty dictionary to store key-value pairs.
    while argv:  # While there are arguments left to parse...
        if argv[0][0] == "-":  # Found a "-name value" pair.
            opts[argv[0]] = argv[1]  # Add key and value to the dictionary.
        argv = argv[1:]  # Reduce the argument list by copying it starting from index 1.
    return opts


def main():
    args = getopts(sys.argv)
    action = None
    if "-action" not in args.keys() or args["-action"] not in actions:
        logger.error("Please input a action ({}).".format(actions))
        sys.exit()
    else:
        action = args["-action"]

    src = args["-src"]
    tgt = args["-tgt"]
    file = args["-file"]

    src_dynamodb = boto3.resource(
        "dynamodb",
        region_name=src,
        aws_access_key_id=os.getenv("aws_access_key_id"),
        aws_secret_access_key=os.getenv("aws_secret_access_key"),
    )

    tgt_dynamodb = boto3.resource(
        "dynamodb",
        region_name=tgt,
        aws_access_key_id=os.getenv("aws_access_key_id"),
        aws_secret_access_key=os.getenv("aws_secret_access_key"),
    )

    if action == "export":
        response = src_dynamodb.Table("se-configdata").scan()
        items = response["Items"]

        while "LastEvaluatedKey" in response:
            response = src_dynamodb.Table("se-configdata").scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items = response["Items"]

        for item in items:
            item.pop("value")

        Write_dict_to_csv("se-configdata.csv", items[0].keys(), items)
    elif action == "load":
        with open(file, "r") as csv_file:
            for row in csv.DictReader(csv_file):
                item = src_dynamodb.Table("se-configdata").get_item(
                    Key={"setting_id": row["setting_id"], "variable": row["variable"]}
                )
                data = item["Item"]
                tgt_dynamodb.Table("se-configdata").put_item(Item=data)
                logger.info(
                    f"setting_id: {data['setting_id']}/variable: {data['variable']}"
                )
    else:
        logger.info("The action ({action}) is not supported.".format(action=action))


if __name__ == "__main__":
    main()
