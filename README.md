# LDPlayer 다중 창 고정 좌표 자동화 템플릿

여러 LDPlayer 인스턴스를 동시에 돌릴 때, 각 창의 ADB 포트(시리얼) 기준으로 고정 좌표 클릭을 반복합니다.

## 파일 구성
- `multi_ld_clicker.py`: 메인 자동화 스크립트
- `config.example.json`: 설정 예시
- `mouse_position_helper.py`: 데스크톱 마우스 좌표 확인 보조 도구
- `run.bat`: Windows 실행용 배치 파일
- `setup_windows.bat`: Python/ADB/디바이스/설정 자동 점검 배치

## 질문 답변
- **Q. 로컬에 내려받아서 실행하면 되나?**
  - 네. Windows 로컬에서 Python + ADB 환경만 맞추면 실행됩니다.
  - 다만 **제가 사용자 PC에 직접 접속해서 받아주거나 설치를 대신 실행할 수는 없습니다.**
- **Q. 환경 구성도 자동으로 되나?**
  - 완전 자동 설치는 OS 권한/정책 때문에 100% 보장되진 않습니다.
  - 대신 `setup_windows.bat`를 추가해서 Python/ADB/디바이스/설정파일까지 자동 점검/초기화되게 했습니다.
- **Q. 중간에 스크린샷 찍을 수 있나?**
  - 네. `taps` 안에 `{"action":"screenshot"...}` 액션을 넣으면 원하는 순서에서 저장할 수 있습니다.
- **Q. 좌표/클릭 타이밍은 직접 설정해야 하나?**
  - 네. 인스턴스/게임별로 다르기 때문에 직접 설정이 맞습니다.
- **Q. LDPlayer 녹화 매크로 연동은 복잡한가?**
  - 완전 구현은 복잡도가 올라갑니다. 다만 실무적으로는
    1) LD 내부 녹화 매크로로 큰 흐름 처리
    2) 본 스크립트로 분기 지점(중간 스샷/특정 좌표 탭)만 보강
    이 혼합 방식이 가장 안정적입니다.

## 사전 준비
1. LDPlayer 설정에서 **ADB 디버깅** 활성화
2. 각 인스턴스 ADB 포트 확인 (`5555`, `5557`, `5559` 등)
3. PC에 Python 3 설치
4. Android platform-tools(`adb`) 설치 후 PATH 등록

## 빠른 시작
1. 이 폴더에서 `setup_windows.bat` 실행(환경 점검 + `config.json` 자동 생성)
2. `config.json`의 좌표/포트/반복 간격 수정
3. `run.bat` 실행

## config 핵심 값
- `iterations`: 0이면 무한 반복, 10 같은 숫자면 해당 횟수 후 종료
- `instances[].adb_serial`: 인스턴스별 ADB 시리얼 (예: `127.0.0.1:5555`)
- `instances[].taps[]`: 액션 시퀀스
  - `action: "tap"` → `x`, `y` 좌표 클릭
  - `action: "screenshot"` → 현재 화면 캡처 (`screenshot_name` 옵션)
  - `action: "sleep"` → 클릭 없이 시간 대기
  - `wait_before_s`: 해당 액션 전에 대기 시간
  - `delay_after_s`: 해당 액션 후 다음 동작 전 대기 시간
- `screenshot_every_loops`: 루프 단위 주기적 캡처(0이면 비활성)

## 중간 스크린샷 예시
```json
{
  "action": "screenshot",
  "screenshot_name": "after_gacha",
  "wait_before_s": 0.0,
  "delay_after_s": 0.3
}
```

## 좌표 잡는 법
### 방법 A (추천): LDPlayer 개발자 옵션
1. 안드로이드 개발자 옵션에서 **포인터 위치(pointer location)** 켜기
2. 원하는 버튼을 직접 터치/클릭
3. 화면 상단에 표시되는 x/y를 읽어 `config.json`에 입력

### 방법 B (보조): 데스크톱 마우스 좌표 확인
- `python mouse_position_helper.py` 실행
- 원하는 위치에 마우스를 올리고 Enter
- 출력된 x/y를 참고값으로 사용

> 참고: 방법 B는 윈도우 화면 좌표라서 LD 창 크기/위치가 바뀌면 오차가 생길 수 있습니다.

## 타이밍(언제 클릭하는지) 맞추는 법
1. 먼저 느슨하게(`delay_after_s` 크게) 시작
2. 로그의 `tap#N ... t+Xs`를 보면서 실제 게임 반응 타이밍 확인
3. `wait_before_s` / `delay_after_s`를 0.2~0.5초 단위로 줄여서 튜닝

## 주의사항
- 창 해상도/DPI를 바꾸면 좌표가 어긋날 수 있음
- 게임 정책 위반 가능성 있음(계정 제재 리스크)
- 밤샘 실행 시 Windows 절전 모드 해제 권장
