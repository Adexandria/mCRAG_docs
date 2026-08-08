#!/usr/bin/env bash

set -euo pipefail

MIMETYPE="html"
SKIP_INGESTION=false
SKIP_TESTCASES=false
EXPERIMENT_ID=""
QUERY=""
MEDIA_PATH="docs_output"
USE_BASE_RETRIEVER=false

INFERENCE_MODULE="evaluation.test_case.inference"

INGEST_MODULE="app.retriever.ingest_document"

CORRECTIVE_MODULE="app.crag.complier.corrective"

BASE_MODULE="app.crag.complier.base_complier"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --query)           QUERY="$2"; shift 2 ;;
    --experiment-id)   EXPERIMENT_ID="$2"; shift 2 ;;
    --media-path)       MEDIA_PATH="$2"; shift 2 ;;
    --mimetype)        MIMETYPE="$2"; shift 2 ;;
    --use-base-retriever)  USE_BASE_RETRIEVER=true; shift ;;
    --skip-testcases)  SKIP_TESTCASES=true; shift ;;
    --skip-ingest)     SKIP_INGESTION=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$QUERY" ]]; then
  echo "ERROR: --query is required" >&2
  exit 1
fi

if [[ -z "$EXPERIMENT_ID" ]]; then
  echo "ERROR: --experiment-id is required" >&2
  exit 1
fi


case "$MIMETYPE" in
  html|pdf|md) ;;
  *) echo "ERROR: --mimetype must be one of html, pdf, md (got '$MIMETYPE')" >&2; exit 1 ;;
esac

run_stage() {
  local name="$1"; shift
  local module="$1"; shift

  echo ""
  echo "============================================================"
  echo "[$name] python -m $module $*"
  echo "============================================================"

  local start end elapsed
  start=$(date +%s)

  if ! python -m "$module" "$@"; then
    echo ""
    echo "PIPELINE FAILED at [$name] — aborting. See output above." >&2
    exit 1
  fi

  end=$(date +%s)
  elapsed=$((end - start))
  echo "[$name] completed in ${elapsed}s"
}

PIPELINE_START=$(date +%s)

if [[ "$SKIP_TESTCASES" == false ]]; then
  run_stage "1/3 inference" "$INFERENCE_MODULE"
else
  echo ""
  echo "[1/3 inference] skipped (--skip-testcases)"
fi
 
if [[ "$SKIP_INGESTION" == false ]]; then
  run_stage "2/3 ingest" "$INGEST_MODULE" --experiment-id "$EXPERIMENT_ID"
else
  echo ""
  echo "[2/3 ingest] skipped (--skip-ingest)"
fi

if [[ "${USE_BASE_RETRIEVER}" == true ]]; then
  echo ""
  echo "============================================================"
  echo "Using base retriever for the final stage"
  echo "============================================================"
  run_stage "3/3 base workflow" "$BASE_MODULE" \
    --query "$QUERY" \
    --experiment-id "$EXPERIMENT_ID" \
    --mimetype "$MIMETYPE"\
    --media-path "$MEDIA_PATH"
else
  echo ""
  echo "============================================================"
  echo "Using corrective retriever for the final stage"
  echo "============================================================"
  run_stage "3/3 corrective workflow" "$CORRECTIVE_MODULE" \
    --query "$QUERY" \
    --experiment-id "$EXPERIMENT_ID" \
    --mimetype "$MIMETYPE"\
    --media-path "$MEDIA_PATH"
fi

PIPELINE_END=$(date +%s)
echo "OUTPUT_PATH=${MEDIA_PATH}"
echo ""
echo "============================================================"
echo "Pipeline completed successfully in RUNTIME=$((PIPELINE_END - PIPELINE_START))s"
echo "============================================================"
 