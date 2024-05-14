resource "aws_lambda_function" "extract_lambda" {
  function_name = "extract_lambda"
  s3_bucket = aws_s3_bucket.extract_lambda_storage.bucket
  s3_key = "lambda/extract_lambda.zip"
  role = aws_iam_role.extract_lambda_role.arn
  handler = "handler.lambda_handler"
  runtime = "python3.11"
}

data "archive_file" "extract_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/handler.py"
  output_path = "${path.module}/../function.zip"
}