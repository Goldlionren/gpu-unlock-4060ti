# Published numerical evidence

These JSON files preserve the measured rates, latency samples, numeric errors, seed, software/source identity and sampled operating telemetry from the original stock/cold/warm runs. GPU UUID, PCI address and host timestamps were removed from benchmark exports; raw host diagnostic logs and board PROM are not published. The comparison files preserve all metadata-match results from the original complete local records.

- stock/cold/warm-gemm.json: all 2048/4096/8192 results, including unsupported E5M2 and failed FP8 thresholds.
- cold-comparison.json and warm-comparison.json: stock-versus-unlocked ratios and numerical status.
- stock-fp8-numerics.json and unlocked-fp8-numerics.json: 12 targeted FP8 cases; values match exactly.

Power and clocks are point samples, not continuous measurements. The original comparison script expects complete private telemetry fields; use its saved comparison output when reading these sanitized exports. Raw source logs remain local and their absence must not be interpreted as additional testing.
