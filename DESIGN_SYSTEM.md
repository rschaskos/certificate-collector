# System Design: Federal Certificate (Certidão Federal) Automation

**Version:** 1.0.0
**Date:** February 2026
**Project:** Certificate Collector - Federal Certificate Automation
**Technology Stack:** PyAutoGUI + OpenCV + Tesseract OCR

---

## Executive Summary

This document specifies the complete system architecture for automated Federal Certificate (Certidão Federal) generation from the Brazilian Federal Revenue Service (Receita Federal). The system employs a **dual-strategy approach** combining Computer Vision (CV) template matching with hardcoded fallback coordinates to ensure maximum reliability across different screen resolutions and environmental conditions.

### Key Design Principles

1. **Redundancy:** Every action has a primary method (CV) and fallback method (XY coordinates)
2. **Logging:** Comprehensive logging at every step for debugging and audit trails
3. **Human-like Behavior:** All mouse movements and keyboard inputs are humanized to avoid detection
4. **Graceful Degradation:** System continues even if individual components fail
5. **Retry Logic:** Built-in exponential backoff and retry mechanisms for transient failures

---

## 1. Architecture Overview

### 1.1 Five-Step Process

The automation follows a strictly linear 5-step workflow:

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Fill CNPJ & Emit Certificate                       │
│  - Find CNPJ input field                                    │
│  - Enter CNPJ number                                        │
│  - Click "Emitir Certidão" button                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Handle Modal (Conditional)                         │
│  - Detect "Certidão Válida Encontrada" modal                │
│  - Click "Consultar Certidão" (white button, left)          │
│  - OR continue if no modal appears                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Date Selection Page                                │
│  - Wait for date selection page                             │
│  - Click "Consultar Certidão" (blue button)                 │
│  - Confirm dates are auto-filled correctly                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Verify Certificate Status                          │
│  - Check results table for certificate status               │
│  - Confirm "Válida" or "Vencida"                            │
│  - Return success if valid, failure if expired              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Download Certificate                               │
│  - Locate download button/icon in table                     │
│  - Click download                                           │
│  - Verify PDF file was created in downloads folder          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Dual-Strategy Approach

Each step implements both methods:

```
┌─────────────────────────────────────┐
│   Element Detection Request          │
└────────────┬────────────────────────┘
             │
             ├─────────────────────────────────────┐
             │                                     │
             ▼                                     ▼
    ┌────────────────────┐         ┌─────────────────────┐
    │  METHOD 1: CV      │         │  METHOD 2: FALLBACK │
    │  Template Matching │         │  XY Coordinates     │
    │  Using OpenCV      │         │  Hardcoded Positions│
    └─────────┬──────────┘         └────────┬────────────┘
              │                             │
              ├─ Load template image        ├─ Use hardcoded (x, y)
              ├─ Take screenshot            ├─ Use bounding box region
              ├─ Compare with template      ├─ Calculate center point
              ├─ Get confidence score       └─ Direct to target
              └─ Calculate center point
                   │
                   ▼
         SUCCESS? ──YES──→ ┌────────────────┐
         (conf ≥ 0.8)      │ EXECUTE ACTION │
              │            │ (Click/Type)   │
              NO           └────────────────┘
              │
              ▼
         ┌──────────────────────────┐
         │ Log CV Failure           │
         │ Fall Back to Method 2    │
         │ Use XY Coordinates       │
         │ EXECUTE ACTION           │
         │ (Click/Type)             │
         └──────────────┬───────────┘
                        │
                        ▼
           ┌────────────────────────┐
           │ Both Methods Failed?    │
           │ Log Error & Continue    │
           │ or Retry               │
           └────────────────────────┘
```

---

## 2. Detailed Step Specifications

### 2.1 Step 1: Fill CNPJ and Emit Certificate

**Objective:** Fill the CNPJ input field and click "Emitir Certidão" button

**Primary Method (CV-Based - `step_1_click_cv`):**
- **Template:** `1_btn_cnpj.png` (Field input area)
- **Confidence Threshold:** 0.8 (80%)
- **Detection Strategy:** OCR fallback for CNPJ field since it's text-based
- **Approach:**
  1. Perform OCR on screen to find "Informe" or "CNPJ" label
  2. Calculate field position (label + offset of 40px downward by default)
  3. Click field and type CNPJ
  4. Find "Emitir Certidão" button using template matching or OCR

**Fallback Method (XY Coordinates - `step_1_click_fallback`):**
- **CNPJ Field Position:**
  - Primary: `(376, 478)` - Single click point
- **Emitir Button Position:**
  - Bounding Box: Region `(1360, 667)` to `(1539, 696)`
  - Center Point: `(1449, 681)`
- **Action:**
  1. Click at CNPJ field position
  2. Type the CNPJ number
  3. Click at Emitir button center point

**Validation:**
- After clicking, wait for page transition (2-3 seconds)
- Look for success indicators: "Válida Encontrada", "Certidão Válida", "Data Inicial", "Data Final"
- If "Informe" text still present → button click failed → retry

**Logging Requirements:**
- Log each method attempt (CV vs Fallback)
- Log detected CNPJ field position
- Log confidence scores for template matching
- Log validation result (success/failure)
- Log page transition time

---

### 2.2 Step 2: Handle Modal (Conditional)

**Objective:** Detect and handle the "Certidão Válida Encontrada" modal dialog

**Condition:** This step only executes if modal appears. If no modal, skip to Step 3.

**Modal Detection:**
- Watch for any of these text patterns:
  - "Válida Encontrada"
  - "Certidão Válida"
  - "valida encontrada"
  - "Encontrada"
  - "certificado valido"
  - "Certificado Válido"
  - "foi encontrada"
  - "Certidão foi"

**Primary Method (CV-Based - `step_2_click_cv`):**
- **Template:** `2_btn_emitir.png` (Modal button area)
- **Confidence Threshold:** 0.75 (75%) - Lower for modal since elements may be slightly distorted
- **Detection Strategy:** Template matching on modal region
- **Approach:**
  1. Take screenshot and detect modal presence
  2. Find "Consultar Certidão" button using template matching
  3. Button is typically on the LEFT side of the modal (white/light colored)

**Fallback Method (XY Coordinates - `step_2_click_fallback`):**
- **Consultar Button (Modal) Position:**
  - Bounding Box: Region `(877, 626)` to `(1090, 655)`
  - Center Point: `(983, 640)`
- **Action:**
  1. Click at center point
  2. Wait for modal to close

**Retry Logic:**
- If modal button not found, attempt to close with `Escape` key
- Retry up to 2 times with 1-second delays

**Logging Requirements:**
- Log modal detection
- Log which text pattern triggered modal detection
- Log button position found (CV or fallback)
- Log modal close status

---

### 2.3 Step 3: Date Selection Page

**Objective:** Navigate to date selection page and click "Consultar Certidão"

**Prerequisites:**
- Previous steps completed successfully
- Modal (if present) closed
- Page has transitioned to date selection

**Page Confirmation:**
Look for date-related text on page:
- "Data Inicial"
- "Data Final"
- "Data de Emissão"

If none found, log warning but continue (graceful degradation)

**Primary Method (CV-Based - `step_3_click_cv`):**
- **Template:** `3_btn_consultar.png` (Consultar button on dates page)
- **Confidence Threshold:** 0.75 (75%)
- **Approach:**
  1. Wait for date page to load (retry with exponential backoff)
  2. Verify date markers present
  3. Find "Consultar Certidão" button using template matching
  4. Button is typically blue colored

**Fallback Method (XY Coordinates - `step_3_click_fallback`):**
- **Consultar Button (Dates) Position:**
  - Bounding Box: Region `(1329, 842)` to `(1538, 867)`
  - Center Point: `(1433, 854)`
- **Action:**
  1. Click at center point
  2. Wait for results to load (3-4 seconds)

**Retry Logic:**
- Retry logic with exponential backoff:
  - Attempt 1: Immediate search (timeout 30s)
  - Attempt 2: Wait 1s + jitter, search again
  - Attempt 3: Wait 2s + jitter, search again
  - Max 3 attempts

**Confidence Threshold Adjustment:**
- If OCR confidence too low (< 50%), reduce threshold to 50%
- Button text "Consultar" may have OCR confidence around 55% due to styling

**Logging Requirements:**
- Log date page confirmation (which markers found)
- Log which method succeeded (CV or fallback)
- Log confidence scores
- Log retry attempts and timing
- Log results page load time

---

### 2.4 Step 4: Verify Certificate Status

**Objective:** Check that certificate is "Válida" (not "Vencida" or error)

**Primary Method (OCR-Based):**
- Use OCR to scan results table for status text
- Search for exact text matches:
  - "Válida" (certificate is valid) → Success, continue
  - "Vencida" (certificate is expired) → Failure, return False

**Status Determination:**
```
If "Válida" found:
  ├─ Log success message
  ├─ Continue to Step 5 (download)
  └─ Return TRUE

If "Vencida" found:
  ├─ Log expiration message
  ├─ Display user message: "CERTIDÃO VENCIDA! Consulte o contador da instituição."
  └─ Return FALSE (cannot proceed to download)

If neither found:
  ├─ Log warning: "Status not clearly determined"
  ├─ Take screenshot for debugging
  └─ Continue to Step 5 anyway (attempt download)
```

**No Fallback Method:**
- This step is purely OCR-based because it requires reading table content
- No hardcoded XY coordinates for status (content-dependent)

**Logging Requirements:**
- Log detected status (Válida / Vencida / Unknown)
- Log OCR confidence for status text
- Log results table analysis

---

### 2.5 Step 5: Download Certificate

**Objective:** Click download button/icon and verify PDF file creation

**Primary Method (CV-Based - `step_5_click_cv`):**
- **Template:** `4_btn_consultar.png` and `5_btn_baixar.png` (Download icon area)
- **Confidence Threshold:** 0.75 (75%)
- **Approach:**
  1. Find download icon in results table using template matching
  2. Download icons are typically in rightmost column ("2a Via")
  3. Click download icon

**Fallback Method 1 (OCR Text Search - `step_5_click_fallback_ocr`):**
- Search for "Via" text (from "2a Via" column header)
- Click approximately 50 pixels below text (first data row)
- Position: Center of "Via" column header, offset downward

**Fallback Method 2 (Estimated Position - `step_5_click_fallback_xy`):**
- **Download Button Position:**
  - Bounding Box: Region `(1477, 571)` to `(1499, 586)`
  - Center Point: `(1488, 578)`
- **Action:**
  1. Click at center point
  2. Wait for download to start (3-5 seconds)

**Download Verification (Critical):**
- **Before clicking:** Get timestamp of most recent PDF in downloads folder
- **After clicking:** Wait 5 seconds
- **Verification:**
  1. List all PDF files in downloads directory
  2. Sort by modification time (newest first)
  3. Check if newest file is newer than reference timestamp
  4. Check file size > 0 KB (not empty)
  5. Return success ONLY if new PDF detected

**Special Handling:**
- Browser may show download permission dialog
- Accept default behavior (file should auto-save due to Chrome flags)
- If no PDF detected after 10 seconds, consider download failed

**Logging Requirements:**
- Log each method attempted (CV, OCR fallback, XY fallback)
- Log download button position found
- Log reference timestamp (before click)
- Log new files detected (if any)
- Log download verification result (success/failure)
- Log file name, size, and timestamp

---

## 3. Cross-Cutting Concerns

### 3.1 Error Handling Strategy

```
┌──────────────────────────────┐
│  Step Execution              │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Primary Method (CV)         │
│  Attempt with timeout        │
└──────────┬───────────────────┘
           │
     Success?
     / \
    /   \
  YES   NO
   │     │
   │     ▼
   │  ┌─────────────────────────┐
   │  │ Log CV Failure          │
   │  │ Note confidence scores  │
   │  │ Note timing info        │
   │  └──────────┬──────────────┘
   │             │
   │             ▼
   │  ┌─────────────────────────┐
   │  │ Fallback Method (XY)    │
   │  │ Use hardcoded coords    │
   │  └──────────┬──────────────┘
   │             │
   │       Success?
   │       / \
   │      /   \
   │    YES   NO
   │     │     │
   └─────┤     ├────→ ┌──────────────┐
         │     │      │ Log Error    │
         │     │      │ Take Scr.    │
         │     │      │ Retry/Skip   │
         │     │      │ or Fail      │
         │     │      └──────────────┘
         │     │
         └─────┴────→ ┌──────────────┐
                      │ Continue to  │
                      │ Next Step    │
                      └──────────────┘
```

### 3.2 Logging Architecture

Every step must log:

1. **Step Entry:**
   - Step number and name
   - Timestamp
   - Input parameters

2. **Method Attempts:**
   - Which method attempted (CV/Fallback)
   - Template name (if CV)
   - Confidence score (if applicable)
   - Coordinates used (if fallback)
   - Retry count and timing

3. **Detection Results:**
   - What was detected/found
   - Position found (x, y)
   - Bounding box information
   - OCR confidence scores

4. **Actions Performed:**
   - Mouse movement (humanized)
   - Click coordinates
   - Key presses/typing
   - Delays added

5. **Validation:**
   - What validation performed
   - Result (pass/fail)
   - Evidence (text found, etc.)

6. **Step Exit:**
   - Final result (success/failure)
   - Reason for failure (if applicable)
   - Time taken

**Log Format:**
```
[TIMESTAMP] [STEP N/5] [METHOD] [STATUS] - Message
[TIMESTAMP] [DEBUG] - Detailed diagnostic info
[TIMESTAMP] [WARNING] - Non-critical issues
[TIMESTAMP] [ERROR] - Critical issues
```

**Example:**
```
[14:32:45] [STEP 1/5] [CV] [SUCCESS] - CNPJ field found at (376, 478), confidence: 0.92
[14:32:46] [DEBUG] - CNPJ typed: 12345678000190
[14:32:47] [STEP 1/5] [CV] [SUCCESS] - Emitir button found at (1449, 681), confidence: 0.85
[14:32:50] [STEP 1/5] [VALIDATION] [SUCCESS] - Page transition confirmed, "Válida Encontrada" found
```

### 3.3 Humanization Requirements

All interactions must appear natural:

**Mouse Movement:**
- Use easing functions (easeOutQuad)
- Duration based on distance (0.2-1.0 seconds)
- Small random offsets (±3-5 pixels) added to target
- Never instant jumps

**Keyboard Input:**
- Character-by-character typing (not paste)
- Random interval between keystrokes (50-150ms)
- Variable typing speed (simulate human variance)
- Use keyboard navigation (Tab, Enter) when appropriate

**Delays:**
- Random delays between actions (0.5-1.5 seconds typical)
- Longer delays at transitions (2-3 seconds)
- Jitter added to all delays (±20%)

**Failure Signature:**
- Avoid repeating exact same action immediately
- Always log when retrying (appears in logs)
- Use different coordinates/methods on retry

### 3.4 Timeout Strategy

| Step | Action | Timeout | Rationale |
|------|--------|---------|-----------|
| 1 | CNPJ field detection | 10s | Field usually visible immediately |
| 1 | Emitir button click | 10s | Button visible before/after modal |
| 1 | Page validation | 3s | Page transition is quick |
| 2 | Modal detection | 30s | Wait for dynamic content |
| 2 | Modal button click | 15s | Once modal detected, button visible |
| 3 | Date page wait | 30s | Server may take time to load |
| 3 | Consultar button click | 15s | Button visible once page loads |
| 3 | Results load | 4s | Results render quickly |
| 4 | Status check | 5s | Status already on screen |
| 5 | Download detection | 10s | Button visible in table |
| 5 | Download completion | 10s | File usually downloaded immediately |

### 3.5 Retry Logic

**Exponential Backoff Pattern:**

```
Attempt 1:
├─ Execute immediately
└─ If fail, sleep 0s, proceed to Attempt 2

Attempt 2:
├─ Sleep 1.0s + random jitter (0-0.5s)
├─ Execute
└─ If fail, sleep additional time, proceed to Attempt 3

Attempt 3:
├─ Sleep 2.0s + random jitter (0-0.5s)
├─ Execute
└─ If fail, log final failure and stop

Max Attempts: 3 (configurable per step)
Jitter: Random 0-500ms (prevents synchronized failures)
```

**When to Retry:**
- OCR confidence below threshold
- Element not found in first attempt
- Page not fully loaded
- Network delay (element will appear soon)

**When NOT to Retry:**
- Both methods clearly failed (CV + XY)
- User explicitly canceled
- Certificate status is "Vencida" (expired)
- File system error (permissions, disk full)

---

## 4. Template Management

### 4.1 Template Directory Structure

```
/templates/
├── 1_btn_cnpj.png
│   ├── Size: ~2.5 KB
│   ├── Dimensions: Variable (button area)
│   └── Purpose: CNPJ field detection
│
├── 2_btn_emitir.png
│   ├── Size: ~2.3 KB
│   ├── Dimensions: ~180×30 pixels (button)
│   └── Purpose: Emitir button on first page
│
├── 3_btn_consultar.png
│   ├── Size: ~3.9 KB
│   ├── Dimensions: ~215×30 pixels (button)
│   └── Purpose: Consultar button on dates page
│
├── 4_btn_consultar.png
│   ├── Size: ~3.1 KB
│   ├── Dimensions: ~215×30 pixels (button)
│   └── Purpose: Secondary consultar reference
│
└── 5_btn_baixar.png
    ├── Size: ~0.4 KB
    ├── Dimensions: ~22×15 pixels (small icon)
    └── Purpose: Download button/icon
```

### 4.2 Template Matching Configuration

**OpenCV Parameters:**
- **Algorithm:** `TM_CCOEFF_NORMED` (normalized cross-correlation coefficient)
  - Best for matching templates in natural images
  - Handles scale variations and lighting changes
  - Returns confidence 0.0-1.0

**Confidence Thresholds:**
- **Button-based templates:** 0.75-0.80 (75-80%)
  - UI elements are distinct
- **Text-based templates:** Variable 0.60-0.75
  - Depends on text clarity and OCR quality
- **Icons/Small elements:** 0.70-0.75
  - May have anti-aliasing artifacts

**Resolution Independence:**
- Templates captured at 1920×1080 (full HD)
- Works on 1920×1080, 1366×768, 1280×720 screens
- Fallback coordinates may need adjustment for non-standard resolutions
- Consider scaling templates for resolutions < 1280×720

### 4.3 Missing Templates Handling

**If templates directory is empty:**
1. Log warning at initialization
2. List expected template files
3. Recommend running capture mode
4. Continue anyway using OCR-only fallback
5. System will work but with lower confidence

**If individual template missing:**
1. Log warning for specific template
2. Skip CV method for that step
3. Fall back to XY coordinates immediately
4. No retry with CV (already failed)

---

## 5. Resolution and Coordinate Handling

### 5.1 Screen Resolution Considerations

**Tested Resolutions:**
- 1920×1080 (Full HD) - Primary target
- 1366×768 (HD) - Common laptop
- 1280×720 (HD) - Minimal support

**Coordinates mapping to 1920×1080:**
| Element | Full HD (1920×1080) | Note |
|---------|----------------------|------|
| CNPJ Button | (376, 478) | Left side, ~25% height |
| Emitir Button | (1449, 681) | Right side, ~63% height |
| Modal Consultar | (983, 640) | Center-left, ~59% height |
| Dates Consultar | (1433, 854) | Right side, ~79% height |
| Download Button | (1488, 578) | Right edge, ~53% height |

**Scaling for Other Resolutions:**

For resolution conversion, use:
```
new_x = (old_x / 1920) × screen_width
new_y = (old_y / 1080) × screen_height
```

Example: 1366×768 screen
- CNPJ Button: (376/1920 × 1366, 478/1080 × 768) = (267, 341)
- Emitir Button: (1449/1920 × 1366, 681/1080 × 768) = (1031, 485)

**Note:** These calculations are approximations. Best practice is to:
1. Capture templates at target resolution
2. Test on multiple resolutions
3. Adjust coordinates empirically
4. Store resolution-specific fallbacks if needed

### 5.2 Multi-Monitor Handling

**Current Limitation:**
- System assumes single primary monitor
- Mouse coordinates are absolute (screen-wide)
- May fail if window is on secondary monitor

**Future Enhancement:**
- Detect which monitor window is on
- Adjust coordinates based on monitor offset
- Use relative positioning within window

---

## 6. Data Flow and State Management

### 6.1 State Diagram

```
INIT
  │
  ├─→ Open Chrome (wait for load)
  │
  ├─→ STEP 1: Fill CNPJ & Emit
  │   ├─ Try CV method (template)
  │   ├─ Fallback to XY coordinates
  │   └─ Validate page transition
  │       Success? ──NO──→ FAIL
  │       │
  │      YES
  │       │
  │       ▼
  ├─→ STEP 2: Handle Modal (Optional)
  │   ├─ Detect modal (if present)
  │   ├─ Click modal button (CV or XY)
  │   └─ Validate modal close
  │       Success? ──NO──→ WARN (continue anyway)
  │       │
  │      YES
  │       │
  │       ▼
  ├─→ STEP 3: Date Selection
  │   ├─ Confirm date page visible
  │   ├─ Click Consultar (CV or XY)
  │   └─ Validate results load
  │       Success? ──NO──→ FAIL
  │       │
  │      YES
  │       │
  │       ▼
  ├─→ STEP 4: Check Status
  │   ├─ Search for "Válida" in results
  │   ├─ Or search for "Vencida"
  │   └─ Return status
  │       "Válida"? ──NO──→ FAIL
  │       │
  │      YES
  │       │
  │       ▼
  ├─→ STEP 5: Download
  │   ├─ Find download button (CV or OCR or XY)
  │   ├─ Click download
  │   ├─ Wait for file creation
  │   └─ Verify PDF file exists
  │       File exists? ──NO──→ FAIL
  │       │
  │      YES
  │       │
  │       ▼
  ├─→ SUCCESS (PDF downloaded)
  │
  └─→ CLEANUP & CLOSE
```

### 6.2 Data Structures

**Step Result:**
```python
{
    "step": 1,
    "name": "Fill CNPJ & Emit",
    "success": True/False,
    "method": "CV" | "FALLBACK" | "OCR",
    "confidence": 0.0-1.0,
    "position": (x, y),
    "bounding_box": (x1, y1, x2, y2),
    "duration_ms": 1234,
    "error": "Optional error message",
    "retry_count": 0-3,
    "timestamp": "2026-02-27T14:32:45"
}
```

**Global State:**
```python
{
    "cnpj": "12345678000190",
    "session_id": "uuid",
    "screen_resolution": (1920, 1080),
    "start_time": timestamp,
    "steps_completed": [1, 2, 3, 4, 5],
    "steps_failed": [],
    "total_duration": 45.2,
    "pdf_path": "/downloads/certidao_federal_12345678000190.pdf",
    "screenshots": [
        "/screenshots/step0_page_loaded.png",
        "/screenshots/step1_cnpj_filled.png",
        ...
    ],
    "logs": "/logs/federal_pyautogui_20260227.log"
}
```

---

## 7. OCR Integration

### 7.1 Tesseract Configuration

**Library:** `pytesseract` (Python wrapper for Tesseract)

**Installation Paths:**
- Windows default: `C:\Tesseract-OCR\tesseract.exe`
- Alternate: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Environment variable: `TESSERACT_PATH`
- System PATH: Fallback if installed globally

**Language Configuration:**
- Primary: `lang='por'` (Portuguese)
- Portuguese handles accented characters (á, é, í, ó, ú, ç)

**OCR Parameters:**
```python
pytesseract.image_to_data(
    image,
    output_type=pytesseract.Output.DICT,
    lang='por'
)
```

Returns:
- `text[]`: Recognized text words
- `conf[]`: Confidence scores (0-100)
- `left[], top[], width[], height[]`: Bounding box for each word

### 7.2 Confidence Thresholds

**OCR Confidence Interpretation:**
- 100: Perfect match
- 80-99: Very confident
- 60-79: Reasonably confident
- 40-59: Uncertain, may have errors
- 0-39: Likely incorrect

**Minimum Thresholds by Use Case:**
| Use Case | Min Confidence | Reason |
|----------|---|---|
| Button text (specific) | 70% | Buttons are clear, good contrast |
| Status text ("Válida") | 70% | Important, must be accurate |
| Date text | 60% | Smaller font, acceptable error |
| Modal detection | 40% | Permissive, validate separately |
| Field labels | 50% | Permissive, many similar patterns |

**Confidence Handling:**
```
If confidence < threshold:
├─ Log warning with actual score
├─ If critical operation → Return None (trigger fallback)
└─ If informational → Continue with caution

Always filter matches below 40% (likely garbage)
```

### 7.3 Text Matching Strategy

**Matching Methods:**
1. **Exact match:** `text.lower() == target.lower()`
2. **Substring match:** `target in text or text in target` (case-insensitive)
3. **Fuzzy match:** (Future) Use difflib or fuzzywuzzy for approximate matches

**Current Strategy:** Substring matching
- "Emitir Certidão" matches both exact and "Emitir" only
- "Válida Encontrada" matches "Válida" or "Encontrada" separately
- More forgiving for OCR errors

**Multi-word Matching:**
- Break multi-word targets into components
- Search for components separately
- Require majority of words to match

**VLibras Filtering:**
- VLibras (accessibility tool) creates UI elements on screen edges
- Filter out matches in right 15% of screen (`x > screen_width * 0.85`)
- Prevents false positives from overlays

---

## 8. Chrome Browser Integration

### 8.1 Chrome Launch Configuration

**Launch Parameters:**
```
--start-maximized
  └─ Window opens full screen

--no-first-run
  └─ Skip welcome screen

--no-default-browser-check
  └─ Skip browser checks

--disable-popup-blocking
  └─ Allow popups (might be needed for certificate)

--download-directory={path}
  └─ Set downloads folder for PDF capture

--safebrowsing-disable-download-protection
  └─ Don't block downloads as "unsafe"

--safebrowsing-disable-extension-blacklist
  └─ Don't block extensions
```

**URL:** `https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj`

### 8.2 Detection and Process Management

**Process Detection:**
- On Windows, multiple Chrome processes may exist
- Parent process handle tracked for termination
- Exit codes:
  - 0: Normal exit
  - 21: Delegated to existing instance (URL opened in existing window)

**Process Lifecycle:**
1. Launch Chrome with URL
2. Wait 2 seconds for process initialization
3. Check if delegated to existing instance (exit code 21)
4. Wait additional 5 seconds for page load
5. Check page loaded with screenshot
6. Proceed with automation
7. Close process on completion (or on error)

---

## 9. Testing and Validation

### 9.1 Unit Testing Strategy

**Per-Step Tests:**
- `test_step_1_cnpj_field_detection()` - Template matching
- `test_step_1_cnpj_field_fallback()` - XY coordinates
- `test_step_1_emitir_button_detection()` - Template matching
- `test_step_2_modal_detection()` - Modal present/absent scenarios
- `test_step_3_date_page_load()` - Page confirmation
- `test_step_4_status_validation()` - Valid/Expired certificates
- `test_step_5_download_verification()` - File creation detection

**Mock Data:**
- Pre-captured screenshots for each step
- Known valid CNPJs for testing
- Expected coordinate positions

### 9.2 Integration Testing

**End-to-End Flow:**
1. Real Chrome launch
2. Real Receita Federal website
3. Real CNPJ lookup
4. Verify each step succeeds
5. Verify PDF download

**Test CNPJs:**
- Use valid public CNPJs (government, large companies)
- Avoid private/sensitive CNPJs

### 9.3 Edge Cases

**Resolution Changes:**
- Test at 1920×1080 (primary)
- Test at 1366×768 (secondary)
- Test at 1280×720 (minimum)
- Verify template scaling works

**Network Delays:**
- Slow page loads → Rely on retry logic
- Delayed results rendering → Extended timeouts

**Modal Variations:**
- Modal always appears (for certain companies)
- Modal never appears (for others)
- Both paths must be tested

**Certificate Status:**
- Valid certificate (happy path)
- Expired certificate (sad path)
- Status unknown/unreadable

**Download Scenarios:**
- PDF downloads successfully
- PDF download hangs
- Download dialog appears
- Filename conflicts

---

## 10. Deployment and Configuration

### 10.1 System Requirements

**Operating System:**
- Windows 10/11 (Primary target)
- Linux with display server (Secondary)
- macOS (Untested)

**Software Requirements:**
- Python 3.8+
- Chrome/Chromium browser
- Tesseract-OCR 5.x
- OpenCV 4.x
- PyAutoGUI 0.9.53+

**Hardware:**
- Minimum: 2 CPU cores, 4GB RAM
- Recommended: 4+ cores, 8GB RAM
- Full HD (1920×1080) display recommended
- 100 MB disk space for logs/screenshots

### 10.2 Directory Structure

```
/project-root/
├── /certificates/
│   ├── federal_pyautogui.py      (Main automation module)
│   ├── federal.py                 (Alternative implementations)
│   ├── federal_visual.py          (Visual automation class)
│   └── base.py                    (Base class)
│
├── /templates/                     (Template images)
│   ├── 1_btn_cnpj.png
│   ├── 2_btn_emitir.png
│   ├── 3_btn_consultar.png
│   ├── 4_btn_consultar.png
│   └── 5_btn_baixar.png
│
├── /core/
│   ├── visual_automation.py       (VisualAutomation class)
│   ├── logger.py
│   ├── config.py
│   └── browser.py
│
├── /downloads/                     (Downloaded PDFs)
│   └── certidao_federal_*.pdf
│
├── /screenshots/                   (Debug screenshots)
│   ├── step0_page_loaded_*.png
│   ├── step1_cnpj_filled_*.png
│   └── error_*.png
│
├── /logs/                          (Log files)
│   └── federal_pyautogui_YYYYMMDD.log
│
└── DESIGN_SYSTEM.md               (This document)
```

### 10.3 Configuration Files

**Recommended config.py structure:**
```python
# Screen/Display
SCREEN_RESOLUTION = (1920, 1080)  # Override auto-detection
MONITOR_INDEX = 0                  # For multi-monitor setups

# Timeouts (seconds)
TIMEOUT_ELEMENT_DETECTION = 30
TIMEOUT_PAGE_LOAD = 5
TIMEOUT_DOWNLOAD = 10

# OCR/CV
OCR_CONFIDENCE_MIN = 0.70
TEMPLATE_CONFIDENCE_MIN = 0.75
TESSERACT_PATH = None             # Auto-detect if None

# Paths
TEMPLATES_DIR = "./templates"
DOWNLOADS_DIR = "./downloads"
SCREENSHOTS_DIR = "./screenshots"
LOGS_DIR = "./logs"

# Humanization
HUMAN_CLICK_DURATION_MIN = 0.3
HUMAN_CLICK_DURATION_MAX = 0.6
HUMAN_DELAY_MIN = 0.5
HUMAN_DELAY_MAX = 1.5
```

---

## 11. Performance Metrics

### 11.1 Expected Timing

**Per-Step Timing (Normal Conditions):**
| Step | Min | Avg | Max | Note |
|------|-----|-----|-----|------|
| 1 | 8s | 12s | 20s | Network delay possible |
| 2 | 2s | 4s | 8s | Modal optional |
| 3 | 5s | 8s | 15s | Page load varies |
| 4 | 1s | 2s | 5s | Just scanning |
| 5 | 5s | 8s | 15s | Download time varies |
| **Total** | **21s** | **34s** | **63s** | End-to-end |

### 11.2 Success Rates

**Target Metrics:**
- CV Method Success: > 95% (when templates available)
- Fallback Success: > 90% (hardcoded coordinates)
- End-to-End Success: > 98% (with retry logic)
- False Negatives: < 1% (rare failures)

---

## 12. Security Considerations

### 12.1 Credential Handling

**CNPJ Privacy:**
- CNPJ is business public information (not secret)
- Still, avoid logging actual CNPJ values in console
- Log only: "Processing CNPJ: [MASKED]" or hash

**PDF Storage:**
- PDFs are sensitive (contain company info)
- Store in secure directory with restricted permissions
- Consider encryption for sensitive deployments
- Delete old PDFs after processing/archival

### 12.2 Detection Avoidance

**Why Avoid Detection:**
- Some websites block automated access
- Federal Revenue Service (Receita Federal) generally allows bulk queries
- PyAutoGUI is undetectable (uses OS-level mouse/keyboard)
- No WebDriver, no Selenium, no browser automation indicators

**Detection Vectors (All Mitigated):**
- WebDriver detection → Not using Selenium ✓
- Browser automation detection → OS-level controls ✓
- Unnatural mouse movements → Humanized with easing ✓
- Instant keyboard input → Randomized delays ✓
- Instant page navigation → Realistic timeouts ✓

### 12.3 Resource Limits

**To Avoid Abuse Bans:**
- Add delays between requests (currently 30-60 seconds per cert)
- Implement request throttling (max X requests per minute)
- Respect robots.txt (if applicable)
- Consider user-agent spoofing (if needed)
- Implement IP rotation (if high volume)

---

## 13. Future Enhancements

### 13.1 Planned Improvements

1. **Multi-Resolution Support**
   - Auto-scale templates for any resolution
   - Resolution-specific coordinate sets
   - Relative positioning within window

2. **Deep Learning Models**
   - Replace template matching with YOLO/Faster R-CNN
   - Improve accuracy on UI elements
   - Reduce need for manual template capture

3. **Database Integration**
   - Store results in database
   - Track certificate history per CNPJ
   - Implement caching

4. **Batch Processing**
   - Accept CNPJ list as input
   - Process multiple certificates
   - Parallel processing with rate limiting
   - Generate report at end

5. **Web Dashboard**
   - Real-time status display
   - Historical reports
   - CNPJ search interface
   - Manual PDF upload fallback

6. **Error Recovery**
   - Checkpoint system (save state between steps)
   - Resume from last successful step
   - Retry policy per step
   - Notification on repeated failures

7. **Proxy/VPN Support**
   - Route through proxy
   - IP rotation for high-volume
   - Geo-location handling

8. **Advanced Logging**
   - Structured logging (JSON)
   - Centralized log aggregation
   - Performance metrics tracking
   - Audit trail with hashing

---

## 14. Troubleshooting Guide

### 14.1 Common Issues

**Issue:** "Template not found" error
- **Cause:** Templates directory empty or file missing
- **Solution:** Run template capture mode or check file paths
- **Fallback:** System will use XY coordinates instead

**Issue:** OCR confidence too low
- **Cause:** Text rendering issues, poor contrast, non-standard font
- **Solution:** Increase confidence threshold tolerance (down to 50%)
- **Debug:** Check screenshots in `/screenshots/` directory

**Issue:** Clicks landing in wrong position
- **Cause:** Screen resolution different from 1920×1080
- **Solution:** Scale coordinates using formula in Section 5.1
- **Debug:** Enable screenshot on every click

**Issue:** Page never completes loading
- **Cause:** Network issue, website down, session expired
- **Solution:** Increase timeout values, retry
- **Debug:** Check Chrome console for errors

**Issue:** PDF not found after download
- **Cause:** Browser dialog appeared, different download folder, file name changed
- **Solution:** Check actual download folder, verify browser settings
- **Debug:** List files in downloads folder with timestamps

**Issue:** Modal button click has no effect
- **Cause:** Modal still loading, element not visible, overlay blocking
- **Solution:** Increase delay, press Escape to close modal, take screenshot
- **Debug:** Compare actual position with expected bounding box

### 14.2 Debug Mode

**Enable detailed logging:**
```python
cert = FederalPyAutoGUI(cnpj)
cert.logger.setLevel(logging.DEBUG)  # Enable debug logs
cert.run()
```

**Save screenshots for every action:**
```python
# Automatically takes screenshots of each step
# Check /screenshots/ folder after run
```

**Inspect templates:**
```python
cert = FederalPyAutoGUI(cnpj)
cert.log(f"Templates found: {list(cert.templates_dir.glob('*.png'))}")
```

---

## Appendix A: Configuration Quick Reference

```ini
[Screen]
Width = 1920
Height = 1080

[Timeouts]
ElementDetection = 30       ; seconds
PageLoad = 5                ; seconds
Download = 10               ; seconds

[OCR]
MinConfidence = 0.70        ; 70%
Language = por              ; Portuguese
TesseractPath = auto        ; Auto-detect

[CV]
TemplateConfidence = 0.75   ; 75%
Method = TM_CCOEFF_NORMED

[Humanization]
ClickDuration = 0.3-0.6     ; seconds
Delay = 0.5-1.5             ; seconds
TypingInterval = 0.05-0.15  ; seconds

[Coordinates]
; All coordinates for 1920×1080 resolution
CnpjButton = 376, 478
EmitirButton = 1449, 681
ModalConsultar = 983, 640
DatesConsultar = 1433, 854
DownloadButton = 1488, 578

[Paths]
TemplatesDir = ./templates
DownloadsDir = ./downloads
ScreenshotsDir = ./screenshots
LogsDir = ./logs
```

---

## Appendix B: Step-by-Step Checklist

**Before Running Automation:**
- [ ] Chrome installed and accessible
- [ ] Tesseract-OCR installed (or configured in PATH)
- [ ] Templates directory populated or empty (graceful fallback)
- [ ] Downloads directory exists and writable
- [ ] Valid CNPJ number available
- [ ] Sufficient disk space for PDFs and logs

**Running Automation:**
- [ ] User aware automation will control mouse for ~30-60 seconds
- [ ] Mouse position at neutral location (not interfering)
- [ ] Internet connection stable
- [ ] Receita Federal website accessible
- [ ] No other applications using mouse/keyboard

**After Automation Completes:**
- [ ] Check PDF in downloads folder
- [ ] Verify PDF file size > 0 KB
- [ ] Check logs in `/logs/` for errors
- [ ] Review screenshots in `/screenshots/` if issues occurred
- [ ] Verify certificate content (page 1-2 visible)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-27 | Initial system design specification |

---

**Document Maintainer:** Certificate Collector Team
**Last Updated:** February 27, 2026
**Status:** APPROVED FOR IMPLEMENTATION
