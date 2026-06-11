# Example Inputs And Samples

## Golden-set samples (model-generated, Phase 2)

`sample_rca_1.json` … `sample_rca_4.json` were generated live with
`qwen2.5:7b` and prompt `v2` from the four golden incidents in
`eval/golden_set.jsonl`:

1. Login API returns HTTP 500 immediately after a deployment.
2. Checkout requests time out after a database migration.
3. Background invoice jobs stopped running after a scheduler change.
4. CPU usage spikes after enabling a new analytics endpoint.

## Method fixtures (hand-written, Phase 4)

`sample_rca_fishbone_fixture.json` and `sample_rca_fault_tree_fixture.json`
are hand-written fixtures used to develop the method-aware PDF/HTML renderers.
They follow the exact `method_detail` shapes the v3 prompts request. Replace
them with live model output once the Phase 4 loop has been run against Ollama:

```powershell
python -m agentic_rca "checkout requests time out after a database migration" --method fishbone
python -m agentic_rca "background invoice jobs stopped running after a scheduler change" --method fault_tree
```
