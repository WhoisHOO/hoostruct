# HooStruct

[English](README.md) | **한국어**

비정형 데이터를 구조화되고 검증 가능한 레코드로 변환하는 툴. 첫 지원 소스는 영상.

## 왜 필요한가

카메라 영상 같은 비정형 데이터는 용량이 커서 계속 보관할 수 없지만, 그 안의 정보(이벤트, 상태, 수치)는
원본이 사라진 뒤에도 운영·분석·감사·증빙에 계속 필요하다. HooStruct는 그 정보를 압축된 정형 레코드로
추출하고, 레코드가 변조되지 않았음을 증명할 수 있게 만든 뒤에야 원본을 처분하게 한다.

```
소스(영상) ─> 샘플링 ─> 추출 엔진 ─> 레코드(JSONL) + 매니페스트
                                 └> 보존 정책 (원본 유지 / 삭제)
```

## 동작 방식

1. **등록(Ingest)**: 소스 파일을 해시(sha256 = `source_id`)하고 메타데이터를 추출한다.
   원본이 삭제된 뒤에도 모든 레코드가 출처를 추적할 수 있다.
2. **샘플링**: 소스를 시간 구간(window)으로 나눈다.
3. **추출**: 엔진이 구간을 레코드로 바꾼다.
   - `motion` - OpenCV 프레임 차분으로 구간별 활동성 지수 계산. 모델도 학습도 불필요.
   - `vlm` - 대표 프레임을 로컬 [Ollama](https://ollama.com) 비전 모델(기본 `gemma4:12b`)에 보낸다.
     응답은 JSON 스키마로 강제되며 자유 서술은 허용하지 않는다.
   - `motion+vlm` (기본) - 2단 게이팅: 모든 구간에 모션 레코드를 남기고, 활동성이 임계값을
     넘는 구간만 VLM에 보낸다. 추론 비용이 영상 길이가 아니라 실제 발생한 일의 양에 비례한다.
   - `mock` - 배선 테스트용.
4. **무결성**: 레코드는 sha256 해시 체인을 이룬다(각 레코드의 해시가 이전 레코드 해시를 포함).
   매니페스트가 체인 머리를 고정하며, `hoostruct verify`가 체인을 재계산해 수정·삭제·삽입을 탐지한다.
5. **보존**: 원본은 기본적으로 유지된다. `--delete-source`를 명시해야, 그리고 레코드와 매니페스트
   저장이 성공한 뒤에만 삭제된다.

## 빠른 시작

```bash
pip install "hoostruct[cv] @ git+https://github.com/WhoisHOO/hoostruct"
ollama pull gemma4:12b           # 비전을 지원하는 Ollama 모델이면 무엇이든 가능

hoostruct refine footage.mp4 --out data/records
hoostruct verify data/records/<id>.records.jsonl
```

주요 옵션: `--engine mock|motion|vlm|motion+vlm`, `--interval 60` (구간 길이, 초),
`--gate-threshold 0.02`, `--vlm-model`, `--frames-per-window`, `--delete-source`.
설치 없이 `python -m hoostruct ...`로도 실행할 수 있다.

레코드 예시 (`vlm.observation`):

```json
{
  "source_id": "0ac1bbbf...", "t_start": 0.0, "t_end": 60.0,
  "event_type": "vlm.observation",
  "payload": {"summary": "...", "events": [{"type": "...", "description": "..."}], "frame_times": [30.0]},
  "engine": "vlm", "engine_version": "gemma4:12b",
  "prev_record_hash": "...", "record_hash": "..."
}
```

## 확장

모든 단계가 인터페이스다: 새 모델이나 도메인은 `Extractor`로, 다른 분할 전략은 `Sampler`로,
데이터베이스나 기존 시스템 연동은 `RecordSink`로 구현한다. 레코드 공통 envelope은 고정이고
엔진별 필드는 `payload`에 들어가므로, 새 엔진을 추가해도 스키마 변경이 필요 없다.
도메인 특화 프롬프트는 VLM 엔진에 직접 전달할 수 있다(`VlmExtractor(prompt=...)`).

의존성은 허용적 라이선스(Apache-2.0/MIT)만 받는다. 코어는 선택적 OpenCV 외 의존성이 없다.

## 개발

```bash
python -m unittest discover -s tests
```

## 라이선스

Apache License 2.0. [LICENSE](LICENSE) 참조.
