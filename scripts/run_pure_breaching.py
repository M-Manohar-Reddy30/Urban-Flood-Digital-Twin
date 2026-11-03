from pathlib import Path
from whitebox import WhiteboxTools

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/processed/hydrology/conditioning/ballari_dem_whitebox_input.tif"
OUTPUT = ROOT / "data/processed/hydrology/conditioning/ballari_dem_pure_breached.tif"

wbt = WhiteboxTools()
wbt.set_verbose_mode(True)

result = wbt.breach_depressions_least_cost(
    dem=str(SOURCE),
    output=str(OUTPUT),
    dist=100,
    min_dist=True,
    fill=False
)

print("\nReturn code:", result)
print("Output exists:", OUTPUT.exists())

if result != 0 or not OUTPUT.exists():
    raise RuntimeError("Pure breaching failed.")

print("Pure breaching completed successfully.")
