# LDPlayer pyautogui 윈도우 클릭커

LDPlayer 윈도우 위에서 `pyautogui`로 직접 클릭하고, 스크린샷은 ADB로 찍는 자동화 도구.

LD Player 멀티 조작 기능으로 여러 인스턴스에 클릭이 복제되고,
스크린샷/앱 제어만 각 인스턴스별로 ADB를 통해 수행합니다.

---

## 구조

```
pyautogui.click(x, y)               ← 윈도우 스크린 좌표로 직접 클릭
    ↕  LD 멀티 조작이 나머지 인스턴스에 복제
ADB screencap → logs/ld-1/, logs/ld-2/  ← 각 인스턴스별 스크린샷
```

config의 `x`, `y`는 **Windows 화면 절대 좌표**입니다.
`mouse_position_helper.py`로 클릭할 위치의 좌표를 측정하여 사용합니다.

---

## 파일 구성

| 파일 | 설명 |
|------|------|
| `window_clicker.py` | 메인 실행 스크립트 |
| `config-window.json` | 설정 파일 |
| `mouse_position_helper.py` | 마우스 스크린 좌표 측정 도구 |
| `requirements.txt` | Python 의존성 |

---

## 설치

### 필수 요건
- Python 3.11+
- ADB (Android Platform Tools)
- LDPlayer (ADB 디버깅 활성화)

### 설치 순서
```bat
pip install -r requirements.txt
```

---

## 사용법

### 1. 좌표 측정

`mouse_position_helper.py`로 클릭할 위치의 Windows 스크린 좌표를 측정합니다.

```bat
python mouse_position_helper.py
```

- `Enter`: 현재 커서의 스크린 좌표 출력
- `q`: 종료

```
> (Enter)
#1: x=480, y=301
> (Enter)
#2: x=100, y=200
```

### 2. config 설정

`config-window.json`을 수정합니다.

```json
{
  "screenshot_targets": [
    {"name": "ld-1", "adb_serial": "127.0.0.1:5555"},
    {"name": "ld-2", "adb_serial": "127.0.0.1:5557"}
  ],
  "steps": [
    {"action": "tap", "x": 480, "y": 301, "delay_after_s": 1.0},
    {"action": "screenshot", "screenshot_name": "example", "delay_after_s": 0.5}
  ]
}
```

`x`, `y`는 `mouse_position_helper.py`로 측정한 Windows 화면 절대 좌표입니다.

설정 상세는 [CONFIG.md](CONFIG.md) 참고.

### 3. 실행

```bat
python window_clicker.py --config config-window.json
```

`Ctrl+C`로 종료.

---

## 설정 상세

### 최상위 필드

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `screenshot_targets` | `[]` | ADB 스크린샷/앱 제어 대상 목록 |
| `steps` | `[]` | 실행할 액션 시퀀스 |
| `iterations` | `0` | 반복 횟수 (0 = 무한) |
| `startup_wait_s` | `2` | 시작 전 대기 |
| `loop_delay_s` | `2` | 루프 간 대기 |
| `log_dir` | `logs` | 스크린샷 저장 경로 |

### 액션 종류

| action | 실행 방법 | 필수 필드 |
|--------|----------|-----------|
| `tap` | `pyautogui.click(x, y)` | `x`, `y` (스크린 좌표) |
| `screenshot` | ADB `screencap` (모든 targets) | `screenshot_name` |
| `sleep` | `time.sleep()` | - |
| `clipboard` | `pyperclip.copy()` + `Ctrl+V` | `text` |
| `clear_data` | ADB `pm clear` (모든 targets) | `app_package` |
| `start_app` | ADB `monkey` (모든 targets) | `app_package` |
| `stop_app` | ADB `am force-stop` (모든 targets) | `app_package` |
| `app_switch` | ADB `keyevent` (모든 targets) | - |

### 공통 필드

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `wait_before_s` | `0.0` | 액션 실행 전 대기 |
| `delay_after_s` | `0.5` | 액션 실행 후 대기 |

---

## 문제 해결

### ADB 연결 안 될 때
```bat
adb kill-server
adb start-server
adb connect 127.0.0.1:5555
adb devices
```

### 클릭 위치가 어긋날 때
1. `mouse_position_helper.py`로 좌표 재측정
2. LD Player 창 위치/크기 변경 시 config 좌표 업데이트 필요

---

## 주의사항
- 게임 정책 위반 가능성 있음 (계정 제재 리스크)
- 밤샘 실행 시 Windows 절전/화면끄기 정책 확인
- `pyautogui`는 실제 마우스를 움직이므로 실행 중 PC 사용 불가
