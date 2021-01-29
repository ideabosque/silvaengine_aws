import boto3, json, sys, os, dotenv, zipfile
from datetime import datetime, date
from decimal import Decimal
from time import sleep


# Look for a .env file
if len(sys.argv) == 2:
    dotenv.load_dotenv(sys.argv[-1])
else:
    dotenv.load_dotenv('.env')

if os.getenv('lambda_config') is not None:
    lambda_config = __import__(os.getenv('lambda_config'))
    lambdaConfig = getattr(lambda_config, 'lambdaConfig')
else:
    from lambda_config import lambdaConfig

import logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        # logging.FileHandler("cloudformation_stack.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger()


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


class CloudformationStack(object):
    def __init__(self):
        self.aws_cloudformation = boto3.client(
            'cloudformation',
            region_name=os.getenv("region_name"),
            aws_access_key_id=os.getenv('aws_access_key_id'),
            aws_secret_access_key=os.getenv('aws_secret_access_key')
        )
        self.aws_s3 = boto3.resource(
            's3',
            aws_access_key_id=os.getenv('aws_access_key_id'),
            aws_secret_access_key=os.getenv('aws_secret_access_key')
        )
        self.aws_lambda = boto3.client(
            'lambda',
            aws_access_key_id=os.getenv('aws_access_key_id'),
            aws_secret_access_key=os.getenv('aws_secret_access_key')
        )

    @staticmethod
    def zip_dir(dirpath, fzip, is_package=True):
        basedir = os.path.dirname(dirpath) + '/'
        for root, dirs, files in os.walk(dirpath):
            # if os.path.basename(root)[0] == '.':
                # continue  # skip hidden directories
            dirname = root.replace(basedir, '')
            for f in files:
                # if f[-1] == '~' or (f[0] == '.' and f != '.htaccess'):
                    # skip backup files and all hidden files except .htaccess
                    # continue
                if not is_package:
                    dirname = ''
                fzip.write(root + '/' + f, dirname + '/' + f)

    def pack_aws_lambda(self, lambda_file, base, packages, package_files=[], files={}):
        fzip = zipfile.ZipFile(lambda_file, 'w', zipfile.ZIP_DEFLATED)
        base = "{root_path}/{base}".format(
            root_path=os.getenv('root_path'),
            base=base
        )
        self.zip_dir(base, fzip, is_package=False)
        for package in packages:
            self.zip_dir(
                "{site_packages}/{package}".format(
                    site_packages=os.getenv('site_packages'),
                    package=package
                ),
                fzip
            )
        for f in package_files:
            fzip.write(
                "{root_path}/deployment/{site_packages}/{file}".format(
                    root_path=os.getenv('root_path'),
                    site_packages=os.getenv('site_packages'),
                    file=f
                ),
                f
            )
        for f, path in files.items():
            fzip.write(
                "{path}/{file}".format(path=path, file=f), f
            )
        fzip.close()

    def pack_aws_lambda_layer(self, layer_file, packages, package_files=[], files={}):
        fzip = zipfile.ZipFile(layer_file, 'w', zipfile.ZIP_DEFLATED)
        for package in packages:
            self.zip_dir(
                "{site_packages}/{package}".format(
                    site_packages=os.getenv('site_packages'),
                    package=package
                ),
                fzip
            )
        for f in package_files:
            fzip.write(
                "{root_path}/deployment/{site_packages}/{file}".format(
                    root_path=os.getenv('root_path'),
                    site_packages=os.getenv('site_packages'),
                    file=f
                ),
                f
            )
        for f, path in files.items():
            fzip.write(
                "{path}/{file}".format(path=path, file=f), f
            )
        fzip.close()

    def upload_aws_s3_bucket(self, lambda_file, bucket):
        f = open(lambda_file, 'rb')
        self.aws_s3.Bucket(bucket).put_object(Key=lambda_file, Body=f)

    # Check if the stack exists.
    def _stack_exists(self, stack_name):
        stacks = self.aws_cloudformation.list_stacks()['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if stack_name == stack['StackName']:
                return True
        return False

    # Retrieve the last version of the object in a S3 bucket.
    def _get_object_last_version(self, s3_key):
        object_summary = self.aws_s3.ObjectSummary(os.getenv('bucket'), s3_key)
        return object_summary.get()['VersionId']

    def _get_layer_version_arn(self, layer_name):
        response = self.aws_lambda.list_layer_versions(
            LayerName=layer_name
        )
        assert len(response['LayerVersions']) > 0,\
             'Cannot find the lambda layer ({layer_name}).'.format(layer_name=layer_name)
        
        return response['LayerVersions'][0]['LayerVersionArn']

    @classmethod
    def deploy(cls):
        cf = cls()
        # Package and upload the code.
        for name, funct in lambdaConfig["functions"].items():
            if funct["update"]:
                lambda_file = "{function_name}.zip".format(function_name=name)
                cf.pack_aws_lambda(
                    lambda_file,
                    funct["base"],
                    funct["packages"],
                    package_files=funct["package_files"],
                    files=funct["files"]
                )
                cf.upload_aws_s3_bucket(lambda_file, os.getenv("bucket"))
                logger.info("Upload the lambda package.")

        for name, layer in lambdaConfig["layers"].items():
            if layer["update"]:
                layer_file = "{layer_name}.zip".format(layer_name=name)
                cf.pack_aws_lambda_layer(
                    layer_file,
                    layer["packages"],
                    package_files=layer["package_files"],
                    files=layer["files"]
                )
                cf.upload_aws_s3_bucket(layer_file, os.getenv("bucket"))
                logger.info("Upload the lambda layer package.")

        # Update the cloudformation stack.
        stack_name = os.getenv("stack_name")
        template = open("{stack_name}.json".format(stack_name=stack_name), "r")
        template = json.load(template)

        for key, value in template["Resources"].items():
            if value["Type"] == "AWS::Lambda::Function":
                function_name = value["Properties"]["FunctionName"]
                function_file = "{function_name}.zip".format(function_name=function_name)
                function_version = "{function_name}_version".format(function_name=function_name)
                template["Resources"][key]["Properties"]["Layers"] = [
                    (
                        layer if isinstance(layer, dict) else cf._get_layer_version_arn(layer)
                    ) for layer in template["Resources"][key]["Properties"]["Layers"]
                ]
                template["Resources"][key]["Properties"]["Code"] = {
                    "S3Bucket": os.getenv("bucket"),
                    "S3ObjectVersion": os.getenv(function_version, cf._get_object_last_version(function_file)),
                    "S3Key": function_file
                }
                template["Resources"][key]["Properties"]["Environment"]["Variables"] = dict(
                    (
                        k,
                        os.getenv(k, v)
                    ) for k, v in template["Resources"][key]["Properties"]["Environment"]["Variables"].items()
                )
            elif value["Type"] == "AWS::Lambda::LayerVersion":
                layer_name = value["Properties"]["LayerName"]
                layer_file = "{layer_name}.zip".format(layer_name=layer_name)
                layer_version = "{layer_name}_version".format(layer_name=layer_name)
                template["Resources"][key]["Properties"]["Content"] = {
                    "S3Bucket": os.getenv("bucket"),
                    "S3ObjectVersion": os.getenv(layer_version, cf._get_object_last_version(layer_file)),
                    "S3Key": layer_file
                }

        params = {
            "StackName": stack_name,
            "TemplateBody": json.dumps(template, indent=4),
            "Capabilities": ['CAPABILITY_NAMED_IAM'],
            "Tags": [
                {
                    "Key": 'autostack',
                    "Value": 'true'
                }
            ],
            "Parameters": []
        }
        if cf._stack_exists(stack_name):
            response = cf.aws_cloudformation.update_stack(**params)
        else:
            response = cf.aws_cloudformation.create_stack(**params)
        logger.info(
            json.dumps(response, indent=4, cls=JSONEncoder, ensure_ascii=False)
        )

        stack = cf.aws_cloudformation.describe_stacks(StackName=stack_name)["Stacks"][0]
        while (stack["StackStatus"].find("IN_PROGRESS") != -1):
            logger.info(
                json.dumps(stack["StackStatus"], indent=4, cls=JSONEncoder, ensure_ascii=False)
            )
            sleep(5)
            stack = cf.aws_cloudformation.describe_stacks(
                StackName=stack_name
            )["Stacks"][0]

        if stack["StackStatus"] == "CREATE_COMPLETE":
            logger.info(
                json.dumps(stack["StackStatus"], indent=4, cls=JSONEncoder, ensure_ascii=False)
            )
        else:
            logger.info(
                json.dumps(stack["StackStatus"], indent=4, cls=JSONEncoder, ensure_ascii=False)
            )


if __name__ == "__main__":
    CloudformationStack.deploy()
