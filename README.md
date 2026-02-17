# LDPlayer pyautogui 윈도우 클릭커

LDPlayer 윈도우 위에서 `pyautogui`로 직접 클릭하고, 스크린샷은 ADB로 찍는 자동화 도구.

LD Player 멀티 조작 기능으로 여러 인스턴스에 클릭이 복제되고,
스크린샷/앱 제어만 각 인스턴스별로 ADB를 통해 수행합니다.

---

## 구조

```
pyautogui.click(screen_x, screen_y)     ← 1개 윈도우만 클릭
    ↕  LD 멀티 조작이 나머지 인스턴스에 복제
ADB screencap → logs/ld-1/, logs/ld-2/  ← 각 인스턴스별 스크린샷
```

### 좌표 매핑

게임 픽셀 좌표를 `game_rect`로 비례 매핑하여 스크린 좌표로 변환합니다.

```
screen_x = rect.left + (game_x / res_w) * rect.width
screen_y = rect.top  + (game_y / res_h) * rect.height
```

---

## 파일 구성

| 파일 | 설명 |
|------|------|
| `window_clicker.py` | 메인 실행 스크립트 |
| `config-window.json` | 설정 파일 |
| `mouse_position_helper.py` | 마우스 좌표 / game_rect 측정 도구 |
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

### 1. game_rect 측정

`mouse_position_helper.py`로 LD Player 게임 영역의 스크린 좌표를 측정합니다.

```bat
python mouse_position_helper.py
```

- `Enter`: 현재 커서 좌표 출력
- `r`: game_rect 측정 모드 (좌상단 → 우하단)
- `q`: 종료

```
> r
Move cursor to TOP-LEFT corner of the game area, then press Enter...
  #1: x=0, y=31
Move cursor to BOTTOM-RIGHT corner of the game area, then press Enter...
  #2: x=960, y=571
=> game_rect: {"left": 0, "top": 31, "width": 960, "height": 540}
```

### 2. config 설정

`config-window.json`을 수정합니다.

```json
{
  "game_rect": {"left": 0, "top": 31, "width": 960, "height": 540},
  "game_resolution": {"w": 1280, "h": 720},
  "screenshot_targets": [
    {"name": "ld-1", "adb_serial": "127.0.0.1:5555"},
    {"name": "ld-2", "adb_serial": "127.0.0.1:5557"}
  ],
  "steps": [
    {"action": "tap", "x": 640, "y": 360, "delay_after_s": 1.0},
    {"action": "screenshot", "screenshot_name": "example", "delay_after_s": 0.5}
  ]
}
```

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
| `game_rect` | (필수) | 게임 영역의 스크린 절대좌표 |
| `game_resolution` | `1280x720` | 게임 내부 해상도 (좌표 기준) |
| `screenshot_targets` | `[]` | ADB 스크린샷/앱 제어 대상 목록 |
| `steps` | `[]` | 실행할 액션 시퀀스 |
| `iterations` | `0` | 반복 횟수 (0 = 무한) |
| `startup_wait_s` | `2` | 시작 전 대기 |
| `loop_delay_s` | `2` | 루프 간 대기 |
| `log_dir` | `logs` | 스크린샷 저장 경로 |

### 액션 종류

| action | 실행 방법 | 필수 필드 |
|--------|----------|-----------|
| `tap` | `pyautogui.click()` | `x`, `y` |
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

### step별 game_rect 오버라이드

세로/가로 전환이 필요한 step에서 개별 오버라이드 가능:

```json
{
  "action": "tap",
  "x": 360, "y": 640,
  "game_rect": {"left": 320, "top": 0, "width": 320, "height": 540},
  "game_resolution": {"w": 720, "h": 1280}
}
```

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
1. `mouse_position_helper.py`로 `game_rect` 재측정
2. LD Player 창 위치/크기 변경 시 `game_rect` 업데이트 필요

---

## 주의사항
- 게임 정책 위반 가능성 있음 (계정 제재 리스크)
- 밤샘 실행 시 Windows 절전/화면끄기 정책 확인
- `pyautogui`는 실제 마우스를 움직이므로 실행 중 PC 사용 불가
