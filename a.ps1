# cleanup-deleted-files.ps1
# Removes all files that were deleted in previous git commits but may still
# exist in the Docker build context or working tree.
# Run from the backend/ directory: .\cleanup-deleted-files.ps1

$ErrorActionPreference = "SilentlyContinue"

$files = @(
    # -----------------------------------------------------------------------
    # app — alembic (entire migration history removed)
    # -----------------------------------------------------------------------
    "app\alembic.ini"
    "app\src\alembic\__init__.py"
    "app\src\alembic\env.py"
    "app\src\alembic\script.py.mako"
    "app\src\alembic\versions\__init__.py"
    "app\src\alembic\versions\001_initial_schema.py"
    "app\src\alembic\versions\002_performance_indexes.py"
    "app\src\alembic\versions\003_missing_columns.py"
    "app\src\alembic\versions\004_persona_rename.py"
    "app\src\alembic\versions\005_customer.py"
    "app\src\alembic\versions\006_schema_refactor.py"
    "app\src\alembic\versions\007_model_fixes.py"

    # -----------------------------------------------------------------------
    # app — docs
    # -----------------------------------------------------------------------
    "app\docs\orm_01_rbac.mmd"
    "app\docs\orm_02_tenant.mmd"
    "app\docs\orm_03_venue.mmd"
    "app\docs\orm_04_menu.mmd"
    "app\docs\orm_05_orders.mmd"
    "app\docs\orm_06_commerce.mmd"
    "app\docs\orm_diagram.mmd"
    "app\docs\schema_diagram.mmd"

    # -----------------------------------------------------------------------
    # app — routes
    # -----------------------------------------------------------------------
    "app\src\application\routes\Coupons.py"
    "app\src\application\routes\Menu.py"
    "app\src\application\routes\Organizations.py"

    # -----------------------------------------------------------------------
    # app — services
    # -----------------------------------------------------------------------
    "app\src\application\services\Coupon.py"
    "app\src\application\services\HomePage.py"
    "app\src\application\services\Organization.py"
    "app\src\application\services\Permission.py"

    # -----------------------------------------------------------------------
    # app — models
    # -----------------------------------------------------------------------
    "app\src\models\Coupon.py"
    "app\src\models\HomePageInfo.py"

    # -----------------------------------------------------------------------
    # app — repositories
    # -----------------------------------------------------------------------
    "app\src\repositories\CouponRepository.py"
    "app\src\repositories\HomePageInfoRepository.py"
    "app\src\repositories\OrganizationRepository.py"

    # -----------------------------------------------------------------------
    # app — schemas
    # -----------------------------------------------------------------------
    "app\src\schemas\ApplicationUser.py"
    "app\src\schemas\Coupon.py"
    "app\src\schemas\Organization.py"

    # -----------------------------------------------------------------------
    # app — base
    # -----------------------------------------------------------------------
    "app\src\base\BaseUser.py"

    # -----------------------------------------------------------------------
    # system — alembic (stale migration files)
    # -----------------------------------------------------------------------
    "system\src\alembic\versions\002_performance_indexes.py"
    "system\src\alembic\versions\003_persona_rename.py"

    # -----------------------------------------------------------------------
    # system — docs
    # -----------------------------------------------------------------------
    "system\docs\orm_01_rbac.mmd"
    "system\docs\orm_02_users.mmd"
    "system\docs\orm_03_tenant.mmd"
    "system\docs\orm_04_registration_content.mmd"
    "system\docs\orm_diagram.mmd"

    # -----------------------------------------------------------------------
    # system — routes / services
    # -----------------------------------------------------------------------
    "system\src\system\routes\Registration.py"
    "system\src\system\routes\Settings.py"
    "system\src\system\services\Settings.py"

    # -----------------------------------------------------------------------
    # system — models
    # -----------------------------------------------------------------------
    "system\src\models\HomePageInfo.py"
    "system\src\models\SystemUser.py"

    # -----------------------------------------------------------------------
    # system — repositories
    # -----------------------------------------------------------------------
    "system\src\repositories\HomePageInfoRepository.py"
    "system\src\repositories\OrganizationRepository.py"

    # -----------------------------------------------------------------------
    # system — schemas
    # -----------------------------------------------------------------------
    "system\src\schemas\HomePageInfo.py"

    # -----------------------------------------------------------------------
    # system — base / core
    # -----------------------------------------------------------------------
    "system\src\base\BaseUser.py"
    "system\src\core\Initializer.py"
)

$dirs = @(
    "app\src\alembic\versions"
    "app\src\alembic"
    "app\docs"
    "system\docs"
)

$deleted = 0
$skipped = 0

Write-Host ""
Write-Host "Cleaning up files deleted in previous commits..." -ForegroundColor Cyan
Write-Host ""

foreach ($file in $files) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        Write-Host "  deleted  $file" -ForegroundColor Red
        $deleted++
    } else {
        Write-Host "  skipped  $file" -ForegroundColor DarkGray
        $skipped++
    }
}

Write-Host ""
Write-Host "Cleaning up empty directories..." -ForegroundColor Cyan
Write-Host ""

foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        $items = Get-ChildItem $dir -Recurse -Force
        if ($null -eq $items -or $items.Count -eq 0) {
            Remove-Item $dir -Recurse -Force
            Write-Host "  removed  $dir" -ForegroundColor Red
        } else {
            Write-Host "  kept     $dir (not empty)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  skipped  $dir (does not exist)" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Done. $deleted file(s) deleted, $skipped already absent." -ForegroundColor Green
Write-Host ""
