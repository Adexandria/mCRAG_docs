SECTION_ROUTING = {
    "summary":       ["info"],
    "performance":   ["info", "metrics"],
    "configuration": ["info", "params"],
    "lineage":       ["info", "outputs"],       
    "metadata":      ["info", "tags"],
}


PREFIX_ROUTING = {
    "info":    "info.",
    "metrics": "data.metrics.",
    "params":  "data.params.",
    "tags":    "data.tags.",
    "inputs":  "inputs.",
    "outputs": "outputs.",
}


SECTION ={
    "summary":       "info",
    "performance":   "metrics",
    "configuration": "params",
    "lineage":       "outputs inputs",
    "metadata":      "tags",
}


# Extract keywords from the flattened run data based on the defined PREFIX_ROUTING and ignoring certain stop terms and prefixes.
STOP_TERMS = {
    "uri",
    "artifact",
    "uuid",
    "id",
    "time",
    "mlflow",
    "source",
}

SKIP_PREFIXES = (
    "info.artifact_uri",
    "info.start_time",
    "info.end_time",
)

# Location of the corpus vocabulary JSON file, which contains the vocabulary for each section.
CORPUS_VOCAB_PATH = "corpus_vocab.json"