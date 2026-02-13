# LDPlayer 다중 창 고정 좌표 자동화 템플릿

> Python/ADB를 처음 써도 따라할 수 있게 다시 정리한 가이드입니다.

## 이게 뭐하는 도구인가요?
여러 LDPlayer 인스턴스를 동시에 돌릴 때, 각 창에 대해 **정해진 좌표를 자동으로 클릭**하고,
필요하면 **중간 스크린샷**까지 저장하는 도구입니다.

---

## 핵심 질문 먼저 답변

### 1) ADB가 뭔가요?
**ADB(Android Debug Bridge)**는 PC에서 안드로이드(에뮬레이터 포함)를 제어하는 공식 명령 도구입니다.
이 프로젝트는 클릭/스크린샷을 ADB로 보내기 때문에 ADB가 필요합니다.

- 공식 문서: https://developer.android.com/tools/adb
- Platform Tools 다운로드: https://developer.android.com/tools/releases/platform-tools

### 2) Android Platform Tools는 반드시 설치해야 하나요?
**네, 사실상 필수입니다.**
여기 스크립트는 내부적으로 `adb` 명령을 사용하므로, `adb.exe`가 없으면 동작하지 않습니다.

### 3) 파이썬도 필수인가요?
**네, 현재 스크립트가 Python으로 작성되어 있어서 Python 3 설치가 필요합니다.**
- Python 다운로드: https://www.python.org/downloads/windows/

### 4) 네가 내 PC에 직접 내려받고 설치해줄 수 있나요?
아니요. 저는 이 채팅 안에서 파일/코드만 준비할 수 있고,
**사용자 PC에 원격 접속해서 직접 설치 실행은 못합니다.**

### 5) 그냥 윈도우 클릭 매크로(AutoHotkey/매크로툴)면 안 되나요?
가능은 합니다. 다만 다중 LD 창/백그라운드/창 포커스 변경 상황에서는 실패율이 올라갈 수 있습니다.

- 단순 반복 + 항상 같은 창 1개: 윈도우 클릭 매크로도 충분히 가능
- 다중 인스턴스 + 창 전환/포커스 영향 줄이고 싶음: **ADB 방식이 더 안정적**

### 6) 데이터 캐시 삭제하면 LD 매크로가 꺼지는데, 매크로 On/Off도 조작 가능?
핵심만 말하면:
- **ADB만으로는 LDPlayer "호스트 UI"의 매크로 버튼을 직접 누르기 어렵습니다.**
- 대신 더 안정적인 방법은, 매크로 의존을 줄이고 이 스크립트에서 앱 제어를 같이 하는 것입니다.

이번 버전에서 아래 액션을 추가했습니다.
- `action: "stop_app"` + `app_package`
- `action: "clear_data"` + `app_package`
- `action: "start_app"` + `app_package`

즉, 게임 데이터 초기화/앱 재실행을 LD 매크로가 아니라 ADB 액션으로 처리할 수 있습니다.

---

## 파일 구성
- `multi_ld_clicker.py`: 메인 자동화 스크립트
- `config.example.json`: 설정 예시
- `mouse_position_helper.py`: 데스크톱 마우스 좌표 확인 보조 도구
- `setup_windows.bat`: Python/ADB/디바이스/설정 자동 점검 배치
- `run.bat`: 실행용 배치 파일 (`setup_windows.bat` 먼저 호출)

---

## 진짜 초보용 설치 순서 (Windows)

### 0) LDPlayer에서 ADB 디버깅 켜기
- LDPlayer 설정에서 **ADB 디버깅** 활성화

### 1) Python 설치
1. https://www.python.org/downloads/windows/ 접속
2. 설치할 때 **Add python.exe to PATH** 체크
3. 설치 완료

### 1-1) Python PATH가 안 잡혔을 때 수동 설정
`python --version`이 안 나오면 아래 둘 중 하나로 PATH를 잡아주세요.

방법 A (GUI)
1. 시작 메뉴에서 **환경 변수 편집** 검색 → "시스템 환경 변수 편집" 실행
2. 아래쪽 **환경 변수(N)...** 클릭
3. 사용자 변수의 `Path` 선택 후 **편집**
4. Python 설치 경로 2개를 추가(예시):
   - `C:\Users\<내계정>\AppData\Local\Programs\Python\Python312\`
   - `C:\Users\<내계정>\AppData\Local\Programs\Python\Python312\Scripts\`
5. 확인 후 새 cmd를 열고 `python --version` 재확인

방법 B (명령어, 현재 사용자 기준)
```bat
setx PATH "%PATH%;C:\Users\<내계정>\AppData\Local\Programs\Python\Python312;C:\Users\<내계정>\AppData\Local\Programs\Python\Python312\Scripts"
```
> `setx` 후에는 **새 cmd 창을 다시 열어야** 반영됩니다.

### 2) ADB(Platform Tools) 설치
방법 A(권장, 수동):
1. https://developer.android.com/tools/releases/platform-tools 다운로드
2. 압축 해제(예: `C:\platform-tools`)
3. PATH 추가 (GUI)
   - 시작 메뉴 → **환경 변수 편집**
   - 사용자 변수 `Path` → 편집 → 새로 만들기 → `C:\platform-tools`
   - 확인 저장 후 새 cmd 실행
4. 확인: `adb version`

방법 B(명령어로 PATH 추가, 현재 사용자 기준):
```bat
setx PATH "%PATH%;C:\platform-tools"
```
> 역시 새 cmd 창에서 다시 확인해야 합니다.

방법 C(선택, winget 자동 설치):
- PowerShell(관리자)에서:
  - `winget install --id Google.AndroidSDK.PlatformTools -e`

ADB 연결 확인(중요)
```bat
adb devices
```
- `device` 로 나오면 정상
- `offline` 이면 LD 재시작 + `adb kill-server && adb start-server`

### 3) 설치 확인
`cmd`에서 아래 실행:
- `python --version`
- `where python`
- `adb version`
- `where adb`
- `adb devices`

---

## 빠른 시작
1. 이 폴더에서 `setup_windows.bat` 실행
   - Python/ADB 있는지 체크
   - `adb devices` 출력
   - `config.json`이 없으면 자동 생성
2. `config.json` 수정 (좌표/포트/타이밍)
3. `run.bat` 실행

---

## 진짜 "복붙"용 명령어 순서 (cmd 기준)
아래는 **Windows CMD**에서 그대로 복붙해서 확인하는 순서입니다.

### A. PATH 반영 확인
```bat
python --version
where python
adb version
where adb
adb devices
```

정상 기준:
- `python --version` 버전 출력
- `where python` 경로 출력
- `adb version` 버전 출력
- `where adb` 경로 출력
- `adb devices`에 최소 1개 `device` 상태

### B. Python PATH 수동 추가 (필요할 때만)
> `<내계정>` / `Python312` 부분은 본인 환경에 맞게 바꿔서 1회 실행
```bat
setx PATH "%PATH%;C:\Users\<내계정>\AppData\Local\Programs\Python\Python312;C:\Users\<내계정>\AppData\Local\Programs\Python\Python312\Scripts"
```
실행 후 **cmd 창을 닫고 새로 열어서** 다시 아래 확인:
```bat
python --version
where python
```

### C. ADB(PATH) 수동 추가 (필요할 때만)
```bat
setx PATH "%PATH%;C:\platform-tools"
```
실행 후 **cmd 새로 열고** 확인:
```bat
adb version
where adb
adb devices
```

### D. 프로젝트 실행(복붙 순서)
```bat
cd /d <프로젝트_폴더_경로>
setup_windows.bat
notepad config.json
run.bat
```

설명:
- `setup_windows.bat`: 환경 체크 + `config.json` 자동 생성
- `notepad config.json`: 좌표/포트 수정
- `run.bat`: 자동화 실행

### E. .bat 실행 방법 (더블클릭 / CMD)
- 방법 1: 파일 탐색기에서 `setup_windows.bat` 더블클릭 → 이후 `run.bat` 더블클릭
- 방법 2: CMD에서 직접 실행
```bat
cd /d <프로젝트_폴더_경로>
setup_windows.bat
run.bat
```

## 실행 중 멈추는 방법 (중요)
1. 실행한 **같은 CMD 창**에서 `Ctrl + C`를 누르세요.
2. 이번 버전부터는 모든 워커에 정지 신호를 보내고 순차 종료합니다.
3. PowerShell에서 안 먹으면 `Ctrl + Break` 또는 창 닫기로 종료 가능합니다.

> `run.bat`를 더블클릭으로 실행했을 때 창이 바로 닫히면, CMD를 직접 열어 실행하면 종료 제어가 더 쉽습니다.

## 설정(config.json)에서 꼭 알아야 할 것
앱 제어 액션(새로 추가):
- `action: "stop_app"` + `app_package`: 앱 강제 종료
- `action: "clear_data"` + `app_package`: 앱 데이터 초기화(`pm clear`)
- `action: "start_app"` + `app_package`: 앱 실행(`monkey -p`)

예시:
```json
{ "action": "stop_app", "app_package": "com.example.game", "delay_after_s": 0.3 },
{ "action": "clear_data", "app_package": "com.example.game", "delay_after_s": 0.8 },
{ "action": "start_app", "app_package": "com.example.game", "delay_after_s": 3.0 }
```

- `iterations`: `0`이면 무한 반복
- `instances[].adb_serial`: 각 LD 인스턴스 ADB 주소 (예: `127.0.0.1:5555`)
- `instances[].taps[]`: 동작 순서
  - `action: "tap"` → 좌표 클릭
  - `action: "screenshot"` → 그 시점 화면 저장
  - `action: "sleep"` → 클릭 없이 대기
- `wait_before_s`: 해당 동작 전에 대기
- `delay_after_s`: 해당 동작 후 다음 동작 전 대기

중간 스크린샷 예시:
```json
{
  "action": "screenshot",
  "screenshot_name": "after_gacha",
  "wait_before_s": 0.0,
  "delay_after_s": 0.3
}
```

---

## 좌표 잡는 법
### 방법 A (추천): LDPlayer 개발자 옵션
1. 개발자 옵션에서 **포인터 위치(pointer location)** 켜기
2. 버튼 터치/클릭
3. 표시된 x/y를 config에 입력

### 방법 B (보조): 마우스 좌표 스크립트
- `python mouse_position_helper.py`
- 마우스를 위치시키고 Enter

> 방법 B는 윈도우 좌표 기반이라 창 크기/위치 바뀌면 오차가 생길 수 있습니다.

---

## LDPlayer 녹화 매크로와 같이 쓰는 게 복잡한가요?
완전 자동 연동(매크로 상태까지 외부에서 정교 제어)은 복잡도가 꽤 올라갑니다.
보통은 아래가 가장 현실적입니다:
1. LD 내부 녹화 매크로로 큰 루프 처리
2. 이 스크립트로 분기 지점(중간 스샷, 특수 탭, 시간 대기)만 보강

---

### 자주 보는 에러: `winget은(는) 예상되지 않았습니다.`
이건 보통 `setup_windows.bat` 안의 안내문이 CMD에서 잘못 파싱될 때 생깁니다.
최신 파일로 교체 후 다시 실행하세요. (이번 버전에서 수정됨)

그리고 이 메시지는 **ADB가 PATH에 없을 때** 같이 뜰 수 있으니 아래도 같이 확인:
```bat
where adb
adb version
```

## 문제 생기면 먼저 확인
1. `adb devices`에 `device` 상태로 보이는지
2. `config.json`의 `adb_serial`이 맞는지
3. LD 해상도/DPI를 바꾸지 않았는지
4. 좌표가 현재 UI와 맞는지
5. `where python`, `where adb` 경로가 내가 설치한 위치와 맞는지
6. 안 되면 cmd 재시작(환경변수 반영) 후 `setup_windows.bat` 재실행

### 지금 나온 에러(`device ... not found`) 빠른 해결 순서
아래를 CMD에서 순서대로 실행:
```bat
adb kill-server
adb start-server
adb connect 127.0.0.1:5555
adb connect 127.0.0.1:5557
adb devices
```

- `adb devices`에 `127.0.0.1:5555 device`, `127.0.0.1:5557 device`로 보여야 정상
- 안 보이면 LD 멀티 인스턴스의 ADB 포트 번호가 다른 것일 수 있으니 포트 재확인 후 `config.json` 수정
- 이번 버전부터는 스크립트가 실행 시 `adb connect`를 자동 재시도합니다.

---

## 주의사항
- 게임 정책 위반 가능성 있음(계정 제재 리스크)
- 밤샘 실행 시 Windows 절전/화면끄기 정책 확인
