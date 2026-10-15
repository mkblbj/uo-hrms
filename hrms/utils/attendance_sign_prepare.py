"""Run on demand on the server: CSV -> Nemo HTTP -> validated WAV bundle."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from hrms.utils.attendance_sign_audio import validate_wav, write_bundle


def _request(url: str, payload: bytes | None = None, *, post: bool = False) -> bytes:
	request = Request(url, data=payload, method="POST" if post else "GET")
	if payload is not None:
		request.add_header("Content-Type", "application/json")
	with urlopen(request, timeout=60) as response:
		return response.read()


def prepare_bundle(csv_path, output_dir, engine_url: str, speaker_id: int, speed: float = 1.0) -> dict:
	if not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
		raise ValueError("Speed must be between 0.5 and 2.0")
	with Path(csv_path).open(encoding="utf-8-sig", newline="") as stream:
		reader = csv.DictReader(stream)
		if not {"employee_id", "employee_name", "spoken_name"}.issubset(reader.fieldnames or []):
			raise ValueError("CSV requires employee_id,employee_name,spoken_name")
		rows = []
		seen = set()
		for row in reader:
			row = {
				key: (row.get(key) or "").strip() for key in ("employee_id", "employee_name", "spoken_name")
			}
			if not all(row.values()) or row["employee_id"] in seen:
				raise ValueError("Every employee needs a unique ID, display name and confirmed spoken name")
			seen.add(row["employee_id"])
			rows.append(row)
	if not rows:
		raise ValueError("CSV has no employees")
	engine_url = engine_url.rstrip("/")
	speakers = json.loads(_request(engine_url + "/speakers"))
	voice = next(
		((s["name"], style["name"]) for s in speakers for style in s["styles"] if style["id"] == speaker_id),
		None,
	)
	if voice is None:
		raise ValueError("Speaker ID is not available in this Nemo engine")
	manifest = {
		"version": 1,
		"locale": "ja-JP",
		"source": {
			"engine": "VOICEVOX Nemo",
			"speaker_id": speaker_id,
			"voice": " / ".join(voice),
			"credit": "VOICEVOX Nemo",
		},
		"clips": {},
	}
	assets = {}
	for row in rows:
		spoken = row["spoken_name"]
		if spoken.endswith("さん"):
			spoken = spoken[:-2]
		clips = {}
		for kind, greeting in (("IN", "出勤を記録しました。"), ("OUT", "お疲れさまでした。")):
			text = f"{spoken}さん、{greeting}"
			query = json.loads(
				_request(
					engine_url + "/audio_query?" + urlencode({"speaker": speaker_id, "text": text}), post=True
				)
			)
			query.update(outputSamplingRate=16000, outputStereo=False, speedScale=speed)
			data = _request(
				engine_url + "/synthesis?" + urlencode({"speaker": speaker_id}),
				json.dumps(query).encode(),
				post=True,
			)
			validate_wav(data)
			asset_id = hashlib.sha256(data).hexdigest()
			assets[asset_id] = data
			clips[kind] = {"employee_name": row["employee_name"], "asset_id": asset_id}
		manifest["clips"][row["employee_id"]] = clips
	write_bundle(Path(output_dir), manifest, assets)
	return manifest


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--input-csv", required=True)
	parser.add_argument("--output", required=True)
	parser.add_argument("--engine-url", default="http://127.0.0.1:50121")
	parser.add_argument("--speaker-id", required=True, type=int)
	parser.add_argument("--speed", type=float, default=1.0)
	args = parser.parse_args()
	result = prepare_bundle(args.input_csv, args.output, args.engine_url, args.speaker_id, args.speed)
	print(json.dumps({"employees": len(result["clips"]), "source": result["source"]}, ensure_ascii=False))


if __name__ == "__main__":
	main()
