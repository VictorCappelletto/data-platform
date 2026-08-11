# HDL Ingest

Medallion product: **landing → bronze → silver** for synthetic `orders`.

## Run

```bash
export LAKE_ROOT=./data/lake PLATFORM_ENV=local
python -c "from hdl_ingest.pipelines.ingest import run_pipeline; print(run_pipeline())"
```

## Layers

| Layer | Content |
|-------|---------|
| landing | Raw CSV seed |
| bronze | Typed / normalized rows |
| silver | Deduped + `is_current` |
