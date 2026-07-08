# GenEval2 Masked Multi-Turn Length Stats

- Model/tokenizer: `/root/private_data/agentic_image/models/Qwen3-VL-8B-Instruct`
- Template: `qwen3_vl_nothink`
- Primary summary: train + val

## Train + Val

- count: `193`
- average: `14963.5`
- median: `16550`
- p90: `25488`
- p95: `26351`
- p99: `27849`
- max: `29182`

## Split Summaries

### train
- count: `179`
- average: `14711.7`
- median: `16437`
- p90: `25338`
- p95: `26351`
- p99: `27611`
- max: `29182`

### val
- count: `14`
- average: `18183.3`
- median: `18234`
- p90: `26051`
- p95: `26051`
- p99: `28130`
- max: `28130`

### test
- count: `14`
- average: `20518.9`
- median: `18738`
- p90: `26634`
- p95: `26634`
- p99: `28581`
- max: `28581`

## Cutoff Candidates

- `4096`: exceeding train+val rows=`164`, turn_mask=false target truncations=`235`
- `8192`: exceeding train+val rows=`138`, turn_mask=false target truncations=`134`
- `12288`: exceeding train+val rows=`128`, turn_mask=false target truncations=`97`
- `16384`: exceeding train+val rows=`99`, turn_mask=false target truncations=`37`
- `32768`: exceeding train+val rows=`0`, turn_mask=false target truncations=`0`

## Recommendation

- Recommended cutoff_len: `32768`
- Any turn_mask=false assistant target truncated at recommendation: `False`

PASS
