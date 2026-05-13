# QD Sweep Reproducibility Report

## 목적
- QD sweep 결과의 반복 실행 안정성을 확인한다.
- 평균 성능뿐 아니라 run-to-run variation과 CV를 통해 측정값 신뢰도를 점검한다.

## 입력 데이터
- `results/qd_sweep_summary.csv`
- workload: `rand_read`, `rand_write`
- QD: 1, 4, 16, 32
- 반복 횟수: 각 조건 3회

## 산출물
- `results/qd_sweep_reproducibility.csv`
- `results/qd_sweep_plots/qd_sweep_iops_cv.png`
- `results/qd_sweep_plots/qd_sweep_bandwidth_cv.png`
- `results/qd_sweep_plots/qd_sweep_p99_cv.png`
- `results/qd_sweep_plots/qd_sweep_p99_run_to_run.png`

## 결과 요약
- 대부분의 IOPS/BW CV는 약 0.006~0.064 범위로 나타났다.
- p99 latency CV는 약 0.008~0.094 범위로 나타났다.
- 처리량 기준으로 가장 큰 변동성은 `rand_read QD16`에서 나타났다.
- p99 latency 기준으로 가장 큰 변동성은 `rand_write QD32`에서 나타났다.

## 해석
- 전체적으로 반복 측정의 재현성은 나쁘지 않다.
- 그러나 tail latency는 평균 성능보다 workload와 QD 변화에 더 민감하게 반응했다.
- `rand_write QD32`는 처리량 이득이 크지 않으면서 p99 latency 수준과 변동성이 모두 높아 QoS 관점에서 불리한 조건이다.
- 따라서 QD sweep 해석에서는 최고 IOPS뿐 아니라 p99 latency와 CV를 함께 봐야 한다.

## 한계
- 각 조건당 반복 횟수는 3회이므로 통계적으로 충분한 표본은 아니다.
- 30초 단기 테스트이므로 장시간 sustained workload의 안정성은 아직 확인하지 않았다.
- SSD 내부 동작 원인, 예를 들어 GC, SLC cache, thermal throttling 등은 이 결과만으로 단정할 수 없다.

## 다음 작업
- Week 6 결과를 README 또는 stage report에 요약한다.
- 필요하면 반복 횟수를 5회로 늘려 같은 분석을 재실행한다.
- 이후 Week 7 direct I/O vs buffered I/O 또는 Week 8 1단계 정리로 진행한다.