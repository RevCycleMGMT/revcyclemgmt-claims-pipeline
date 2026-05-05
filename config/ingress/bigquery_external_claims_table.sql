CREATE EXTERNAL TABLE `<PROJECT_ID>.<DATASET>.claim_ingress_files`
OPTIONS (
  format = 'CSV',
  uris = ['gs://<CUSTOMER_CLAIM_INGRESS_BUCKET>/claims/*.csv'],
  skip_leading_rows = 1
);
