# MLFlow CRAG Documentation

Automated MLflow experiment documentation using Corrective Retrieval-Augmented Generation (CRAG). The pipeline retrieves experiment data from MLflow, validates it structurally, and generates evidence-grounded documentation , with corrective loops that rewrite queries using corpus vocabulary when retrieval misses, and an LLM judge that verifies every generated claim against the MLflow evidence.

## Project structure

```
app/
├── crag/                     # The CRAG pipeline
│   ├── graph.py              # Graph wiring for both workflows: corrective and base (non-corrective)
│   ├── nodes.py              # Graph nodes: retrieval, structural grading, claim grading, aggregation, generation
│   ├── llm.py                # All LLM calls: generation, query rewriting, judge
│   ├── prompt.py             # Prompt templates used by the LLM functions
│   ├── response.py           # Pydantic models for LLM JSON responses
│   ├── state.py              # Graph state definition
│   ├── vector_stores.py      # Chroma vector store setup
│   └── compiler/
│       ├── base_compiler.py  # Runs and tests the base graph workflow
│       └── corrective.py     # Runs and tests the corrective graph workflow
├── docs/
│   ├── extract_template.py   # Fills the documentation template; outputs HTML / Markdown / PDF
│   └── response.py           # Response models for the documentation template
├── retriever/
│   ├── extract_data.py       # Fetches experiment data from the MLflow server
│   └── ingest_document.py    # Chunks and ingests runs into the vector store
├── evaluation/
│   └── test_case/
│       └── inference.py      # Reproducible MLflow runs for testing
├── template/                 # Documentation template files
└── config.py                 # Project configuration
```

## Installation

1. Install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. *(Optional — PDF output on Windows)* Install [MSYS2](https://www.msys2.org/) and the GTK runtime required by WeasyPrint:

   ```bash
   pacman -S mingw-w64-x86_64-gtk3
   ```

   HTML and Markdown output work without this step.

3. Set your Anthropic API key in the env file

## Usage

1. **Start the MLflow server:**

   ```bash
   uvx mlflow server
   ```

2. **Create reproducible test runs:**

   ```bash
   python -m app.evaluation.test_case.inference
   ```

3. **Ingest the experiment data** into the vector store:

   ```bash
   python -m app.retriever.ingest_document
   ```

4. **Run the corrective workflow:**

   ```bash
   python -m app.crag.compiler.corrective
   ```

   To run the baseline (non-corrective) workflow instead:

   ```bash
   python -m app.crag.compiler.base_compiler
   ```

## Running the pipeline via script

1. **Start the MLflow server:**

```bash
   uvx mlflow server
```

2. **First run only** — generates test data, ingests it, and runs the corrective workflow:

```bash
   ./run_pipeline.sh --query "Which attempt gave the best result" --experiment-id 1
```

3. **Subsequent runs** — reuse existing data and just run the corrective workflow:

```bash
   ./run_pipeline.sh --query "Which attempt gave the best result" --experiment-id 1 \
     --skip-testcases --skip-ingest
```

4. **Base (non-corrective) workflow** — same as above, using plain retrieval instead:

```bash
   ./run_pipeline.sh --query "Which attempt gave the best result" --experiment-id 1 \
     --skip-testcases --skip-ingest --use-base-retriever
```


## How it works

```
query → retrieve → grade structure → aggregate → generate → judge
              ↑                                             │
              └─────────transform query (corpus vocabulary)←┘
                        (bounded retries)
```

- **Structural grading** — because MLflow is the ground truth, retrieved data cannot be factually wrong, only incomplete: grading validates metadata anchors and field-group coverage instead of semantic relevance.
- **Corrective loop** — when retrieval misses the field groups a question needs, the query is rewritten into vocabulary harvested from the corpus itself and retrieval is retried (bounded).
- **claim-graded answers** — a judge verifies every claim in the generated answer against the MLflow evidence; verdicts (`supported`, `data_insufficient`, `unsupported`, …) are stamped on the final document. If verdict is supported or retries is greater than two, it generates documentation.

## Output

Documentation is rendered from a template into HTML, Markdown, or PDF, including the query, the judged response, and run information cards traceable to MLflow run IDs.


## Using the GitHub Action Workflow

This action automates the Corrective RAG (Retrieval-Augmented Generation) pipeline for MLFlow experiment documentation. The workflow is triggered manually to accept a user-provided query and experiment ID.

The pipeline consists of three main stages:

1. **Generate test data (optional)**: Populates an MLFlow experiment with reproducible sample runs. This step creates 22 synthetic runs if enabled, useful for demonstration purposes.

2. **Data ingestion**: Ingests experiment runs into a Chroma vector store and builds a searchable vocabulary from the run artifacts. This vocabulary enables semantic retrieval during documentation generation.

3. **Generate documentation**: Executes a corrective retrieval workflow to extract relevant experiment information and compile it into structured documentation in your chosen format (HTML, PDF, or Markdown).


## Inputs Reference Table
| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `experiment-id` | Yes | — | MLFlow experiment ID |
| `query` | Yes | — | Documentation query/focus |
| `mlflow-tracking-uri` | No | `http://127.0.0.1:5000` | MLFlow server endpoint |
| `start-mlflow-server` | No | `false` | Start local server if unreachable |
| `skip-testcases` | No | `true` | Skip synthetic data generation |
| `anthropic-api-key` | Yes | — | Anthropic API key |
| `output-format` | No | `html` | Output format: `html`, `markdown`, `pdf` |

### Usage

Full input options are documented in [action.yml](action.yml).

**Local MLFlow server with test data**:
```yaml
steps:
  - uses: ./
    with: 
      query: ${{ github.event.inputs.query }}
      experiment-id: ${{ github.event.inputs.experiment_id }}
      start-mlflow-server: true
      skip-testcases: false
      anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Remote MLFlow server with test data**:
```yaml
steps:
  - uses: ./
    with: 
      query: ${{ github.event.inputs.query }}
      experiment-id: ${{ github.event.inputs.experiment_id }}     
      mlflow-tracking-uri: ${{ vars.MLFLOW_TRACKING_URI }}     
      skip-testcases: false
      anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Basic (existing experiments only)**:
```yaml
steps:
  - uses: ./
    with: 
      query: ${{ github.event.inputs.query }}
      experiment-id: ${{ github.event.inputs.experiment_id }}     
      mlflow-tracking-uri: ${{ vars.MLFLOW_TRACKING_URI }}     
      anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Specify output format**:
Default is HTML. Set `output-format` to `pdf` or `markdown`:
```yaml
- uses: ./
  with: 
    query: ${{ github.event.inputs.query }}
    experiment-id: ${{ github.event.inputs.experiment_id }}     
    mlflow-tracking-uri: ${{ vars.MLFLOW_TRACKING_URI }}     
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    output-format: pdf
```
