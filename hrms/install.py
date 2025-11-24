import click

from hrms.setup import after_install as setup


def after_install():
	try:
		print("Setting up UO HR System...")
		setup()

		click.secho("Thank you for installing UO HR! 株式会社UO人力资源管理系统安装成功！", fg="green")

	except Exception as e:
		BUG_REPORT_URL = "https://github.com/uo/hrms/issues/new"
		click.secho(
			"Installation for UO HR app failed due to an error."
			" Please try re-installing the app or"
			f" report the issue on {BUG_REPORT_URL} if not resolved.",
			fg="bright_red",
		)
		raise e
