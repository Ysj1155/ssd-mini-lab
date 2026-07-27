# 외장 SSD Validation 면접 설명 자료

## 1. 30초 소개

> 외장 SSD를 black-box DUT로 두고 Windows, USB, exFAT, fio file-target
> 경계에서 관측 가능한 성능, tail latency, 반복성, 상태 의존성과 CRC32C
> 무결성을 검증했습니다. 단순 벤치마크가 아니라 요구사항, runner/observer,
> raw evidence, analyzer, verdict를 manifest로 연결했고, 재현되지 않은 가설과
> 수집 한계도 결과로 보존했습니다.

## 2. 2분 설명

문제는 benchmark 숫자가 실행 시점과 상태에 따라 달라져도 그 이유를 쉽게
SSD 내부 동작으로 단정하게 된다는 점이었습니다. 그래서 외장 SSD를 제품
경계의 DUT로 정의하고 내부 FTL/GC 프로젝트와 분리했습니다.

먼저 QD sweep과 sustained workload로 throughput뿐 아니라 p99, p99.9,
maximum latency와 반복 variation을 측정했습니다. 이후 결과가 session에 따라
달라지는 것을 보고 연속 repeat가 독립 실험이 아닐 수 있다고 판단했습니다.
실험 단위를 reconnect-start 전체 sequence로 바꾸고, ABBA/BAAB와
counterbalanced order를 사용해 workload ratio, cycle, position 효과를
분리하려고 했습니다.

가장 중요한 결과는 세 가지입니다.

1. 4K random write는 QD16 이후 throughput이 포화됐지만 QD32에서 p99와
   변동성이 커졌습니다.
2. conditioning uplift와 mixed-ratio 방향은 독립 session에서 재현되지
   않았습니다. 요구사항 완료와 성능 가설 확인을 별도 verdict로 관리했습니다.
3. QD32 block-size sweep에서는 64K가 throughput knee였고 1M은 throughput
   이득 없이 p99가 read 13.77배, write 15.69배 증가했습니다.

마지막으로 4 GiB 전용 파일을 CRC32C로 완전히 write/readback해 integrity
Pass를 얻었습니다. 동시에 실행한 Windows counter는 모두 0이어서 diagnostic
evidence는 Limited로 유지했습니다. 즉, 성공한 무결성 결과와 제한된 관측성을
서로 덮어쓰지 않았습니다.

## 3. STAR 사례

### 사례 A — 독립적이지 않은 repeat 개선

**Situation**

연속 QD16 probe에서 write conditioning 이후 평균 throughput이 상승했지만,
마지막 repeat에서 상승폭이 사라졌습니다.

**Task**

관측된 uplift가 반복 가능한 상태 효과인지 검증해야 했습니다.

**Action**

- 연속 fio repeat를 독립 session으로 간주하지 않음
- 600초 disconnect, 동일 USB port, 초기 idle을 포함한 reconnect-start
  sequence를 새 실험 단위로 정의
- baseline → QD32 condition → post QD16 probe를 session마다 한 쌍으로 비교
- 세 session의 paired delta와 QoS를 함께 보존

**Result**

Bandwidth delta는 `-6.37%`, `-7.59%`, `+23.33%`로 방향이 섞였습니다.
따라서 conditioning uplift 가설은 재현되지 않았습니다. 대신 session-level
state variation이 크다는 더 방어 가능한 결론을 얻었습니다.

### 사례 B — 성공 파일을 Complete로 오판하지 않기

**Situation**

fio와 동시에 Windows logical-disk counter collector를 실행했고 CSV와 manifest가
정상 생성됐습니다.

**Task**

파일 존재 여부가 아니라 workload 진단에 사용할 수 있는 evidence인지
판정해야 했습니다.

**Action**

- throughput, IOPS, queue counter의 nonzero activity sample 수를 analyzer에서 확인
- query error와 signal validity를 분리
- 최소 한 개의 nonzero sample이 없으면 `Limited` 처리
- integrity verdict와 observer status를 별도 필드로 유지

**Result**

Write 16개와 verify 7개 sample이 모두 0이어서 observer는 Limited,
CRC32C write/readback은 Pass로 판정했습니다.

## 4. 자주 받을 질문

### 왜 raw device가 아니라 file target을 사용했나요?

실제 사용 경로인 Windows/USB/exFAT 경계의 제품 동작을 안전하게 검증하기
위해서입니다. Raw-device write는 데이터 손실 위험과 별도 안전 검토가 필요하며
이 포트폴리오 범위가 아닙니다. 대신 전용 파일과 명시적 target path를 사용하고
runner가 기존 integrity target을 거부하도록 했습니다.

### 왜 평균 latency 외에 p99와 p99.9를 봤나요?

평균은 드문 stall을 숨길 수 있기 때문입니다. QD32 300초 실행에서는 p99.9에
크게 반영되지 않는 5~6초 maximum-latency outlier도 있었습니다. 그래서 평균,
p99, p99.9, maximum과 time window를 함께 보존했습니다.

### QD32가 항상 나쁜 조건이라는 뜻인가요?

아닙니다. 4K random write의 해당 file-target 조건에서는 QD16 이후 throughput
이득이 거의 없고 QD32 tail latency가 증가했습니다. Workload, block size,
host path가 달라지면 결과도 달라질 수 있습니다.

### 64K가 이 SSD의 최적 block size인가요?

보편적 최적값이라고 주장하지 않습니다. QD32, 32 GiB file target,
Windows AIO, direct I/O라는 통제 조건에서 관측된 throughput knee입니다.
Block size가 커질 때 QD32의 in-flight bytes도 128 KiB, 2 MiB, 32 MiB로
함께 증가하므로 block size 단독 효과로 해석하지 않습니다.

### 가설이 재현되지 않았는데 테스트는 왜 Pass인가요?

요구사항 Pass는 계획된 조건과 증거가 완성됐다는 뜻입니다. 성능 가설 verdict는
관측 방향이 독립 session에서 반복됐는지를 나타냅니다. 검증 절차가 성공적으로
가설을 반박할 수도 있으므로 두 판정을 분리했습니다.

### 내부 cache나 GC가 원인 아닌가요?

가능성은 열려 있지만 이 evidence로는 판단할 수 없습니다. USB bridge,
Windows scheduling, exFAT, host background activity와 SSD 내부 상태가 함께
포함돼 있고 firmware/NAND trace가 없습니다. 따라서 외부에서 관측된
session-level variation까지만 결론으로 둡니다.

### CRC32C Pass가 무엇을 증명하나요?

테스트된 경로에서 새 4 GiB 파일이 완전히 기록되고 완전히 읽혀 fio verification
error 없이 일치했다는 뜻입니다. Power-loss protection, endurance, internal ECC
coverage, cable removal recovery는 증명하지 않습니다.

### 첫 integrity 실행은 왜 실패했고 무엇을 바꿨나요?

fio는 4 GiB를 정상 기록했지만 종료 후 생성 파일이 남지 않았습니다. 실패
evidence를 삭제하지 않고 보존했습니다. Retry에서는 runner가 먼저
`FileMode.CreateNew`와 `SetLength`로 전용 파일을 만들고 fio가 `overwrite=1`로
기록하게 했습니다. 기존 파일을 거부하는 안전 규칙은 유지하면서 verify-only
phase가 같은 파일을 사용할 수 있게 했습니다.

### 성능 regression threshold는 어떻게 정했나요?

아직 hard threshold를 정하지 않았습니다. 현재 profile은 `Observation`
모드입니다. 독립 regression session이 충분히 쌓인 뒤 baseline source,
sample count, statistic과 tolerance를 versioned contract로 추가할 계획입니다.

## 5. 숫자 메모

| 항목 | 기억할 수치 |
|---|---|
| 4K random write QD16 → QD32 | 192.23 → 193.01 MiB/s |
| 같은 조건 p99 | 398.00 → 1,067.69 µs |
| State paired BW delta | -6.37%, -7.59%, +23.33% |
| Block-size read 1M/64K | BW 1.001x, p99 13.77x |
| Block-size write 1M/64K | BW 0.985x, p99 15.69x |
| Integrity byte count | phase별 4,294,967,296 bytes |
| Integrity verdict | Pass |
| Host counter | 23 samples, nonzero 0, Limited |
| 자동 테스트 | 37개 |

## 6. 피해야 할 표현

- “QD32가 SSD를 느리게 만든다”
- “64K가 SSD의 최적 block size다”
- “SLC cache가 소진됐다”
- “GC 때문에 latency가 증가했다”
- “CRC32C Pass이므로 power loss에도 안전하다”
- “CSV가 생성됐으므로 observer evidence가 Complete다”

대신 조건과 경계를 포함해 말합니다.

> 이 Windows/USB/exFAT file-target 조건에서 해당 방향이 관측됐으며,
> 내부 원인은 현재 evidence로 식별할 수 없습니다.

## 7. 다음 단계

Broad sweep을 추가하지 않고 compact regression profile을 독립 session에
적용해 baseline variation을 축적하는 것이 다음 기술 단계입니다. 별도 안전
검토와 disposable target이 준비될 경우에만 application-level interruption과
post-reconnect checksum을 검토하며, 이를 power-loss validation으로 부르지
않습니다.
