# 설정 가이드 (config-window.json)

## 최소 설정

아무 옵션 없이 `steps`만 있으면 동작합니다.
나머지는 전부 기본값이 적용됩니다.

```json
{
  "steps": [
    {"action": "tap", "x": 480, "y": 301}
  ]
}
```

이 경우 기본값으로 **1회 실행** 후 종료됩니다.

---

## 전체 설정 예시

```json
{
  "log_dir": "logs",
  "iterations": 0,
  "startup_wait_s": 3,
  "loop_delay_s": 2,
  "connect_retries": 8,
  "connect_retry_delay_s": 2.0,
  "screenshot_targets": [
    {"name": "ld-1", "adb_serial": "127.0.0.1:5555"},
    {"name": "ld-2", "adb_serial": "127.0.0.1:5557"}
  ],
  "steps": [
    {"action": "tap", "x": 480, "y": 301, "delay_after_s": 1.0},
    {"action": "screenshot", "screenshot_name": "after_tap", "delay_after_s": 0.5},
    {"action": "sleep", "delay_after_s": 3.0},
    {"action": "clipboard", "text": "hello", "x": 500, "y": 400, "delay_after_s": 0.5},
    {"action": "start_app", "app_package": "com.example.game", "delay_after_s": 5.0},
    {"action": "stop_app", "app_package": "com.example.game"},
    {"action": "clear_data", "app_package": "com.example.game"},
    {"action": "app_switch", "delay_after_s": 1.0}
  ]
}
```

---

## 최상위 필드

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `steps` | array | `[]` | 실행할 액션 시퀀스. 아래 [액션 상세](#액션-상세) 참고 |
| `iterations` | int | `1` | 반복 횟수. `0` = 무한 반복 (`Ctrl+C`로 종료) |
| `startup_wait_s` | float | `2` | 시작 전 대기 시간(초). ADB 연결 등 준비 시간 |
| `loop_delay_s` | float | `2` | 루프 사이 대기 시간(초) |
| `log_dir` | string | `"logs"` | 스크린샷 저장 디렉토리 경로 |
| `screenshot_targets` | array | `[]` | ADB 스크린샷/앱 제어 대상 목록. 아래 [스크린샷 타겟](#스크린샷-타겟) 참고 |
| `connect_retries` | int | `5` | ADB 연결 재시도 횟수 |
| `connect_retry_delay_s` | float | `2.0` | ADB 연결 재시도 간격(초) |

### iterations 동작

| 값 | 동작 |
|----|------|
| `1` (기본값) | steps를 한 번 실행하고 종료 |
| `5` | steps를 5번 반복 후 종료 |
| `0` | 무한 반복. `Ctrl+C`로 종료 |

---

## 스크린샷 타겟

`screenshot_targets`는 ADB 명령(스크린샷, 앱 시작/종료/데이터삭제)을 수행할 대상 목록입니다.
클릭(`tap`)은 pyautogui가 처리하므로 여기에 포함되지 않습니다.

```json
"screenshot_targets": [
  {"name": "ld-1", "adb_serial": "127.0.0.1:5555"},
  {"name": "ld-2", "adb_serial": "127.0.0.1:5557"}
]
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 인스턴스 이름. 로그 디렉토리명으로 사용 (`logs/ld-1/`) |
| `adb_serial` | string | ADB 시리얼. LDPlayer 기본 포트: 5555, 5557, 5559... |

비워두면 (`[]`) ADB 관련 액션(screenshot, start_app 등)이 스킵됩니다.

---

## 액션 상세

### 공통 필드

모든 액션에서 사용 가능한 필드:

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `action` | string | `"tap"` | 액션 종류 |
| `wait_before_s` | float | `0.0` | 이 액션 실행 **전** 대기(초) |
| `delay_after_s` | float | `0.5` | 이 액션 실행 **후** 대기(초) |

---

### `tap` — 화면 클릭

Windows 스크린 절대 좌표로 `pyautogui.click(x, y)` 실행.

```json
{"action": "tap", "x": 480, "y": 301, "delay_after_s": 1.0}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `x` | int | `0` | Windows 화면 X 좌표 |
| `y` | int | `0` | Windows 화면 Y 좌표 |

좌표 측정: `python mouse_position_helper.py` 실행 후 Enter로 현재 마우스 위치 확인.

---

### `screenshot` — 스크린샷 촬영

모든 `screenshot_targets`에서 ADB로 스크린샷을 캡처.

```json
{"action": "screenshot", "screenshot_name": "after_login", "delay_after_s": 0.5}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `screenshot_name` | string | `""` | 파일명 라벨. 비어있으면 `step{번호}` 사용 |

저장 위치: `{log_dir}/{target_name}/{timestamp}_loop{N}_{label}.png`

예: `logs/ld-1/20260217_143022_loop1_after_login.png`

---

### `sleep` — 대기

`delay_after_s`만큼 대기. 별도 필수 필드 없음.

```json
{"action": "sleep", "delay_after_s": 5.0}
```

`tap`의 `delay_after_s`와 동일하지만, 의미를 명확히 하고 싶을 때 사용.

---

### `clipboard` — 클립보드 붙여넣기

텍스트를 클립보드에 복사한 뒤 `Ctrl+V`로 붙여넣기.

```json
{"action": "clipboard", "text": "hello123", "delay_after_s": 0.5}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `text` | string | `""` | 붙여넣을 텍스트. 비어있으면 스킵 |

입력 필드에 포커스가 있는 상태에서 사용해야 합니다.
필요시 먼저 `tap`으로 입력 필드를 클릭하세요.

---

### `start_app` — 앱 실행

모든 `screenshot_targets`에서 ADB로 앱 실행.

```json
{"action": "start_app", "app_package": "com.example.game", "delay_after_s": 5.0}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `app_package` | string | `""` | Android 패키지명 (필수) |

---

### `stop_app` — 앱 강제 종료

모든 `screenshot_targets`에서 ADB로 앱 강제 종료.

```json
{"action": "stop_app", "app_package": "com.example.game"}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `app_package` | string | `""` | Android 패키지명 (필수) |

---

### `clear_data` — 앱 데이터 삭제

모든 `screenshot_targets`에서 ADB로 앱 데이터 초기화 (`pm clear`).

```json
{"action": "clear_data", "app_package": "com.example.game"}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `app_package` | string | `""` | Android 패키지명 (필수) |

**주의**: 앱의 모든 로컬 데이터(로그인 정보, 캐시 등)가 삭제됩니다.

---

### `app_switch` — 최근 앱 전환

모든 `screenshot_targets`에서 ADB로 최근 앱 목록(KEYCODE_APP_SWITCH) 전환.

```json
{"action": "app_switch", "delay_after_s": 1.0}
```

별도 필수 필드 없음.

---

## 사용 패턴 예시

### 단순 클릭 반복

특정 위치를 10번 클릭:

```json
{
  "iterations": 10,
  "loop_delay_s": 1,
  "steps": [
    {"action": "tap", "x": 480, "y": 301}
  ]
}
```

### 클릭 + 스크린샷 확인

클릭 후 결과를 스크린샷으로 저장:

```json
{
  "iterations": 1,
  "screenshot_targets": [
    {"name": "ld-1", "adb_serial": "127.0.0.1:5555"}
  ],
  "steps": [
    {"action": "tap", "x": 480, "y": 301, "delay_after_s": 2.0},
    {"action": "screenshot", "screenshot_name": "result"}
  ]
}
```

### 앱 재시작 루틴

앱 종료 → 데이터 삭제 → 앱 시작 → 대기 → 클릭:

```json
{
  "iterations": 1,
  "screenshot_targets": [
    {"name": "ld-1", "adb_serial": "127.0.0.1:5555"},
    {"name": "ld-2", "adb_serial": "127.0.0.1:5557"}
  ],
  "steps": [
    {"action": "stop_app", "app_package": "com.example.game", "delay_after_s": 2.0},
    {"action": "clear_data", "app_package": "com.example.game", "delay_after_s": 1.0},
    {"action": "start_app", "app_package": "com.example.game", "delay_after_s": 10.0},
    {"action": "tap", "x": 480, "y": 301, "delay_after_s": 1.0},
    {"action": "screenshot", "screenshot_name": "after_restart"}
  ]
}
```

### 무한 반복 매크로

`Ctrl+C`로 종료할 때까지 반복:

```json
{
  "iterations": 0,
  "loop_delay_s": 3,
  "steps": [
    {"action": "tap", "x": 480, "y": 301, "delay_after_s": 1.0},
    {"action": "tap", "x": 600, "y": 400, "delay_after_s": 1.0}
  ]
}
```
