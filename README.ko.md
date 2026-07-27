# 외장 SSD Black-Box Validation Portfolio

fio, Python, PowerShell로 외장 SSD를 실제 DUT(Device Under Test)로 다루고,
요구사항부터 판정까지 추적 가능한 검증 흐름을 만든 프로젝트입니다.

```text
요구사항
-> 통제 조건
-> runner / observer
-> raw evidence
-> analyzer
-> verdict
```

이 프로젝트의 목표는 가장 높은 벤치마크 숫자를 얻는 것이 아닙니다.
같은 질문을 다시 검증할 수 있도록 조건과 증거를 남기고, 성능·QoS·무결성
판정과 해석 한계를 분리하는 것이 목표입니다.

## 1. 검증 경계

| 항목 | 범위 |
|---|---|
| DUT | SanDisk 외장 SSD |
| 접근 방식 | Windows에서 fio file target 사용 |
| 경로 | USB → 외장 SSD bridge/enclosure → exFAT → file target |
| 주요 도구 | fio 3.42, Python analyzer, PowerShell runner/observer |
| 검증 항목 | 성능, p99/p99.9 QoS, 반복성, 상태 의존성, CRC32C 무결성 |
| 제외 범위 | raw-device write, 강제 전원 차단, firmware/NAND/FTL/GC 내부 분석 |

측정값에는 SSD만이 아니라 USB, Windows scheduling, exFAT, enclosure와
file-target 효과가 함께 포함됩니다. 내부 FTL이나 GC를 직접 관측하지 않았기
때문에 이를 성능 변화의 원인으로 주장하지 않습니다.

FTL/GC white-box 프로젝트와도 의도적으로 분리했습니다. 이 저장소의 질문은
“내부 알고리즘이 어떻게 동작하는가?”가 아니라 “제품 경계에서 어떤 동작을
관측했고, 그 결과를 다시 검증할 수 있는가?”입니다.

## 2. 검증 시스템

| 구성 요소 | 역할 | 대표 산출물 |
|---|---|---|
| Requirement | 검증 질문과 판정 규칙 정의 | requirement matrix |
| Runner | 통제된 fio 실행과 실행 조건 기록 | fio JSON, logs, `runner_manifest.json` |
| Observer | 실행 전후 또는 동기화된 host evidence 수집 | observer manifest, counter CSV |
| Analyzer | raw result를 비교 가능한 지표로 변환 | summary/verdict CSV |
| Integrated manifest | DUT, 조건, 증거, 누락을 하나의 run ID로 연결 | `run_manifest.json` |
| Report | 관측, 판정, anomaly, 해석 한계 정리 | result report |

증거가 존재한다는 사실만으로 `Complete`를 부여하지 않습니다. 예를 들어
Windows counter CSV가 생성됐더라도 실제 workload를 나타내는 nonzero sample이
없으면 `Limited`로 판정합니다.

## 3. 통제 조건

| 연구 질문 | 대표 조건 | 반복/배치 |
|---|---|---|
| QD에 따른 성능·QoS 변화 | 4K random read/write, QD 1/4/16/32, 30초 | 조건별 3회 |
| sustained QoS | 4K random read/write, QD16/QD32, 120/300초 | 조건별 3회 |
| 상태 의존성 | reconnect-start baseline → write condition → post probe | 독립 session 3회 |
| mixed ratio | 90:10, 70:30, 50:50, 4K QD16 | cycle/position counterbalance |
| idle sensitivity | 300/60/0/0/60/300초 idle | mirrored pair |
| block size | 4K/64K/1M random read/write, QD32 | Latin-square, 각 3회 |
| file integrity | 4 GiB, 1M, QD4, CRC32C write/readback | 완전 기록·완전 검증 |

## 4. 대표 결과

### 사례 A — 처리량만 보면 놓치는 QD/QoS trade-off

4K random write는 QD16에서 평균 192.23 MiB/s, QD32에서
193.01 MiB/s였습니다. 처리량 이득은 거의 없었지만 평균 p99는
398.00 µs에서 1,067.69 µs로 증가했습니다. QD32 p99 CV도 0.431로
짧은 반복 실행 중 가장 불안정했습니다.

결론은 “QD가 높을수록 빠르다”가 아니라 다음과 같습니다.

> QD16 이후 write throughput은 포화됐고, QD32는 평균 처리량 이득 없이
> tail latency와 반복성 부담을 키웠다.

### 사례 B — 재현되지 않은 가설도 검증 결과로 보존

write conditioning 이후 QD16 처리량이 상승한다는 초기 관측을 검증하기 위해
실험 단위를 연속 fio repeat에서 완전한 reconnect-start session으로 바꿨습니다.
세 session의 paired bandwidth delta는 각각 `-6.37%`, `-7.59%`,
`+23.33%`였습니다.

방향이 일치하지 않았으므로 성능 가설은
`not_reproduced_under_controlled_external_sequence`로 판정했습니다.
반면 계획된 session, raw data, paired metric과 manifest가 모두 존재하므로
증거 요구사항은 Pass입니다.

이 분리는 프로젝트의 중요한 원칙입니다.

```text
evidence requirement Pass
!=
performance hypothesis confirmed
```

### 사례 C — 64K throughput knee와 1M latency cost

QD32 random I/O에서 4K, 64K, 1M을 cycle과 순서 위치에 counterbalance했습니다.

| Workload | 64K BW | 1M/64K BW | 1M/64K p99 |
|---|---:|---:|---:|
| Read | 303.713 MiB/s | 1.001x | 13.77x |
| Write | 497.109 MiB/s | 0.985x | 15.69x |

64K에서 처리량 plateau에 도달했고 1M은 처리량 이득 없이 p99만 크게
증가했습니다. 따라서 64K는 이 DUT와 QD32 file-target 조건에서 관측된
throughput knee입니다. 모든 workload에 적용되는 보편적 최적 block size라는
주장은 하지 않습니다.

### 사례 D — CRC32C file-target integrity

전용 4 GiB 파일을 새로 생성한 뒤 fio가 CRC32C metadata와 함께 전체를
기록하고 별도 verify-only read로 전체를 검증했습니다.

| Phase | 처리 bytes | fio error | 결과 |
|---|---:|---:|---|
| CRC32C write | 4,294,967,296 | 0 | Complete |
| CRC32C verify read | 4,294,967,296 | 0 | Pass |

`REQ-DATA-009`는 Pass입니다. 단, 이 결과는 테스트된
Windows/exFAT/USB/file-target 경로에서 한 번의 완전한 write/readback이
성공했음을 의미하며 power-loss protection이나 내부 ECC 동작을 증명하지
않습니다.

동시에 실행한 Windows logical-disk observer는 write 16개, verify 7개의
sample을 생성했지만 모두 zero activity였습니다. 따라서 무결성은 `Pass`,
host diagnostic evidence는 `Limited`로 독립 판정했습니다.

## 5. Requirement-Based Regression

완료된 characterization 조건을 다음 8개 component로 축소했습니다.

- 4K random read/write: QD1, QD16
- 64K random read/write: QD32
- 4K QD16 random write: 120초 sustained QoS
- 4 GiB CRC32C integrity

현재 성능 threshold는 `Observation`입니다. 독립 regression session이 충분히
쌓이기 전까지 기존 측정값을 임의의 hard pass/fail 기준으로 사용하지 않습니다.
Analyzer는 다음 판정을 하나의 점수로 합치지 않고 별도 필드로 유지합니다.

- evidence status
- integrity verdict
- performance verdict
- QoS verdict
- host observer status

자세한 contract는
[Compact External SSD Regression Profile](docs/reports/external_ssd_regression_profile.md)에
정리되어 있습니다.

## 6. 검증 가능한 산출물

| 목적 | 문서 |
|---|---|
| DUT 및 해석 경계 | [DUT profile](docs/reports/external_ssd_dut_profile.md) |
| 요구사항과 판정 규칙 | [Requirement matrix](docs/reports/external_ssd_requirement_matrix.md) |
| 전체 결과 해석 | [Product validation report](docs/reports/external_ssd_product_validation.md) |
| Block-size 결과 | [Block-size sweep result](docs/reports/external_ssd_block_size_sweep_result.md) |
| 무결성 결과 | [Data-integrity result](docs/reports/external_ssd_data_integrity_result.md) |
| Regression contract | [Regression profile](docs/reports/external_ssd_regression_profile.md) |
| 면접 설명 자료 | [Interview brief](docs/reports/external_ssd_interview_brief_ko.md) |
| Raw/derived evidence | [results/external_ssd](results/external_ssd) |

## 7. 자동 검증

```powershell
cd D:\ssd_lab
python -m unittest discover -s tests -p "test_*.py"
```

Analyzer 회귀 테스트에는 fio error, CRC verification error, byte mismatch,
zero-only host counter, 누락된 regression component 시나리오가 포함됩니다.

외장 SSD fio workload는 사용자가 target path를 확인한 후 직접 실행합니다.
Codex는 명시적인 요청 없이는 외장 SSD workload를 실행하지 않습니다.
