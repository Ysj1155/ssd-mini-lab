# Korean Interview Brief

## 30-Second Project Summary

이 프로젝트는 fio를 사용해서 SSD 성능을 단순 측정하는 데서 끝내지 않고, 테스트 조건 정의, 결과 파싱, 재현성 확인, tail latency 분석, 경로/cache 영향 분리, sustained workload 관찰까지 확장한 SSD validation mini-lab입니다.

처음에는 sequential/random read/write baseline을 만들었고, 이후 queue depth, direct/buffered I/O, WSL 경로 차이, QoS 지표, sustained smoke test로 실험 범위를 넓혔습니다. 핵심 목표는 가장 높은 IOPS를 찾는 것이 아니라, 어떤 조건에서 결과가 안정적이고 해석 가능한지 검증하는 흐름을 만드는 것이었습니다.

## 60-Second Project Summary

이 프로젝트에서는 fio JSON 결과를 Python으로 파싱해서 CSV와 그래프로 정리하는 반복 가능한 분석 파이프라인을 만들었습니다.

Baseline 이후에는 queue depth sweep을 통해 QD 증가가 IOPS를 높이지만 p99 latency도 증가시킬 수 있다는 점을 확인했습니다. 또한 반복 실행 결과를 CV로 비교해서 단일 실행 결과만으로 판단하지 않도록 했습니다.

Direct I/O와 buffered I/O 비교에서는 buffered 결과가 더 좋아 보일 수 있지만, 이것을 SSD 자체 성능 향상으로 단정하지 않고 OS/filesystem cache 영향으로 해석했습니다. WSL 비교에서는 WSL ext4와 `/mnt/d` 경로가 서로 다른 테스트 경로라는 점을 확인했고, 경로 자체도 테스트 조건으로 명시해야 한다는 것을 배웠습니다.

최근에는 QoS 관점에서 p99, p99.9, CV를 모아 평균 IOPS만으로는 validation 판단이 부족하다는 점을 정리했고, sustained smoke test를 추가해 시간에 따른 성능 변화와 latency spike 후보를 보기 시작했습니다.

## Strong Interview Points

### 1. 평균 성능보다 검증 조건을 먼저 본다

말할 포인트:

> 저는 fio 결과를 볼 때 평균 bandwidth나 IOPS만 보지 않고, workload, block size, queue depth, direct mode, path, runtime 같은 조건을 먼저 고정하려고 했습니다. 조건이 명확하지 않으면 숫자 비교 자체가 위험하다고 봤습니다.

연결되는 파일:

- `parse_fio_results.py`
- `docs/reports/baseline_v1.md`
- `docs/reports/ssd_validation_competency_map.md`

### 2. 평균 IOPS만으로는 충분하지 않다

말할 포인트:

> QD sweep에서 IOPS가 좋아지는 조건이 항상 좋은 조건은 아니었습니다. QD가 올라가면 처리량은 증가할 수 있지만 p99 latency도 같이 커질 수 있어서, validation에서는 평균 성능과 tail latency를 같이 봐야 한다고 정리했습니다.

연결되는 파일:

- `docs/reports/reproducibility_qd_sweep.md`
- `docs/reports/qos_tail_latency_review.md`

### 3. 재현성을 별도 지표로 본다

말할 포인트:

> 같은 조건을 반복 실행하고 CV를 계산해서 run-to-run variation을 확인했습니다. 단일 benchmark 결과보다 반복 실행 시 변동성이 얼마나 되는지가 validation 관점에서 더 중요할 수 있다고 봤습니다.

연결되는 파일:

- `analyze_qd_reproducibility.py`
- `results/qd_sweep_reproducibility.csv`

### 4. 경로와 cache 효과를 구분하려고 했다

말할 포인트:

> direct I/O와 buffered I/O 결과가 다르게 나왔을 때 buffered가 빠르다고 해서 SSD media가 빠르다고 해석하지 않았습니다. OS cache나 filesystem 영향이 섞일 수 있으므로, 이것을 별도 테스트 경로로 보고 한계를 문서화했습니다.

연결되는 파일:

- `docs/reports/direct_buffered_week7.md`
- `docs/reports/wsl_path_compare_week9.md`

### 5. 실험 한계를 명확히 말할 수 있다

말할 포인트:

> 현재 실험은 file-based fio 테스트이기 때문에 NAND, FTL, garbage collection, thermal throttling 같은 내부 원인을 직접 증명하지는 못합니다. 대신 어떤 수준까지 말할 수 있고 어떤 부분은 추가 telemetry나 raw device 테스트가 필요한지 구분하려고 했습니다.

연결되는 파일:

- `README.md`
- `docs/reports/ssd_validation_competency_map.md`

### 6. sustained workload로 안정성을 보기 시작했다

말할 포인트:

> 짧은 benchmark만으로는 시간이 지나면서 성능이나 latency가 어떻게 변하는지 보기 어렵기 때문에 sustained smoke test를 추가했습니다. 첫 run에서는 first third와 last third를 비교했고, max latency와 time-window average latency spike 후보를 분리해서 해석했습니다.

연결되는 파일:

- `run_sustained_smoke.ps1`
- `analyze_sustained_smoke.py`
- `docs/reports/sustained_workload_week10.md`

## Questions I Can Answer With This Project

### Q. 왜 fio를 썼나요?

fio는 workload, block size, queue depth, direct mode, runtime 등을 명시적으로 제어할 수 있어서 storage validation 연습에 적합하다고 봤습니다. 단순 벤치마크 툴보다 테스트 조건을 직접 설계하고 JSON 결과를 파싱할 수 있다는 점이 좋았습니다.

### Q. 가장 중요한 배움은 무엇인가요?

가장 큰 배움은 높은 평균 IOPS가 곧 좋은 validation 결과는 아니라는 점입니다. p99, p99.9, 반복 실행 variation, path/cache 영향까지 같이 봐야 숫자를 안전하게 해석할 수 있었습니다.

### Q. 이 프로젝트의 한계는 무엇인가요?

현재는 file-based 테스트라서 SSD 내부 동작을 직접 증명하지 못합니다. Windows filesystem, WSL path, OS cache, 외장 SSD의 경우 USB/enclosure 영향이 섞일 수 있습니다. 그래서 보고서마다 path와 direct mode를 명시하고, 내부 원인 추정은 조심스럽게 제한했습니다.

### Q. 다음에 개선한다면 무엇을 하겠나요?

먼저 sustained smoke test를 3회 이상 반복해서 p99, p99.9, max latency, spike 후보, first-vs-last ratio의 변동성을 확인하겠습니다. 그 다음 더 긴 runtime으로 확장하고, 가능하다면 SMART/NVMe telemetry를 함께 수집해서 성능 변화와 장치 상태를 같이 보겠습니다.

## Resume Bullet Candidates

- Built a fio-based SSD validation mini-lab with repeatable JSON parsing, CSV summarization, and latency/throughput visualization.
- Compared queue-depth scaling, direct vs buffered I/O, WSL path effects, and sustained workload behavior.
- Analyzed p99/p99.9 latency, run-to-run CV, first-vs-last sustained windows, and latency-spike candidates.
- Documented test limitations to avoid over-claiming device-internal causes from file-based benchmarks.

## Obsidian TIL Draft

오늘 배운 점:

평균 IOPS는 validation에서 출발점일 뿐 결론이 아니다. 같은 평균 성능이라도 p99 latency가 크거나 반복 실행 변동성이 크면 실제 안정성은 다르게 평가될 수 있다.

또한 fio 결과는 항상 테스트 경로와 함께 해석해야 한다. direct I/O인지 buffered I/O인지, WSL ext4인지 `/mnt/d`인지, Windows filesystem이 개입됐는지에 따라 숫자의 의미가 달라진다.

좋은 테스트 엔지니어링은 숫자를 많이 모으는 것이 아니라, 어떤 조건에서 얻은 숫자인지 설명하고 그 숫자로 무엇을 말할 수 없는지도 분명히 아는 것이라고 느꼈다.
