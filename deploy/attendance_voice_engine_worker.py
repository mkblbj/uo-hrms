#!/usr/bin/env python3
"""Host-only lease reconciler. Fixed Compose services; no socket, shell or arbitrary jobs."""

import argparse
import json
import logging
import signal
import subprocess
import time
from pathlib import Path


class EngineWorker:
	def __init__(self, roots, compose, gpu=True, runner=None):
		self.roots = [Path(p) for p in roots]
		self.compose = str(compose)
		self.mode = "gpu" if gpu else "cpu"
		self.runner = runner or (
			lambda cmd: subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, timeout=120)
		)
		self.started = {}
		self.initial = True

	def command(self, action, service):
		self.runner(
			[
				"docker",
				"compose",
				"-f",
				self.compose,
				"--profile",
				service.rsplit("-", 1)[-1],
				*action,
				service,
			]
		)

	def tick(self, now=None):
		now = time.time() if now is None else now
		desired = set()
		for root in self.roots:
			for path in root.glob("*/private/attendance-voice-settings/engine-lease.json"):
				try:
					data = json.loads(path.read_text())
					if (
						data.get("engine") in ("nemo", "voicevox")
						and now < float(data.get("expires_at", 0)) <= now + 120
					):
						desired.add(data["engine"])
				except (OSError, ValueError, TypeError):
					continue
		if self.initial:
			# Recover engines from a previous worker run even when its lease expired.
			for engine in ("nemo", "voicevox"):
				if engine not in desired:
					for mode in ("gpu", "cpu"):
						self.command(["stop"], engine + "-" + mode)
			self.initial = False
		for engine in desired:
			if engine not in self.started:
				service = engine + "-" + self.mode
				self.command(["up", "-d"], service)
				self.started[engine] = service
		for engine in list(self.started):
			if engine not in desired:
				self.command(["stop"], self.started.pop(engine))

	def shutdown(self):
		for engine in list(self.started):
			self.command(["stop"], self.started.pop(engine))


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--sites-root", action="append", required=True)
	parser.add_argument("--compose", required=True)
	parser.add_argument("--cpu", action="store_true")
	args = parser.parse_args()
	worker = EngineWorker(args.sites_root, Path(args.compose).resolve(), gpu=not args.cpu)
	signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(0)))
	try:
		while True:
			try:
				worker.tick()
			except (OSError, subprocess.SubprocessError):
				logging.exception("Attendance voice engine reconciliation failed")
			time.sleep(2)
	finally:
		worker.shutdown()


if __name__ == "__main__":
	main()
