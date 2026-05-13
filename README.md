# SSD Mini Lab

fio 기반 SSD 성능 검증 미니 프로젝트입니다. 단순한 최고 속도 측정보다 **조건-로그-파싱-시각화-해석** 흐름을 만들고, 평균 성능뿐 아니라 **tail latency, QoS, 반복 측정 재현성**을 함께 보는 것을 목표로 합니다.

현재 프로젝트는 SSD Validation Engineer 24주 로드맵 중 **1단계: fio 기반 SSD 검증 체계 만들기**를 진행 중입니다. 현재까지 baseline 실행/파싱, QD parameter sweep, QD sweep 재현성 분석까지 완료했습니다.

---

## 현재 진행 상태

| 영역 | 상태 | 산출물 |
|---|---:|---|
| fio JSON 파싱 | 완료 | `parse_fio_results.py`, `results/fio_summary.csv`, `results/qd_sweep_summary.csv` |
| baseline plot | 완료 | `plot_fio_summary.py`, `results/plots/` |
| QD sweep 분석 | 완료 | `analyze_qd_sweep.py`, `results/qd_sweep_grouped.csv`, `results/qd_sweep_plots/` |
| QD sweep 재현성 분석 | 완료 | `analyze_qd_reproducibility.py`, `results/qd_sweep_reproducibility.csv` |
| 문서화 | 진행 중 | `docs/notes/parameter_sweep.md`, `docs/reports/reproducibility_qd_sweep.md` |

로드맵 기준으로는 **Week 5 parameter sweep의 QD sweep 산출물 완료**, **Week 6 reproducibility 분석 1차 완료** 상태입니다.

---

## Repository 구조

```text
ssd-mini-lab/
├─ parse_fio_results.py
├─ plot_fio_summary.py
├─ analyze_qd_sweep.py
├─ analyze_qd_reproducibility.py
├─ docs/
│  ├─ notes/
│  │  └─ parameter_sweep.md
│  └─ reports/
│     └─ reproducibility_qd_sweep.md
├─ results/
│  ├─ fio_summary.csv
│  ├─ qd_sweep_summary.csv
│  ├─ qd_sweep_grouped.csv
│  ├─ qd_sweep_reproducibility.csv
│  ├─ plots/
│  └─ qd_sweep_plots/
└─ README.md
```

`results/`에는 실험 결과 CSV와 그래프가 저장됩니다. fio가 생성하는 임시 testfile은 `.gitignore`로 제외합니다.

---

## 사용 기술

- Python
- pandas
- matplotlib
- fio
- PowerShell / Windows 환경
- Git / GitHub

---

## 1. fio JSON 파싱

`parse_fio_results.py`는 fio JSON 결과를 읽어서 validation 관점의 주요 지표를 CSV로 정리합니다.

추출 지표:

- workload
- run number
- QD / iodepth
- bandwidth MiB/s
- IOPS
- mean completion latency
- p95 / p99 / p99.9 completion latency

### Baseline 결과 파싱

```powershell
cd D:\ssd_lab
python .\parse_fio_results.py
```

기본 출력:

```text
results/fio_summary.csv
```

### QD sweep 결과 파싱

```powershell
cd D:\ssd_lab
python .\parse_fio_results.py `
  --input-dir D:\ssd_lab\results\qd_sweep `
  --output D:\ssd_lab\results\qd_sweep_summary.csv
```

---

## 2. Baseline plot 생성

`plot_fio_summary.py`는 baseline workload 결과를 읽어서 workload별 bandwidth, IOPS, latency, run-to-run variation, CV summary를 생성합니다.

```powershell
cd D:\ssd_lab
python .\plot_fio_summary.py
```

기본 입력:

```text
results/fio_summary.csv
```

기본 출력:

```text
results/plots/
```

---

## 3. QD sweep 분석

`analyze_qd_sweep.py`는 `results/qd_sweep_summary.csv`를 읽어 QD별 평균/표준편차 요약 CSV와 그래프를 생성합니다.

```powershell
cd D:\ssd_lab
python .\analyze_qd_sweep.py
```

출력:

```text
results/qd_sweep_grouped.csv
results/qd_sweep_plots/qd_sweep_iops.png
results/qd_sweep_plots/qd_sweep_bandwidth.png
results/qd_sweep_plots/qd_sweep_p99_latency.png
results/qd_sweep_plots/qd_sweep_mean_latency.png
```

### QD sweep 주요 결과

| workload | QD | Avg Bandwidth (MiB/s) | Avg IOPS | Avg p99 latency (us) |
|---|---:|---:|---:|---:|
| rand_read | 1 | 20.41 | 5,225.49 | 286.04 |
| rand_read | 4 | 80.79 | 20,681.08 | 314.71 |
| rand_read | 16 | 203.94 | 52,207.00 | 505.86 |
| rand_read | 32 | 209.96 | 53,749.12 | 804.18 |
| rand_write | 1 | 46.06 | 11,790.25 | 108.37 |
| rand_write | 4 | 124.41 | 31,849.25 | 158.72 |
| rand_write | 16 | 126.64 | 32,418.56 | 607.57 |
| rand_write | 32 | 122.55 | 31,371.02 | 1,280.68 |

### QD sweep 해석

- `rand_read`는 QD16까지 IOPS와 bandwidth가 크게 증가하고, QD32에서는 증가폭이 작아집니다.
- `rand_write`는 QD4~QD16에서 처리량이 거의 포화되고, QD32에서는 IOPS가 오히려 감소합니다.
- p99 latency는 read/write 모두 QD가 높아질수록 증가합니다.
- 특히 `rand_write QD32`는 처리량 이득이 거의 없고 p99 latency가 크게 악화되어 QoS 관점에서 불리합니다.

---

## 4. QD sweep 재현성 분석

`analyze_qd_reproducibility.py`는 같은 QD/workload 조건에서 3회 반복 실행한 결과의 run-to-run variation을 분석합니다.

```powershell
cd D:\ssd_lab
python .\analyze_qd_reproducibility.py
```

출력:

```text
results/qd_sweep_reproducibility.csv
results/qd_sweep_plots/qd_sweep_iops_cv.png
results/qd_sweep_plots/qd_sweep_bandwidth_cv.png
results/qd_sweep_plots/qd_sweep_p99_cv.png
results/qd_sweep_plots/qd_sweep_p99_run_to_run.png
```

### CV 기준

```text
CV = standard deviation / mean
```

CV가 낮을수록 같은 조건에서 반복 측정 결과가 안정적입니다.

### 재현성 분석 주요 결과

| 관점 | 가장 큰 변동 조건 | CV |
|---|---|---:|
| bandwidth | rand_read QD16 | 0.0639 |
| IOPS | rand_read QD16 | 0.0639 |
| p99 latency | rand_write QD32 | 0.0943 |

### 재현성 해석

- 대부분의 IOPS/BW CV는 약 0.006~0.064 범위로, 반복 측정의 재현성은 전반적으로 나쁘지 않습니다.
- p99 latency CV는 약 0.008~0.094 범위로, 평균 처리량보다 tail latency가 더 민감하게 흔들릴 수 있음을 보여줍니다.
- `rand_write QD32`는 p99 latency 수준과 변동성이 모두 높아 추가 분석 후보 조건입니다.

---

## Validation 관점의 핵심 포인트

이 프로젝트는 단순히 “속도가 얼마나 빠른가”를 측정하는 데서 끝내지 않습니다.

현재까지의 핵심 관찰은 다음과 같습니다.

1. QD를 높이면 처리량이 증가할 수 있지만, 일정 지점 이후에는 성능 포화와 tail latency 악화가 나타납니다.
2. 최고 IOPS 조건이 항상 좋은 조건은 아닙니다.
3. 평균 bandwidth/IOPS와 p99 latency를 함께 봐야 QoS 관점의 해석이 가능합니다.
4. 반복 실행 CV를 통해 측정값의 신뢰성과 흔들림을 함께 판단할 수 있습니다.
5. 현재 결과만으로 SSD 내부 원인, 예를 들어 GC, SLC cache, thermal throttling 등을 단정하지 않습니다.

---

## 현재 한계

- 단일 SSD와 단일 시스템 환경에서 수행한 결과입니다.
- QD sweep은 30초 단기 테스트이므로 sustained workload 특성은 아직 확인하지 않았습니다.
- 각 조건은 3회 반복이므로 통계적으로 충분한 표본은 아닙니다.
- SSD 내부 동작 원인은 현재 실험만으로 직접 증명할 수 없습니다.

---

## 다음 작업

로드맵 기준 다음 후보는 아래 중 하나입니다.

1. **Week 7 — direct I/O vs buffered I/O**
   - OS page cache 영향과 storage 자체 성능을 구분하는 실험

2. **Week 8 — 1단계 정리 주간**
   - README 보강
   - 실험 절차 문서화
   - Stage 1 review 작성

3. **추가 parameter sweep**
   - block size sweep
   - numjobs sweep

현재는 QD sweep과 재현성 분석을 마쳤으므로, 다음 단계는 **direct I/O vs buffered I/O** 또는 **Stage 1 review 정리**가 적절합니다.

---

## Commit history checkpoint

- `Add QD sweep analysis outputs`
- `Add QD sweep reproducibility analysis`
- `Add project README`

---

## Project goal

이 미니랩의 목표는 벤치마크 도구를 많이 실행해보는 것이 아닙니다.

목표는 **실험 조건을 통제하고, 결과를 자동으로 정리하며, 그래프와 문서로 해석 가능한 검증 흐름을 만드는 것**입니다.
