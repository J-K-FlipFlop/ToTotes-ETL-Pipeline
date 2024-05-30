import boto3
from botocore.exceptions import ClientError
import ast
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_secret() -> dict:
    """Looks up Totesys database credentials from AWS SecretsManager and
    returns them as a dictionary

    Returns:
        Dictionary containing secret keys/values

    Raises:
        ClientError if unable to get secrets from AWS"""

    secret_name = "totesys-blackwater-credentials"
    region_name = "eu-west-2"

    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager", region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        logger.error(e)
        raise e

    secret = get_secret_value_response["SecretString"]
    logger.info("Totesys datbase credentials accessed")
    return ast.literal_eval(secret)
