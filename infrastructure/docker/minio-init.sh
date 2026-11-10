#!/bin/sh
set -eu

MC_CFG="/tmp/.mc"

until mc --config-dir "${MC_CFG}" alias set local "http://minio:9000" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  echo "Waiting for MinIO endpoint..."
  sleep 2
done

mc --config-dir "${MC_CFG}" mb --ignore-existing "local/${S3_BUCKET_PUBLIC}"
mc --config-dir "${MC_CFG}" mb --ignore-existing "local/${S3_BUCKET_PRIVATE}"

# Enforce private-by-default permissions on BOTH buckets (zero blanket public read).
mc --config-dir "${MC_CFG}" anonymous set none "local/${S3_BUCKET_PUBLIC}"
mc --config-dir "${MC_CFG}" anonymous set none "local/${S3_BUCKET_PRIVATE}"

echo "Bucket anonymous policies verified:"
echo "  ${S3_BUCKET_PUBLIC}: $(mc --config-dir "${MC_CFG}" anonymous get "local/${S3_BUCKET_PUBLIC}")"
echo "  ${S3_BUCKET_PRIVATE}: $(mc --config-dir "${MC_CFG}" anonymous get "local/${S3_BUCKET_PRIVATE}")"
