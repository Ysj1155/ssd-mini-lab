# Parameter Sweep - Queue Depth

## 목적
- fio random read/write workload에서 queue depth 변화가 IOPS, bandwidth, p99 latency에 미치는 영향을 확인한다.

## 실험 조건
- Workload: rand_read, rand_write
- Block size: 4K
- QD: 1, 4, 16, 32
- 반복 횟수: 각 조건 3회
- Runtime: 30초
- Direct I/O: enabled
- 입력 파일: results/qd_sweep_summary.csv
- 요약 파일: results/qd_sweep_grouped.csv
- 그래프 폴더: results/qd_sweep_plots/

## 결과 요약
- rand_read는 QD16까지 IOPS가 증가하고, QD32에서는 증가폭이 작아진다.
- rand_write는 QD4~QD16에서 처리량이 거의 포화되고, QD32에서는 오히려 IOPS가 감소한다.
- p99 latency는 read/write 모두 QD가 높아질수록 증가한다.
- 특히 rand_write는 QD16 이후 tail latency 악화가 뚜렷하다.

## 해석
- QD 증가는 병렬성을 높여 처리량을 개선할 수 있지만, 일정 지점 이후에는 latency penalty가 커진다.
- 이 실험 환경에서는 read는 QD16~32 근처에서 처리량 포화가 나타난다.
- write는 QD4 이후 처리량 이득이 작고, QD16~32에서 p99 latency가 급격히 악화된다.
- 따라서 단순 최고 IOPS만 볼 경우 QD32 read가 좋아 보일 수 있지만, QoS 관점에서는 p99 latency 증가를 함께 봐야 한다.

## 한계
- 단일 SSD와 단일 시스템 환경에서 측정한 결과이므로 일반화는 제한적이다.
- 30초 단기 테스트이므로 sustained workload 특성은 아직 확인하지 않았다.
- SSD 내부 GC, SLC cache, thermal throttling 등의 원인을 직접 증명한 것은 아니다.

## 다음 작업
- QD sweep 결과를 README 또는 baseline report에 요약한다.
- 반복 실행 결과의 표준편차/CV를 사용해 Week 6 재현성 분석으로 확장한다.
- 이후 direct I/O vs buffered I/O 또는 장시간 sustained test로 넘어간다.