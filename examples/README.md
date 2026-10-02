# Examples

## Outage investigation

`outage-investigation.json` is the primary human-readable end-to-end demo. It contains:

- supporting and opposing observations;
- proposition dependencies;
- four candidate root causes;
- two aliases that compile to one semantic CID;
- a known expected winner used only for validation metadata.

Run:

```bash
qids-cam demo --problem examples/outage-investigation.json
qids-cam compare --problem examples/outage-investigation.json
```

## Minimal RAG adapter

`rag_adapter.py` shows the integration seam between retrieval/NLI output and QIDS-CAM. It uses a fixed corpus so it remains deterministic and dependency-free.

```bash
python -m examples.rag_adapter
qids-cam verify results/rag-adapter-proof.json
```

Replace the example `retrieve` and evidence labeling with a vector/lexical retriever and a calibrated contradiction evaluator. Include all relevant evaluator, corpus, and policy versions in the constraint context when declaring the constraint namespace. This release starts fresh caches on each solve.
