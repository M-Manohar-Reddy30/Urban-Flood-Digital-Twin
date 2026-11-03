from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data/raw/dem"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com"

TILES = [
    "Copernicus_DSM_COG_10_N15_00_E077_00_DEM",
    "Copernicus_DSM_COG_10_N14_00_E076_00_DEM",
    "Copernicus_DSM_COG_10_N14_00_E077_00_DEM",
]


def download_tile(tile):
    url = f"{BASE}/{tile}/{tile}.tif"
    output = OUTPUT_DIR / f"{tile}.tif"
    temporary = OUTPUT_DIR / f"{tile}.tif.part"

    if output.exists() and output.stat().st_size > 0:
        print("Already exists:", output.name)
        return

    print(f"\nDownloading: {tile}")

    for attempt in range(1, 4):
        try:
            request = Request(
                url,
                headers={"User-Agent": "Ballari-Urban-Flood-Research/1.0"}
            )

            total = 0

            with urlopen(request, timeout=120) as response:
                with open(temporary, "wb") as file:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        file.write(chunk)
                        total += len(chunk)

                        print(
                            f"\rDownloaded: {total / (1024 * 1024):.2f} MB",
                            end="",
                            flush=True,
                        )

            if total == 0:
                raise RuntimeError("Downloaded file is empty.")

            temporary.replace(output)

            print(f"\nSaved: {output}")
            print(f"Size: {total / (1024 * 1024):.2f} MB")
            return

        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            temporary.unlink(missing_ok=True)
            print(f"\nAttempt {attempt}/3 failed: {exc}")

            if attempt < 3:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to download {tile}")


def main():
    for tile in TILES:
        download_tile(tile)

    print("\nAll requested Copernicus tiles downloaded.")


if __name__ == "__main__":
    main()
