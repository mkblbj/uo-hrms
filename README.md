<div align="center">
	<a href="https://uo.co.jp/hr">
		<img src=".github/uo-hr-logo.png" height="80px" width="80px" alt="UO HR Logo">
	</a>
	<h2>UO HR - 人力资源管理系统</h2>
	<p align="center">
		<p>株式会社UO专属的现代化人力资源和薪资管理系统</p>
	</p>
</div>

<div align="center">
	<img src=".github/hrms-hero.png"/>
</div>

<div align="center">
	<a href="https://frappe.io/hr">Website</a>
	-
	<a href="https://docs.frappe.io/hr/introduction">Documentation</a>
</div>

## UO HR 人力资源管理系统

UO HR 是株式会社UO定制开发的完整人力资源管理解决方案，包含员工管理、入职管理、请假、薪资、税务等13个以上的模块。

## 项目说明
本系统基于 Frappe HR 进行二次开发，针对株式会社UO的业务需求进行了深度定制和优化，确保符合日本劳动法规和公司管理流程。

## Key Features

- **Employee Lifecycle**: From onboarding employees, managing promotions and transfers, all the way to documenting feedback with exit interviews, make life easier for employees throughout their life cycle.
- **Leave and Attendance**: Configure leave policies, pull regional holidays with a click, check-in and check-out with geolocation capturing, track leave balances and attendance with reports.
- **Expense Claims and Advances**: Manage employee advances, claim expenses, configure multi-level approval workflows, all this with seamless integration with ERPNext accounting.
- **Performance Management**: Track goals, align goals with key result areas (KRAs), enable employees to evaluate themselves, make managing appraisal cycles easy.
- **Payroll & Taxation**: Create salary structures, configure income tax slabs, run standard payroll, accomodate additional salaries and off cycle payments, view income breakup on salary slips and so much more.
- **UO HR Mobile App**: 移动端申请和审批请假，打卡签到/签退，随时访问员工档案。

<details open>

<summary>View Screenshots</summary>
	<img src=".github/hrms-appraisal.png"/>
	<img src=".github/hrms-requisition.png"/>
	<img src=".github/hrms-attendance.png"/>
	<img src=".github/hrms-salary.png"/>
	<img src=".github/hrms-pwa.png"/>
</details>

### Under the Hood

- [**Frappe Framework**](https://github.com/frappe/frappe): A full-stack web application framework written in Python and Javascript. The framework provides a robust foundation for building web applications, including a database abstraction layer, user authentication, and a REST API.

- [**Frappe UI**](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface. The Frappe UI library provides a variety of components that can be used to build single-page applications on top of the Frappe Framework.

## Production Setup

### 部署说明

本系统为株式会社UO内部使用，采用 Docker 容器化部署方案。


## 开发环境搭建
### Docker 部署
需要安装 Docker、docker-compose 和 git。参考 [Docker 文档](https://docs.docker.com/)。安装完成后执行：
```bash
cd /home/uo/dev/hrms/docker
docker-compose up
```

等待安装脚本创建站点后，可以通过浏览器访问 `http://localhost:8000`。

登录凭据：
- 用户名: `Administrator`
- 密码: `admin`

### 本地开发环境

1. 按照 [安装步骤](https://frappeframework.com/docs/user/en/installation) 设置 bench 并启动服务器
	```sh
	$ bench start
	```
2. 在另一个终端窗口执行：
	```sh
	$ bench new-site hrms.localhost
	$ bench get-app erpnext
	$ bench get-app hrms
	$ bench --site hrms.localhost install-app hrms
	$ bench --site hrms.localhost add-to-hosts
	```
3. 访问 `http://hrms.localhost:8080`

## 技术支持

如有问题或需要技术支持，请联系：
- 邮箱: hr@uo.co.jp
- 内部文档: 参考公司内网文档中心

## 安全与隐私

本系统涉及员工敏感信息，请严格遵守公司信息安全政策。如发现安全漏洞，请立即报告至 security@uo.co.jp。

<br />
<br />
<div align="center" style="padding-top: 0.75rem;">
	<p>© 2025 株式会社UO. All Rights Reserved.</p>
	<p>基于 <a href="https://github.com/frappe/hrms">Frappe HR</a> 进行二次开发</p>
</div>

