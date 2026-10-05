# ============================================================
# Todards Daily Update
# ============================================================

$projectPath = "D:\DS\todards"

# Activate/locate Python environment
$pythonPath = "D:\DS\environments\ml-global\python.exe"

# Move to project root
Set-Location $projectPath

# Today's date for Git commit
$today = Get-Date -Format "dd-MM-yyyy"

Write-Host ""
Write-Host "============================================"
Write-Host "TODARDS DAILY UPDATE"
Write-Host "Date: $today"
Write-Host "============================================"
Write-Host ""

# ============================================================
# 1. RUN MAIN PYTHON PIPELINE
# ============================================================

Write-Host "========== RUNNING MAIN.PY =========="
Write-Host ""

& $pythonPath main.py

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "ERROR: main.py failed."
    Write-Host "Git operations will NOT be executed."
    Write-Host ""

    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "main.py completed successfully."
Write-Host ""


# ============================================================
# 2. GIT ADD
# ============================================================

Write-Host "========== GIT ADD =========="
Write-Host ""

git add .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: git add failed."
    exit $LASTEXITCODE
}


# ============================================================
# 3. GIT COMMIT
# ============================================================

Write-Host ""
Write-Host "========== GIT COMMIT =========="
Write-Host ""

git commit -m "$today"

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "No changes to commit, or git commit failed."
    Write-Host ""

    # Do not push if commit failed.
    exit $LASTEXITCODE
}


# ============================================================
# 4. GIT PUSH
# ============================================================

Write-Host ""
Write-Host "========== GIT PUSH =========="
Write-Host ""

git push -u origin main

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "ERROR: git push failed."
    exit $LASTEXITCODE
}


# ============================================================
# COMPLETE
# ============================================================

Write-Host ""
Write-Host "============================================"
Write-Host "TODARDS DAILY UPDATE COMPLETED"
Write-Host "Date: $today"
Write-Host "============================================"
Write-Host ""